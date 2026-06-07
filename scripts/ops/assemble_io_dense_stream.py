import json
import math
from pathlib import Path

IN_DIR = Path('artifacts/enc3/io_dense_dumps')
OUT_DIR = Path('artifacts/enc3')
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_STREAM = OUT_DIR / 'kingsvale-io-dense-assembled-by-time.bin'
OUT_JSON = OUT_DIR / 'kingsvale-io-dense-assembled-by-time.json'


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
    sigs = [('MZ', b'MZ'), ('PK', b'PK\x03\x04'), ('ENC3', b'ENC3'), ('GZIP', b'\x1f\x8b\x08'), ('ZLIB_78', b'\x78')]
    out = []
    for n, s in sigs:
        p = data.find(s)
        if p != -1:
            out.append({'name': n, 'offset': p})
    return out

files = sorted([p for p in IN_DIR.glob('*.bin')], key=lambda p: p.stat().st_mtime)
parts = []
entries = []
for p in files:
    b = p.read_bytes()
    parts.append(b)
    st = p.stat()
    entries.append({'file': str(p).replace('\\','/'), 'size': len(b), 'mtime': st.st_mtime})

stream = b''.join(parts)
OUT_STREAM.write_bytes(stream)

report = {
    'input_dir': str(IN_DIR).replace('\\','/'),
    'count': len(files),
    'total_size': len(stream),
    'stream_file': str(OUT_STREAM).replace('\\','/'),
    'entropy': round(entropy(stream), 4) if stream else 0.0,
    'headers': headers(stream[:262144]) if stream else [],
    'entries': entries,
}
OUT_JSON.write_text(json.dumps(report, indent=2), encoding='utf-8')

print(json.dumps({'count': report['count'], 'total_size': report['total_size'], 'stream_file': report['stream_file'], 'entropy': report['entropy'], 'headers': report['headers'], 'json': str(OUT_JSON).replace('\\','/')}, indent=2))
