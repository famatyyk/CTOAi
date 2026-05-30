"""Window detection and capture — finds Tibia client window and captures it.

Uses Win32 API (ctypes) on Windows; falls back to full-screen mss capture on
other platforms so the rest of the bot can run headless in CI.
"""
from __future__ import annotations
import ctypes
import ctypes.wintypes as wt
import logging
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger(__name__)

_WINDOW_TITLES = ["Tibia", "TibiaClient", "The Forgotten Server"]

# ── Win32 helpers ────────────────────────────────────────────────────────────
try:
    _user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    _WIN32_AVAILABLE = True
except AttributeError:
    _WIN32_AVAILABLE = False


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

    found: list[WindowHandle] = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    def _enum_cb(hwnd: int, _lParam: int) -> bool:
        buf = ctypes.create_unicode_buffer(256)
        _user32.GetWindowTextW(hwnd, buf, 256)
        title = buf.value
        for pat in _WINDOW_TITLES:
            if pat.lower() in title.lower() and _user32.IsWindowVisible(hwnd):
                rect = wt.RECT()
                _user32.GetWindowRect(hwnd, ctypes.byref(rect))
                found.append(WindowHandle(
                    hwnd=hwnd,
                    title=title,
                    rect=(rect.left, rect.top, rect.right, rect.bottom),
                ))
                break
        return True

    _user32.EnumWindows(_enum_cb, 0)
    if found:
        log.info("Tibia window found: %s  hwnd=%d  %dx%d",
                 found[0].title, found[0].hwnd, found[0].width, found[0].height)
        return found[0]
    log.warning("Tibia window not found (titles searched: %s)", _WINDOW_TITLES)
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

    with mss.mss() as sct:
        if handle is not None:
            region = {
                "left": handle.left,
                "top": handle.top,
                "width": handle.width,
                "height": handle.height,
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
