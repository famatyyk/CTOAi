import json
import math
from pathlib import Path

from x64dbg_automate import X64DbgClient
from x64dbg_automate.events import EventType

X32DBG = r"C:\Users\zycie\AppData\Local\Microsoft\WinGet\Packages\x64dbg.x64dbg_Microsoft.Winget.Source_8wekyb3d8bbwe\release\x32\x32dbg.exe"
ART = Path("artifacts/enc3")
DUMPS = ART / "protect_dumps"
ART.mkdir(parents=True, exist_ok=True)
DUMPS.mkdir(parents=True, exist_ok=True)

TARGET_HITS = 40
EVENT_BUDGET = 400
WAIT_BP_SEC = 20
MAX_DUMP_BYTES = 1024 * 1024

EXEC_PROTECT_FLAGS = {0x10, 0x20, 0x40, 0x80}


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


def detect_headers(data: bytes):
    sigs = [("MZ", b"MZ"), ("PK", b"PK\x03\x04"), ("ENC3", b"ENC3"), ("ZLIB_78", b"\x78")]
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


def read_mem(c, addr, size):
    try:
        if addr is None or size is None or size <= 0:
            return b""
        return bytes(c.read_memory(int(addr), int(size)))
    except Exception:
        return b""


report = {
    "flow": "post_transform_protect_capture",
    "config": {
        "TARGET_HITS": TARGET_HITS,
        "EVENT_BUDGET": EVENT_BUDGET,
        "WAIT_BP_SEC": WAIT_BP_SEC,
        "MAX_DUMP_BYTES": MAX_DUMP_BYTES,
    },
    "events": [],
}

sessions = X64DbgClient.list_sessions()
report["sessions"] = [str(s) for s in sessions]
if not sessions:
    report["fatal"] = "no_x64dbg_session"
else:
    c = X64DbgClient(X32DBG)
    c.attach_session(sessions[-1].pid)
    report["is_debugging_before"] = bool(c.is_debugging())

    nt_protect = c.eval_sync("NtProtectVirtualMemory")[0]
    report["NtProtectVirtualMemory"] = nt_protect
    c.set_breakpoint("NtProtectVirtualMemory")

    hits = 0
    ev_count = 0
    try:
        while hits < TARGET_HITS and ev_count < EVENT_BUDGET:
            c.go()
            bp_ev = c.wait_for_debug_event(EventType.EVENT_BREAKPOINT, WAIT_BP_SEC)
            ev_count += 1

            regs = c.get_regs().model_dump().get("context", {})
            eip = int(regs.get("eip", 0)) if isinstance(regs, dict) else 0
            esp = int(regs.get("esp", 0)) if isinstance(regs, dict) else 0
            if eip != int(nt_protect):
                continue

            process_handle = rd32(c, esp + 0x4)
            base_ptr = rd32(c, esp + 0x8)
            size_ptr = rd32(c, esp + 0xC)
            new_protect = rd32(c, esp + 0x10)
            old_protect_ptr = rd32(c, esp + 0x14)
            ret_addr = rd32(c, esp)

            ev = {
                "entry_event": str(bp_ev),
                "args": {
                    "ProcessHandle": process_handle,
                    "BaseAddressPtr": base_ptr,
                    "RegionSizePtr": size_ptr,
                    "NewProtect": new_protect,
                    "OldProtectPtr": old_protect_ptr,
                },
                "ret_addr": ret_addr,
            }

            if not ret_addr:
                ev["error"] = "no_return_address"
                report["events"].append(ev)
                continue

            try:
                c.set_breakpoint(int(ret_addr))
                c.go()
                ret_ev = c.wait_for_debug_event(EventType.EVENT_BREAKPOINT, WAIT_BP_SEC)
                ev["ret_event"] = str(ret_ev)

                regs_ret = c.get_regs().model_dump().get("context", {})
                ntstatus = int(regs_ret.get("eax", 0)) if isinstance(regs_ret, dict) else None
                ev["ntstatus"] = ntstatus

                base_addr = rd32(c, base_ptr) if base_ptr else None
                region_size = rd32(c, size_ptr) if size_ptr else None
                old_protect = rd32(c, old_protect_ptr) if old_protect_ptr else None
                ev["resolved"] = {
                    "base_address": base_addr,
                    "region_size": region_size,
                    "old_protect": old_protect,
                }

                wants_exec = isinstance(new_protect, int) and any((new_protect & f) == f for f in EXEC_PROTECT_FLAGS)
                if ntstatus == 0 and wants_exec and isinstance(base_addr, int) and base_addr > 0 and isinstance(region_size, int) and region_size > 0:
                    dump_len = min(int(region_size), MAX_DUMP_BYTES)
                    blob = read_mem(c, base_addr, dump_len)
                    ev["dump_size"] = len(blob)
                    if blob:
                        idx = len(report["events"]) + 1
                        fp = DUMPS / f"protect-{idx:03d}.bin"
                        fp.write_bytes(blob)
                        ev["dump_file"] = str(fp).replace('\\', '/')
                        ev["entropy"] = round(entropy(blob), 4)
                        ev["headers"] = detect_headers(blob[:65536])
                        hits += 1
                else:
                    ev["skip_reason"] = "non_exec_or_failed_or_invalid"
            except Exception as ex:
                ev["error"] = str(ex)
            finally:
                try:
                    c.clear_breakpoint(int(ret_addr))
                except Exception:
                    pass

            report["events"].append(ev)
    except Exception as ex:
        report["fatal"] = str(ex)

    report["summary"] = {
        "total_break_events": ev_count,
        "captured_exec_transitions": hits,
        "with_dump_file": sum(1 for e in report["events"] if e.get("dump_file")),
    }

out = ART / "kingsvale-post-transform-protect.json"
out.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({
    "json": str(out).replace('\\', '/'),
    "summary": report.get("summary"),
    "top_dumps": [
        {
            "file": e.get("dump_file"),
            "dump_size": e.get("dump_size"),
            "entropy": e.get("entropy"),
            "headers": e.get("headers"),
        }
        for e in report.get("events", []) if e.get("dump_file")
    ][:5],
}, indent=2))
