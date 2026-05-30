"""AGENT 7 / AGENT 9: Memory offset calibration tool for Tibia 7.4 OTS.

Usage:
    python scripts/calibrate_memory.py --scan-hp    # scan for HP offset
    python scripts/calibrate_memory.py --scan-all   # scan all offsets
    python scripts/calibrate_memory.py --verify     # verify current offsets
    python scripts/calibrate_memory.py --export     # export to bot/perception/memory_reader.py

Workflow:
  1. Run Tibia client + be logged in
  2. Note your current HP (e.g. 185)
  3. Run: python scripts/calibrate_memory.py --scan-hp --value 185
  4. Take a hit, note new HP (e.g. 167)
  5. Run: python scripts/calibrate_memory.py --scan-hp --value 167 --refine
  6. Confirmed offset printed — update memory_reader.py

Requires: Windows + admin or same-user process + pip install pywin32 (optional)
"""
from __future__ import annotations
import argparse
import ctypes
import ctypes.wintypes as wt
import json
import struct
import sys
import time
from pathlib import Path
from typing import Optional

PROCESS_VM_READ       = 0x0010
PROCESS_QUERY_INFO    = 0x0400
TH32CS_SNAPPROCESS    = 0x00000002
MEM_COMMIT            = 0x1000
PAGE_READABLE         = 0x02 | 0x04 | 0x20 | 0x40  # READONLY|READWRITE|EXECUTE_READ|EXECUTE_READWRITE

# Current offsets from memory_reader.py (update after calibration)
KNOWN_OFFSETS = {
    "hp":      0x00532BA0,
    "hp_max":  0x00532BA4,
    "mp":      0x00532BA8,
    "mp_max":  0x00532BAC,
    "level":   0x00532BB0,
    "exp":     0x00532BB4,
    "pos_x":   0x00532B94,
    "pos_y":   0x00532B98,
    "pos_z":   0x00532B9C,
}

TIBIA_EXE = "Tibia.exe"


class _PROCESSENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize",              wt.DWORD),
        ("cntUsage",            wt.DWORD),
        ("th32ProcessID",       wt.DWORD),
        ("th32DefaultHeapID",   ctypes.POINTER(ctypes.c_ulong)),
        ("th32ModuleID",        wt.DWORD),
        ("cntThreads",          wt.DWORD),
        ("th32ParentProcessID", wt.DWORD),
        ("pcPriClassBase",      ctypes.c_long),
        ("dwFlags",             wt.DWORD),
        ("szExeFile",           ctypes.c_char * 260),
    ]


class _MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress",       ctypes.c_void_p),
        ("AllocationBase",    ctypes.c_void_p),
        ("AllocationProtect", wt.DWORD),
        ("RegionSize",        ctypes.c_size_t),
        ("State",             wt.DWORD),
        ("Protect",           wt.DWORD),
        ("Type",              wt.DWORD),
    ]


def find_pid(name: str) -> Optional[int]:
    k32 = ctypes.windll.kernel32
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == wt.HANDLE(-1).value:
        return None
    entry = _PROCESSENTRY32()
    entry.dwSize = ctypes.sizeof(_PROCESSENTRY32)
    found = None
    if k32.Process32First(snap, ctypes.byref(entry)):
        while True:
            if entry.szExeFile.decode("utf-8", errors="ignore").lower() == name.lower():
                found = entry.th32ProcessID
                break
            if not k32.Process32Next(snap, ctypes.byref(entry)):
                break
    k32.CloseHandle(snap)
    return found


def open_process(pid: int):
    return ctypes.windll.kernel32.OpenProcess(
        PROCESS_VM_READ | PROCESS_QUERY_INFO, False, pid)


def read_int32(handle, addr: int) -> Optional[int]:
    buf  = ctypes.create_string_buffer(4)
    read = ctypes.c_size_t(0)
    ok   = ctypes.windll.kernel32.ReadProcessMemory(
        handle, ctypes.c_void_p(addr), buf, 4, ctypes.byref(read))
    if ok and read.value == 4:
        return struct.unpack("<i", bytes(buf))[0]
    return None


def scan_value(handle, target: int, prev_candidates: list[int] | None = None) -> list[int]:
    """Scan process memory for int32 == target. If prev_candidates given, filter."""
    k32    = ctypes.windll.kernel32
    found  = []
    mbi    = _MEMORY_BASIC_INFORMATION()
    addr   = 0

    if prev_candidates is not None:
        for a in prev_candidates:
            v = read_int32(handle, a)
            if v == target:
                found.append(a)
        return found

    # Full scan
    chunk   = 4096 * 64
    buf_raw = ctypes.create_string_buffer(chunk)
    while addr < 0x7FFFFFFF:
        res = k32.VirtualQueryEx(
            handle, ctypes.c_void_p(addr),
            ctypes.byref(mbi), ctypes.sizeof(mbi))
        if not res:
            break
        if (mbi.State == MEM_COMMIT
                and (mbi.Protect & PAGE_READABLE)
                and mbi.RegionSize > 0):
            region_addr = mbi.BaseAddress or addr
            size        = mbi.RegionSize
            offset      = 0
            while offset < size:
                read_size = min(chunk, size - offset)
                read_n    = ctypes.c_size_t(0)
                if k32.ReadProcessMemory(
                        handle,
                        ctypes.c_void_p(region_addr + offset),
                        buf_raw, read_size,
                        ctypes.byref(read_n)):
                    data = bytes(buf_raw[:read_n.value])
                    for i in range(0, len(data) - 3, 4):
                        val = struct.unpack_from("<i", data, i)[0]
                        if val == target:
                            found.append(region_addr + offset + i)
                offset += read_size
        addr = (mbi.BaseAddress or addr) + max(mbi.RegionSize, 1)
    return found


def verify_offsets(handle) -> None:
    print("\n=== Verifying known offsets ===")
    for name, offset in KNOWN_OFFSETS.items():
        val = read_int32(handle, offset)
        print(f"  {name:10s} @ 0x{offset:08X} = {val}")


def export_offsets(updates: dict) -> None:
    """Patch memory_reader.py with new offset values."""
    path = Path("bot/perception/memory_reader.py")
    if not path.exists():
        print("ERROR: memory_reader.py not found")
        return
    content = path.read_text(encoding="utf-8")
    for name, addr in updates.items():
        const_name = f"OFFSET_{name.upper()}"
        old_line_pattern = f"{const_name}   = 0x"
        for line in content.splitlines():
            if line.startswith(const_name):
                new_line = f"{const_name.ljust(16)} = 0x{addr:08X}   # calibrated"
                content = content.replace(line, new_line)
                print(f"  Updated {const_name} → 0x{addr:08X}")
                break
    path.write_text(content, encoding="utf-8")
    print(f"\nExported to {path}")


def main():
    if sys.platform != "win32":
        print("This tool requires Windows.")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Tibia memory offset calibration")
    parser.add_argument("--scan-hp",  action="store_true", help="Scan for HP offset")
    parser.add_argument("--scan-mp",  action="store_true", help="Scan for MP offset")
    parser.add_argument("--scan-all", action="store_true", help="Verify all known offsets")
    parser.add_argument("--verify",   action="store_true", help="Verify current offsets")
    parser.add_argument("--export",   action="store_true", help="Export calibrated offsets")
    parser.add_argument("--value",    type=int, help="Target value to scan for")
    parser.add_argument("--refine",   action="store_true", help="Refine previous scan results")
    parser.add_argument("--candidates-file", default=".calibrate_candidates.json",
                        help="File to store scan candidates between runs")
    args = parser.parse_args()

    pid = find_pid(TIBIA_EXE)
    if pid is None:
        print(f"ERROR: {TIBIA_EXE} not found. Start Tibia client first.")
        sys.exit(1)

    handle = open_process(pid)
    if not handle:
        print(f"ERROR: Cannot open process PID {pid}. Try running as Administrator.")
        sys.exit(1)

    print(f"Attached to {TIBIA_EXE} PID {pid}")

    try:
        if args.verify or args.scan_all:
            verify_offsets(handle)

        if (args.scan_hp or args.scan_mp) and args.value is not None:
            field = "HP" if args.scan_hp else "MP"
            cands_file = Path(args.candidates_file)

            prev = None
            if args.refine and cands_file.exists():
                prev = json.loads(cands_file.read_text())
                print(f"Refining {len(prev)} candidates for {field}={args.value}...")
            else:
                print(f"Full scan for {field}={args.value} (this may take 30-60s)...")

            results = scan_value(handle, args.value, prev)
            print(f"Found {len(results)} candidates")

            if len(results) <= 20:
                for a in results:
                    print(f"  0x{a:08X}")
                if len(results) == 1:
                    print(f"\n✅ CONFIRMED OFFSET for {field}: 0x{results[0]:08X}")
                    print(f"   Update memory_reader.py: OFFSET_{field.upper()} = 0x{results[0]:08X}")
            else:
                print("  Too many results — take a hit and re-run with --refine --value <new_hp>")

            cands_file.write_text(json.dumps(results))

        if args.export:
            # Load confirmed offsets from a JSON file if available
            conf_file = Path(".calibrate_confirmed.json")
            if conf_file.exists():
                confirmed = json.loads(conf_file.read_text())
                export_offsets(confirmed)
            else:
                print("No confirmed offsets file found. Run --scan-hp/--scan-mp first.")

    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


if __name__ == "__main__":
    main()
