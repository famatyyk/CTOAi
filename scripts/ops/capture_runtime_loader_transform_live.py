import json
import os
import math
import time
import atexit
import hashlib
from pathlib import Path

from x64dbg_automate import X64DbgClient
from x64dbg_automate.events import EventType
from x64dbg_automate.models import MemoryBreakpointType

X32DBG = r"C:\Users\zycie\AppData\Local\Microsoft\WinGet\Packages\x64dbg.x64dbg_Microsoft.Winget.Source_8wekyb3d8bbwe\release\x32\x32dbg.exe"
ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "artifacts" / "enc3"
DUMPS = ART / "runtime_loader_dumps"
REPORT = ART / "kingsvale-runtime-loader-live.json"
LOCK = ART / "kingsvale-runtime-loader-live.lock"
ART.mkdir(parents=True, exist_ok=True)
DUMPS.mkdir(parents=True, exist_ok=True)

TIMEBOX_SEC = int(os.getenv("CTOA_RUNTIME_TIMEBOX_SEC", "300"))
WAIT_BP_SEC = int(os.getenv("CTOA_RUNTIME_WAIT_BP_SEC", "3"))
MAX_EVENTS = int(os.getenv("CTOA_RUNTIME_MAX_EVENTS", "1600"))
MAX_DUMPS = int(os.getenv("CTOA_RUNTIME_MAX_DUMPS", "900"))
REGION_DUMP_CAP = int(os.getenv("CTOA_RUNTIME_REGION_DUMP_CAP", str(8 * 1024 * 1024)))
MAX_WATCH_PAGES = int(os.getenv("CTOA_RUNTIME_MAX_WATCH_PAGES", "16"))
MIN_DUMP_SIZE = int(os.getenv("CTOA_RUNTIME_MIN_DUMP_SIZE", "192"))
DEDUP_PREFIX = int(os.getenv("CTOA_RUNTIME_DEDUP_PREFIX", "65536"))
MAX_PAGE_WRITE_TRACK = int(os.getenv("CTOA_RUNTIME_MAX_PAGE_WRITE_TRACK", "4096"))
ALLOC_TRACK_SAMPLE = int(os.getenv("CTOA_RUNTIME_ALLOC_TRACK_SAMPLE", "4096"))
FIRST_TOUCH_BREAKPAGES = int(os.getenv("CTOA_RUNTIME_FIRST_TOUCH_BREAKPAGES", "2"))
HOT_ALLOC_SHAPES = int(os.getenv("CTOA_RUNTIME_HOT_ALLOC_SHAPES", "1"))
REGION_DIFF_CHECKS = int(os.getenv("CTOA_RUNTIME_REGION_DIFF_CHECKS", "1"))
MOVE_EXEC_HISTORY = int(os.getenv("CTOA_RUNTIME_MOVE_EXEC_HISTORY", "24"))
PAGE = 0x1000


# Single-instance guard: avoid breakpoint races from duplicate runners.
_lock_owner_pid = os.getpid()


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(int(pid), 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except Exception:
        return False


def _read_lock_pid():
    try:
        raw = LOCK.read_text(encoding="ascii", errors="ignore").strip()
        return int(raw) if raw else None
    except Exception:
        return None


if LOCK.exists():
    existing_pid = _read_lock_pid()
    if isinstance(existing_pid, int) and not _pid_alive(existing_pid):
        try:
            LOCK.unlink()
        except Exception:
            pass

try:
    fd = os.open(str(LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.write(fd, str(_lock_owner_pid).encode("ascii", errors="ignore"))
    os.close(fd)
except FileExistsError:
    print(json.dumps({"json": str(REPORT).replace("\\", "/"), "fatal": "lock_exists_duplicate_runner", "lock": str(LOCK).replace("\\", "/"), "owner_pid": _read_lock_pid()}, indent=2))
    raise SystemExit(0)


def _release_lock():
    try:
        if LOCK.exists():
            owner = _read_lock_pid()
            if owner == _lock_owner_pid:
                LOCK.unlink()
    except Exception:
        pass


atexit.register(_release_lock)


PAGE_EXECUTE = 0x10
PAGE_EXECUTE_READ = 0x20
PAGE_EXECUTE_READWRITE = 0x40
PAGE_EXECUTE_WRITECOPY = 0x80
FILE_MAP_EXECUTE = 0x20
DEFAULT_MAP_DUMP_SIZE = 0x40000


def has_exec(prot):
    if not isinstance(prot, int):
        return False
    return bool(prot & (PAGE_EXECUTE | PAGE_EXECUTE_READ | PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY))


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
    n = min(len(data), 131072)
    p = 0
    for b in data[:n]:
        if b in (9, 10, 13) or 32 <= b <= 126:
            p += 1
    return p / float(n)


def dump_score(size: int, ent: float, hdrs, pr: float) -> float:
    score = 0.0
    if size >= 1024:
        score += 1.0
    if size >= 16384:
        score += 1.2
    if size >= 65536:
        score += 1.4
    if 4.8 <= ent <= 7.95:
        score += 1.0
    if 5.4 <= ent <= 7.4:
        score += 0.7
    if 0.12 <= pr <= 0.95:
        score += 0.6
    names = {h.get("name") for h in (hdrs or []) if isinstance(h, dict)}
    if "MZ" in names:
        score += 3.0
    if "PE" in names:
        score += 2.4
    if "PK" in names:
        score += 1.5
    if "GZIP" in names:
        score += 1.6
    if "ENC3" in names:
        score += 1.2
    return round(score, 4)


def bounded_region_size(size, fallback=DEFAULT_MAP_DUMP_SIZE):
    if isinstance(size, int) and size > 0:
        return min(size, REGION_DUMP_CAP)
    return min(fallback, REGION_DUMP_CAP)


def sample_prefix(c, base, size):
    sample = min(ALLOC_TRACK_SAMPLE, bounded_region_size(size, ALLOC_TRACK_SAMPLE))
    if not isinstance(base, int) or base <= 0 or sample <= 0:
        return b""
    return rb(c, base, sample)


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
        try:
            v = c.eval_sync(n)[0]
            if isinstance(v, int) and v > 0:
                return n, v
        except Exception:
            continue
    return None, None


report = {
    "flow": "runtime_loader_transform_return_dump",
    "status": "starting",
    "config": {
        "TIMEBOX_SEC": TIMEBOX_SEC,
        "WAIT_BP_SEC": WAIT_BP_SEC,
        "MAX_EVENTS": MAX_EVENTS,
        "MAX_DUMPS": MAX_DUMPS,
        "REGION_DUMP_CAP": REGION_DUMP_CAP,
        "MAX_WATCH_PAGES": MAX_WATCH_PAGES,
    },
    "events": [],
    "dumps": [],
    "errors": [],
}


seen_dump_fingerprints = set()


def flush(status=None, summary=None):
    if status:
        report["status"] = status
    if summary is not None:
        report["summary"] = summary
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")


def dump_blob(kind, blob: bytes, meta=None):
    if not blob:
        return None
    if len(blob) < MIN_DUMP_SIZE:
        return None
    if len(report["dumps"]) >= MAX_DUMPS:
        return None

    sig_len = min(len(blob), max(128, DEDUP_PREFIX))
    sig = hashlib.sha1(blob[:sig_len]).hexdigest() + f":{len(blob)}"
    if sig in seen_dump_fingerprints:
        return None

    idx = len(report["dumps"]) + 1
    fp = DUMPS / f"{kind}-{idx:04d}.bin"
    fp.write_bytes(blob)

    ent = round(entropy(blob), 4)
    hdr = headers(blob[:131072])
    pr = round(printable_ratio(blob), 4)
    score = dump_score(len(blob), ent, hdr, pr)

    item = {
        "kind": kind,
        "file": str(fp).replace("\\", "/"),
        "size": len(blob),
        "entropy": ent,
        "headers": hdr,
        "printable_ratio": pr,
        "score": score,
        "fingerprint": sig,
    }
    if meta:
        item.update(meta)
    report["dumps"].append(item)
    seen_dump_fingerprints.add(sig)
    return item



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
    print(json.dumps({"json": str(REPORT).replace("\\", "/"), "fatal": report["fatal"]}, indent=2))
    raise SystemExit(0)

c = X64DbgClient(X32DBG)
c.attach_session(sessions[-1].pid)
report["state_before"] = {"is_debugging": bool(c.is_debugging()), "is_running": bool(c.is_running())}

hooks = {}
hook_candidates = [
    "LdrLoadDll", "ntdll!LdrLoadDll",
    "LdrGetProcedureAddress", "ntdll!LdrGetProcedureAddress",
    "GetProcAddress", "kernel32!GetProcAddress",
    "LoadLibraryA", "kernel32!LoadLibraryA",
    "LoadLibraryW", "kernel32!LoadLibraryW",
    "NtCreateSection", "ntdll!NtCreateSection",
    "CreateFileMappingW", "kernel32!CreateFileMappingW",
    "CreateFileMappingW", "KernelBase!CreateFileMappingW",
    "CreateFileMappingA", "kernel32!CreateFileMappingA",
    "CreateFileMappingA", "KernelBase!CreateFileMappingA",
    "NtAllocateVirtualMemory", "ntdll!NtAllocateVirtualMemory",
    "VirtualAlloc", "kernel32!VirtualAlloc",
    "VirtualAlloc", "KernelBase!VirtualAlloc",
    "VirtualAllocEx", "kernel32!VirtualAllocEx",
    "VirtualAllocEx", "KernelBase!VirtualAllocEx",
    "NtProtectVirtualMemory", "ntdll!NtProtectVirtualMemory",
    "VirtualProtect", "kernel32!VirtualProtect",
    "VirtualProtect", "KernelBase!VirtualProtect",
    "WriteProcessMemory", "kernel32!WriteProcessMemory",
    "WriteProcessMemory", "KernelBase!WriteProcessMemory",
    "MapViewOfFile", "kernel32!MapViewOfFile",
    "MapViewOfFile", "KernelBase!MapViewOfFile",
    "MapViewOfFileEx", "kernel32!MapViewOfFileEx",
    "MapViewOfFileEx", "KernelBase!MapViewOfFileEx",
    "NtMapViewOfSection", "ntdll!NtMapViewOfSection",
    "NtWriteVirtualMemory", "ntdll!NtWriteVirtualMemory",
    "RtlMoveMemory", "ntdll!RtlMoveMemory",
    "RtlCopyMemory", "ntdll!RtlCopyMemory",
    "memcpy", "msvcrt!memcpy",
    "memmove", "msvcrt!memmove",
    "RtlDecompressBuffer", "ntdll!RtlDecompressBuffer",
    "BCryptDecrypt", "bcrypt!BCryptDecrypt",
    "CryptDecrypt", "advapi32!CryptDecrypt",
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

exec_watch_bp = {}
page_write_volume = {}
alloc_regions = {}
alloc_touch_bp = {}
alloc_shape_counts = {}
hot_alloc_watch = {}
section_handles = {}
map_relations = []
recent_move_regions = []


def alloc_shape_key(size, prot, alloc_type):
    return f"{int(size) if isinstance(size, int) else 0}:{int(prot) if isinstance(prot, int) else 0}:{int(alloc_type) if isinstance(alloc_type, int) else 0}"


def track_alloc_region(base, size, prot, source, alloc_type=None):
    if not isinstance(base, int) or not isinstance(size, int) or base <= 0 or size <= 0:
        return
    prefix = sample_prefix(c, base, size)
    shape = alloc_shape_key(size, prot, alloc_type)
    alloc_regions[base] = {
        "base": base,
        "size": size,
        "prot": prot,
        "source": source,
        "alloc_type": alloc_type,
        "shape_key": shape,
        "initial_sha1": hashlib.sha1(prefix).hexdigest() if prefix else None,
        "last_sha1": hashlib.sha1(prefix).hexdigest() if prefix else None,
        "first_touch_dumped": False,
        "bp_addrs": [],
        "diff_checks": 0,
    }
    alloc_shape_counts[shape] = alloc_shape_counts.get(shape, 0) + 1
    pages = min(FIRST_TOUCH_BREAKPAGES, max(1, (size + PAGE - 1) // PAGE))
    for i in range(pages):
        addr = (base + i * PAGE) & ~(PAGE - 1)
        if addr in alloc_touch_bp:
            continue
        try:
            c.set_memory_breakpoint(int(addr), MemoryBreakpointType.a, True)
            alloc_touch_bp[addr] = base
            alloc_regions[base]["bp_addrs"].append(addr)
        except Exception:
            continue


def clear_alloc_breakpoints(base):
    region = alloc_regions.get(base)
    if not isinstance(region, dict):
        return
    for addr in region.get("bp_addrs", []):
        try:
            c.clear_memory_breakpoint(int(addr))
        except Exception:
            pass
        alloc_touch_bp.pop(addr, None)
    region["bp_addrs"] = []


def refresh_hot_alloc_watchers():
    top_shapes = [shape for shape, _count in sorted(alloc_shape_counts.items(), key=lambda kv: kv[1], reverse=True)[:HOT_ALLOC_SHAPES]]
    if not top_shapes:
        return
    for base, region in alloc_regions.items():
        if not isinstance(region, dict):
            continue
        if region.get("shape_key") not in top_shapes:
            continue
        addr = int(region.get("base", 0))
        if addr <= 0 or addr in hot_alloc_watch:
            continue
        try:
            c.set_memory_breakpoint(addr, MemoryBreakpointType.a, False)
            hot_alloc_watch[addr] = base
        except Exception:
            continue


def maybe_dump_first_touch(base, reason, trigger=None):
    region = alloc_regions.get(base)
    if not isinstance(region, dict) or region.get("first_touch_dumped"):
        return None
    prefix = sample_prefix(c, region["base"], region["size"])
    sha1 = hashlib.sha1(prefix).hexdigest() if prefix else None
    if region.get("last_sha1") and sha1 == region.get("last_sha1") and reason != "memory_breakpoint":
        return None
    region["last_sha1"] = sha1
    d = dump_region(c, "alloc_first_touch", region["base"], region["size"], {"source": region.get("source"), "reason": reason, "trigger": trigger, "prot": region.get("prot")})
    report["events"].append({"type": "alloc_first_touch", "base": region["base"], "size": region["size"], "shape_key": region.get("shape_key"), "source": region.get("source"), "reason": reason, "trigger": trigger, "dump": d.get("file") if d else None})
    region["first_touch_dumped"] = True
    clear_alloc_breakpoints(base)
    if isinstance(region.get("prot"), int) and has_exec(region.get("prot")):
        arm_exec_watch(region["base"], region["size"], f"{region.get("source")}:first_touch")
    return d


def poll_alloc_region_diffs(trigger_eip=None):
    for base, region in list(alloc_regions.items()):
        if not isinstance(region, dict) or region.get("first_touch_dumped"):
            continue
        region["diff_checks"] = int(region.get("diff_checks", 0)) + 1
        if region["diff_checks"] < REGION_DIFF_CHECKS:
            continue
        prefix = sample_prefix(c, region.get("base"), region.get("size"))
        sha1 = hashlib.sha1(prefix).hexdigest() if prefix else None
        if not sha1 or sha1 == region.get("last_sha1"):
            continue
        report["events"].append({"type": "alloc_region_diff", "base": region.get("base"), "size": region.get("size"), "shape_key": region.get("shape_key"), "trigger": trigger_eip})
        maybe_dump_first_touch(base, "region_diff_poll", trigger_eip)


def remember_recent_move(dest, size, source):
    if not isinstance(dest, int) or not isinstance(size, int) or dest <= 0 or size <= 0:
        return
    recent_move_regions.append({"base": dest, "size": size, "source": source, "ts": time.time()})
    if len(recent_move_regions) > MOVE_EXEC_HISTORY:
        del recent_move_regions[:-MOVE_EXEC_HISTORY]


def match_recent_move(base, size):
    if not isinstance(base, int) or not isinstance(size, int) or base <= 0 or size <= 0:
        return None
    best = None
    end = base + size
    for move in reversed(recent_move_regions):
        move_base = int(move.get("base", 0))
        move_size = int(move.get("size", 0))
        move_end = move_base + move_size
        overlap = max(0, min(end, move_end) - max(base, move_base))
        if overlap <= 0:
            continue
        candidate = dict(move)
        candidate["overlap"] = overlap
        if best is None or overlap > best.get("overlap", 0):
            best = candidate
    return best


def add_write_volume(base, size, source):
    if not isinstance(base, int) or not isinstance(size, int) or base <= 0 or size <= 0:
        return
    end = base + size
    cur = base
    while cur < end:
        page_base = cur & ~(PAGE - 1)
        page_end = min(end, page_base + PAGE)
        written = max(0, page_end - cur)
        meta = page_write_volume.get(page_base)
        if meta is None:
            if len(page_write_volume) >= MAX_PAGE_WRITE_TRACK:
                cur = page_end
                continue
            meta = {"bytes": 0, "hits": 0, "sources": []}
            page_write_volume[page_base] = meta
        meta["bytes"] += written
        meta["hits"] += 1
        if source and source not in meta["sources"]:
            meta["sources"].append(source)
            if len(meta["sources"]) > 4:
                meta["sources"] = meta["sources"][-4:]
        cur = page_end


def rank_exec_watch_pages(base, size):
    if not isinstance(base, int) or not isinstance(size, int) or base <= 0 or size <= 0:
        return []
    pages = []
    end = base + size
    cur = base
    while cur < end:
        page_base = cur & ~(PAGE - 1)
        meta = page_write_volume.get(page_base, {})
        pages.append((int(meta.get("bytes", 0)), int(meta.get("hits", 0)), page_base, list(meta.get("sources", []))))
        cur = page_base + PAGE
    pages.sort(key=lambda item: (item[0], item[1], -item[2]), reverse=True)
    return pages


def arm_exec_watch(base, size, source):
    if not isinstance(base, int) or not isinstance(size, int) or base <= 0 or size <= 0:
        return
    ranked_pages = rank_exec_watch_pages(base, size)
    if not ranked_pages:
        ranked_pages = [(0, 0, base + i * PAGE, []) for i in range(min(MAX_WATCH_PAGES, max(1, (size + PAGE - 1) // PAGE)))]
    for priority, item in enumerate(ranked_pages[:MAX_WATCH_PAGES], start=1):
        written, hits, addr, sources = item
        if addr in exec_watch_bp:
            continue
        try:
            c.set_breakpoint(int(addr))
            exec_watch_bp[addr] = {
                "base": base,
                "size": size,
                "source": source,
                "triggered": False,
                "priority": priority,
                "page_write_bytes": written,
                "page_write_hits": hits,
                "page_sources": sources,
            }
        except Exception:
            continue


def wait_return_and_regs(ret_addr):
    c.set_breakpoint(int(ret_addr))
    c.go()
    c.wait_for_debug_event(EventType.EVENT_BREAKPOINT, WAIT_BP_SEC)
    rr = c.get_regs().model_dump().get("context", {})
    return rr if isinstance(rr, dict) else {}


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

        poll_alloc_region_diffs(eip)

        if eip in alloc_touch_bp:
            alloc_base = alloc_touch_bp.get(eip)
            maybe_dump_first_touch(alloc_base, "memory_breakpoint", eip)
            flush("running")
            continue

        for alloc_base, alloc_meta in list(alloc_regions.items()):
            if alloc_meta.get("first_touch_dumped"):
                continue
            if eip >= int(alloc_meta.get("base", 0)) and eip < int(alloc_meta.get("base", 0)) + int(alloc_meta.get("size", 0)):
                maybe_dump_first_touch(alloc_base, "execute_in_region", eip)
                break

        if eip in exec_watch_bp:
            m = exec_watch_bp[eip]
            if not m.get("triggered"):
                d = dump_region(c, "exec_watch_hit", m["base"], m["size"], {"trigger": eip, "source": m.get("source")})
                report["events"].append({"type": "exec_watch_hit", "eip": eip, "source": m.get("source"), "priority": m.get("priority"), "page_write_bytes": m.get("page_write_bytes"), "page_write_hits": m.get("page_write_hits"), "page_sources": m.get("page_sources"), "dump": d.get("file") if d else None})
                m["triggered"] = True
            try:
                c.clear_breakpoint(int(eip))
            except Exception:
                pass
            exec_watch_bp.pop(eip, None)
            flush("running")
            continue

        hit = None
        for n, a in hooks.items():
            if eip == int(a):
                hit = n
                break
        if not hit:
            continue

        report["events"].append({"type": "hook_entry", "hook": hit, "eip": eip, "esp": esp})

        ret = rd32(c, esp)
        if not isinstance(ret, int) or ret <= 0:
            flush("running")
            continue

        try:
            if "NtCreateSection" in hit:
                section_handle_ptr = rd32(c, esp + 0x4)
                maximum_size_ptr = rd32(c, esp + 0x8)
                section_page_prot = rd32(c, esp + 0xC)
                alloc_attrs = rd32(c, esp + 0x10)
                rr = wait_return_and_regs(ret)
                status = int(rr.get("eax", 0)) if isinstance(rr, dict) else 0
                section_handle = rd32(c, section_handle_ptr) if isinstance(section_handle_ptr, int) else None
                maximum_size = rd32(c, maximum_size_ptr) if isinstance(maximum_size_ptr, int) else None
                if status == 0 and isinstance(section_handle, int) and section_handle > 0:
                    section_handles[section_handle] = {"api": hit, "max_size": maximum_size, "prot": section_page_prot, "attrs": alloc_attrs}
                report["events"].append({"type": "NtCreateSection", "hook": hit, "status": status, "section_handle": section_handle, "maximum_size": maximum_size, "prot": section_page_prot, "attrs": alloc_attrs})
                continue

            if "CreateFileMapping" in hit:
                protect = rd32(c, esp + 0x10)
                max_size_low = rd32(c, esp + 0x18)
                rr = wait_return_and_regs(ret)
                section_handle = int(rr.get("eax", 0)) if isinstance(rr, dict) else 0
                if section_handle > 0:
                    section_handles[section_handle] = {"api": hit, "max_size": max_size_low, "prot": protect}
                report["events"].append({"type": "CreateFileMapping", "hook": hit, "section_handle": section_handle, "protect": protect, "maximum_size_low": max_size_low})
                continue

            if "NtProtectVirtualMemory" in hit:
                base_ptr = rd32(c, esp + 0x8)
                size_ptr = rd32(c, esp + 0xC)
                new_prot = rd32(c, esp + 0x10)
                old_prot_ptr = rd32(c, esp + 0x14)
                rr = wait_return_and_regs(ret)
                status = int(rr.get("eax", 0)) if isinstance(rr, dict) else 0
                base = rd32(c, base_ptr) if isinstance(base_ptr, int) else None
                size = rd32(c, size_ptr) if isinstance(size_ptr, int) else None
                old_prot = rd32(c, old_prot_ptr) if isinstance(old_prot_ptr, int) else None
                d = None
                move_link = None
                if status == 0 and isinstance(base, int) and isinstance(size, int) and size > 0:
                    kind = "protect_exec_out" if has_exec(new_prot) else "protect_rw_out"
                    move_link = match_recent_move(base, size) if has_exec(new_prot) else None
                    d = dump_region(c, kind, base, size, {"api": hit, "new_prot": new_prot, "old_prot": old_prot, "status": status, "move_link": move_link})
                    if has_exec(new_prot):
                        arm_exec_watch(base, size, hit)
                        if move_link:
                            report["events"].append({"type": "move_protect_exec_link", "hook": hit, "base": base, "size": size, "new_prot": new_prot, "move_base": move_link.get("base"), "move_size": move_link.get("size"), "move_source": move_link.get("source"), "overlap": move_link.get("overlap")})
                report["events"].append({"type": "NtProtectVirtualMemory", "hook": hit, "status": status, "base": base, "size": size, "new_prot": new_prot, "old_prot": old_prot, "move_link": move_link, "dump": d.get("file") if d else None})
                continue

            if "VirtualProtect" in hit:
                base = rd32(c, esp + 0x4)
                size = rd32(c, esp + 0x8)
                new_prot = rd32(c, esp + 0xC)
                old_prot_ptr = rd32(c, esp + 0x10)
                rr = wait_return_and_regs(ret)
                ok = int(rr.get("eax", 0)) if isinstance(rr, dict) else 0
                old_prot = rd32(c, old_prot_ptr) if isinstance(old_prot_ptr, int) else None
                d = None
                move_link = None
                if ok and has_exec(new_prot) and isinstance(base, int) and isinstance(size, int):
                    move_link = match_recent_move(base, size)
                    d = dump_region(c, "virtualprotect_exec_out", base, size, {"api": hit, "new_prot": new_prot, "old_prot": old_prot, "ok": bool(ok), "move_link": move_link})
                    arm_exec_watch(base, size, hit)
                    if move_link:
                        report["events"].append({"type": "move_protect_exec_link", "hook": hit, "base": base, "size": size, "new_prot": new_prot, "move_base": move_link.get("base"), "move_size": move_link.get("size"), "move_source": move_link.get("source"), "overlap": move_link.get("overlap")})
                report["events"].append({"type": "VirtualProtect", "hook": hit, "ok": bool(ok), "base": base, "size": size, "new_prot": new_prot, "old_prot": old_prot, "move_link": move_link, "dump": d.get("file") if d else None})
                continue

            if "NtAllocateVirtualMemory" in hit:
                base_ptr = rd32(c, esp + 0x8)
                size_ptr = rd32(c, esp + 0x10)
                alloc_type = rd32(c, esp + 0x14)
                prot = rd32(c, esp + 0x18)
                rr = wait_return_and_regs(ret)
                status = int(rr.get("eax", 0)) if isinstance(rr, dict) else 0
                base = rd32(c, base_ptr) if isinstance(base_ptr, int) else None
                size = rd32(c, size_ptr) if isinstance(size_ptr, int) else None
                d = None
                if status == 0 and isinstance(base, int) and isinstance(size, int) and size > 0:
                    kind = "alloc_exec_out" if has_exec(prot) else "alloc_rw_out"
                    d = dump_region(c, kind, base, size, {"api": hit, "prot": prot, "alloc_type": alloc_type, "status": status})
                    track_alloc_region(base, size, prot, hit, alloc_type)
                    refresh_hot_alloc_watchers()
                    if has_exec(prot):
                        arm_exec_watch(base, size, hit)
                report["events"].append({"type": "NtAllocateVirtualMemory", "hook": hit, "status": status, "base": base, "size": size, "prot": prot, "alloc_type": alloc_type, "shape_key": alloc_shape_key(size, prot, alloc_type), "dump": d.get("file") if d else None})
                continue

            if "VirtualAlloc" in hit:
                size = rd32(c, esp + 0x8)
                alloc_type = rd32(c, esp + 0xC)
                prot = rd32(c, esp + 0x10)
                rr = wait_return_and_regs(ret)
                base = int(rr.get("eax", 0)) if isinstance(rr, dict) else 0
                d = None
                if base > 0 and isinstance(size, int) and size > 0:
                    kind = "virtualalloc_exec_out" if has_exec(prot) else "virtualalloc_rw_out"
                    d = dump_region(c, kind, base, size, {"api": hit, "prot": prot, "alloc_type": alloc_type})
                    track_alloc_region(base, size, prot, hit, alloc_type)
                    refresh_hot_alloc_watchers()
                    if has_exec(prot):
                        arm_exec_watch(base, size, hit)
                report["events"].append({"type": "VirtualAlloc", "hook": hit, "base": base, "size": size, "prot": prot, "alloc_type": alloc_type, "shape_key": alloc_shape_key(size, prot, alloc_type), "dump": d.get("file") if d else None})
                continue

            if "WriteProcessMemory" in hit:
                dest = rd32(c, esp + 0x8)
                src = rd32(c, esp + 0xC)
                nsize = rd32(c, esp + 0x10)
                nwr_ptr = rd32(c, esp + 0x14)
                rr = wait_return_and_regs(ret)
                ok = int(rr.get("eax", 0)) if isinstance(rr, dict) else 0
                nwr = rd32(c, nwr_ptr) if isinstance(nwr_ptr, int) else None
                got = nwr if isinstance(nwr, int) and nwr > 0 else nsize
                if not isinstance(got, int) or got <= 0:
                    got = 0
                blob = rb(c, src, min(got, REGION_DUMP_CAP)) if isinstance(src, int) and got > 0 else b""
                if isinstance(dest, int) and isinstance(got, int) and got > 0:
                    add_write_volume(dest, got, hit)
                d = dump_blob("writeprocess_src", blob, {"api": hit, "dest": dest, "src": src, "nsize": nsize, "written": nwr, "ok": bool(ok)}) if blob else None
                report["events"].append({"type": "WriteProcessMemory", "hook": hit, "ok": bool(ok), "dest": dest, "src": src, "nsize": nsize, "written": nwr, "tracked_write_bytes": got, "dump": d.get("file") if d else None})
                continue
            if "NtMapViewOfSection" in hit:
                section_handle = rd32(c, esp + 0x4)
                base_ptr = rd32(c, esp + 0xC)
                view_size_ptr = rd32(c, esp + 0x1C)
                win32_prot = rd32(c, esp + 0x28)
                rr = wait_return_and_regs(ret)
                status = int(rr.get("eax", 0)) if isinstance(rr, dict) else 0
                base = rd32(c, base_ptr) if isinstance(base_ptr, int) else None
                view_size = rd32(c, view_size_ptr) if isinstance(view_size_ptr, int) else None
                dump_size = bounded_region_size(view_size)
                d = None
                section_meta = section_handles.get(section_handle) if isinstance(section_handle, int) else None
                if status == 0 and isinstance(base, int) and base > 0:
                    kind = "mapview_section_exec_out" if has_exec(win32_prot) else "mapview_section_out"
                    d = dump_region(c, kind, base, dump_size, {"api": hit, "status": status, "view_size": view_size, "win32_prot": win32_prot, "section_handle": section_handle})
                    map_relations.append({"section_handle": section_handle, "base": base, "view_size": view_size, "api": hit})
                    if has_exec(win32_prot):
                        arm_exec_watch(base, dump_size, hit)
                report["events"].append({"type": "NtMapViewOfSection", "hook": hit, "status": status, "section_handle": section_handle, "section_meta": section_meta, "base": base, "view_size": view_size, "win32_prot": win32_prot, "dump": d.get("file") if d else None})
                continue

            if "MapViewOfFile" in hit:
                file_mapping_handle = rd32(c, esp + 0x4)
                desired_access = rd32(c, esp + 0x8)
                view_size = rd32(c, esp + 0x14)
                rr = wait_return_and_regs(ret)
                base = int(rr.get("eax", 0)) if isinstance(rr, dict) else 0
                dump_size = bounded_region_size(view_size)
                d = None
                section_meta = section_handles.get(file_mapping_handle) if isinstance(file_mapping_handle, int) else None
                if base > 0:
                    kind = "mapview_exec_out" if isinstance(desired_access, int) and (desired_access & FILE_MAP_EXECUTE) else "mapview_out"
                    d = dump_region(c, kind, base, dump_size, {"api": hit, "desired_access": desired_access, "view_size": view_size, "section_handle": file_mapping_handle})
                    map_relations.append({"section_handle": file_mapping_handle, "base": base, "view_size": view_size, "api": hit})
                    if isinstance(desired_access, int) and (desired_access & FILE_MAP_EXECUTE):
                        arm_exec_watch(base, dump_size, hit)
                report["events"].append({"type": "MapViewOfFile", "hook": hit, "section_handle": file_mapping_handle, "section_meta": section_meta, "base": base, "desired_access": desired_access, "view_size": view_size, "dump": d.get("file") if d else None})
                continue

            if "NtWriteVirtualMemory" in hit:
                dest = rd32(c, esp + 0x8)
                src = rd32(c, esp + 0xC)
                nsize = rd32(c, esp + 0x10)
                nwr_ptr = rd32(c, esp + 0x14)
                rr = wait_return_and_regs(ret)
                status = int(rr.get("eax", 0)) if isinstance(rr, dict) else 0
                nwr = rd32(c, nwr_ptr) if isinstance(nwr_ptr, int) else None
                got = nwr if isinstance(nwr, int) and nwr > 0 else nsize
                if not isinstance(got, int) or got <= 0:
                    got = 0
                src_blob = rb(c, src, min(got, REGION_DUMP_CAP)) if isinstance(src, int) and got > 0 else b""
                dst_blob = rb(c, dest, min(got, REGION_DUMP_CAP)) if isinstance(dest, int) and got > 0 else b""
                if isinstance(dest, int) and isinstance(got, int) and got > 0:
                    add_write_volume(dest, got, hit)
                ds = dump_blob("ntwritevirtualmemory_src", src_blob, {"api": hit, "dest": dest, "src": src, "nsize": nsize, "written": nwr, "status": status}) if src_blob else None
                dd = dump_blob("ntwritevirtualmemory_dest", dst_blob, {"api": hit, "dest": dest, "src": src, "nsize": nsize, "written": nwr, "status": status}) if dst_blob else None
                report["events"].append({"type": "NtWriteVirtualMemory", "hook": hit, "status": status, "dest": dest, "src": src, "nsize": nsize, "written": nwr, "tracked_write_bytes": got, "dump_src": ds.get("file") if ds else None, "dump_dest": dd.get("file") if dd else None})
                continue

            if "RtlMoveMemory" in hit or "RtlCopyMemory" in hit or "memcpy" in hit or "memmove" in hit:
                dest = rd32(c, esp + 0x4)
                src = rd32(c, esp + 0x8)
                nsize = rd32(c, esp + 0xC)
                rr = wait_return_and_regs(ret)
                _ = rr
                got = nsize if isinstance(nsize, int) and nsize > 0 else 0
                src_blob = rb(c, src, min(got, REGION_DUMP_CAP)) if isinstance(src, int) and got > 0 else b""
                dst_blob = rb(c, dest, min(got, REGION_DUMP_CAP)) if isinstance(dest, int) and got > 0 else b""
                if isinstance(dest, int) and isinstance(got, int) and got > 0:
                    add_write_volume(dest, got, hit)
                    remember_recent_move(dest, got, hit)
                ds = dump_blob("rtlmovememory_src", src_blob, {"api": hit, "dest": dest, "src": src, "nsize": nsize}) if src_blob else None
                dd = dump_blob("rtlmovememory_dest", dst_blob, {"api": hit, "dest": dest, "src": src, "nsize": nsize}) if dst_blob else None
                report["events"].append({"type": "RtlMoveMemory", "hook": hit, "dest": dest, "src": src, "nsize": nsize, "tracked_write_bytes": got, "dump_src": ds.get("file") if ds else None, "dump_dest": dd.get("file") if dd else None})
                continue

            if "RtlDecompressBuffer" in hit:
                fmt = rd32(c, esp + 0x4)
                out_ptr = rd32(c, esp + 0x8)
                out_cap = rd32(c, esp + 0xC)
                in_ptr = rd32(c, esp + 0x10)
                in_size = rd32(c, esp + 0x14)
                final_ptr = rd32(c, esp + 0x18)
                rr = wait_return_and_regs(ret)
                status = int(rr.get("eax", 0)) if isinstance(rr, dict) else 0
                final_size = rd32(c, final_ptr) if isinstance(final_ptr, int) else None
                got = final_size if isinstance(final_size, int) and final_size > 0 else out_cap
                if not isinstance(got, int) or got <= 0:
                    got = 0
                blob = rb(c, out_ptr, min(got, REGION_DUMP_CAP)) if isinstance(out_ptr, int) and got > 0 else b""
                d = dump_blob("rtldecompress_out", blob, {"api": hit, "fmt": fmt, "status": status, "out_cap": out_cap, "out_size": final_size, "in_size": in_size, "out_ptr": out_ptr, "in_ptr": in_ptr}) if blob else None
                report["events"].append({"type": "RtlDecompressBuffer", "hook": hit, "status": status, "fmt": fmt, "out_ptr": out_ptr, "out_cap": out_cap, "out_size": final_size, "in_size": in_size, "dump": d.get("file") if d else None})
                continue

            if "BCryptDecrypt" in hit:
                in_ptr = rd32(c, esp + 0x8)
                in_size = rd32(c, esp + 0xC)
                out_ptr = rd32(c, esp + 0x1C)
                out_cap = rd32(c, esp + 0x20)
                out_size_ptr = rd32(c, esp + 0x24)
                rr = wait_return_and_regs(ret)
                status = int(rr.get("eax", 0)) if isinstance(rr, dict) else 0
                out_size = rd32(c, out_size_ptr) if isinstance(out_size_ptr, int) else None
                got = out_size if isinstance(out_size, int) and out_size > 0 else out_cap
                if not isinstance(got, int) or got <= 0:
                    got = 0
                blob = rb(c, out_ptr, min(got, REGION_DUMP_CAP)) if isinstance(out_ptr, int) and got > 0 else b""
                d = dump_blob("bcryptdecrypt_out", blob, {"api": hit, "status": status, "in_size": in_size, "out_cap": out_cap, "out_size": out_size, "in_ptr": in_ptr, "out_ptr": out_ptr}) if blob else None
                report["events"].append({"type": "BCryptDecrypt", "hook": hit, "status": status, "in_size": in_size, "out_cap": out_cap, "out_size": out_size, "dump": d.get("file") if d else None})
                continue

            if "CryptDecrypt" in hit:
                data_ptr = rd32(c, esp + 0x14)
                data_len_ptr = rd32(c, esp + 0x18)
                rr = wait_return_and_regs(ret)
                ok = int(rr.get("eax", 0)) if isinstance(rr, dict) else 0
                out_size = rd32(c, data_len_ptr) if isinstance(data_len_ptr, int) else None
                got = out_size if isinstance(out_size, int) and out_size > 0 else 0
                blob = rb(c, data_ptr, min(got, REGION_DUMP_CAP)) if isinstance(data_ptr, int) and got > 0 else b""
                d = dump_blob("cryptdecrypt_out", blob, {"api": hit, "ok": bool(ok), "out_size": out_size, "data_ptr": data_ptr}) if blob else None
                report["events"].append({"type": "CryptDecrypt", "hook": hit, "ok": bool(ok), "out_size": out_size, "dump": d.get("file") if d else None})
                continue

            # Generic loader/proc APIs: log return status and return value.
            rr = wait_return_and_regs(ret)
            eax = int(rr.get("eax", 0)) if isinstance(rr, dict) else 0
            report["events"].append({"type": "LoaderApi", "hook": hit, "eax": eax})

        except Exception as ex:
            report["events"].append({"type": "hook_error", "hook": hit, "error": str(ex)})
            report["errors"].append({"hook": hit, "error": str(ex)})
        finally:
            try:
                c.clear_breakpoint(int(ret))
            except Exception:
                pass
            flush("running")

except Exception as ex:
    report["error"] = str(ex)
finally:
    for n in hooks.keys():
        try:
            c.clear_breakpoint(n)
        except Exception:
            pass

top_candidates = sorted(report.get("dumps", []), key=lambda d: float(d.get("score", 0.0)), reverse=True)[:12]
report["top_candidates"] = top_candidates
report["section_handles"] = section_handles
report["map_relations"] = map_relations
summary = {
    "events_seen": seen,
    "events": len(report.get("events", [])),
    "dumps": len(report.get("dumps", [])),
    "top_candidates": len(top_candidates),
    "tracked_pages": len(page_write_volume),
    "tracked_alloc_regions": len(alloc_regions),
    "section_handles": len(section_handles),
    "map_relations": len(map_relations),
    "alloc_shapes": len(alloc_shape_counts),
    "hot_alloc_watch": len(hot_alloc_watch),
    "recent_move_regions": len(recent_move_regions),
    "elapsed_sec": round(time.time() - start, 2),
}
flush("done", summary)
print(json.dumps({"json": str(REPORT).replace("\\", "/"), "summary": summary, "hooks": hooks}, indent=2))



