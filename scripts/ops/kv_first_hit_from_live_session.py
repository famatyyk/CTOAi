import json
import math
from pathlib import Path

from x64dbg_automate import X64DbgClient
from x64dbg_automate.events import EventType

MAX_DUMP = 0x2000
EVENT_BUDGET = 60
NTREADFILE_SCAN_COUNT = 20
WINDOW_SIZE = 0x400
WINDOW_STEP = 0x100
ENTROPY_WINDOW = 0x200
ENTROPY_STEP = 0x80
ENTROPY_THRESHOLD = 6.8
ENTROPY_MIN_REGION = 0x400
ENTROPY_MEDIUM_THRESHOLD = 6.0
ENTROPY_MEDIUM_MIN_REGION = 0x300


def _safe_read_dword(client, addr):
    try:
        return int(client.read_dword(addr))
    except Exception:
        return None


def _safe_read_bytes(client, addr, size):
    try:
        if addr is None or size is None or size <= 0:
            return b""
        return bytes(client.read_memory(int(addr), int(size)))
    except Exception:
        return b""


def _ascii_preview(data):
    return "".join(chr(b) if 32 <= b <= 126 else "." for b in data)


def _dump_blob(addr, requested_len, data):
    return {
        "addr": addr,
        "requested_len": int(requested_len or 0),
        "dumped_len": len(data),
        "hex": data.hex(),
        "ascii_preview": _ascii_preview(data[:128]),
    }


def _detect_headers(data):
    signatures = [
        ("MZ", b"MZ"),
        ("PK", b"PK\x03\x04"),
        ("ENC3", b"ENC3"),
    ]
    hits = []
    for name, sig in signatures:
        off = data.find(sig)
        if off != -1:
            hits.append({"header": name, "offset": off})
    hits.sort(key=lambda x: x["offset"])
    return hits


def _extract_payload(data, artifact_dir):
    header_hits = _detect_headers(data)
    extraction = {
        "detected_headers": header_hits,
        "extracted": False,
    }
    if not header_hits:
        return extraction

    best = header_hits[0]
    offset = int(best["offset"])
    payload = data[offset:]
    payload_path = artifact_dir / "kingsvale-buffer-payload-post.bin"
    payload_path.write_bytes(payload)

    extraction.update(
        {
            "extracted": True,
            "selected_header": best["header"],
            "selected_offset": offset,
            "payload_size": len(payload),
            "payload_file": str(payload_path).replace('\\', '/'),
            "scan_mode": "direct",
        }
    )
    return extraction


def _scan_moving_windows(chunks, window_size=WINDOW_SIZE, step=WINDOW_STEP):
    joined = b"".join(chunks)
    result = {
        "joined_size": len(joined),
        "window_size": window_size,
        "step": step,
        "hits": [],
        "extracted": False,
    }
    if not joined:
        return result

    end = max(1, len(joined) - window_size + 1)
    seen = set()
    for start in range(0, end, step):
        window = joined[start : start + window_size]
        for hit in _detect_headers(window):
            global_off = start + int(hit["offset"])
            key = (hit["header"], global_off)
            if key in seen:
                continue
            seen.add(key)
            result["hits"].append(
                {
                    "header": hit["header"],
                    "global_offset": global_off,
                    "window_start": start,
                }
            )

    result["hits"].sort(key=lambda x: x["global_offset"])
    return result


def _extract_from_joined_scan(joined_data, moving_scan, artifact_dir):
    if not moving_scan.get("hits"):
        return None

    best = moving_scan["hits"][0]
    offset = int(best["global_offset"])
    payload = joined_data[offset:]
    payload_path = artifact_dir / "kingsvale-buffer-payload-post.bin"
    payload_path.write_bytes(payload)

    return {
        "detected_headers": moving_scan["hits"],
        "extracted": True,
        "selected_header": best["header"],
        "selected_offset": offset,
        "payload_size": len(payload),
        "payload_file": str(payload_path).replace('\\', '/'),
        "scan_mode": "moving_window",
        "window_size": moving_scan.get("window_size"),
        "step": moving_scan.get("step"),
        "joined_size": moving_scan.get("joined_size"),
    }


def _entropy(data):
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


def _high_entropy_regions(data, window=ENTROPY_WINDOW, step=ENTROPY_STEP, threshold=ENTROPY_THRESHOLD, min_region=ENTROPY_MIN_REGION):
    if len(data) < window:
        return []

    hot = []
    for start in range(0, len(data) - window + 1, step):
        chunk = data[start : start + window]
        h = _entropy(chunk)
        if h >= threshold:
            hot.append((start, start + window, h))

    if not hot:
        return []

    merged = []
    cur_s, cur_e, cur_h = hot[0]
    hvals = [cur_h]
    for s, e, h in hot[1:]:
        if s <= cur_e:
            cur_e = max(cur_e, e)
            hvals.append(h)
        else:
            if cur_e - cur_s >= min_region:
                merged.append({
                    "start": cur_s,
                    "end": cur_e,
                    "length": cur_e - cur_s,
                    "max_entropy": max(hvals),
                    "avg_entropy": sum(hvals) / len(hvals),
                })
            cur_s, cur_e, cur_h = s, e, h
            hvals = [h]

    if cur_e - cur_s >= min_region:
        merged.append({
            "start": cur_s,
            "end": cur_e,
            "length": cur_e - cur_s,
            "max_entropy": max(hvals),
            "avg_entropy": sum(hvals) / len(hvals),
        })
    return merged


def _carve_regions(data, regions, artifact_dir, prefix):
    carved = []
    for i, r in enumerate(regions, start=1):
        payload = data[r["start"] : r["end"]]
        path = artifact_dir / f"{prefix}-{i:02d}.bin"
        path.write_bytes(payload)
        carved.append(
            {
                "index": i,
                "file": str(path).replace('\\', '/'),
                "start": r["start"],
                "end": r["end"],
                "length": r["length"],
                "max_entropy": r["max_entropy"],
                "avg_entropy": r["avg_entropy"],
            }
        )
    return carved


out = {"flow": "first_hit_from_live_session", "errors": []}
artifact_dir = Path("artifacts/enc3")
artifact_dir.mkdir(parents=True, exist_ok=True)

sessions = X64DbgClient.list_sessions()
out["sessions"] = [str(s) for s in sessions]
if not sessions:
    out["fatal"] = "no_x64dbg_sessions_found"
else:
    sess = sessions[-1]
    out["selected_session_pid"] = sess.pid
    c = X64DbgClient(
        r"C:\Users\zycie\AppData\Local\Microsoft\WinGet\Packages\x64dbg.x64dbg_Microsoft.Winget.Source_8wekyb3d8bbwe\release\x32\x32dbg.exe"
    )
    c.attach_session(sess.pid)
    out["is_debugging_before"] = bool(c.is_debugging())

    readfile_addr = c.eval_sync("ReadFile")[0]
    ntreadfile_addr = c.eval_sync("NtReadFile")[0]
    out["api_addresses"] = {
        "ReadFile": readfile_addr,
        "NtReadFile": ntreadfile_addr,
    }

    bps = []
    for name in ["CreateFileW", "ReadFile", "NtReadFile", "RtlDecompressBuffer"]:
        try:
            bps.append([name, bool(c.set_breakpoint(name))])
        except Exception as e:
            bps.append([name, f"err: {e}"])

    for addr in [0x005D5900, 0x005DEA30, 0x005CD050, 0x005CEB30]:
        try:
            bps.append([hex(addr), bool(c.set_breakpoint(addr))])
        except Exception as e:
            bps.append([hex(addr), f"err: {e}"])

    out["breakpoints"] = bps

    out["config"] = {
        "MAX_DUMP": MAX_DUMP,
        "EVENT_BUDGET": EVENT_BUDGET,
        "NTREADFILE_SCAN_COUNT": NTREADFILE_SCAN_COUNT,
        "WINDOW_SIZE": WINDOW_SIZE,
        "WINDOW_STEP": WINDOW_STEP,
        "ENTROPY_WINDOW": ENTROPY_WINDOW,
        "ENTROPY_STEP": ENTROPY_STEP,
        "ENTROPY_THRESHOLD": ENTROPY_THRESHOLD,
        "ENTROPY_MIN_REGION": ENTROPY_MIN_REGION,
        "ENTROPY_MEDIUM_THRESHOLD": ENTROPY_MEDIUM_THRESHOLD,
        "ENTROPY_MEDIUM_MIN_REGION": ENTROPY_MEDIUM_MIN_REGION,
    }

    try:
        out["hit_trace"] = []
        out["ntreadfile_samples"] = []
        post_chunks = []
        target_hit_done = False
        readfile_done = False

        event_count = 0
        while event_count < EVENT_BUDGET:
            c.go()
            ev = c.wait_for_debug_event(EventType.EVENT_BREAKPOINT, 45)
            event_count += 1

            regs = c.get_regs()
            dump = regs.model_dump() if hasattr(regs, "model_dump") else {}
            ctx = dump.get("context", {}) if isinstance(dump, dict) else {}

            if not (isinstance(ctx, dict) and "eip" in ctx):
                out["hit_trace"].append({"arch": "unknown", "event": str(ev)})
                continue

            ip = int(ctx.get("eip", 0))
            sp = int(ctx.get("esp", 0))
            if ip == int(readfile_addr):
                hit_api = "ReadFile"
            elif ip == int(ntreadfile_addr):
                hit_api = "NtReadFile"
            else:
                hit_api = None

            out["hit_trace"].append(
                {
                    "ip": ip,
                    "sp": sp,
                    "hit_api": hit_api,
                    "event": str(ev),
                }
            )

            if not hit_api:
                continue

            out["hit"] = str(ev)
            out["arch"] = "x32"
            out["hit_api"] = hit_api
            out["regs"] = {
                "ip": ip,
                "sp": sp,
                "ax": ctx.get("eax"),
                "bx": ctx.get("ebx"),
                "cx": ctx.get("ecx"),
                "dx": ctx.get("edx"),
                "si": ctx.get("esi"),
                "di": ctx.get("edi"),
            }

            if hit_api == "ReadFile" and not readfile_done:
                args = {
                    "hFile": _safe_read_dword(c, sp + 0x4),
                    "lpBuffer": _safe_read_dword(c, sp + 0x8),
                    "nNumberOfBytesToRead": _safe_read_dword(c, sp + 0xC),
                    "lpNumberOfBytesRead": _safe_read_dword(c, sp + 0x10),
                    "lpOverlapped": _safe_read_dword(c, sp + 0x14),
                }
                out["api_args"] = args
                req_len = min(int(args["nNumberOfBytesToRead"] or 0), MAX_DUMP)
                pre = _safe_read_bytes(c, args["lpBuffer"], req_len)
                out["buffer_dump_pre"] = _dump_blob(args["lpBuffer"], args["nNumberOfBytesToRead"], pre)
                out["post_header_scan"] = _extract_payload(pre, artifact_dir)
                readfile_done = True
                if out["post_header_scan"].get("extracted"):
                    target_hit_done = True
                    break

            if hit_api == "NtReadFile" and len(out["ntreadfile_samples"]) < NTREADFILE_SCAN_COUNT:
                args = {
                    "FileHandle": _safe_read_dword(c, sp + 0x4),
                    "Event": _safe_read_dword(c, sp + 0x8),
                    "ApcRoutine": _safe_read_dword(c, sp + 0xC),
                    "ApcContext": _safe_read_dword(c, sp + 0x10),
                    "IoStatusBlock": _safe_read_dword(c, sp + 0x14),
                    "Buffer": _safe_read_dword(c, sp + 0x18),
                    "Length": _safe_read_dword(c, sp + 0x1C),
                    "ByteOffset": _safe_read_dword(c, sp + 0x20),
                    "Key": _safe_read_dword(c, sp + 0x24),
                }

                req_len = min(int(args["Length"] or 0), MAX_DUMP)
                pre = _safe_read_bytes(c, args["Buffer"], req_len)
                sample = {
                    "api_args": args,
                    "buffer_dump_pre": _dump_blob(args["Buffer"], args["Length"], pre),
                }

                ret_addr = _safe_read_dword(c, sp)
                sample["return"] = {"return_addr": ret_addr}

                if ret_addr:
                    try:
                        sample["return"]["ret_bp_set"] = bool(c.set_breakpoint(int(ret_addr)))
                        c.go()
                        ev_ret = c.wait_for_debug_event(EventType.EVENT_BREAKPOINT, 45)
                        sample["return"]["ret_event"] = str(ev_ret)

                        iosb = args.get("IoStatusBlock")
                        iosb_status = _safe_read_dword(c, iosb)
                        iosb_info = _safe_read_dword(c, (iosb + 4) if iosb else None)
                        sample["return"]["iosb"] = {
                            "status": iosb_status,
                            "information": iosb_info,
                        }

                        post_req = iosb_info if isinstance(iosb_info, int) and iosb_info > 0 else args.get("Length")
                        post_len = min(int(post_req or 0), MAX_DUMP)
                        post = _safe_read_bytes(c, args["Buffer"], post_len)
                        sample["buffer_dump_post"] = _dump_blob(args["Buffer"], post_req, post)
                        sample["direct_scan"] = _extract_payload(post, artifact_dir)
                        post_chunks.append(post)

                        if sample["direct_scan"].get("extracted"):
                            out["post_header_scan"] = sample["direct_scan"]
                            out["api_args"] = args
                            out["ntreadfile_return"] = sample["return"]
                            out["buffer_dump_pre"] = sample["buffer_dump_pre"]
                            out["buffer_dump_post"] = sample["buffer_dump_post"]
                            out["hit_api"] = "NtReadFile"
                            target_hit_done = True
                            out["ntreadfile_samples"].append(sample)
                            break
                    except Exception as e:
                        sample["return"]["error"] = str(e)
                    finally:
                        try:
                            c.clear_breakpoint(int(ret_addr))
                        except Exception:
                            pass

                out["ntreadfile_samples"].append(sample)

                if len(out["ntreadfile_samples"]) >= NTREADFILE_SCAN_COUNT:
                    break

        if not target_hit_done:
            if post_chunks:
                moving = _scan_moving_windows(post_chunks)
                joined = b"".join(post_chunks)
                extracted = _extract_from_joined_scan(joined, moving, artifact_dir)
                if extracted:
                    out["post_header_scan"] = extracted
                    target_hit_done = True
                else:
                    out["post_header_scan"] = {
                        "detected_headers": moving.get("hits", []),
                        "extracted": False,
                        "scan_mode": "moving_window",
                        "window_size": moving.get("window_size"),
                        "step": moving.get("step"),
                        "joined_size": moving.get("joined_size"),
                    }

                regions_high = _high_entropy_regions(
                    joined,
                    threshold=ENTROPY_THRESHOLD,
                    min_region=ENTROPY_MIN_REGION,
                )
                carved_high = _carve_regions(
                    joined,
                    regions_high,
                    artifact_dir,
                    "kingsvale-entropy-carve-high",
                ) if regions_high else []

                regions_medium = _high_entropy_regions(
                    joined,
                    threshold=ENTROPY_MEDIUM_THRESHOLD,
                    min_region=ENTROPY_MEDIUM_MIN_REGION,
                )
                carved_medium = _carve_regions(
                    joined,
                    regions_medium,
                    artifact_dir,
                    "kingsvale-entropy-carve-medium",
                ) if regions_medium else []

                out["entropy_scan"] = {
                    "joined_size": len(joined),
                    "window": ENTROPY_WINDOW,
                    "step": ENTROPY_STEP,
                    "high_threshold": ENTROPY_THRESHOLD,
                    "high_min_region": ENTROPY_MIN_REGION,
                    "high_regions_found": len(regions_high),
                    "high_regions": regions_high,
                    "high_carved_files": carved_high,
                    "medium_threshold": ENTROPY_MEDIUM_THRESHOLD,
                    "medium_min_region": ENTROPY_MEDIUM_MIN_REGION,
                    "medium_regions_found": len(regions_medium),
                    "medium_regions": regions_medium,
                    "medium_carved_files": carved_medium,
                }

        if not target_hit_done and "hit_error" not in out:
            out["hit_error"] = "No payload header found across configured NtReadFile samples"

    except Exception as e:
        out["hit_error"] = str(e)

out_path = artifact_dir / "kingsvale-first-hit-live-session.json"
out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps(out, indent=2))


