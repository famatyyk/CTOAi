import json
from pathlib import Path

SRC = Path('artifacts/enc3/kingsvale-io-dense-live.json')
DUMPS = Path('artifacts/enc3/io_dense_dumps')
OUT = Path('artifacts/enc3/window_aware')
OUT.mkdir(parents=True, exist_ok=True)
OUT_JSON = OUT / 'offset-handle-assembly-summary.json'
OUT_MD = OUT / 'offset-handle-assembly-summary.md'


def load_events():
    data = json.loads(SRC.read_text(encoding='utf-8'))
    # tolerate either top-level list or {events:[...]}
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in ('events', 'captures', 'dumps', 'records'):
            if isinstance(data.get(k), list):
                return data[k]
    return []


def get_dump_file(ev):
    for k in ('dump_file', 'file', 'path', 'dumpPath', 'dump'):
        v = ev.get(k)
        if isinstance(v, str) and v.lower().endswith('.bin'):
            return v.replace('\\', '/')
    return None


def get_handle(ev):
    for k in ('file_handle', 'handle', 'hFile', 'hfile'):
        v = ev.get(k)
        if v is not None:
            return str(v)
    return 'unknown'


def get_offset(ev):
    for k in ('file_offset', 'offset', 'byte_offset', 'synthetic_offset', 'seq_offset'):
        v = ev.get(k)
        if isinstance(v, int):
            return v
        if isinstance(v, str):
            try:
                if v.lower().startswith('0x'):
                    return int(v, 16)
                return int(v)
            except Exception:
                pass
    return None


def get_size(ev):
    for k in ('size', 'nNumberOfBytesToRead', 'bytes', 'read_size'):
        v = ev.get(k)
        if isinstance(v, int) and v > 0:
            return v
    return None


def get_ts(ev):
    for k in ('timestamp', 'ts', 'time', 'created_at', 'event_time'):
        v = ev.get(k)
        if isinstance(v, (int, float)):
            return float(v)
    return 0.0


def main():
    events = load_events()
    rows = []
    for ev in events:
        df = get_dump_file(ev)
        if not df:
            continue
        p = Path(df)
        if not p.exists():
            p = DUMPS / Path(df).name
        if not p.exists():
            continue
        off = get_offset(ev)
        rows.append({
            'dump_path': str(p).replace('\\', '/'),
            'dump_name': p.name,
            'handle': get_handle(ev),
            'offset': off,
            'size': get_size(ev) or p.stat().st_size,
            'ts': get_ts(ev),
        })

    # fallback: if metadata misses files, include remaining dumps by sequence
    known = {r['dump_name'] for r in rows}
    for p in sorted(DUMPS.glob('*.bin')):
        if p.name in known:
            continue
        rows.append({
            'dump_path': str(p).replace('\\', '/'),
            'dump_name': p.name,
            'handle': 'fallback',
            'offset': None,
            'size': p.stat().st_size,
            'ts': p.stat().st_mtime,
        })

    # group by handle and create contiguous stream with gap filling
    by_handle = {}
    for r in rows:
        by_handle.setdefault(r['handle'], []).append(r)

    variants = {}
    handle_meta = []
    for h, items in by_handle.items():
        have_offsets = [x for x in items if isinstance(x['offset'], int)]
        if have_offsets:
            items_sorted = sorted(items, key=lambda x: (x['offset'] if isinstance(x['offset'], int) else 10**18, x['ts']))
            base = min(x['offset'] for x in have_offsets)
            end = max((x['offset'] + x['size']) for x in have_offsets)
            buf = bytearray(max(0, end - base))
            filled = 0
            for x in items_sorted:
                blob = Path(x['dump_path']).read_bytes()
                if not isinstance(x['offset'], int):
                    continue
                pos = x['offset'] - base
                if pos < 0:
                    continue
                n = min(len(blob), len(buf) - pos)
                if n <= 0:
                    continue
                buf[pos:pos+n] = blob[:n]
                filled += n
            stream = bytes(buf)
            source = 'offset'
        else:
            items_sorted = sorted(items, key=lambda x: x['ts'])
            stream = b''.join(Path(x['dump_path']).read_bytes() for x in items_sorted)
            base = 0
            end = len(stream)
            filled = len(stream)
            source = 'time_concat'

        name = f"h_{str(h).replace(':','_').replace('/','_')[:40]}"
        out = OUT / f"{name}_offset_rebuild.bin"
        out.write_bytes(stream)
        variants[name] = {
            'file': str(out).replace('\\', '/'),
            'handle': h,
            'source': source,
            'chunks': len(items),
            'size': len(stream),
            'offset_base': base,
            'offset_end': end,
            'filled_bytes': filled,
        }
        handle_meta.append((h, len(items), len(stream), source))

    # global variant: concat handle streams by chunk count desc, then size desc
    ordered = sorted(variants.values(), key=lambda x: (x['chunks'], x['size']), reverse=True)
    g_blob = b''.join(Path(v['file']).read_bytes() for v in ordered)
    g_fp = OUT / 'g4_handle_offset_global.bin'
    g_fp.write_bytes(g_blob)

    summary = {
        'event_rows': len(rows),
        'handles': len(variants),
        'variants': variants,
        'global': {
            'file': str(g_fp).replace('\\', '/'),
            'size': len(g_blob),
        },
    }
    OUT_JSON.write_text(json.dumps(summary, indent=2), encoding='utf-8')

    md = ['# Offset Handle Assembly', '']
    md.append(f"- Event rows: {summary['event_rows']}")
    md.append(f"- Handles: {summary['handles']}")
    md.append(f"- Global: {summary['global']['file']} size={summary['global']['size']}")
    md.append('')
    md.append('## Handle Variants')
    for k, v in variants.items():
        md.append(
            f"- {k}: handle={v['handle']} source={v['source']} chunks={v['chunks']} size={v['size']} filled={v['filled_bytes']} -> {v['file']}"
        )
    OUT_MD.write_text('\n'.join(md), encoding='utf-8')

    print(json.dumps({'json': str(OUT_JSON).replace('\\', '/'), 'md': str(OUT_MD).replace('\\', '/'), 'handles': len(variants), 'global': summary['global']}, indent=2))


if __name__ == '__main__':
    main()
