import json
import math
import zlib
from pathlib import Path

INPS = [
    Path('artifacts/enc3/kingsvale-ntreadfile-stream-assembled-offset.bin'),
    Path('artifacts/enc3/kingsvale-ntreadfile-stream-assembled-append.bin'),
]
OUT = Path('artifacts/enc3/depack/depack-stream-compare.json')


def entropy(data: bytes) -> float:
    if not data:
        return 0.0
    c = [0] * 256
    for b in data:
        c[b] += 1
    n = float(len(data))
    h = 0.0
    for x in c:
        if x:
            p = x / n
            h -= p * math.log2(p)
    return h


def scan_offsets(data: bytes, limit=262144):
    heads = (b'\x78\x01', b'\x78\x9c', b'\x78\xda')
    n = min(len(data) - 2, limit)
    offs = [0]
    for i in range(max(0, n)):
        if data[i:i+2] in heads:
            offs.append(i)
    for sig in (b'MZ', b'PK\x03\x04'):
        p = data.find(sig)
        if p != -1:
            offs.append(p)
    return sorted(set(o for o in offs if 0 <= o < len(data)-8))[:600]


def magic(data: bytes):
    hits = []
    for n, s in [('MZ', b'MZ'), ('PK', b'PK\x03\x04'), ('ENC3', b'ENC3')]:
        p = data.find(s)
        if p != -1:
            hits.append({'name': n, 'offset': p})
    return hits


def score(data: bytes):
    h = entropy(data)
    s = 0
    if magic(data[:65536]):
        s += 35
    if 4.5 <= h <= 7.8:
        s += 20
    elif h > 7.8:
        s += 10
    if len(data) > 2048:
        s += 10
    return s, round(h, 4)


summary = {'runs': []}
for inp in INPS:
    if not inp.exists():
        summary['runs'].append({'input': str(inp).replace('\\','/'), 'error': 'missing'})
        continue
    data = inp.read_bytes()
    offs = scan_offsets(data)
    hits = []
    for off in offs:
        payload = data[off:]
        for method, wbits in [('zlib', None), ('zlib_raw', -15), ('zlib_gzip', 31)]:
            try:
                dec = zlib.decompress(payload) if wbits is None else zlib.decompress(payload, wbits=wbits)
            except Exception:
                continue
            if not dec:
                continue
            sc, ent = score(dec)
            hits.append({'offset': off, 'method': method, 'out_size': len(dec), 'score': sc, 'entropy': ent, 'magic': magic(dec[:65536])})
    hits.sort(key=lambda x: (x['score'], x['out_size']), reverse=True)
    summary['runs'].append({
        'input': str(inp).replace('\\','/'),
        'size': len(data),
        'offset_count': len(offs),
        'hits': len(hits),
        'top': hits[:10],
    })

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(summary, indent=2), encoding='utf-8')
print(json.dumps({'out': str(OUT).replace('\\','/'), 'runs': [{k:v for k,v in r.items() if k in ('input','hits','offset_count','size')} for r in summary['runs']]}, indent=2))
