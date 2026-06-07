import json
import math
import time
from pathlib import Path

from x64dbg_automate import X64DbgClient
from x64dbg_automate.events import EventType

X32DBG = r"C:\Users\zycie\AppData\Local\Microsoft\WinGet\Packages\x64dbg.x64dbg_Microsoft.Winget.Source_8wekyb3d8bbwe\release\x32\x32dbg.exe"
ART = Path("artifacts/enc3")
DUMPS = ART / "loader_exec_dumps"
ART.mkdir(parents=True, exist_ok=True)
DUMPS.mkdir(parents=True, exist_ok=True)

TIMEBOX_SEC = 240
WAIT_BP_SEC = 4
MAX_EVENTS = 700
MAX_DUMP = 2 * 1024 * 1024
PAGE = 0x1000
EXEC_FLAGS = {0x10, 0x20, 0x40, 0x80}


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


def rmem(c, addr, size):
    try:
        if addr is None or size is None or size <= 0:
            return b""
        return bytes(c.read_memory(int(addr), int(size)))
    except Exception:
        return b""


def has_exec(prot):
    if not isinstance(prot, int):
        return False
    return any((prot & f) == f for f in EXEC_FLAGS)


report = {
    "flow": "loader_exec_burst_capture",
    "config": {
        "TIMEBOX_SEC": TIMEBOX_SEC,
        "WAIT_BP_SEC": WAIT_BP_SEC,
        "MAX_EVENTS": MAX_EVENTS,
        "MAX_DUMP": MAX_DUMP,
    },
    "events": [],
    "dumps": [],
}

sessions = X64DbgClient.list_sessions()
report["sessions"] = [str(s) for s in sessions]
if not sessions:
    report["fatal"] = "no_x64dbg_session"
else:
    c = X64DbgClient(X32DBG)
    c.attach_session(sessions[-1].pid)
    report["state_before"] = {"is_debugging": bool(c.is_debugging()), "is_running": bool(c.is_running())}

    hooks = {}
    for name in ["LdrLoadDll", "VirtualAlloc", "VirtualAllocEx", "VirtualProtect", "NtProtectVirtualMemory"]:
        hooks[name] = c.eval_sync(name)[0]
        c.set_breakpoint(name)
    report["hooks"] = hooks

    exec_bp_meta = {}

    def write_dump(kind, base, size, trigger_addr=None, extra=None):
        if not isinstance(base, int) or base <= 0 or not isinstance(size, int) or size <= 0:
            return None
        blob = rmem(c, base, min(size, MAX_DUMP))
        if not blob:
            return None
        idx = len(report["dumps"]) + 1
        fp = DUMPS / f"{kind}-{idx:03d}.bin"
        fp.write_bytes(blob)
        item = {
            "kind": kind,
            "file": str(fp).replace('\\', '/'),
            "base": base,
            "size": size,
            "captured": len(blob),
            "entropy": round(entropy(blob), 4),
            "headers": headers(blob[:131072]),
            "trigger_addr": trigger_addr,
        }
        if extra:
            item.update(extra)
        report["dumps"].append(item)
        return item

    def arm_exec_breakpoints(base, size, source, protect):
        if not has_exec(protect):
            return
        if not isinstance(base, int) or not isinstance(size, int):
            return
        if base <= 0 or size <= 0:
            return
        max_slots = min(6, max(1, (size + PAGE - 1) // PAGE))
        for i in range(max_slots):
            addr = base + i * PAGE
            if addr in exec_bp_meta:
                continue
            try:
                c.set_breakpoint(int(addr))
                exec_bp_meta[addr] = {
                    "base": base,
                    "size": size,
                    "source": source,
                    "protect": protect,
                    "offset": i * PAGE,
                }
            except Exception:
                continue

    start = time.time()
    ev_count = 0

    try:
        while (time.time() - start) < TIMEBOX_SEC and ev_count < MAX_EVENTS:
            c.go()
            ev = c.wait_for_debug_event(EventType.EVENT_BREAKPOINT, WAIT_BP_SEC)
            ev_count += 1

            regs = c.get_regs().model_dump().get("context", {})
            eip = int(regs.get("eip", 0)) if isinstance(regs, dict) else 0
            esp = int(regs.get("esp", 0)) if isinstance(regs, dict) else 0

            if eip in exec_bp_meta:
                meta = exec_bp_meta.get(eip, {})
                d = write_dump("exec_hit", meta.get("base"), meta.get("size"), trigger_addr=eip, extra={"source": meta.get("source"), "protect": meta.get("protect")})
                report["events"].append({"type": "exec_hit", "eip": eip, "meta": meta, "dump": d.get("file") if d else None})
                try:
                    c.clear_breakpoint(int(eip))
                except Exception:
                    pass
                exec_bp_meta.pop(eip, None)
                continue

            if eip == int(hooks["VirtualAlloc"]):
                lp = rd32(c, esp + 0x4)
                sz = rd32(c, esp + 0x8)
                prot = rd32(c, esp + 0x10)
                ret = rd32(c, esp)
                if ret:
                    try:
                        c.set_breakpoint(int(ret))
                        c.go()
                        c.wait_for_debug_event(EventType.EVENT_BREAKPOINT, WAIT_BP_SEC)
                        r = c.get_regs().model_dump().get("context", {})
                        base = int(r.get("eax", 0)) if isinstance(r, dict) else None
                        arm_exec_breakpoints(base, sz, "VirtualAlloc", prot)
                        report["events"].append({"type": "VirtualAlloc", "base": base, "size": sz, "protect": prot})
                    finally:
                        try:
                            c.clear_breakpoint(int(ret))
                        except Exception:
                            pass
                continue

            if eip == int(hooks["VirtualAllocEx"]):
                lp = rd32(c, esp + 0x8)
                sz = rd32(c, esp + 0xC)
                prot = rd32(c, esp + 0x14)
                ret = rd32(c, esp)
                if ret:
                    try:
                        c.set_breakpoint(int(ret))
                        c.go()
                        c.wait_for_debug_event(EventType.EVENT_BREAKPOINT, WAIT_BP_SEC)
                        r = c.get_regs().model_dump().get("context", {})
                        base = int(r.get("eax", 0)) if isinstance(r, dict) else None
                        arm_exec_breakpoints(base, sz, "VirtualAllocEx", prot)
                        report["events"].append({"type": "VirtualAllocEx", "base": base, "size": sz, "protect": prot})
                    finally:
                        try:
                            c.clear_breakpoint(int(ret))
                        except Exception:
                            pass
                continue

            if eip == int(hooks["VirtualProtect"]):
                base = rd32(c, esp + 0x4)
                sz = rd32(c, esp + 0x8)
                prot = rd32(c, esp + 0xC)
                ret = rd32(c, esp)
                if ret:
                    try:
                        c.set_breakpoint(int(ret))
                        c.go()
                        c.wait_for_debug_event(EventType.EVENT_BREAKPOINT, WAIT_BP_SEC)
                        r = c.get_regs().model_dump().get("context", {})
                        ok = int(r.get("eax", 0)) if isinstance(r, dict) else 0
                        if ok:
                            arm_exec_breakpoints(base, sz, "VirtualProtect", prot)
                        report["events"].append({"type": "VirtualProtect", "base": base, "size": sz, "protect": prot, "ok": ok})
                    finally:
                        try:
                            c.clear_breakpoint(int(ret))
                        except Exception:
                            pass
                continue

            if eip == int(hooks["NtProtectVirtualMemory"]):
                base_ptr = rd32(c, esp + 0x8)
                size_ptr = rd32(c, esp + 0xC)
                prot = rd32(c, esp + 0x10)
                ret = rd32(c, esp)
                if ret:
                    try:
                        c.set_breakpoint(int(ret))
                        c.go()
                        c.wait_for_debug_event(EventType.EVENT_BREAKPOINT, WAIT_BP_SEC)
                        r = c.get_regs().model_dump().get("context", {})
                        status = int(r.get("eax", 0)) if isinstance(r, dict) else None
                        base = rd32(c, base_ptr) if base_ptr else None
                        sz = rd32(c, size_ptr) if size_ptr else None
                        if status == 0:
                            arm_exec_breakpoints(base, sz, "NtProtectVirtualMemory", prot)
                        report["events"].append({"type": "NtProtectVirtualMemory", "base": base, "size": sz, "protect": prot, "status": status})
                    finally:
                        try:
                            c.clear_breakpoint(int(ret))
                        except Exception:
                            pass
                continue

            if eip == int(hooks["LdrLoadDll"]):
                mod_handle_ptr = rd32(c, esp + 0x10)
                ret = rd32(c, esp)
                if ret:
                    try:
                        c.set_breakpoint(int(ret))
                        c.go()
                        c.wait_for_debug_event(EventType.EVENT_BREAKPOINT, WAIT_BP_SEC)
                        r = c.get_regs().model_dump().get("context", {})
                        status = int(r.get("eax", 0)) if isinstance(r, dict) else None
                        hmod = rd32(c, mod_handle_ptr) if mod_handle_ptr else None
                        dumped = None
                        if status == 0 and isinstance(hmod, int) and hmod > 0:
                            d = write_dump("ldr_module", hmod, MAX_DUMP, extra={"status": status})
                            dumped = d.get("file") if d else None
                        report["events"].append({"type": "LdrLoadDll", "status": status, "module_base": hmod, "dump": dumped})
                    finally:
                        try:
                            c.clear_breakpoint(int(ret))
                        except Exception:
                            pass
                continue

    except Exception as e:
        report["fatal"] = str(e)

    report["summary"] = {
        "events_seen": ev_count,
        "dumps": len(report["dumps"]),
        "exec_bp_armed_left": len(exec_bp_meta),
        "elapsed_sec": round(time.time() - start, 2),
    }

out = ART / "kingsvale-loader-exec-burst.json"
out.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({
    "json": str(out).replace('\\', '/'),
    "summary": report.get("summary"),
    "top_dumps": report.get("dumps", [])[:5],
}, indent=2))
