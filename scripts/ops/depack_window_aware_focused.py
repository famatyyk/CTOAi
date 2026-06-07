import json
import math
import zlib
from pathlib import Path

VAR_DIR = Path("artifacts/enc3/window_aware")
OUT_DIR = Path("artifacts/enc3/depack/window-aware")
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_JSON = OUT_DIR / "depack-window-aware-focused.json"
OUT_MD = OUT_DIR / "depack-window-aware-focused.md"


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
    printable = 0
    for b in data:
        if b in (9, 10, 13) or 32 <= b <= 126:
            printable += 1
    return printable / len(data)


def magic(data: bytes):
    sigs = [
        ("MZ", b"MZ"),
        ("PK", b"PK\x03\x04"),
        ("ENC3", b"ENC3"),
        ("GZIP", b"\x1f\x8b\x08"),
        ("ZLIB_78", b"\x78"),
    ]
    out = []
    for name, sig in sigs:
        pos = data.find(sig)
        if pos != -1:
            out.append({"name": name, "offset": pos})
    return out


def score_breakdown(data: bytes) -> dict:
    h = entropy(data)
    pr = printable_ratio(data)
    mags = magic(data[:65536])

    magic_score = 0
    for m in mags:
        base = 22 if m["name"] == "MZ" else 16 if m["name"] in ("PK", "GZIP") else 8
        early_bonus = max(0, 8 - min(8, m["offset"] // 1024))
        magic_score += base + early_bonus
    magic_score = min(45, magic_score)

    size_score = min(25, int(math.log2(len(data) + 1) * 2.2)) if data else 0

    if 5.0 <= h <= 7.6:
        entropy_score = 20
    elif 4.2 <= h < 5.0 or 7.6 < h <= 8.2:
        entropy_score = 12
    else:
        entropy_score = 4

    if 0.10 <= pr <= 0.90:
        printable_score = 10
    elif 0.05 <= pr <= 0.98:
        printable_score = 5
    else:
        printable_score = 1

    total = magic_score + size_score + entropy_score + printable_score
    return {
        "score": total,
        "magic_score": magic_score,
        "size_score": size_score,
        "entropy_score": entropy_score,
        "printable_score": printable_score,
        "entropy": round(h, 4),
        "printable_ratio": round(pr, 4),
        "magic": mags,
    }


def candidate_offsets(data: bytes):
    offs = {0}
    sigs = [b"\x78\x01", b"\x78\x9c", b"\x78\xda", b"MZ", b"PK\x03\x04", b"\x1f\x8b\x08"]
    for sig in sigs:
        pos = data.find(sig)
        if pos != -1:
            for delta in (-1024, -512, -256, -128, -64, -32, -16, -8, 0, 8, 16, 32, 64, 128, 256, 512, 1024):
                off = pos + delta
                if 0 <= off < len(data) - 8:
                    offs.add(off)
    return sorted(offs)


def iter_variants():
    pats = ["v*.bin", "g*.bin"]
    out = []
    seen = set()
    for pat in pats:
        for fp in sorted(VAR_DIR.glob(pat)):
            if fp.name in seen:
                continue
            seen.add(fp.name)
            out.append(fp)
    return out


def main():
    variants = iter_variants()
    transforms = [
        ("id", 0),
        ("xor_ff", 0xFF),
        ("xor_20", 0x20),
        ("xor_cb", 0xCB),
        ("xor_4c", 0x4C),
    ]
    methods = [
        ("zlib", None),
        ("zlib_raw", -15),
        ("zlib_gzip", 31),
    ]

    runs = []
    all_top = []
    all_hits = []

    for vf in variants:
        data = vf.read_bytes()
        offs = candidate_offsets(data)
        hits = []

        for off in offs:
            src = data[off:]
            for tname, key in transforms:
                payload = src if key == 0 else bytes(b ^ key for b in src)
                for method, wbits in methods:
                    try:
                        dec = zlib.decompress(payload) if wbits is None else zlib.decompress(payload, wbits=wbits)
                    except Exception:
                        continue
                    if not dec:
                        continue

                    breakdown = score_breakdown(dec)
                    out_fp = OUT_DIR / f"{vf.stem}-off{off:06d}-{tname}-{method}.bin"
                    out_fp.write_bytes(dec)

                    hit = {
                        "variant": vf.stem,
                        "offset": off,
                        "transform": tname,
                        "method": method,
                        "out_size": len(dec),
                        "score": breakdown["score"],
                        "score_breakdown": {
                            "magic": breakdown["magic_score"],
                            "size": breakdown["size_score"],
                            "entropy": breakdown["entropy_score"],
                            "printable": breakdown["printable_score"],
                        },
                        "entropy": breakdown["entropy"],
                        "printable_ratio": breakdown["printable_ratio"],
                        "magic": breakdown["magic"],
                        "file": str(out_fp).replace("\\", "/"),
                    }
                    hits.append(hit)
                    all_hits.append(hit)

        hits.sort(
            key=lambda x: (
                x["score"],
                len(x.get("magic", [])),
                x["out_size"],
                x["printable_ratio"],
            ),
            reverse=True,
        )
        top = hits[:25]
        runs.append(
            {
                "variant": vf.stem,
                "input": str(vf).replace("\\", "/"),
                "input_size": len(data),
                "offset_count": len(offs),
                "hits": len(hits),
                "top": top,
            }
        )
        all_top.extend(top[:7])

    all_top.sort(
        key=lambda x: (
            x["score"],
            len(x.get("magic", [])),
            x["out_size"],
            x["printable_ratio"],
        ),
        reverse=True,
    )

    best = all_top[0] if all_top else None
    summary = {
        "variant_count": len(runs),
        "runs": runs,
        "global_top": all_top[:40],
        "best_candidate": best,
    }

    OUT_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    md = ["# Depack Window Aware Focused", ""]
    md.append(f"- Variants: {len(runs)}")
    md.append(f"- Total hits: {len(all_hits)}")
    md.append("")
    if best:
        mg = ", ".join(f"{m['name']}@{m['offset']}" for m in best.get("magic", [])) or "none"
        md.append("## Best Candidate (Auto)")
        md.append(
            f"- {best['variant']} score={best['score']} size={best['out_size']} off={best['offset']} "
            f"tr={best['transform']} m={best['method']} ent={best['entropy']} pr={best['printable_ratio']} magic={mg}"
        )
        md.append(f"- file: {best['file']}")
        md.append("")

    md.append("## Per Variant")
    for r in runs:
        md.append(f"- {r['variant']}: size={r['input_size']} offsets={r['offset_count']} hits={r['hits']}")

    md.append("")
    md.append("## Global Top 12")
    for h in summary["global_top"][:12]:
        mg = ", ".join(f"{m['name']}@{m['offset']}" for m in h.get("magic", [])) or "none"
        sb = h.get("score_breakdown", {})
        md.append(
            f"- {h['variant']} score={h['score']} [m={sb.get('magic',0)} s={sb.get('size',0)} e={sb.get('entropy',0)} p={sb.get('printable',0)}] "
            f"size={h['out_size']} off={h['offset']} tr={h['transform']} m={h['method']} ent={h['entropy']} pr={h['printable_ratio']} magic={mg} -> {h['file']}"
        )

    OUT_MD.write_text("\n".join(md), encoding="utf-8")

    print(
        json.dumps(
            {
                "json": str(OUT_JSON).replace("\\", "/"),
                "md": str(OUT_MD).replace("\\", "/"),
                "variants": len(runs),
                "total_hits": len(all_hits),
                "best_candidate": best,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
