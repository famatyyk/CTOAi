import json
import math
from pathlib import Path

from x64dbg_automate import X64DbgClient
from x64dbg_automate.events import EventType

X32DBG = r"C:\Users\zycie\AppData\Local\Microsoft\WinGet\Packages\x64dbg.x64dbg_Microsoft.Winget.Source_8wekyb3d8bbwe\release\x32\x32dbg.exe"
ART = Path("artifacts/enc3")
CHUNKS_DIR = ART / "stream_chunks"
ART.mkdir(parents=True, exist_ok=True)
CHUNKS_DIR.mkdir(parents=True, exist_ok=True)

TARGET_SAMPLES = 80
EVENT_BUDGET = 260
WAIT_BP_SEC = 30
MAX_CHUNK_READ = 0x4000
MAX_TOTAL_BYTES = 2 * 1024 * 1024


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


def detect_headers(data: bytes):
    sigs = [("MZ", b"MZ"), ("PK", b"PK\x03\x04"), ("ENC3", b"ENC3"), ("ZLIB_78", b"\x78")]
    hits = []
    for name, sig in sigs:
        off = data.find(sig)
        if off != -1:
            hits.append({"name": name, "offset": off})
    hits.sort(key=lambda x: x["offset"])
    return hits


def rd32(c, addr):
    try:
        return int(c.read_dword(addr))
    except Exception:
        return None


def read_bytes(c, addr, size):
    try:
        if addr is None or size is None or size <= 0:
            return b""
        return bytes(c.read_memory(int(addr), int(size)))
    except Exception:
        return b""


def read_u64_ptr(c, ptr):
    if not ptr:
        return None
    lo = rd32(c, ptr)
    hi = rd32(c, ptr + 4)
    if lo is None or hi is None:
        return None
    return (int(hi) << 32) | int(lo)


def build_by_offset(segments):
    explicit = [s for s in segments if s.get("file_offset") is not None and s.get("size", 0) > 0]
    if not explicit:
        return b"", {"mode": "offset", "segments": 0, "range_start": None, "range_end": None, "coverage": 0.0}

    explicit.sort(key=lambda s: s["file_offset"])
    start = explicit[0]["file_offset"]
    end = max(s["file_offset"] + s["size"] for s in explicit)
    total = end - start
    if total <= 0:
        return b"", {"mode": "offset", "segments": len(explicit), "range_start": start, "range_end": end, "coverage": 0.0}

    buf = bytearray(total)
    mask = bytearray(total)

    for s in explicit:
        pos = s["file_offset"] - start
        blob = Path(s["chunk_file"]).read_bytes()
        n = min(len(blob), s["size"])
        if n <= 0:
            continue
        buf[pos : pos + n] = blob[:n]
        mask[pos : pos + n] = b"\x01" * n

    covered = sum(1 for b in mask if b)
    coverage = covered / total if total else 0.0
    return bytes(buf), {
        "mode": "offset",
        "segments": len(explicit),
        "range_start": start,
        "range_end": end,
        "total_span": total,
        "covered_bytes": covered,
        "coverage": round(coverage, 4),
    }


def build_by_order(segments):
    parts = []
    for s in segments:
        if s.get("size", 0) <= 0:
            continue
        parts.append(Path(s["chunk_file"]).read_bytes())
    data = b"".join(parts)
    return data, {"mode": "append", "segments": len(parts), "total_size": len(data)}


out = {
    "flow": "ntreadfile_stream_capture",
    "config": {
        "TARGET_SAMPLES": TARGET_SAMPLES,
        "EVENT_BUDGET": EVENT_BUDGET,
        "WAIT_BP_SEC": WAIT_BP_SEC,
        "MAX_CHUNK_READ": MAX_CHUNK_READ,
        "MAX_TOTAL_BYTES": MAX_TOTAL_BYTES,
    },
    "errors": [],
    "samples": [],
}

sessions = X64DbgClient.list_sessions()
out["sessions"] = [str(s) for s in sessions]
if not sessions:
    out["fatal"] = "no_x64dbg_session"
else:
    c = X64DbgClient(X32DBG)
    c.attach_session(sessions[-1].pid)
    out["is_debugging_before"] = bool(c.is_debugging())

    nt_addr = c.eval_sync("NtReadFile")[0]
    out["NtReadFile"] = nt_addr

    c.set_breakpoint("NtReadFile")

    total_bytes = 0
    events = 0
    handle_offsets = {}

    try:
        while len(out["samples"]) < TARGET_SAMPLES and events < EVENT_BUDGET and total_bytes < MAX_TOTAL_BYTES:
            c.go()
            ev = c.wait_for_debug_event(EventType.EVENT_BREAKPOINT, WAIT_BP_SEC)
            events += 1

            regs = c.get_regs().model_dump().get("context", {})
            eip = int(regs.get("eip", 0)) if isinstance(regs, dict) else 0
            esp = int(regs.get("esp", 0)) if isinstance(regs, dict) else 0

            if eip != int(nt_addr):
                continue

            args = {
                "FileHandle": rd32(c, esp + 0x4),
                "Event": rd32(c, esp + 0x8),
                "ApcRoutine": rd32(c, esp + 0xC),
                "ApcContext": rd32(c, esp + 0x10),
                "IoStatusBlock": rd32(c, esp + 0x14),
                "Buffer": rd32(c, esp + 0x18),
                "Length": rd32(c, esp + 0x1C),
                "ByteOffsetPtr": rd32(c, esp + 0x20),
                "Key": rd32(c, esp + 0x24),
            }
            explicit_off = read_u64_ptr(c, args["ByteOffsetPtr"])
            ret_addr = rd32(c, esp)

            sample = {
                "entry_event": str(ev),
                "eip": eip,
                "esp": esp,
                "args": args,
                "file_offset": explicit_off,
                "file_offset_source": "explicit" if explicit_off is not None else "none",
                "ret_addr": ret_addr,
            }

            if not ret_addr:
                sample["error"] = "no_return_address"
                out["samples"].append(sample)
                continue

            try:
                c.set_breakpoint(int(ret_addr))
                c.go()
                ev_ret = c.wait_for_debug_event(EventType.EVENT_BREAKPOINT, WAIT_BP_SEC)
                sample["ret_event"] = str(ev_ret)

                iosb = args.get("IoStatusBlock")
                iosb_status = rd32(c, iosb)
                iosb_info = rd32(c, iosb + 4) if iosb else None
                sample["iosb"] = {"status": iosb_status, "information": iosb_info}

                req = iosb_info if isinstance(iosb_info, int) and iosb_info > 0 else args.get("Length")
                size = min(int(req or 0), MAX_CHUNK_READ)
                blob = read_bytes(c, args.get("Buffer"), size)
                sample["size"] = len(blob)

                # If ByteOffset is NULL (sequential read), infer per-handle stream cursor.
                if sample.get("file_offset") is None:
                    fh = args.get("FileHandle")
                    if isinstance(fh, int) and fh > 0:
                        cur = int(handle_offsets.get(fh, 0))
                        sample["file_offset"] = cur
                        sample["file_offset_source"] = "synthetic_handle_cursor"
                        handle_offsets[fh] = cur + len(blob)

                idx = len(out["samples"]) + 1
                chunk_path = CHUNKS_DIR / f"chunk-{idx:03d}.bin"
                chunk_path.write_bytes(blob)
                sample["chunk_file"] = str(chunk_path).replace('\\', '/')
                sample["entropy"] = round(entropy(blob), 4)
                sample["headers"] = detect_headers(blob[:4096])

                total_bytes += len(blob)
            except Exception as e:
                sample["error"] = str(e)
            finally:
                try:
                    c.clear_breakpoint(int(ret_addr))
                except Exception:
                    pass

            out["samples"].append(sample)

    except Exception as e:
        out["fatal"] = str(e)

    offset_data, offset_meta = build_by_offset(out["samples"])
    append_data, append_meta = build_by_order(out["samples"])

    off_path = ART / "kingsvale-ntreadfile-stream-assembled-offset.bin"
    app_path = ART / "kingsvale-ntreadfile-stream-assembled-append.bin"
    off_path.write_bytes(offset_data)
    app_path.write_bytes(append_data)

    out["assembled"] = {
        "offset": {
            **offset_meta,
            "file": str(off_path).replace('\\', '/'),
            "size": len(offset_data),
            "entropy": round(entropy(offset_data), 4) if offset_data else 0.0,
            "headers": detect_headers(offset_data[:32768]) if offset_data else [],
        },
        "append": {
            **append_meta,
            "file": str(app_path).replace('\\', '/'),
            "size": len(append_data),
            "entropy": round(entropy(append_data), 4) if append_data else 0.0,
            "headers": detect_headers(append_data[:32768]) if append_data else [],
        },
    }

    src_counts = {}
    for s in out["samples"]:
        k = s.get("file_offset_source", "none")
        src_counts[k] = src_counts.get(k, 0) + 1
    out["offset_source_counts"] = src_counts

out_path = ART / "kingsvale-ntreadfile-stream-capture.json"
out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps({
    "samples": len(out.get("samples", [])),
    "offset_size": out.get("assembled", {}).get("offset", {}).get("size", 0),
    "append_size": out.get("assembled", {}).get("append", {}).get("size", 0),
    "offset_headers": out.get("assembled", {}).get("offset", {}).get("headers", []),
    "append_headers": out.get("assembled", {}).get("append", {}).get("headers", []),
    "offset_source_counts": out.get("offset_source_counts", {}),
    "json": str(out_path).replace('\\', '/'),
}, indent=2))
