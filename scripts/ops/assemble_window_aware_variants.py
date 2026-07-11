import hashlib
import json
import math
from pathlib import Path
from collections import defaultdict

IN_DIR = Path('artifacts/enc3/io_dense_dumps')
OUT_DIR = Path('artifacts/enc3/window_aware')
OUT_DIR.mkdir(parents=True, exist_ok=True)

MIN_OVERLAP = 512
MAX_OVERLAP = 2048
BLOCK = 512


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


def headers(data: bytes):
    sigs = [
        ('MZ', b'MZ'),
        ('PK', b'PK\x03\x04'),
        ('ENC3', b'ENC3'),
        ('GZIP', b'\x1f\x8b\x08'),
        ('ZLIB_78', b'\x78'),
    ]
    out = []
    for n, s in sigs:
        p = data.find(s)
        if p != -1:
            out.append({'name': n, 'offset': p})
    out.sort(key=lambda x: x['offset'])
    return out


def find_best_overlap(a: bytes, b: bytes, min_ov=MIN_OVERLAP, max_ov=MAX_OVERLAP):
    max_len = min(max_ov, len(a), len(b))
    for ov in range(max_len, min_ov - 1, -1):
        if a[-ov:] == b[:ov]:
            return ov
    return 0


def merge_overlap(chunks):
    if not chunks:
        return b'', []
    cur = bytes(chunks[0])
    ops = [{'action': 'seed', 'size': len(cur)}]
    for ch in chunks[1:]:
        ov = find_best_overlap(cur, ch)
        if ov > 0:
            cur += ch[ov:]
            ops.append({'action': 'merge_overlap', 'overlap': ov, 'append': len(ch) - ov})
        else:
            cur += ch
            ops.append({'action': 'append_raw', 'append': len(ch)})
    return cur, ops


def dedup_chunks(chunks):
    seen = set()
    out = []
    for ch in chunks:
        h = hashlib.sha1(ch, usedforsecurity=False).hexdigest()
        if h in seen:
            continue
        seen.add(h)
        out.append(ch)
    return out


def dedup_blocks(stream: bytes, block=BLOCK):
    seen = set()
    out = bytearray()
    for i in range(0, len(stream), block):
        part = stream[i:i+block]
        if not part:
            continue
        h = hashlib.sha1(part, usedforsecurity=False).hexdigest()
        if h in seen:
            continue
        seen.add(h)
        out += part
    return bytes(out)


files = sorted([p for p in IN_DIR.glob('*.bin')], key=lambda p: p.stat().st_mtime)
entries = []
chunks = []
for p in files:
    b = p.read_bytes()
    kind = p.stem.split('-')[0] if '-' in p.stem else p.stem
    entries.append({'file': str(p).replace('\\', '/'), 'size': len(b), 'kind': kind, 'mtime': p.stat().st_mtime})
    chunks.append((p, b, kind))

by_kind = defaultdict(list)
for p, b, k in chunks:
    by_kind[k].append(b)

variants = {}
meta = {}

# V1: raw time concat
v1 = b''.join(b for _, b, _ in chunks)
variants['v1_time_concat'] = v1
meta['v1_time_concat'] = {'desc': 'raw time-ordered concatenation'}

# V2: time + dedup chunk + overlap merge
v2_chunks = dedup_chunks([b for _, b, _ in chunks])
v2, v2_ops = merge_overlap(v2_chunks)
variants['v2_time_dedup_overlap'] = v2
meta['v2_time_dedup_overlap'] = {'desc': 'time order, exact chunk dedup, overlap merge', 'ops': v2_ops[:120]}

# V3: by-kind then overlap merge per kind, then merge groups
kind_streams = []
for k in sorted(by_kind.keys()):
    ks, _ = merge_overlap(dedup_chunks(by_kind[k]))
    kind_streams.append(ks)
v3, v3_ops = merge_overlap(kind_streams)
variants['v3_kind_group_overlap'] = v3
meta['v3_kind_group_overlap'] = {'desc': 'group by kind then overlap merge', 'ops': v3_ops[:120]}

# V4: MZ-anchored neighborhood stream (chunks around first MZ-containing chunk)
mz_idx = None
for i, (_, b, _) in enumerate(chunks):
    if b.find(b'MZ') != -1:
        mz_idx = i
        break
if mz_idx is None:
    sel = [b for _, b, _ in chunks]
else:
    lo = max(0, mz_idx - 6)
    hi = min(len(chunks), mz_idx + 7)
    sel = [chunks[i][1] for i in range(lo, hi)]
v4, v4_ops = merge_overlap(dedup_chunks(sel))
variants['v4_mz_anchor_window'] = v4
meta['v4_mz_anchor_window'] = {'desc': 'window around first chunk containing MZ', 'ops': v4_ops[:120], 'anchor_index': mz_idx}

# V5: block-level dedup from v2
v5 = dedup_blocks(v2, BLOCK)
variants['v5_block_dedup_512'] = v5
meta['v5_block_dedup_512'] = {'desc': '512-byte block dedup over v2 stream'}

summary = {
    'input_count': len(files),
    'input_total': sum(e['size'] for e in entries),
    'variants': {},
    'entries': entries,
}

for name, blob in variants.items():
    fp = OUT_DIR / f'{name}.bin'
    fp.write_bytes(blob)
    summary['variants'][name] = {
        'file': str(fp).replace('\\', '/'),
        'size': len(blob),
        'entropy': round(entropy(blob), 4) if blob else 0.0,
        'headers': headers(blob[:262144]) if blob else [],
        **meta.get(name, {}),
    }

json_path = OUT_DIR / 'window-aware-assembly-summary.json'
md_path = OUT_DIR / 'window-aware-assembly-summary.md'
json_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')

md = ['# Window Aware Assembly', '']
md.append(f"- Input chunks: {summary['input_count']}")
md.append(f"- Input bytes: {summary['input_total']}")
md.append('')
md.append('## Variants')
for name, v in summary['variants'].items():
    hs = ', '.join(f"{h['name']}@{h['offset']}" for h in v.get('headers', [])) or 'none'
    md.append(f"- {name}: size={v['size']} entropy={v['entropy']} headers={hs} -> {v['file']}")
md_path.write_text('\n'.join(md), encoding='utf-8')

print(json.dumps({
    'json': str(json_path).replace('\\', '/'),
    'md': str(md_path).replace('\\', '/'),
    'variants': {k: {'size': v['size'], 'headers': v['headers']} for k, v in summary['variants'].items()}
}, indent=2))
