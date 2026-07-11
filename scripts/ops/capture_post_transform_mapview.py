import json
import math
from pathlib import Path

from x64dbg_automate import X64DbgClient
from x64dbg_automate.events import EventType

X32DBG = r"C:\Users\zycie\AppData\Local\Microsoft\WinGet\Packages\x64dbg.x64dbg_Microsoft.Winget.Source_8wekyb3d8bbwe\release\x32\x32dbg.exe"
ART = Path("artifacts/enc3")
DUMPS = ART / "mapview_dumps"
ART.mkdir(parents=True, exist_ok=True)
DUMPS.mkdir(parents=True, exist_ok=True)

TARGET_SUCCESSES = 25
EVENT_BUDGET = 400
WAIT_BP_SEC = 45
MAX_DUMP_BYTES = 1024 * 1024


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
    sigs = [
        ("MZ", b"MZ"),
        ("PK", b"PK\x03\x04"),
        ("ENC3", b"ENC3"),
        ("GZIP", b"\x1F\x8B\x08"),
        ("ZLIB_78", b"\x78"),
    ]
    out = []
    for name, sig in sigs:
        pos = data.find(sig)
        if pos != -1:
            out.append({"name": name, "offset": pos})
    out.sort(key=lambda x: x["offset"])
    return out


def rd32(c, addr):
    try:
        return int(c.read_dword(int(addr)))
    except Exception:
        return None


def read_ptr(c, ptr):
    if ptr is None:
        return None
    return rd32(c, int(ptr))


def read_size_t_ptr(c, ptr):
    if ptr is None:
        return None
    return rd32(c, int(ptr))


def read_mem(c, addr, size):
    try:
        if addr is None or size is None or size <= 0:
            return b""
        return bytes(c.read_memory(int(addr), int(size)))
    except Exception:
        return b""


report = {
    "flow": "post_transform_mapview_capture",
    "config": {
        "TARGET_SUCCESSES": TARGET_SUCCESSES,
        "EVENT_BUDGET": EVENT_BUDGET,
        "WAIT_BP_SEC": WAIT_BP_SEC,
        "MAX_DUMP_BYTES": MAX_DUMP_BYTES,
    },
    "events": [],
    "errors": [],
}

sessions = X64DbgClient.list_sessions()
report["sessions"] = [str(s) for s in sessions]

if not sessions:
    report["fatal"] = "no_x64dbg_session"
else:
    c = X64DbgClient(X32DBG)
    c.attach_session(sessions[-1].pid)
    report["is_debugging_before"] = bool(c.is_debugging())

    nt_map = c.eval_sync("NtMapViewOfSection")[0]
    report["NtMapViewOfSection"] = nt_map

    c.set_breakpoint("NtMapViewOfSection")

    success = 0
    events = 0
    try:
        while success < TARGET_SUCCESSES and events < EVENT_BUDGET:
            c.go()
            bp_ev = c.wait_for_debug_event(EventType.EVENT_BREAKPOINT, WAIT_BP_SEC)
            events += 1

            regs = c.get_regs().model_dump().get("context", {})
            eip = int(regs.get("eip", 0)) if isinstance(regs, dict) else 0
            esp = int(regs.get("esp", 0)) if isinstance(regs, dict) else 0

            if eip != int(nt_map):
                continue

            args = {
                "SectionHandle": rd32(c, esp + 0x4),
                "ProcessHandle": rd32(c, esp + 0x8),
                "BaseAddressPtr": rd32(c, esp + 0xC),
                "ZeroBits": rd32(c, esp + 0x10),
                "CommitSize": rd32(c, esp + 0x14),
                "SectionOffsetPtr": rd32(c, esp + 0x18),
                "ViewSizePtr": rd32(c, esp + 0x1C),
                "InheritDisposition": rd32(c, esp + 0x20),
                "AllocationType": rd32(c, esp + 0x24),
                "Win32Protect": rd32(c, esp + 0x28),
            }
            ret_addr = rd32(c, esp)

            ev = {
                "entry_event": str(bp_ev),
                "eip": eip,
                "esp": esp,
                "args": args,
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

                base_addr = read_ptr(c, args.get("BaseAddressPtr"))
                view_size = read_size_t_ptr(c, args.get("ViewSizePtr"))
                ev["mapped"] = {
                    "base_address": base_addr,
                    "view_size": view_size,
                }

                if ntstatus == 0 and isinstance(base_addr, int) and base_addr > 0 and isinstance(view_size, int) and view_size > 0:
                    dump_size = min(int(view_size), MAX_DUMP_BYTES)
                    blob = read_mem(c, base_addr, dump_size)
                    ev["dump_size"] = len(blob)
                    if blob:
                        idx = len(report["events"]) + 1
                        dump_path = DUMPS / f"mapview-{idx:03d}.bin"
                        dump_path.write_bytes(blob)
                        ev["dump_file"] = str(dump_path).replace('\\', '/')
                        ev["entropy"] = round(entropy(blob), 4)
                        ev["headers"] = detect_headers(blob[:65536])
                        success += 1
                else:
                    ev["skip_reason"] = "ntstatus_nonzero_or_invalid_mapping"

            except Exception as ex:
                ev["error"] = str(ex)
            finally:
                try:
                    c.clear_breakpoint(int(ret_addr))
                except Exception as clear_exc:
                    ev["clear_breakpoint_error"] = str(clear_exc)

            report["events"].append(ev)

    except Exception as ex:
        report["fatal"] = str(ex)

    report["summary"] = {
        "total_break_events": events,
        "captured_mappings": success,
        "with_dump_file": sum(1 for e in report["events"] if e.get("dump_file")),
    }

out_json = ART / "kingsvale-post-transform-mapview.json"
out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

print(json.dumps({
    "json": str(out_json).replace('\\', '/'),
    "summary": report.get("summary"),
    "top_dumps": [
        {
            "file": e.get("dump_file"),
            "dump_size": e.get("dump_size"),
            "entropy": e.get("entropy"),
            "headers": e.get("headers"),
        }
        for e in report.get("events", [])
        if e.get("dump_file")
    ][:5],
}, indent=2))

