import hashlib
import json
import math
import zlib
from collections import defaultdict, deque
from pathlib import Path

IN_DIR = Path("artifacts/enc3/io_dense_dumps")
OUT_DIR = Path("artifacts/enc3/window_aware")
OUT_DIR.mkdir(parents=True, exist_ok=True)

MIN_OVERLAP = 64
MAX_OVERLAP = 2048
ROLLING_WINDOW = 64
ROLLING_STRIDE = 32
MIN_CLUSTER_EDGE_SCORE = 220
TOP_NEIGHBORS = 3
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
    out.sort(key=lambda x: x["offset"])
    return out


def sha1(data: bytes) -> str:
    return hashlib.sha1(data, usedforsecurity=False).hexdigest()


def find_best_overlap(a: bytes, b: bytes, min_ov=MIN_OVERLAP, max_ov=MAX_OVERLAP) -> int:
    max_len = min(max_ov, len(a), len(b))
    for ov in range(max_len, min_ov - 1, -1):
        if a[-ov:] == b[:ov]:
            return ov
    return 0


def rolling_hashes(data: bytes, window=ROLLING_WINDOW, stride=ROLLING_STRIDE) -> set[int]:
    if not data:
        return set()
    if len(data) <= window:
        return {zlib.adler32(data) & 0xFFFFFFFF}
    out = set()
    for i in range(0, len(data) - window + 1, stride):
        out.add(zlib.adler32(data[i : i + window]) & 0xFFFFFFFF)
    if (len(data) - window) % stride != 0:
        out.add(zlib.adler32(data[-window:]) & 0xFFFFFFFF)
    return out


def jaccard(a: set[int], b: set[int]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if inter == 0:
        return 0.0
    union = len(a | b)
    return inter / union if union else 0.0


def edge_score(overlap: int, jac: float) -> int:
    # overlap dominates ordering, rolling-hash similarity stabilizes low-overlap neighbors
    return int(overlap * 2.0 + jac * 1000)


def dedup_blocks(stream: bytes, block=BLOCK) -> bytes:
    seen = set()
    out = bytearray()
    for i in range(0, len(stream), block):
        part = stream[i : i + block]
        if not part:
            continue
        h = sha1(part)
        if h in seen:
            continue
        seen.add(h)
        out += part
    return bytes(out)


def merge_ordered_chunks(chunks: list[bytes]) -> tuple[bytes, list[dict]]:
    if not chunks:
        return b"", []
    cur = bytes(chunks[0])
    ops = [{"action": "seed", "size": len(cur)}]
    for ch in chunks[1:]:
        ov = find_best_overlap(cur, ch)
        if ov > 0:
            cur += ch[ov:]
            ops.append({"action": "merge_overlap", "overlap": ov, "append": len(ch) - ov})
        else:
            cur += ch
            ops.append({"action": "append_raw", "append": len(ch)})
    return cur, ops


def build_clusters(node_ids: list[int], outgoing: dict[int, list[dict]], best_out: dict[int, dict]) -> list[list[int]]:
    adj = {nid: set() for nid in node_ids}

    # Mutual best edges are high-confidence adjacency links.
    inv_best = {}
    for a, edge in best_out.items():
        inv_best[edge["to"]] = a
    for a, edge in best_out.items():
        b = edge["to"]
        if inv_best.get(a) == b and edge["score"] >= MIN_CLUSTER_EDGE_SCORE:
            adj[a].add(b)
            adj[b].add(a)

    # Expand with top-k neighbors above threshold to avoid singleton fragmentation.
    for a in node_ids:
        for edge in outgoing.get(a, [])[:TOP_NEIGHBORS]:
            if edge["score"] >= MIN_CLUSTER_EDGE_SCORE:
                b = edge["to"]
                adj[a].add(b)
                adj[b].add(a)

    clusters = []
    seen = set()
    for nid in node_ids:
        if nid in seen:
            continue
        q = deque([nid])
        comp = []
        seen.add(nid)
        while q:
            cur = q.popleft()
            comp.append(cur)
            for nb in adj[cur]:
                if nb not in seen:
                    seen.add(nb)
                    q.append(nb)
        clusters.append(sorted(comp))
    clusters.sort(key=len, reverse=True)
    return clusters


def order_cluster(cluster: list[int], outgoing: dict[int, list[dict]], incoming_weight: dict[int, int]) -> list[int]:
    if not cluster:
        return []
    if len(cluster) == 1:
        return [cluster[0]]

    in_cluster = set(cluster)
    # Start from node with weakest incoming weight (likely beginning of local sequence).
    start = min(cluster, key=lambda n: (incoming_weight.get(n, 0), n))

    order = [start]
    used = {start}
    cur = start
    while len(order) < len(cluster):
        nxt = None
        for edge in outgoing.get(cur, []):
            cand = edge["to"]
            if cand in in_cluster and cand not in used:
                nxt = cand
                break
        if nxt is None:
            # Restart from strongest not-yet-used node to keep informative chunks early.
            leftovers = [n for n in cluster if n not in used]
            nxt = max(leftovers, key=lambda n: incoming_weight.get(n, 0))
        order.append(nxt)
        used.add(nxt)
        cur = nxt
    return order


def main():
    files = sorted([p for p in IN_DIR.glob("*.bin")], key=lambda p: p.stat().st_mtime)
    if not files:
        raise SystemExit("No input chunks in artifacts/enc3/io_dense_dumps")

    nodes = []
    for idx, p in enumerate(files):
        blob = p.read_bytes()
        nodes.append(
            {
                "id": idx,
                "file": str(p).replace("\\", "/"),
                "name": p.name,
                "size": len(blob),
                "kind": p.stem.split("-")[0] if "-" in p.stem else p.stem,
                "mtime": p.stat().st_mtime,
                "blob": blob,
                "roll": rolling_hashes(blob),
            }
        )

    outgoing: dict[int, list[dict]] = defaultdict(list)
    incoming_weight: dict[int, int] = defaultdict(int)
    edge_count = 0

    for a in nodes:
        for b in nodes:
            if a["id"] == b["id"]:
                continue
            ov = find_best_overlap(a["blob"], b["blob"])
            jac = jaccard(a["roll"], b["roll"])
            sc = edge_score(ov, jac)
            if sc <= 0:
                continue
            outgoing[a["id"]].append(
                {
                    "to": b["id"],
                    "score": sc,
                    "overlap": ov,
                    "jaccard": round(jac, 5),
                }
            )
            incoming_weight[b["id"]] += sc
            edge_count += 1

    for nid in list(outgoing.keys()):
        outgoing[nid].sort(key=lambda e: (e["score"], e["overlap"], e["jaccard"]), reverse=True)

    best_out = {nid: edges[0] for nid, edges in outgoing.items() if edges}
    node_ids = [n["id"] for n in nodes]
    clusters = build_clusters(node_ids, outgoing, best_out)

    chunk_map = {n["id"]: n["blob"] for n in nodes}

    cluster_orders = []
    cluster_streams = []
    for ci, cl in enumerate(clusters, start=1):
        order = order_cluster(cl, outgoing, incoming_weight)
        cluster_orders.append({"cluster": ci, "size": len(cl), "order": order})
        stream, _ = merge_ordered_chunks([chunk_map[nid] for nid in order])
        cluster_streams.append((ci, cl, order, stream))

    variants: dict[str, bytes] = {}
    meta: dict[str, dict] = {}

    # g1: concatenate cluster streams sorted by cluster size and confidence.
    cluster_streams_sorted = sorted(
        cluster_streams,
        key=lambda x: (len(x[1]), sum(incoming_weight.get(n, 0) for n in x[1])),
        reverse=True,
    )
    g1 = b"".join(cs[3] for cs in cluster_streams_sorted)
    variants["g1_overlap_graph_cluster_concat"] = g1
    meta["g1_overlap_graph_cluster_concat"] = {
        "desc": "clustered by rolling-hash + overlap graph, then cluster streams concatenated",
        "cluster_count": len(cluster_streams_sorted),
    }

    # g2: best global path from strongest node, then append leftovers in confidence order.
    best_seed = max(node_ids, key=lambda n: incoming_weight.get(n, 0))
    used = {best_seed}
    path = [best_seed]
    cur = best_seed
    while True:
        nxt = None
        for edge in outgoing.get(cur, []):
            cand = edge["to"]
            if cand not in used:
                nxt = cand
                break
        if nxt is None:
            break
        used.add(nxt)
        path.append(nxt)
        cur = nxt

    leftovers = [n for n in sorted(node_ids, key=lambda x: incoming_weight.get(x, 0), reverse=True) if n not in used]
    full_path = path + leftovers
    g2, g2_ops = merge_ordered_chunks([chunk_map[n] for n in full_path])
    variants["g2_overlap_graph_best_path"] = g2
    meta["g2_overlap_graph_best_path"] = {
        "desc": "best-edge path from strongest seed + confidence-ordered leftovers",
        "seed": best_seed,
        "path": full_path,
        "ops": g2_ops[:160],
    }

    # g3: block dedup over best path stream.
    g3 = dedup_blocks(g2, BLOCK)
    variants["g3_overlap_graph_best_path_block_dedup_512"] = g3
    meta["g3_overlap_graph_best_path_block_dedup_512"] = {
        "desc": "512-byte block dedup over g2",
    }

    summary = {
        "input_count": len(nodes),
        "input_total": sum(n["size"] for n in nodes),
        "edge_count": edge_count,
        "min_overlap": MIN_OVERLAP,
        "max_overlap": MAX_OVERLAP,
        "rolling": {"window": ROLLING_WINDOW, "stride": ROLLING_STRIDE},
        "clusters": cluster_orders,
        "variants": {},
    }

    for name, blob in variants.items():
        out = OUT_DIR / f"{name}.bin"
        out.write_bytes(blob)
        summary["variants"][name] = {
            "file": str(out).replace("\\", "/"),
            "size": len(blob),
            "entropy": round(entropy(blob), 4) if blob else 0.0,
            "headers": headers(blob[:262144]) if blob else [],
            **meta.get(name, {}),
        }

    json_path = OUT_DIR / "overlap-graph-assembly-summary.json"
    md_path = OUT_DIR / "overlap-graph-assembly-summary.md"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    md = ["# Overlap Graph Assembly", ""]
    md.append(f"- Input chunks: {summary['input_count']}")
    md.append(f"- Input bytes: {summary['input_total']}")
    md.append(f"- Graph edges: {summary['edge_count']}")
    md.append("")
    md.append("## Cluster Orders")
    for cl in summary["clusters"]:
        md.append(f"- C{cl['cluster']} size={cl['size']} order={cl['order']}")
    md.append("")
    md.append("## Variants")
    for name, v in summary["variants"].items():
        hs = ", ".join(f"{h['name']}@{h['offset']}" for h in v.get("headers", [])) or "none"
        md.append(f"- {name}: size={v['size']} entropy={v['entropy']} headers={hs} -> {v['file']}")
    md_path.write_text("\n".join(md), encoding="utf-8")

    print(
        json.dumps(
            {
                "json": str(json_path).replace("\\", "/"),
                "md": str(md_path).replace("\\", "/"),
                "variants": {
                    k: {"size": v["size"], "headers": v["headers"]}
                    for k, v in summary["variants"].items()
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
