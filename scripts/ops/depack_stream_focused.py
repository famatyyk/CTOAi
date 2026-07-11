import json
import math
import zlib
from pathlib import Path

INP = Path('artifacts/enc3/kingsvale-ntreadfile-stream-assembled-append.bin')
OUT_DIR = Path('artifacts/enc3/depack')
OUT_DIR.mkdir(parents=True, exist_ok=True)
JSON_OUT = OUT_DIR / 'depack-stream-focused-summary.json'
MD_OUT = OUT_DIR / 'depack-stream-focused-summary.md'
MAX_WRITE = 8 * 1024 * 1024


def entropy(data: bytes) -> float:
    if not data:
        return 0.0
    cnt = [0] * 256
    for b in data:
        cnt[b] += 1
    n = float(len(data))
    h = 0.0
    for c in cnt:
        if c:
            p = c / n
            h -= p * math.log2(p)
    return h


def printable_ratio(data: bytes) -> float:
    if not data:
        return 0.0
    p = sum(1 for b in data if 32 <= b <= 126 or b in (9, 10, 13))
    return p / len(data)


def detect_magic(data: bytes):
    sigs = [('MZ', b'MZ'), ('PK', b'PK\x03\x04'), ('ENC3', b'ENC3'), ('GZIP', b'\x1f\x8b\x08')]
    hits = []
    for name, sig in sigs:
        off = data.find(sig)
        if off != -1:
            hits.append({'name': name, 'offset': off})
    return hits


def score_blob(data: bytes):
    h = entropy(data)
    p = printable_ratio(data)
    m = detect_magic(data[:65536])
    s = 0
    if m:
        s += 35
    if 4.5 <= h <= 7.8:
        s += 20
    elif h > 7.8:
        s += 10
    if p > 0.05:
        s += 10
    if len(data) > 2048:
        s += 10
    if data.count(0) / len(data) < 0.95:
        s += 5
    return s, round(h,4), round(p,4), m


def xor_data(data: bytes, k: int) -> bytes:
    if k == 0:
        return data
    return bytes(b ^ k for b in data)


def zlib_head_offsets(data: bytes, limit: int = 65536):
    heads = (b'\x78\x01', b'\x78\x9c', b'\x78\xda')
    offs = {0}
    n = min(len(data)-2, limit)
    for i in range(max(0, n)):
        if data[i:i+2] in heads:
            offs.add(i)
    return offs


if not INP.exists():
    raise SystemExit(f'missing {INP}')

data = INP.read_bytes()

# Focused offsets: detected known hits + nearby windows + early zlib markers
base = {55, 18851}
for b in list(base):
    for d in (-128, -64, -32, -16, -8, 0, 8, 16, 32, 64, 128):
        o = b + d
        if 0 <= o < len(data)-8:
            base.add(o)
base |= {o for o in zlib_head_offsets(data, 131072) if o < 262144}
offsets = sorted(base)

transforms = [
    ('id', 0),
    ('xor_20', 0x20),
    ('xor_ff', 0xFF),
]

hits = []
for off in offsets:
    src = data[off:]
    for tname, key in transforms:
        payload = xor_data(src, key)
        for method, wbits in [('zlib', None), ('zlib_raw', -15), ('zlib_gzip', 31)]:
            try:
                if wbits is None:
                    dec = zlib.decompress(payload)
                else:
                    dec = zlib.decompress(payload, wbits=wbits)
            except zlib.error:
                continue
            if not dec:
                continue
            score, ent, pr, magic = score_blob(dec)
            out_name = f'stream-focused-off{off:06d}-{tname}-{method}.bin'
            out_file = OUT_DIR / out_name
            out_file.write_bytes(dec[:MAX_WRITE])
            hits.append({
                'offset': off,
                'transform': tname,
                'method': method,
                'out_size': len(dec),
                'score': score,
                'entropy': ent,
                'printable_ratio': pr,
                'magic': magic,
                'file': str(out_file).replace('\\','/'),
            })

hits.sort(key=lambda x: (x['score'], x['out_size']), reverse=True)
summary = {
    'input': str(INP).replace('\\','/'),
    'input_size': len(data),
    'offset_count': len(offsets),
    'transform_count': len(transforms),
    'hits': len(hits),
    'top': hits[:20],
}
JSON_OUT.write_text(json.dumps(summary, indent=2), encoding='utf-8')

md = ['# Focused Depack Summary', '', f"- Input: {summary['input']}", f"- Input size: {summary['input_size']}", f"- Offset count: {summary['offset_count']}", f"- Hits: {summary['hits']}", '', '## Top Hits']
for h in summary['top'][:10]:
    mg = ', '.join(f"{m['name']}@{m['offset']}" for m in h.get('magic', [])) or 'none'
    md.append(f"- score={h['score']} size={h['out_size']} off={h['offset']} transform={h['transform']} method={h['method']} ent={h['entropy']} magic={mg} -> {h['file']}")
MD_OUT.write_text('\n'.join(md), encoding='utf-8')

print(json.dumps({'hits': summary['hits'], 'top1': summary['top'][0] if summary['top'] else None, 'json': str(JSON_OUT).replace('\\','/'), 'md': str(MD_OUT).replace('\\','/')}, indent=2))
