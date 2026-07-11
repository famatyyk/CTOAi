"""Window detection and capture — finds Tibia client window and captures it.

Uses Win32 API (ctypes) on Windows; falls back to full-screen mss capture on
other platforms so the rest of the bot can run headless in CI.
"""

from __future__ import annotations
import ctypes
import ctypes.wintypes as wt
import logging
import time
from dataclasses import dataclass
from typing import Optional

from ..config.runtime_profile import get_float, get_int, get_list, get_str

log = logging.getLogger(__name__)

_WINDOW_TITLES_DEFAULT = ["Tibia", "TibiaClient", "The Forgotten Server", "KingsVale"]
_WINDOW_LOG_INTERVAL_SEC = get_float("BOT_WINDOW_LOG_INTERVAL_SEC", 30.0)
_WINDOW_MIN_WIDTH = get_int("BOT_WINDOW_MIN_WIDTH", 640)
_WINDOW_MIN_HEIGHT = get_int("BOT_WINDOW_MIN_HEIGHT", 480)
_WINDOW_TITLE_EXCLUDES = [
    "opera",
    "chrome",
    "edge",
    "firefox",
    "brave",
    "search",
    "google",
    "bing",
    "youtube",
]
_last_window_log_ts = 0.0
_last_window_log_hwnd = 0
_last_window_miss_log_ts = 0.0
_last_good_handle: Optional["WindowHandle"] = None


def _window_title_patterns() -> list[str]:
    vals = get_list("BOT_WINDOW_TITLES", _WINDOW_TITLES_DEFAULT)
    return vals or _WINDOW_TITLES_DEFAULT


def _active_window_title_hint() -> str:
    return get_str("BOT_WINDOW_TITLE_ACTIVE", "").strip().lower()


# ── Win32 helpers ────────────────────────────────────────────────────────────
try:
    _user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    _gdi32 = ctypes.windll.gdi32  # type: ignore[attr-defined]
    _WIN32_AVAILABLE = True
except AttributeError:
    _WIN32_AVAILABLE = False


class _BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wt.DWORD),
        ("biWidth", wt.LONG),
        ("biHeight", wt.LONG),
        ("biPlanes", wt.WORD),
        ("biBitCount", wt.WORD),
        ("biCompression", wt.DWORD),
        ("biSizeImage", wt.DWORD),
        ("biXPelsPerMeter", wt.LONG),
        ("biYPelsPerMeter", wt.LONG),
        ("biClrUsed", wt.DWORD),
        ("biClrImportant", wt.DWORD),
    ]


class _BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", _BITMAPINFOHEADER),
        ("bmiColors", wt.DWORD * 3),
    ]


@dataclass
class WindowHandle:
    hwnd: int
    title: str
    rect: tuple[int, int, int, int]  # left, top, right, bottom

    @property
    def width(self) -> int:
        return self.rect[2] - self.rect[0]

    @property
    def height(self) -> int:
        return self.rect[3] - self.rect[1]

    @property
    def left(self) -> int:
        return self.rect[0]

    @property
    def top(self) -> int:
        return self.rect[1]


def find_tibia_window() -> Optional[WindowHandle]:
    """Return the first Tibia window found, or None."""
    if not _WIN32_AVAILABLE:
        log.debug("Win32 not available — window detection skipped")
        return None

    title_patterns = _window_title_patterns()
    found: list[tuple[int, WindowHandle]] = []
    active_hint = _active_window_title_hint()

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    def _enum_cb(hwnd: int, _lParam: int) -> bool:
        buf = ctypes.create_unicode_buffer(256)
        _user32.GetWindowTextW(hwnd, buf, 256)
        title = buf.value
        title_lower = title.lower()
        for pat in title_patterns:
            if pat.lower() in title_lower and _user32.IsWindowVisible(hwnd):
                if any(exclude in title_lower for exclude in _WINDOW_TITLE_EXCLUDES):
                    break
                rect = wt.RECT()
                _user32.GetWindowRect(hwnd, ctypes.byref(rect))
                handle = WindowHandle(
                    hwnd=hwnd,
                    title=title,
                    rect=(rect.left, rect.top, rect.right, rect.bottom),
                )
                if (
                    handle.width < _WINDOW_MIN_WIDTH
                    or handle.height < _WINDOW_MIN_HEIGHT
                ):
                    break
                score = handle.width * handle.height
                if active_hint and active_hint in title_lower:
                    score += 10_000_000
                elif pat.lower() in title_lower:
                    score += 1_000
                found.append((score, handle))
                break
        return True

    _user32.EnumWindows(_enum_cb, 0)
    if found:
        handle = max(found, key=lambda item: item[0])[1]
        global _last_window_log_ts, _last_window_log_hwnd, _last_good_handle
        now = time.monotonic()
        should_log = (
            int(handle.hwnd) != int(_last_window_log_hwnd)
            or (now - _last_window_log_ts) >= _WINDOW_LOG_INTERVAL_SEC
        )
        if should_log:
            log.info(
                "Tibia window found: %s  hwnd=%d  %dx%d",
                handle.title,
                handle.hwnd,
                handle.width,
                handle.height,
            )
            _last_window_log_hwnd = int(handle.hwnd)
            _last_window_log_ts = now
        _last_good_handle = handle
        return handle

    global _last_window_miss_log_ts
    if _last_good_handle is not None:
        try:
            if _user32.IsWindow(_last_good_handle.hwnd):
                rect = wt.RECT()
                _user32.GetWindowRect(_last_good_handle.hwnd, ctypes.byref(rect))
                refreshed = WindowHandle(
                    hwnd=_last_good_handle.hwnd,
                    title=_last_good_handle.title,
                    rect=(rect.left, rect.top, rect.right, rect.bottom),
                )
                if (
                    refreshed.width >= _WINDOW_MIN_WIDTH
                    and refreshed.height >= _WINDOW_MIN_HEIGHT
                ):
                    return refreshed
        except Exception as exc:
            log.debug("cached Tibia window refresh failed: %s", exc)

    now = time.monotonic()
    if (now - _last_window_miss_log_ts) >= _WINDOW_LOG_INTERVAL_SEC:
        log.warning("Tibia window not found (titles searched: %s)", title_patterns)
        _last_window_miss_log_ts = now
    return None


def capture_window(handle: Optional[WindowHandle] = None):
    """Capture the Tibia window; returns numpy array (BGR) or None."""
    try:
        import mss
        import numpy as np
    except ImportError:
        return None

    if handle is None:
        handle = find_tibia_window()

    if handle is not None:
        try:
            import cv2

            client_rect = wt.RECT()
            _user32.GetClientRect(handle.hwnd, ctypes.byref(client_rect))
            width = int(client_rect.right - client_rect.left)
            height = int(client_rect.bottom - client_rect.top)
            if width > 0 and height > 0:
                hwnd_dc = _user32.GetWindowDC(handle.hwnd)
                mem_dc = _gdi32.CreateCompatibleDC(hwnd_dc)
                bitmap = _gdi32.CreateCompatibleBitmap(hwnd_dc, width, height)
                old_bitmap = _gdi32.SelectObject(mem_dc, bitmap)
                try:
                    for print_flag in (2, 0, 1):
                        if _user32.PrintWindow(handle.hwnd, mem_dc, print_flag) != 1:
                            continue
                        bmi = _BITMAPINFO()
                        bmi.bmiHeader.biSize = ctypes.sizeof(_BITMAPINFOHEADER)
                        bmi.bmiHeader.biWidth = width
                        bmi.bmiHeader.biHeight = -height
                        bmi.bmiHeader.biPlanes = 1
                        bmi.bmiHeader.biBitCount = 32
                        bmi.bmiHeader.biCompression = 0
                        bmi.bmiHeader.biSizeImage = width * height * 4
                        buffer = (ctypes.c_ubyte * (width * height * 4))()
                        got_bits = _gdi32.GetDIBits(
                            mem_dc, bitmap, 0, height, buffer, ctypes.byref(bmi), 0
                        )
                        if got_bits:
                            frame = np.frombuffer(buffer, dtype=np.uint8).reshape(
                                (height, width, 4)
                            )
                            if frame.mean() > 1.0:
                                return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                finally:
                    _gdi32.SelectObject(mem_dc, old_bitmap)
                    _gdi32.DeleteObject(bitmap)
                    _gdi32.DeleteDC(mem_dc)
                    _user32.ReleaseDC(handle.hwnd, hwnd_dc)
        except Exception as exc:
            log.debug("PrintWindow capture failed: %s", exc)

    with mss.mss() as sct:
        if handle is not None:
            client_left = handle.left
            client_top = handle.top
            client_right = handle.rect[2]
            client_bottom = handle.rect[3]
            try:
                client_rect = wt.RECT()
                _user32.GetClientRect(handle.hwnd, ctypes.byref(client_rect))
                client_point = wt.POINT(0, 0)
                _user32.ClientToScreen(handle.hwnd, ctypes.byref(client_point))
                client_left = int(client_point.x)
                client_top = int(client_point.y)
                client_right = client_left + int(client_rect.right - client_rect.left)
                client_bottom = client_top + int(client_rect.bottom - client_rect.top)
            except Exception as exc:
                log.debug("client rect fallback failed: %s", exc)
            region = {
                "left": client_left,
                "top": client_top,
                "width": max(1, client_right - client_left),
                "height": max(1, client_bottom - client_top),
            }
        else:
            region = sct.monitors[1]  # full primary screen fallback

        shot = sct.grab(region)
        try:
            import cv2

            frame = np.array(shot)
            return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        except ImportError:
            return np.array(shot)


def bring_to_front(handle: WindowHandle) -> bool:
    """Bring Tibia window to foreground. Returns True on success."""
    if not _WIN32_AVAILABLE or handle is None:
        return False
    try:
        _user32.SetForegroundWindow(handle.hwnd)
        return True
    except Exception as exc:
        log.warning("bring_to_front failed: %s", exc)
        return False
