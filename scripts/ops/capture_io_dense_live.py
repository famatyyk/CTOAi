import json
import math
import time
from pathlib import Path

from x64dbg_automate import X64DbgClient
from x64dbg_automate.events import EventType

X32DBG = r"C:\Users\zycie\AppData\Local\Microsoft\WinGet\Packages\x64dbg.x64dbg_Microsoft.Winget.Source_8wekyb3d8bbwe\release\x32\x32dbg.exe"
ART = Path("artifacts/enc3")
DUMPS = ART / "io_dense_dumps"
REPORT = ART / "kingsvale-io-dense-live.json"
ART.mkdir(parents=True, exist_ok=True)
DUMPS.mkdir(parents=True, exist_ok=True)

TIMEBOX_SEC = 240
WAIT_BP_SEC = 3
MAX_EVENTS = 1000
CHUNK_DUMP_LIMIT = 64 * 1024
REGION_DUMP_CAP = 8 * 1024 * 1024
PAGE = 0x1000
MAX_WATCH_PAGES = 8
MAX_DUMPS = 600


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
    sigs = [("MZ", b"MZ"), ("PK", b"PK\x03\x04"), ("ENC3", b"ENC3"), ("GZIP", b"\x1f\x8b\x08"), ("ZLIB_78", b"\x78")]
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
            print(f"[capture_io_dense_live] resolve_symbol failed for {n}: {exc}")
        if isinstance(v, int) and v > 0:
            return n, v
    return None, None


report = {
    "flow": "io_dense_exec_watch",
    "status": "starting",
    "config": {
        "TIMEBOX_SEC": TIMEBOX_SEC,
        "WAIT_BP_SEC": WAIT_BP_SEC,
        "MAX_EVENTS": MAX_EVENTS,
        "CHUNK_DUMP_LIMIT": CHUNK_DUMP_LIMIT,
        "REGION_DUMP_CAP": REGION_DUMP_CAP,
        "MAX_WATCH_PAGES": MAX_WATCH_PAGES,
        "MAX_DUMPS": MAX_DUMPS,
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


def add_dump(item):
    if len(report["dumps"]) >= MAX_DUMPS:
        return None
    report["dumps"].append(item)
    return item


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
        "file": str(fp).replace('\\', '/'),
        "captured": len(blob),
        "entropy": round(entropy(blob), 4),
        "headers": headers(blob[:65536]),
    }
    if meta:
        item.update(meta)
    return add_dump(item)


def dump_region(c, kind, base, size, meta=None):
    if not isinstance(base, int) or not isinstance(size, int) or base <= 0 or size <= 0:
        return None
    blob = rb(c, base, min(size, REGION_DUMP_CAP))
    return dump_blob(kind, blob, {**(meta or {}), "base": base, "size": size})


flush("starting")
sessions = X64DbgClient.list_sessions()
report["sessions"] = [str(s) for s in sessions]
if not sessions:
    report["fatal"] = "no_x64dbg_session"
    flush("fatal", {"events_seen": 0, "dumps": 0, "elapsed_sec": 0})
    print(json.dumps({"json": str(REPORT).replace('\\', '/'), "fatal": report["fatal"]}, indent=2))
    raise SystemExit(0)

c = X64DbgClient(X32DBG)
c.attach_session(sessions[-1].pid)
report["state_before"] = {"is_debugging": bool(c.is_debugging()), "is_running": bool(c.is_running())}

hooks = {}
name, addr = resolve_symbol(c, ["CreateFileW"])
if addr:
    hooks[name] = addr
    c.set_breakpoint(name)
name, addr = resolve_symbol(c, ["ReadFile"])
if addr:
    hooks[name] = addr
    c.set_breakpoint(name)
name, addr = resolve_symbol(c, ["NtReadFile"])
if addr:
    hooks[name] = addr
    c.set_breakpoint(name)
name, addr = resolve_symbol(c, ["ZwMapViewOfSection", "NtMapViewOfSection"])
if addr:
    hooks[name] = addr
    c.set_breakpoint(name)

report["hooks"] = hooks
flush("running")

# Address -> region metadata for execute-watch breakpoints
exec_watch_bp = {}


def arm_exec_watch(base, size, source):
    if not isinstance(base, int) or not isinstance(size, int) or base <= 0 or size <= 0:
        return
    pages = min(MAX_WATCH_PAGES, max(1, (size + PAGE - 1) // PAGE))
    for i in range(pages):
        addr = base + i * PAGE
        if addr in exec_watch_bp:
            continue
        try:
            c.set_breakpoint(int(addr))
            exec_watch_bp[addr] = {"base": base, "size": size, "source": source, "triggered": False}
        except Exception as exc:
            record_error(f"arm_exec_watch:{addr}", exc)


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

        # Outside-module execute surrogate: breakpoints in watched non-module candidate regions.
        if eip in exec_watch_bp:
            m = exec_watch_bp[eip]
            if not m.get("triggered"):
                d = dump_region(c, "exec_outside", m["base"], m["size"], {"trigger": eip, "source": m.get("source")})
                report["events"].append({"type": "exec_outside_hit", "eip": eip, "source": m.get("source"), "dump": d.get("file") if d else None})
                m["triggered"] = True
            clear_breakpoint(eip, "exec_watch")
            exec_watch_bp.pop(eip, None)
            flush("running")
            continue

        # CreateFileW: capture successful handle returns as context evidence.
        if "CreateFileW" in hooks and eip == int(hooks["CreateFileW"]):
            ret = rd32(c, esp)
            if ret:
                try:
                    c.set_breakpoint(int(ret))
                    c.go(); c.wait_for_debug_event(EventType.EVENT_BREAKPOINT, WAIT_BP_SEC)
                    rr = c.get_regs().model_dump().get("context", {})
                    h = int(rr.get("eax", 0)) if isinstance(rr, dict) else None
                    ok = (h is not None and h not in (0, 0xFFFFFFFF))
                    report["events"].append({"type": "CreateFileW", "handle": h, "ok": bool(ok)})
                finally:
                    clear_breakpoint(ret, "CreateFileW:return")
                flush("running")
            continue

        # ReadFile: dump up to 64KB after successful return.
        if "ReadFile" in hooks and eip == int(hooks["ReadFile"]):
            buf = rd32(c, esp + 0x8)
            n_to_read = rd32(c, esp + 0xC)
            n_read_ptr = rd32(c, esp + 0x10)
            ret = rd32(c, esp)
            if ret:
                try:
                    c.set_breakpoint(int(ret))
                    c.go(); c.wait_for_debug_event(EventType.EVENT_BREAKPOINT, WAIT_BP_SEC)
                    rr = c.get_regs().model_dump().get("context", {})
                    ok = int(rr.get("eax", 0)) if isinstance(rr, dict) else 0
                    n_read = rd32(c, n_read_ptr) if n_read_ptr else None
                    got = int(n_read if isinstance(n_read, int) and n_read > 0 else (n_to_read or 0))
                    got = max(0, got)
                    blob = rb(c, buf, min(got, CHUNK_DUMP_LIMIT)) if ok else b""
                    d = dump_blob("readfile", blob, {"buffer": buf, "requested": n_to_read, "read": n_read}) if blob else None
                    report["events"].append({"type": "ReadFile", "ok": bool(ok), "requested": n_to_read, "read": n_read, "dump": d.get("file") if d else None})
                    if blob and len(blob) >= 1024:
                        arm_exec_watch(buf, max(got, PAGE), "ReadFileBuffer")
                finally:
                    clear_breakpoint(ret, "ReadFile:return")
                flush("running")
            continue

        # NtReadFile: parse buffer + IoStatus.Information and dump up to 64KB.
        if "NtReadFile" in hooks and eip == int(hooks["NtReadFile"]):
            iosb = rd32(c, esp + 0x14)
            buf = rd32(c, esp + 0x18)
            length = rd32(c, esp + 0x1C)
            ret = rd32(c, esp)
            if ret:
                try:
                    c.set_breakpoint(int(ret))
                    c.go(); c.wait_for_debug_event(EventType.EVENT_BREAKPOINT, WAIT_BP_SEC)
                    rr = c.get_regs().model_dump().get("context", {})
                    st = int(rr.get("eax", 0)) if isinstance(rr, dict) else None
                    info = rd32(c, iosb + 4) if iosb else None
                    got = int(info if isinstance(info, int) and info > 0 else (length or 0))
                    got = max(0, got)
                    blob = rb(c, buf, min(got, CHUNK_DUMP_LIMIT)) if st == 0 else b""
                    d = dump_blob("ntread", blob, {"buffer": buf, "length": length, "iosb_info": info, "status": st}) if blob else None
                    report["events"].append({"type": "NtReadFile", "status": st, "length": length, "iosb_info": info, "dump": d.get("file") if d else None})
                    if blob and len(blob) >= 1024:
                        arm_exec_watch(buf, max(got, PAGE), "NtReadFileBuffer")
                finally:
                    clear_breakpoint(ret, "NtReadFile:return")
                flush("running")
            continue

        # (Zw|Nt)MapViewOfSection: dump mapped bytes and arm execute-watch for region.
        map_hook_name = "ZwMapViewOfSection" if "ZwMapViewOfSection" in hooks else ("NtMapViewOfSection" if "NtMapViewOfSection" in hooks else None)
        if map_hook_name and eip == int(hooks[map_hook_name]):
            base_ptr = rd32(c, esp + 0xC)
            view_ptr = rd32(c, esp + 0x1C)
            ret = rd32(c, esp)
            if ret:
                try:
                    c.set_breakpoint(int(ret))
                    c.go(); c.wait_for_debug_event(EventType.EVENT_BREAKPOINT, WAIT_BP_SEC)
                    rr = c.get_regs().model_dump().get("context", {})
                    st = int(rr.get("eax", 0)) if isinstance(rr, dict) else None
                    base = rd32(c, base_ptr) if base_ptr else None
                    view = rd32(c, view_ptr) if view_ptr else None
                    d = dump_region(c, "mapview", base, view or PAGE, {"status": st, "hook": map_hook_name}) if st == 0 else None
                    report["events"].append({"type": map_hook_name, "status": st, "base": base, "view": view, "dump": d.get("file") if d else None})
                    if st == 0 and isinstance(base, int) and isinstance(view, int) and view > 0:
                        arm_exec_watch(base, view, map_hook_name)
                finally:
                    clear_breakpoint(ret, f"{map_hook_name}:return")
                flush("running")
            continue

except Exception as e:
    report["fatal"] = str(e)

summary = {
    "events_seen": seen,
    "dumps": len(report["dumps"]),
    "elapsed_sec": round(time.time() - start, 2),
    "exec_watch_left": len(exec_watch_bp),
}
flush("completed", summary)
print(json.dumps({"json": str(REPORT).replace('\\', '/'), "summary": summary, "fatal": report.get("fatal"), "top_dumps": report.get("dumps", [])[:8]}, indent=2))
