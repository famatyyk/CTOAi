import argparse
import json
import math
import statistics
import zlib
from pathlib import Path


DEFAULT_CANDIDATES = [
    Path("artifacts/enc3/kingsvale-entropy-carve-high-02.bin"),
    Path("artifacts/enc3/kingsvale-entropy-carve-medium-04.bin"),
]

OUT_DIR = Path("artifacts/enc3/depack")
OUT_DIR.mkdir(parents=True, exist_ok=True)

MAX_OFFSET_SCAN = 1024
MAX_BLOB = 8 * 1024 * 1024
ENTROPY_WINDOW = 256
ENTROPY_STEP = 64
HIGH_THRESHOLD = 6.8
MEDIUM_THRESHOLD = 6.0


try:
    import lz4.frame as _lz4_frame
except Exception:
    _lz4_frame = None

try:
    import lz4.block as _lz4_block
except Exception:
    _lz4_block = None

try:
    import lzo as _lzo
except Exception:
    _lzo = None


def entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = [0] * 256
    for b in data:
        counts[b] += 1
    n = float(len(data))
    h = 0.0
    for c in counts:
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
    sigs = [
        ("MZ", b"MZ"),
        ("PK", b"PK\x03\x04"),
        ("ENC3", b"ENC3"),
        ("GZIP", b"\x1f\x8b\x08"),
        ("ZLIB_78_01", b"\x78\x01"),
        ("ZLIB_78_9C", b"\x78\x9c"),
        ("ZLIB_78_DA", b"\x78\xda"),
        ("LZ4_FRAME", b"\x04\x22\x4D\x18"),
    ]
    hits = []
    for name, sig in sigs:
        off = data.find(sig)
        if off != -1:
            hits.append({"name": name, "offset": off})
    hits.sort(key=lambda x: x["offset"])
    return hits


def score_blob(data: bytes):
    h = entropy(data)
    p = printable_ratio(data)
    m = detect_magic(data)
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
    return s, h, p, m


def zlib_like_offsets(data: bytes, max_scan: int):
    offs = {0}
    scan_n = min(max_scan, len(data) - 2)
    if scan_n <= 0:
        return [0]

    z_heads = (b"\x78\x01", b"\x78\x9c", b"\x78\xda")
    for i in range(scan_n):
        if data[i : i + 2] in z_heads:
            offs.add(i)
    return sorted(offs)


def entropy_regions(data: bytes, threshold: float):
    if len(data) < ENTROPY_WINDOW:
        return []

    hot = []
    for s in range(0, len(data) - ENTROPY_WINDOW + 1, ENTROPY_STEP):
        w = data[s : s + ENTROPY_WINDOW]
        h = entropy(w)
        if h >= threshold:
            hot.append((s, s + ENTROPY_WINDOW, h))

    if not hot:
        return []

    merged = []
    cs, ce, ch = hot[0]
    hs = [ch]
    for s, e, h in hot[1:]:
        if s <= ce:
            ce = max(ce, e)
            hs.append(h)
        else:
            merged.append({"start": cs, "end": ce, "max_entropy": max(hs), "avg_entropy": sum(hs) / len(hs)})
            cs, ce, ch = s, e, h
            hs = [h]
    merged.append({"start": cs, "end": ce, "max_entropy": max(hs), "avg_entropy": sum(hs) / len(hs)})
    return merged


def local_entropy_min_offsets(data: bytes, regions, radius=256):
    offs = set()
    if len(data) < 32:
        return offs

    def local_min(center):
        lo = max(0, center - radius)
        hi = min(len(data) - 32, center + radius)
        best_s = lo
        best_h = 999.0
        step = 16
        for s in range(lo, max(lo + 1, hi), step):
            chunk = data[s : s + 64]
            h = entropy(chunk)
            if h < best_h:
                best_h = h
                best_s = s
        return best_s

    for r in regions:
        for c in (r["start"], (r["start"] + r["end"]) // 2, r["end"]):
            offs.add(local_min(c))
    return offs


def rol_byte(v, bits):
    bits = bits % 8
    return ((v << bits) & 0xFF) | (v >> (8 - bits))


def apply_transform(data: bytes, t):
    ttype = t["type"]
    if ttype == "id":
        return data
    if ttype == "xor":
        k = t["key"]
        return bytes(b ^ k for b in data)
    if ttype == "rol":
        r = t["bits"]
        return bytes(rol_byte(b, r) for b in data)
    return data


def build_transforms():
    ts = [{"type": "id", "name": "id"}]
    for k in range(256):
        ts.append({"type": "xor", "key": k, "name": f"xor_{k:02x}"})
    for b in range(1, 8):
        ts.append({"type": "rol", "bits": b, "name": f"rol_{b}"})
    return ts


def try_decompress(payload: bytes):
    results = []

    for method, kwargs in [
        ("zlib", {}),
        ("zlib_raw", {"wbits": -15}),
        ("zlib_gzip", {"wbits": 31}),
    ]:
        try:
            d = zlib.decompress(payload, **kwargs)
            results.append((method, True, d, "ok"))
        except Exception as e:
            results.append((method, False, b"", str(e)[:120]))

    if _lz4_frame is not None:
        try:
            d = _lz4_frame.decompress(payload)
            results.append(("lz4_frame", True, d, "ok"))
        except Exception as e:
            results.append(("lz4_frame", False, b"", str(e)[:120]))
    else:
        results.append(("lz4_frame", False, b"", "module_unavailable"))

    if _lz4_block is not None:
        try:
            d = _lz4_block.decompress(payload)
            results.append(("lz4_block", True, d, "ok"))
        except Exception as e:
            results.append(("lz4_block", False, b"", str(e)[:120]))
    else:
        results.append(("lz4_block", False, b"", "module_unavailable"))

    if _lzo is not None:
        try:
            d = _lzo.decompress(payload)
            results.append(("lzo", True, d, "ok"))
        except Exception as e:
            results.append(("lzo", False, b"", str(e)[:120]))
    else:
        results.append(("lzo", False, b"", "module_unavailable"))

    return results


def process_candidate(cpath: Path, transforms):
    if not cpath.exists():
        return {"candidate": str(cpath).replace('\\', '/'), "error": "missing"}

    data = cpath.read_bytes()
    run = {
        "candidate": str(cpath).replace('\\', '/'),
        "size": len(data),
        "hits": [],
    }

    high = entropy_regions(data, HIGH_THRESHOLD)
    medium = entropy_regions(data, MEDIUM_THRESHOLD)

    offs = set(zlib_like_offsets(data, MAX_OFFSET_SCAN))
    offs |= local_entropy_min_offsets(data, high)
    offs |= local_entropy_min_offsets(data, medium)

    offs = sorted(o for o in offs if 0 <= o < len(data) - 8)
    run["offsets"] = {
        "count": len(offs),
        "values": offs[:400],
        "high_regions": high,
        "medium_regions": medium,
    }

    for off in offs:
        source = data[off:]
        for t in transforms:
            transformed = apply_transform(source, t)
            variants = try_decompress(transformed)
            for method, ok, dec, note in variants:
                if not ok or not dec:
                    continue
                sc, h, p, mg = score_blob(dec)
                fname = f"{cpath.stem}-off{off:04d}-{t['name']}-{method}.bin"
                outp = OUT_DIR / fname
                outp.write_bytes(dec[:MAX_BLOB])
                run["hits"].append(
                    {
                        "offset": off,
                        "transform": t["name"],
                        "method": method,
                        "note": note,
                        "out_size": len(dec),
                        "score": sc,
                        "entropy": round(h, 4),
                        "printable_ratio": round(p, 4),
                        "magic": mg,
                        "file": str(outp).replace('\\', '/'),
                    }
                )

    run["top"] = sorted(run["hits"], key=lambda x: (x["score"], x["out_size"]), reverse=True)[:12]
    return run


def render_md(summary, md_path: Path):
    lines = ["# Advanced Depack Summary", ""]
    lines.append("## Environment")
    lines.append(f"- lz4.frame: {'yes' if _lz4_frame else 'no'}")
    lines.append(f"- lz4.block: {'yes' if _lz4_block else 'no'}")
    lines.append(f"- lzo: {'yes' if _lzo else 'no'}")
    lines.append("")

    for run in summary["runs"]:
        lines.append(f"## {run['candidate']}")
        if run.get("error"):
            lines.append(f"- Error: {run['error']}")
            lines.append("")
            continue
        lines.append(f"- Size: {run['size']}")
        lines.append(f"- Offset candidates: {run['offsets']['count']}")
        lines.append(f"- Hits: {len(run['hits'])}")
        lines.append("- Top candidates:")
        for t in run.get("top", [])[:8]:
            mg = ", ".join(f"{m['name']}@{m['offset']}" for m in t.get("magic", [])) or "none"
            lines.append(
                f"  - score={t['score']} method={t['method']} transform={t['transform']} off={t['offset']} size={t['out_size']} ent={t['entropy']} magic={mg} -> {t['file']}"
            )
        lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", nargs="*", default=[str(p) for p in DEFAULT_CANDIDATES])
    parser.add_argument("--json-out", default="artifacts/enc3/depack/depack-summary.json")
    parser.add_argument("--md-out", default="artifacts/enc3/depack/depack-summary.md")
    args = parser.parse_args()

    transforms = build_transforms()
    runs = [process_candidate(Path(c), transforms) for c in args.candidates]

    scores = [r["top"][0]["score"] for r in runs if r.get("top")]
    summary = {
        "summary": {
            "runs": len(runs),
            "score_mean_top1": round(statistics.mean(scores), 3) if scores else None,
            "lz4_frame_available": _lz4_frame is not None,
            "lz4_block_available": _lz4_block is not None,
            "lzo_available": _lzo is not None,
        },
        "runs": runs,
    }

    json_path = Path(args.json_out)
    md_path = Path(args.md_out)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    render_md(summary, md_path)

    print(json.dumps(summary["summary"], indent=2))
    print(f"json={str(json_path).replace('\\', '/')}")
    print(f"md={str(md_path).replace('\\', '/')}")


if __name__ == "__main__":
    main()
