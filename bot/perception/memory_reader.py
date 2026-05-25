"""AGENT 7 / AGENT 3: Windows ReadProcessMemory — read Tibia client state.

Reads player position (x, y, z), HP, max HP, MP, max MP directly from
Tibia 7.4 OTS process memory without screen parsing.

Offsets are for Tibia 7.4 client (standard OTS build).
Adjust BASE_ADDRESS and offsets per your client version using Cheat Engine.

Graceful fallback: returns None for all fields when:
  - Not on Windows
  - Tibia process not found
  - ctypes / win32 unavailable
  - Access denied (non-elevated process)

Usage:
    reader = TibiaMemoryReader()
    if reader.attach():
        pos = reader.read_position()   # (x, y, z) or None
        hp  = reader.read_hp()         # (current, max) or None
"""
from __future__ import annotations
import logging
import struct
import sys
from typing import Optional

logger = logging.getLogger(__name__)

# ── Tibia 7.4 OTS memory offsets ─────────────────────────────────────────────
# These are typical OTClient / OTS 7.4 offsets — calibrate with Cheat Engine.
TIBIA_PROCESS_NAME = "Tibia.exe"

# Direct offsets (base + offset relative to client base address or fixed)
# For OTClient-based servers (e.g. Nekiro 7.4 downgrade), addresses differ.
# Placeholder values — replace with Cheat Engine findings for your client.
OFFSET_POS_X   = 0x00532B94   # int32 — player X
OFFSET_POS_Y   = 0x00532B98   # int32 — player Y
OFFSET_POS_Z   = 0x00532B9C   # int32 — player Z (floor)
OFFSET_HP      = 0x00532BA0   # int32 — current HP
OFFSET_HP_MAX  = 0x00532BA4   # int32 — max HP
OFFSET_MP      = 0x00532BA8   # int32 — current MP
OFFSET_MP_MAX  = 0x00532BAC   # int32 — max MP
OFFSET_EXP     = 0x00532BB4   # int64 — total experience
OFFSET_LEVEL   = 0x00532BB0   # int32 — player level

# ── Platform check ────────────────────────────────────────────────────────────
_WINDOWS = sys.platform == "win32"

if _WINDOWS:
    try:
        import ctypes
        import ctypes.wintypes as wt
        _CTYPES_OK = True
    except ImportError:
        _CTYPES_OK = False
else:
    _CTYPES_OK = False

PROCESS_VM_READ    = 0x0010
PROCESS_QUERY_INFO = 0x0400
TH32CS_SNAPPROCESS = 0x00000002


class _PROCESSENTRY32(ctypes.Structure if _CTYPES_OK else object):
    if _CTYPES_OK:
        _fields_ = [
            ("dwSize",              ctypes.wintypes.DWORD),
            ("cntUsage",            ctypes.wintypes.DWORD),
            ("th32ProcessID",       ctypes.wintypes.DWORD),
            ("th32DefaultHeapID",   ctypes.POINTER(ctypes.c_ulong)),
            ("th32ModuleID",        ctypes.wintypes.DWORD),
            ("cntThreads",          ctypes.wintypes.DWORD),
            ("th32ParentProcessID", ctypes.wintypes.DWORD),
            ("pcPriClassBase",      ctypes.c_long),
            ("dwFlags",             ctypes.wintypes.DWORD),
            ("szExeFile",           ctypes.c_char * 260),
        ]


class TibiaMemoryReader:
    """Read Tibia process memory via Windows ReadProcessMemory API."""

    def __init__(self, process_name: str = TIBIA_PROCESS_NAME):
        self.process_name = process_name
        self._pid:    Optional[int] = None
        self._handle: Optional[int] = None

    # ── Public API ────────────────────────────────────────────────────────────

    def attach(self) -> bool:
        """Find Tibia process and open handle. Returns True on success."""
        if not _CTYPES_OK:
            logger.debug("Memory reader unavailable (not Windows or no ctypes)")
            return False
        pid = self._find_pid()
        if pid is None:
            logger.debug("Tibia process not found (%s)", self.process_name)
            return False
        try:
            k32 = ctypes.windll.kernel32
            handle = k32.OpenProcess(
                PROCESS_VM_READ | PROCESS_QUERY_INFO, False, pid)
            if not handle:
                logger.warning("OpenProcess failed for PID %d", pid)
                return False
            self._pid    = pid
            self._handle = handle
            logger.info("Attached to Tibia PID %d", pid)
            return True
        except Exception as e:
            logger.warning("attach() error: %s", e)
            return False

    def detach(self) -> None:
        """Close process handle."""
        if self._handle and _CTYPES_OK:
            try:
                ctypes.windll.kernel32.CloseHandle(self._handle)
            except Exception:
                pass
        self._handle = None
        self._pid    = None

    def read_position(self) -> Optional[tuple[int, int, int]]:
        """Return (x, y, z) or None."""
        x = self._read_int32(OFFSET_POS_X)
        y = self._read_int32(OFFSET_POS_Y)
        z = self._read_int32(OFFSET_POS_Z)
        if None in (x, y, z):
            return None
        return (x, y, z)

    def read_hp(self) -> Optional[tuple[int, int]]:
        """Return (current_hp, max_hp) or None."""
        hp     = self._read_int32(OFFSET_HP)
        hp_max = self._read_int32(OFFSET_HP_MAX)
        if None in (hp, hp_max):
            return None
        return (hp, hp_max)

    def read_mp(self) -> Optional[tuple[int, int]]:
        """Return (current_mp, max_mp) or None."""
        mp     = self._read_int32(OFFSET_MP)
        mp_max = self._read_int32(OFFSET_MP_MAX)
        if None in (mp, mp_max):
            return None
        return (mp, mp_max)

    def read_level(self) -> Optional[int]:
        return self._read_int32(OFFSET_LEVEL)

    def read_exp(self) -> Optional[int]:
        return self._read_int64(OFFSET_EXP)

    def read_all(self) -> dict:
        """Return dict with all available fields (None where unreadable)."""
        return {
            "position": self.read_position(),
            "hp":       self.read_hp(),
            "mp":       self.read_mp(),
            "level":    self.read_level(),
            "exp":      self.read_exp(),
        }

    # ── Private helpers ───────────────────────────────────────────────────────

    def _find_pid(self) -> Optional[int]:
        """Enumerate processes to find Tibia PID."""
        if not _CTYPES_OK:
            return None
        try:
            k32 = ctypes.windll.kernel32
            snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
            if snap == ctypes.wintypes.HANDLE(-1).value:
                return None
            entry = _PROCESSENTRY32()
            entry.dwSize = ctypes.sizeof(_PROCESSENTRY32)
            try:
                found = None
                if k32.Process32First(snap, ctypes.byref(entry)):
                    while True:
                        name = entry.szExeFile.decode("utf-8", errors="ignore")
                        if name.lower() == self.process_name.lower():
                            found = entry.th32ProcessID
                            break
                        if not k32.Process32Next(snap, ctypes.byref(entry)):
                            break
                return found
            finally:
                k32.CloseHandle(snap)
        except Exception as e:
            logger.warning("_find_pid error: %s", e)
            return None

    def _read_bytes(self, address: int, size: int) -> Optional[bytes]:
        if not self._handle or not _CTYPES_OK:
            return None
        try:
            buf   = ctypes.create_string_buffer(size)
            read  = ctypes.c_size_t(0)
            ok    = ctypes.windll.kernel32.ReadProcessMemory(
                self._handle, ctypes.c_void_p(address),
                buf, size, ctypes.byref(read))
            if ok and read.value == size:
                return bytes(buf)
            return None
        except Exception:
            return None

    def _read_int32(self, address: int) -> Optional[int]:
        raw = self._read_bytes(address, 4)
        if raw is None:
            return None
        return struct.unpack("<i", raw)[0]

    def _read_int64(self, address: int) -> Optional[int]:
        raw = self._read_bytes(address, 8)
        if raw is None:
            return None
        return struct.unpack("<q", raw)[0]


# Module-level singleton — attach lazily
_reader: Optional[TibiaMemoryReader] = None


def get_reader() -> TibiaMemoryReader:
    """Return attached singleton reader (attaches on first call)."""
    global _reader
    if _reader is None:
        _reader = TibiaMemoryReader()
        _reader.attach()
    return _reader
