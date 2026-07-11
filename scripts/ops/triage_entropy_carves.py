import argparse
import glob
import json
import math
import os
import pathlib
import statistics
import zlib
import lzma
from dataclasses import dataclass, asdict


MAGIC_SIGNATURES = {
    "MZ": b"MZ",
    "PKZIP": b"PK\x03\x04",
    "ENC3": b"ENC3",
    "ELF": b"\x7fELF",
    "PNG": b"\x89PNG\r\n\x1a\n",
    "GZIP": b"\x1f\x8b\x08",
    "ZLIB_78_01": b"\x78\x01",
    "ZLIB_78_9C": b"\x78\x9c",
    "ZLIB_78_DA": b"\x78\xda",
}


@dataclass
class DecompressResult:
    method: str
    success: bool
    out_size: int
    out_entropy: float
    note: str


def shannon_entropy(data: bytes) -> float:
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
    printable = sum(1 for b in data if 32 <= b <= 126 or b in (9, 10, 13))
    return printable / len(data)


def detect_magic(data: bytes):
    hits = []
    for name, sig in MAGIC_SIGNATURES.items():
        off = data.find(sig)
        if off != -1:
            hits.append({"name": name, "offset": off})
    hits.sort(key=lambda x: x["offset"])
    return hits


def try_zlib(data: bytes):
    results = []
    variants = [
        ("zlib", {}),
        ("zlib_raw_deflate", {"wbits": -15}),
        ("zlib_gzip", {"wbits": 31}),
    ]
    for name, kwargs in variants:
        try:
            out = zlib.decompress(data, **kwargs)
            results.append(
                DecompressResult(
                    method=name,
                    success=True,
                    out_size=len(out),
                    out_entropy=round(shannon_entropy(out), 4),
                    note=f"ok; head={out[:8].hex()}",
                )
            )
        except Exception as e:
            results.append(
                DecompressResult(
                    method=name,
                    success=False,
                    out_size=0,
                    out_entropy=0.0,
                    note=str(e)[:160],
                )
            )
    return results


def try_lzma(data: bytes):
    try:
        out = lzma.decompress(data)
        return DecompressResult(
            method="lzma",
            success=True,
            out_size=len(out),
            out_entropy=round(shannon_entropy(out), 4),
            note=f"ok; head={out[:8].hex()}",
        )
    except Exception as e:
        return DecompressResult(
            method="lzma",
            success=False,
            out_size=0,
            out_entropy=0.0,
            note=str(e)[:160],
        )


def try_lz4(data: bytes):
    try:
        import lz4.block

        out = lz4.block.decompress(data)
        return DecompressResult(
            method="lz4_block",
            success=True,
            out_size=len(out),
            out_entropy=round(shannon_entropy(out), 4),
            note=f"ok; head={out[:8].hex()}",
        )
    except Exception as e:
        return DecompressResult(
            method="lz4_block",
            success=False,
            out_size=0,
            out_entropy=0.0,
            note=str(e)[:160],
        )


def score_blob(size, entropy, p_ratio, magic_hits, decompress_results, data):
    score = 0
    reasons = []

    if magic_hits:
        score += 40
        reasons.append("magic-signature")

    succ = [r for r in decompress_results if r.success]
    if succ:
        score += min(50, 20 + 10 * len(succ))
        reasons.append("decompression-success")

    if 5.2 <= entropy <= 7.9:
        score += 12
        reasons.append("entropy-range")

    if size >= 1024:
        score += 8
        reasons.append("size>=1k")

    if 0.05 <= p_ratio <= 0.9:
        score += 6
        reasons.append("printable-mixed")

    zero_ratio = data.count(0) / len(data) if data else 1.0
    if zero_ratio < 0.95:
        score += 8
        reasons.append("not-mostly-zero")

    return score, reasons


def triage_blob(path: pathlib.Path):
    data = path.read_bytes()
    size = len(data)
    entropy = round(shannon_entropy(data), 4)
    p_ratio = round(printable_ratio(data), 4)
    magic_hits = detect_magic(data)

    decomp = []
    decomp.extend(try_zlib(data))
    decomp.append(try_lzma(data))
    decomp.append(try_lz4(data))

    score, reasons = score_blob(size, entropy, p_ratio, magic_hits, decomp, data)

    return {
        "file": str(path).replace('\\', '/'),
        "size": size,
        "entropy": entropy,
        "printable_ratio": p_ratio,
        "magic_hits": magic_hits,
        "decompression": [asdict(x) for x in decomp],
        "score": score,
        "score_reasons": reasons,
    }


def render_markdown(results, out_md):
    lines = []
    lines.append("# Entropy Carve Triage")
    lines.append("")
    lines.append("| Rank | File | Score | Entropy | Size | Magic | Decompress OK |")
    lines.append("|---|---|---:|---:|---:|---|---:|")

    for i, r in enumerate(results, start=1):
        magic = ",".join(m["name"] for m in r["magic_hits"]) or "-"
        ok = sum(1 for d in r["decompression"] if d["success"])
        lines.append(
            f"| {i} | {r['file']} | {r['score']} | {r['entropy']:.3f} | {r['size']} | {magic} | {ok} |"
        )

    lines.append("")
    lines.append("## Notes")
    lines.append("")
    for i, r in enumerate(results, start=1):
        lines.append(f"### {i}. {os.path.basename(r['file'])}")
        lines.append(f"- Score: {r['score']} ({', '.join(r['score_reasons']) or 'n/a'})")
        lines.append(f"- Entropy: {r['entropy']}")
        lines.append(f"- Printable ratio: {r['printable_ratio']}")
        if r["magic_hits"]:
            lines.append("- Magic hits: " + ", ".join(f"{m['name']}@{m['offset']}" for m in r["magic_hits"]))
        else:
            lines.append("- Magic hits: none")
        ok_methods = [d["method"] for d in r["decompression"] if d["success"]]
        lines.append("- Decompress success: " + (", ".join(ok_methods) if ok_methods else "none"))
        lines.append("")

    out_md.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--glob",
        default="artifacts/enc3/kingsvale-entropy-carve-*.bin",
        help="Glob for carve binaries",
    )
    parser.add_argument(
        "--json-out",
        default="artifacts/enc3/kingsvale-entropy-carve-triage.json",
    )
    parser.add_argument(
        "--md-out",
        default="artifacts/enc3/kingsvale-entropy-carve-triage.md",
    )
    args = parser.parse_args()

    files = [pathlib.Path(p) for p in sorted(glob.glob(args.glob))]
    if not files:
        raise SystemExit("No carve files found for triage")

    results = [triage_blob(p) for p in files]
    results.sort(key=lambda x: x["score"], reverse=True)

    summary = {
        "count": len(results),
        "score_mean": round(statistics.mean(r["score"] for r in results), 3),
        "top_file": results[0]["file"],
        "top_score": results[0]["score"],
    }

    out = {"summary": summary, "results": results}

    out_json = pathlib.Path(args.json_out)
    out_md = pathlib.Path(args.md_out)
    out_json.parent.mkdir(parents=True, exist_ok=True)

    out_json.write_text(json.dumps(out, indent=2), encoding="utf-8")
    render_markdown(results, out_md)

    print(json.dumps(summary, indent=2))
    print(f"json={out_json.as_posix()}")
    print(f"md={out_md.as_posix()}")


if __name__ == "__main__":
    main()
