import json
import math
import time
from pathlib import Path

from x64dbg_automate import X64DbgClient
from x64dbg_automate.events import EventType

X32DBG = r"C:\Users\zycie\AppData\Local\Microsoft\WinGet\Packages\x64dbg.x64dbg_Microsoft.Winget.Source_8wekyb3d8bbwe\release\x32\x32dbg.exe"
ART = Path("artifacts/enc3")
DUMPS = ART / "runtime_crypto_dumps"
REPORT = ART / "kingsvale-runtime-crypto-live.json"
ART.mkdir(parents=True, exist_ok=True)
DUMPS.mkdir(parents=True, exist_ok=True)

TIMEBOX_SEC = 240
WAIT_BP_SEC = 3
MAX_EVENTS = 1200
MAX_DUMPS = 800
DUMP_LIMIT = 2 * 1024 * 1024


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
        ("PE", b"PE\x00\x00"),
        ("PK", b"PK\x03\x04"),
        ("GZIP", b"\x1f\x8b\x08"),
        ("ZLIB_7801", b"\x78\x01"),
        ("ZLIB_789C", b"\x78\x9c"),
        ("ZLIB_78DA", b"\x78\xda"),
        ("ENC3", b"ENC3"),
    ]
    out = []
    for n, s in sigs:
        p = data.find(s)
        if p != -1:
            out.append({"name": n, "offset": p})
    out.sort(key=lambda x: x["offset"])
    return out


def rd32(c, addr):
    try:
        return int(c.read_dword(int(addr)))
    except Exception:
        return None


def rb(c, addr, size):
    try:
        if not isinstance(addr, int) or not isinstance(size, int) or addr <= 0 or size <= 0:
            return b""
        return bytes(c.read_memory(int(addr), int(size)))
    except Exception:
        return b""


def resolve_symbol(c, names):
    for n in names:
        v = None
        try:
            v = c.eval_sync(n)[0]
        except Exception as exc:
            print(f"[capture_runtime_crypto] resolve_symbol failed for {n}: {exc}")
        if isinstance(v, int) and v > 0:
            return n, v
    return None, None


report = {
    "flow": "runtime_crypto_decompress_return_dump",
    "status": "starting",
    "config": {
        "TIMEBOX_SEC": TIMEBOX_SEC,
        "WAIT_BP_SEC": WAIT_BP_SEC,
        "MAX_EVENTS": MAX_EVENTS,
        "MAX_DUMPS": MAX_DUMPS,
        "DUMP_LIMIT": DUMP_LIMIT,
    },
    "events": [],
    "dumps": [],
    "errors": [],
}


def flush(status=None, summary=None):
    if status:
        report["status"] = status
    if summary is not None:
        report["summary"] = summary
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")


def record_error(context, exc):
    report["errors"].append({"context": str(context), "error": str(exc)})


def clear_breakpoint(addr, context):
    try:
        c.clear_breakpoint(int(addr))
    except Exception as exc:
        record_error(context, exc)


def dump_blob(kind, blob: bytes, meta=None):
    if not blob:
        return None
    if len(report["dumps"]) >= MAX_DUMPS:
        return None
    idx = len(report["dumps"]) + 1
    fp = DUMPS / f"{kind}-{idx:04d}.bin"
    fp.write_bytes(blob)
    item = {
        "kind": kind,
        "file": str(fp).replace("\\", "/"),
        "size": len(blob),
        "entropy": round(entropy(blob), 4),
        "headers": headers(blob[:131072]),
    }
    if meta:
        item.update(meta)
    report["dumps"].append(item)
    return item


def capture_return_for_rtl(c, esp):
    # NTSTATUS RtlDecompressBuffer(format, outBuf, outSize, inBuf, inSize, finalOutPtr)
    out_buf = rd32(c, esp + 0x8)
    out_cap = rd32(c, esp + 0xC)
    in_buf = rd32(c, esp + 0x10)
    in_size = rd32(c, esp + 0x14)
    final_out_ptr = rd32(c, esp + 0x18)
    ret = rd32(c, esp)
    if not isinstance(ret, int) or ret <= 0:
        return

    try:
        c.set_breakpoint(int(ret))
        c.go()
        c.wait_for_debug_event(EventType.EVENT_BREAKPOINT, WAIT_BP_SEC)
        rr = c.get_regs().model_dump().get("context", {})
        status = int(rr.get("eax", 0)) if isinstance(rr, dict) else 0
        final_out = rd32(c, final_out_ptr) if isinstance(final_out_ptr, int) else None

        guess_len = final_out if isinstance(final_out, int) and final_out > 0 else out_cap
        if not isinstance(guess_len, int) or guess_len <= 0:
            guess_len = 0
        got = min(max(0, guess_len), DUMP_LIMIT)
        blob = rb(c, out_buf, got) if got > 0 else b""
        d = dump_blob(
            "rtl_decompress_out",
            blob,
            {
                "api": "RtlDecompressBuffer",
                "status": status,
                "out_buf": out_buf,
                "out_cap": out_cap,
                "final_out": final_out,
                "in_buf": in_buf,
                "in_size": in_size,
            },
        ) if blob else None

        report["events"].append(
            {
                "type": "RtlDecompressBuffer",
                "status": status,
                "out_cap": out_cap,
                "final_out": final_out,
                "in_size": in_size,
                "dump": d.get("file") if d else None,
            }
        )
    except Exception as ex:
        report["events"].append({"type": "RtlDecompressBuffer_error", "error": str(ex)})
    finally:
        clear_breakpoint(ret, "RtlDecompressBuffer:return")


def capture_return_for_bcrypt(c, esp):
    # NTSTATUS BCryptDecrypt(hKey, pbInput, cbInput, pPaddingInfo, pbIV, cbIV, pbOutput, cbOutput, pcbResult, dwFlags)
    pb_input = rd32(c, esp + 0x8)
    cb_input = rd32(c, esp + 0xC)
    pb_iv = rd32(c, esp + 0x14)
    cb_iv = rd32(c, esp + 0x18)
    pb_output = rd32(c, esp + 0x1C)
    cb_output = rd32(c, esp + 0x20)
    pcb_result = rd32(c, esp + 0x24)
    flags = rd32(c, esp + 0x28)
    ret = rd32(c, esp)
    if not isinstance(ret, int) or ret <= 0:
        return

    try:
        c.set_breakpoint(int(ret))
        c.go()
        c.wait_for_debug_event(EventType.EVENT_BREAKPOINT, WAIT_BP_SEC)
        rr = c.get_regs().model_dump().get("context", {})
        status = int(rr.get("eax", 0)) if isinstance(rr, dict) else 0
        out_len = rd32(c, pcb_result) if isinstance(pcb_result, int) else None

        guess_len = out_len if isinstance(out_len, int) and out_len > 0 else cb_output
        if not isinstance(guess_len, int) or guess_len <= 0:
            guess_len = 0
        got = min(max(0, guess_len), DUMP_LIMIT)
        blob = rb(c, pb_output, got) if got > 0 and isinstance(pb_output, int) and pb_output > 0 else b""
        d = dump_blob(
            "bcrypt_decrypt_out",
            blob,
            {
                "api": "BCryptDecrypt",
                "status": status,
                "cb_input": cb_input,
                "cb_output": cb_output,
                "out_len": out_len,
                "flags": flags,
                "iv_len": cb_iv,
                "pb_input": pb_input,
                "pb_iv": pb_iv,
                "pb_output": pb_output,
            },
        ) if blob else None

        report["events"].append(
            {
                "type": "BCryptDecrypt",
                "status": status,
                "cb_input": cb_input,
                "cb_output": cb_output,
                "out_len": out_len,
                "flags": flags,
                "dump": d.get("file") if d else None,
            }
        )
    except Exception as ex:
        report["events"].append({"type": "BCryptDecrypt_error", "error": str(ex)})
    finally:
        clear_breakpoint(ret, "BCryptDecrypt:return")


def capture_return_for_crypt(c, esp):
    # BOOL CryptDecrypt(hKey, hHash, Final, dwFlags, pbData, pdwDataLen)
    final_flag = rd32(c, esp + 0xC)
    flags = rd32(c, esp + 0x10)
    pb_data = rd32(c, esp + 0x14)
    pdw_data_len = rd32(c, esp + 0x18)
    ret = rd32(c, esp)
    if not isinstance(ret, int) or ret <= 0:
        return

    try:
        c.set_breakpoint(int(ret))
        c.go()
        c.wait_for_debug_event(EventType.EVENT_BREAKPOINT, WAIT_BP_SEC)
        rr = c.get_regs().model_dump().get("context", {})
        ok = int(rr.get("eax", 0)) if isinstance(rr, dict) else 0
        out_len = rd32(c, pdw_data_len) if isinstance(pdw_data_len, int) else None

        got = min(max(0, out_len if isinstance(out_len, int) else 0), DUMP_LIMIT)
        blob = rb(c, pb_data, got) if got > 0 and isinstance(pb_data, int) and pb_data > 0 else b""
        d = dump_blob(
            "crypt_decrypt_out",
            blob,
            {
                "api": "CryptDecrypt",
                "ok": bool(ok),
                "final": final_flag,
                "flags": flags,
                "out_len": out_len,
                "pb_data": pb_data,
            },
        ) if blob else None

        report["events"].append(
            {
                "type": "CryptDecrypt",
                "ok": bool(ok),
                "final": final_flag,
                "flags": flags,
                "out_len": out_len,
                "dump": d.get("file") if d else None,
            }
        )
    except Exception as ex:
        report["events"].append({"type": "CryptDecrypt_error", "error": str(ex)})
    finally:
        clear_breakpoint(ret, "CryptDecrypt:return")


def capture_return_for_ncrypt(c, esp):
    # SECURITY_STATUS NCryptDecrypt(hKey, pbInput, cbInput, pPaddingInfo, pbOutput, cbOutput, pcbResult, dwFlags)
    pb_input = rd32(c, esp + 0x8)
    cb_input = rd32(c, esp + 0xC)
    pb_output = rd32(c, esp + 0x14)
    cb_output = rd32(c, esp + 0x18)
    pcb_result = rd32(c, esp + 0x1C)
    flags = rd32(c, esp + 0x20)
    ret = rd32(c, esp)
    if not isinstance(ret, int) or ret <= 0:
        return

    try:
        c.set_breakpoint(int(ret))
        c.go()
        c.wait_for_debug_event(EventType.EVENT_BREAKPOINT, WAIT_BP_SEC)
        rr = c.get_regs().model_dump().get("context", {})
        status = int(rr.get("eax", 0)) if isinstance(rr, dict) else 0
        out_len = rd32(c, pcb_result) if isinstance(pcb_result, int) else None

        guess_len = out_len if isinstance(out_len, int) and out_len > 0 else cb_output
        got = min(max(0, guess_len if isinstance(guess_len, int) else 0), DUMP_LIMIT)
        blob = rb(c, pb_output, got) if got > 0 and isinstance(pb_output, int) and pb_output > 0 else b""
        d = dump_blob(
            "ncrypt_decrypt_out",
            blob,
            {
                "api": "NCryptDecrypt",
                "status": status,
                "cb_input": cb_input,
                "cb_output": cb_output,
                "out_len": out_len,
                "flags": flags,
                "pb_input": pb_input,
                "pb_output": pb_output,
            },
        ) if blob else None

        report["events"].append(
            {
                "type": "NCryptDecrypt",
                "status": status,
                "cb_input": cb_input,
                "cb_output": cb_output,
                "out_len": out_len,
                "flags": flags,
                "dump": d.get("file") if d else None,
            }
        )
    except Exception as ex:
        report["events"].append({"type": "NCryptDecrypt_error", "error": str(ex)})
    finally:
        clear_breakpoint(ret, "NCryptDecrypt:return")


flush("starting")
sessions = X64DbgClient.list_sessions()
report["sessions"] = [str(s) for s in sessions]
if not sessions:
    report["fatal"] = "no_x64dbg_session"
    flush("fatal", {"events_seen": 0, "dumps": 0, "elapsed_sec": 0})
    print(json.dumps({"json": str(REPORT).replace("\\", "/"), "fatal": report["fatal"]}, indent=2))
    raise SystemExit(0)

c = X64DbgClient(X32DBG)
c.attach_session(sessions[-1].pid)
report["state_before"] = {"is_debugging": bool(c.is_debugging()), "is_running": bool(c.is_running())}

hooks = {}
hook_candidates = [
    "RtlDecompressBuffer",
    "ntdll!RtlDecompressBuffer",
    "RtlDecompressBufferEx",
    "ntdll!RtlDecompressBufferEx",
    "RtlDecompressBufferEx2",
    "ntdll!RtlDecompressBufferEx2",
    "RtlDecompressFragment",
    "ntdll!RtlDecompressFragment",
    "BCryptDecrypt",
    "bcrypt!BCryptDecrypt",
    "CryptDecrypt",
    "advapi32!CryptDecrypt",
    "NCryptDecrypt",
    "ncrypt!NCryptDecrypt",
]
seen_addrs = set()
for sym in hook_candidates:
    name, addr = resolve_symbol(c, [sym])
    if not addr:
        continue
    if int(addr) in seen_addrs:
        continue
    seen_addrs.add(int(addr))
    hooks[name] = int(addr)
    c.set_breakpoint(name)

report["hooks"] = hooks
flush("running")

start = time.time()
seen = 0
try:
    while (time.time() - start) < TIMEBOX_SEC and seen < MAX_EVENTS:
        c.go()
        c.wait_for_debug_event(EventType.EVENT_BREAKPOINT, WAIT_BP_SEC)
        seen += 1

        regs = c.get_regs().model_dump().get("context", {})
        eip = int(regs.get("eip", 0)) if isinstance(regs, dict) else 0
        esp = int(regs.get("esp", 0)) if isinstance(regs, dict) else 0

        # Entry breakpoints -> set temporary return breakpoint and capture output buffer post-call.
        hit = None
        for n, a in hooks.items():
            if eip == int(a):
                hit = n
                break
        if not hit:
            continue

        report["events"].append({
            "type": "hook_entry",
            "hook": hit,
            "eip": eip,
            "esp": esp,
        })

        if "RtlDecompress" in hit:
            capture_return_for_rtl(c, esp)
            flush("running")
            continue
        if "BCryptDecrypt" in hit:
            capture_return_for_bcrypt(c, esp)
            flush("running")
            continue
        if "CryptDecrypt" in hit:
            capture_return_for_crypt(c, esp)
            flush("running")
            continue
        if "NCryptDecrypt" in hit:
            capture_return_for_ncrypt(c, esp)
            flush("running")
            continue

except Exception as ex:
    report["error"] = str(ex)
finally:
    for n in hooks.keys():
        clear_breakpoint(n, f"hook:{n}")

summary = {
    "events_seen": seen,
    "events": len(report.get("events", [])),
    "dumps": len(report.get("dumps", [])),
    "elapsed_sec": round(time.time() - start, 2),
}
flush("done", summary)
print(json.dumps({"json": str(REPORT).replace("\\", "/"), "summary": summary, "hooks": hooks}, indent=2))
