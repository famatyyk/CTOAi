import json
import math
import zlib
from pathlib import Path

VAR_DIR = Path('artifacts/enc3/window_aware')
OUT_DIR = Path('artifacts/enc3/depack/anchor-windows')
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_JSON = OUT_DIR / 'anchor-window-depack.json'
OUT_MD = OUT_DIR / 'anchor-window-depack.md'

TRANSFORMS = [
    ('id', 0),
    ('xor_ff', 0xFF),
    ('xor_20', 0x20),
    ('xor_cb', 0xCB),
    ('xor_4c', 0x4C),
]
METHODS = [
    ('zlib', None),
    ('zlib_raw', -15),
    ('zlib_gzip', 31),
]
WINDOWS = [
    (0, 8192),
    (0, 16384),
    (256, 16384),
    (512, 24576),
    (1024, 32768),
    (2048, 49152),
]


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
    pr = 0
    for b in data:
        if b in (9, 10, 13) or 32 <= b <= 126:
            pr += 1
    return pr / len(data)


def find_magic(data: bytes):
    sigs = [
        ('MZ', b'MZ'),
        ('PK', b'PK\x03\x04'),
        ('ENC3', b'ENC3'),
        ('GZIP', b'\x1f\x8b\x08'),
        ('ZLIB_7801', b'\x78\x01'),
        ('ZLIB_789C', b'\x78\x9c'),
        ('ZLIB_78DA', b'\x78\xda'),
    ]
    out = []
    for n, s in sigs:
        pos = data.find(s)
        if pos != -1:
            out.append({'name': n, 'offset': pos})
    out.sort(key=lambda x: x['offset'])
    return out


def pe_score(data: bytes) -> int:
    if len(data) < 0x100 or not data.startswith(b'MZ'):
        return 0
    try:
        e_lfanew = int.from_bytes(data[0x3C:0x40], 'little')
        if e_lfanew <= 0 or e_lfanew + 4 > len(data):
            return 0
        if data[e_lfanew:e_lfanew + 4] != b'PE\x00\x00':
            return 0
        bonus = 45
        if len(data) >= 32768:
            bonus += 20
        elif len(data) >= 8192:
            bonus += 10
        return bonus
    except Exception:
        return 0


def score_blob(data: bytes) -> dict:
    mags = find_magic(data[:131072])
    h = entropy(data)
    pr = printable_ratio(data)
    size = len(data)

    magic_pts = 0
    for m in mags:
        if m['name'] == 'MZ':
            magic_pts += 24
        elif m['name'] in ('PK', 'GZIP'):
            magic_pts += 16
        else:
            magic_pts += 8
        if m['offset'] <= 4096:
            magic_pts += 6
    magic_pts = min(50, magic_pts)

    size_pts = min(30, int(math.log2(size + 1) * 2.4)) if size else 0
    if 5.0 <= h <= 7.8:
        ent_pts = 18
    elif 4.3 <= h < 5.0 or 7.8 < h <= 8.3:
        ent_pts = 11
    else:
        ent_pts = 4

    if 0.10 <= pr <= 0.90:
        pr_pts = 8
    elif 0.04 <= pr <= 0.98:
        pr_pts = 4
    else:
        pr_pts = 1

    pe_pts = pe_score(data)
    total = magic_pts + size_pts + ent_pts + pr_pts + pe_pts
    return {
        'score': total,
        'score_breakdown': {
            'magic': magic_pts,
            'size': size_pts,
            'entropy': ent_pts,
            'printable': pr_pts,
            'pe': pe_pts,
        },
        'entropy': round(h, 4),
        'printable_ratio': round(pr, 4),
        'magic': mags,
    }


def make_windows(data: bytes):
    anchors = []
    sigs = [b'MZ', b'PK\x03\x04', b'\x1f\x8b\x08', b'\x78\x01', b'\x78\x9c', b'\x78\xda']
    for sig in sigs:
        pos = data.find(sig)
        if pos != -1:
            anchors.append(pos)
    anchors = sorted(set([0] + anchors))

    out = []
    for a in anchors:
        for pre, span in WINDOWS:
            lo = max(0, a - pre)
            hi = min(len(data), lo + span)
            if hi - lo >= 64:
                out.append((a, lo, hi))

    uniq = []
    seen = set()
    for a, lo, hi in out:
        key = (lo, hi)
        if key in seen:
            continue
        seen.add(key)
        uniq.append((a, lo, hi))
    return uniq


def try_depack(payload: bytes, wbits):
    results = []
    try:
        dec = zlib.decompress(payload) if wbits is None else zlib.decompress(payload, wbits=wbits)
        if dec:
            results.append(('single', dec))
    except Exception:
        pass

    try:
        obj = zlib.decompressobj() if wbits is None else zlib.decompressobj(wbits)
        dec = obj.decompress(payload)
        dec += obj.flush()
        if dec:
            results.append(('stream', dec))
    except Exception:
        pass

    staged = []
    for mode, d1 in list(results):
        for m2, w2 in METHODS:
            try:
                d2 = zlib.decompress(d1) if w2 is None else zlib.decompress(d1, wbits=w2)
                if d2:
                    staged.append((f'{mode}_then_{m2}', d2))
            except Exception:
                continue
    results.extend(staged)
    return results


def iter_variants():
    files = []
    for pat in ('v*.bin', 'g*.bin'):
        files.extend(sorted(VAR_DIR.glob(pat)))
    out = []
    seen = set()
    for p in files:
        if p.name in seen:
            continue
        seen.add(p.name)
        out.append(p)
    return out


def main():
    variants = iter_variants()
    all_hits = []
    runs = []

    for vf in variants:
        data = vf.read_bytes()
        windows = make_windows(data)
        hits = []

        for anchor, lo, hi in windows:
            src = data[lo:hi]
            for tname, key in TRANSFORMS:
                payload = src if key == 0 else bytes(b ^ key for b in src)
                for mname, wbits in METHODS:
                    for mode, dec in try_depack(payload, wbits):
                        if len(dec) < 64:
                            continue
                        met = score_blob(dec)
                        out_name = f"{vf.stem}-a{anchor:06d}-w{lo:06d}-{hi:06d}-{tname}-{mname}-{mode}.bin"
                        out_fp = OUT_DIR / out_name
                        out_fp.write_bytes(dec)
                        row = {
                            'variant': vf.stem,
                            'anchor': anchor,
                            'window_lo': lo,
                            'window_hi': hi,
                            'window_size': hi - lo,
                            'transform': tname,
                            'method': mname,
                            'mode': mode,
                            'out_size': len(dec),
                            'score': met['score'],
                            'score_breakdown': met['score_breakdown'],
                            'entropy': met['entropy'],
                            'printable_ratio': met['printable_ratio'],
                            'magic': met['magic'],
                            'file': str(out_fp).replace('\\', '/'),
                        }
                        hits.append(row)
                        all_hits.append(row)

        hits.sort(key=lambda x: (x['score'], x['out_size'], len(x['magic'])), reverse=True)
        runs.append({
            'variant': vf.stem,
            'input': str(vf).replace('\\', '/'),
            'input_size': len(data),
            'windows': len(windows),
            'hits': len(hits),
            'top': hits[:25],
        })

    all_hits.sort(key=lambda x: (x['score'], x['out_size'], len(x['magic'])), reverse=True)
    best = all_hits[0] if all_hits else None

    summary = {
        'variant_count': len(runs),
        'total_hits': len(all_hits),
        'runs': runs,
        'global_top': all_hits[:40],
        'best_candidate': best,
    }
    OUT_JSON.write_text(json.dumps(summary, indent=2), encoding='utf-8')

    md = ['# Anchor Window Depack', '']
    md.append(f"- Variants: {len(runs)}")
    md.append(f"- Total hits (>=64B): {len(all_hits)}")
    md.append('')
    if best:
        mg = ', '.join(f"{m['name']}@{m['offset']}" for m in best.get('magic', [])) or 'none'
        sb = best.get('score_breakdown', {})
        md.append('## Best Candidate')
        md.append(
            f"- {best['variant']} score={best['score']} [m={sb.get('magic',0)} s={sb.get('size',0)} e={sb.get('entropy',0)} p={sb.get('printable',0)} pe={sb.get('pe',0)}] "
            f"size={best['out_size']} anchor={best['anchor']} win={best['window_lo']}:{best['window_hi']} "
            f"tr={best['transform']} m={best['method']} mode={best['mode']} ent={best['entropy']} pr={best['printable_ratio']} magic={mg}"
        )
        md.append(f"- file: {best['file']}")
        md.append('')

    md.append('## Per Variant')
    for r in runs:
        md.append(f"- {r['variant']}: size={r['input_size']} windows={r['windows']} hits={r['hits']}")

    md.append('')
    md.append('## Global Top 12')
    for h in summary['global_top'][:12]:
        mg = ', '.join(f"{m['name']}@{m['offset']}" for m in h.get('magic', [])) or 'none'
        sb = h.get('score_breakdown', {})
        md.append(
            f"- {h['variant']} score={h['score']} [m={sb.get('magic',0)} s={sb.get('size',0)} e={sb.get('entropy',0)} p={sb.get('printable',0)} pe={sb.get('pe',0)}] "
            f"size={h['out_size']} a={h['anchor']} win={h['window_lo']}:{h['window_hi']} tr={h['transform']} m={h['method']} mode={h['mode']} "
            f"ent={h['entropy']} pr={h['printable_ratio']} magic={mg} -> {h['file']}"
        )

    OUT_MD.write_text('\n'.join(md), encoding='utf-8')

    print(json.dumps({
        'json': str(OUT_JSON).replace('\\', '/'),
        'md': str(OUT_MD).replace('\\', '/'),
        'variants': len(runs),
        'total_hits': len(all_hits),
        'best_candidate': best,
    }, indent=2))


if __name__ == '__main__':
    main()
