import json
import math
import time
from pathlib import Path

from x64dbg_automate import X64DbgClient
from x64dbg_automate.events import EventType

X32DBG = r"C:\Users\zycie\AppData\Local\Microsoft\WinGet\Packages\x64dbg.x64dbg_Microsoft.Winget.Source_8wekyb3d8bbwe\release\x32\x32dbg.exe"
ART = Path("artifacts/enc3")
DUMPS = ART / "loader_exec_aggr_dumps"
REPORT = ART / "kingsvale-loader-exec-aggressive-live.json"
ART.mkdir(parents=True, exist_ok=True)
DUMPS.mkdir(parents=True, exist_ok=True)

TIMEBOX_SEC = 150
WAIT_BP_SEC = 3
MAX_EVENTS = 400
MAX_DUMP = 1024 * 1024
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
        if not isinstance(addr, int) or not isinstance(size, int) or addr <= 0 or size <= 0:
            return b""
        return bytes(c.read_memory(int(addr), int(size)))
    except Exception:
        return b""


def has_exec(p):
    return isinstance(p, int) and any((p & f) == f for f in EXEC_FLAGS)


report = {
    "flow": "loader_exec_aggressive_live_capture",
    "status": "starting",
    "config": {"TIMEBOX_SEC": TIMEBOX_SEC, "WAIT_BP_SEC": WAIT_BP_SEC, "MAX_EVENTS": MAX_EVENTS, "MAX_DUMP": MAX_DUMP},
    "events": [],
    "dumps": [],
}


def flush_report(status=None, extra_summary=None):
    if status:
        report["status"] = status
    if extra_summary is not None:
        report["summary"] = extra_summary
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")


flush_report("starting")

sessions = X64DbgClient.list_sessions()
report["sessions"] = [str(s) for s in sessions]
if not sessions:
    report["fatal"] = "no_x64dbg_session"
    flush_report("fatal", {"events_seen": 0, "dumps": 0, "elapsed_sec": 0, "armed_exec_left": 0})
    print(json.dumps({"json": str(REPORT).replace('\\', '/'), "summary": report.get("summary"), "fatal": report.get("fatal")}, indent=2))
    raise SystemExit(0)

c = X64DbgClient(X32DBG)
c.attach_session(sessions[-1].pid)
report["state_before"] = {"is_debugging": bool(c.is_debugging()), "is_running": bool(c.is_running())}

hook_names = ["LdrLoadDll", "VirtualAlloc", "VirtualAllocEx", "VirtualProtect", "NtProtectVirtualMemory"]
hooks = {}
for n in hook_names:
    hooks[n] = c.eval_sync(n)[0]
    c.set_breakpoint(n)
report["hooks"] = hooks
flush_report("running")

armed_exec = {}


def dump_region(kind, base, size, extra=None):
    if not isinstance(base, int) or not isinstance(size, int) or base <= 0 or size <= 0:
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
        "headers": headers(blob[:65536]),
    }
    if extra:
        item.update(extra)
    report["dumps"].append(item)
    return item


def arm_exec(base, size, source, protect):
    if not has_exec(protect) or not isinstance(base, int) or not isinstance(size, int) or base <= 0 or size <= 0:
        return
    slots = min(4, max(1, (size + PAGE - 1) // PAGE))
    for i in range(slots):
        addr = base + i * PAGE
        if addr in armed_exec:
            continue
        try:
            c.set_breakpoint(int(addr))
            armed_exec[addr] = {"base": base, "size": size, "source": source, "protect": protect}
        except Exception:
            pass


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

        if eip in armed_exec:
            m = armed_exec[eip]
            d = dump_region("exec_hit", m["base"], m["size"], {"source": m["source"], "protect": m["protect"], "trigger": eip})
            report["events"].append({"type": "exec_hit", "eip": eip, "dump": d.get("file") if d else None})
            try:
                c.clear_breakpoint(int(eip))
            except Exception:
                pass
            armed_exec.pop(eip, None)
            flush_report("running")
            continue

        if eip == int(hooks["VirtualAlloc"]):
            sz = rd32(c, esp + 0x8)
            prot = rd32(c, esp + 0x10)
            ret = rd32(c, esp)
            if ret:
                c.set_breakpoint(int(ret)); c.go(); c.wait_for_debug_event(EventType.EVENT_BREAKPOINT, WAIT_BP_SEC)
                rr = c.get_regs().model_dump().get("context", {})
                base = int(rr.get("eax", 0)) if isinstance(rr, dict) else None
                d = dump_region("va_ret", base, sz or PAGE, {"protect": prot})
                arm_exec(base, sz or PAGE, "VirtualAlloc", prot)
                report["events"].append({"type": "VirtualAlloc", "base": base, "size": sz, "protect": prot, "dump": d.get("file") if d else None})
                try: c.clear_breakpoint(int(ret))
                except Exception: pass
                flush_report("running")
            continue

        if eip == int(hooks["VirtualAllocEx"]):
            sz = rd32(c, esp + 0xC)
            prot = rd32(c, esp + 0x14)
            ret = rd32(c, esp)
            if ret:
                c.set_breakpoint(int(ret)); c.go(); c.wait_for_debug_event(EventType.EVENT_BREAKPOINT, WAIT_BP_SEC)
                rr = c.get_regs().model_dump().get("context", {})
                base = int(rr.get("eax", 0)) if isinstance(rr, dict) else None
                d = dump_region("vax_ret", base, sz or PAGE, {"protect": prot})
                arm_exec(base, sz or PAGE, "VirtualAllocEx", prot)
                report["events"].append({"type": "VirtualAllocEx", "base": base, "size": sz, "protect": prot, "dump": d.get("file") if d else None})
                try: c.clear_breakpoint(int(ret))
                except Exception: pass
                flush_report("running")
            continue

        if eip == int(hooks["VirtualProtect"]):
            base = rd32(c, esp + 0x4)
            sz = rd32(c, esp + 0x8)
            prot = rd32(c, esp + 0xC)
            ret = rd32(c, esp)
            if ret:
                c.set_breakpoint(int(ret)); c.go(); c.wait_for_debug_event(EventType.EVENT_BREAKPOINT, WAIT_BP_SEC)
                rr = c.get_regs().model_dump().get("context", {})
                ok = int(rr.get("eax", 0)) if isinstance(rr, dict) else 0
                d = dump_region("vp_ret", base, sz or PAGE, {"protect": prot, "ok": ok}) if ok else None
                if ok: arm_exec(base, sz or PAGE, "VirtualProtect", prot)
                report["events"].append({"type": "VirtualProtect", "base": base, "size": sz, "protect": prot, "ok": ok, "dump": d.get("file") if d else None})
                try: c.clear_breakpoint(int(ret))
                except Exception: pass
                flush_report("running")
            continue

        if eip == int(hooks["NtProtectVirtualMemory"]):
            bp = rd32(c, esp + 0x8)
            sp = rd32(c, esp + 0xC)
            prot = rd32(c, esp + 0x10)
            ret = rd32(c, esp)
            if ret:
                c.set_breakpoint(int(ret)); c.go(); c.wait_for_debug_event(EventType.EVENT_BREAKPOINT, WAIT_BP_SEC)
                rr = c.get_regs().model_dump().get("context", {})
                st = int(rr.get("eax", 0)) if isinstance(rr, dict) else None
                base = rd32(c, bp) if bp else None
                sz = rd32(c, sp) if sp else None
                d = dump_region("ntp_ret", base, sz or PAGE, {"protect": prot, "status": st}) if st == 0 else None
                if st == 0: arm_exec(base, sz or PAGE, "NtProtectVirtualMemory", prot)
                report["events"].append({"type": "NtProtectVirtualMemory", "base": base, "size": sz, "protect": prot, "status": st, "dump": d.get("file") if d else None})
                try: c.clear_breakpoint(int(ret))
                except Exception: pass
                flush_report("running")
            continue

        if eip == int(hooks["LdrLoadDll"]):
            modp = rd32(c, esp + 0x10)
            ret = rd32(c, esp)
            if ret:
                c.set_breakpoint(int(ret)); c.go(); c.wait_for_debug_event(EventType.EVENT_BREAKPOINT, WAIT_BP_SEC)
                rr = c.get_regs().model_dump().get("context", {})
                st = int(rr.get("eax", 0)) if isinstance(rr, dict) else None
                base = rd32(c, modp) if modp else None
                d = dump_region("ldr_mod", base, MAX_DUMP, {"status": st}) if st == 0 else None
                report["events"].append({"type": "LdrLoadDll", "status": st, "base": base, "dump": d.get("file") if d else None})
                try: c.clear_breakpoint(int(ret))
                except Exception: pass
                flush_report("running")
            continue

except Exception as e:
    report["fatal"] = str(e)

summary = {
    "events_seen": seen,
    "dumps": len(report["dumps"]),
    "elapsed_sec": round(time.time() - start, 2),
    "armed_exec_left": len(armed_exec),
}
flush_report("completed", summary)
print(json.dumps({"json": str(REPORT).replace('\\', '/'), "summary": summary, "top_dumps": report.get("dumps", [])[:5], "fatal": report.get("fatal")}, indent=2))
