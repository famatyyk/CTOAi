"""Input backend adapter for safer game input dispatch.

Supports two backends:
  - pyautogui (default)
  - pydirectinput (DirectInput-friendly on some game clients)

Selection can be controlled with BOT_INPUT_BACKEND env var.
Allowed values: pyautogui, pydirectinput, auto.
"""
from __future__ import annotations

import logging
import os
import ctypes
from typing import Callable

from ..config.runtime_profile import get_bool, get_str

log = logging.getLogger(__name__)

_mode = get_str("BOT_INPUT_BACKEND", "auto").strip().lower()
_require_focus = get_bool("BOT_INPUT_ONLY_WHEN_TIBIA_ACTIVE", True)

_press: Callable[[str], None]
_click: Callable[[int, int], None]
_available = False
_backend_name = "none"


def _load_pydirectinput() -> bool:
    global _press, _click, _available, _backend_name
    try:
        import pydirectinput  # type: ignore

        _press = pydirectinput.press
        _click = pydirectinput.click
        _available = True
        _backend_name = "pydirectinput"
        log.info("Input backend selected: pydirectinput")
        return True
    except Exception as exc:
        log.debug("pydirectinput unavailable: %s", exc)
        return False


def _load_pyautogui() -> bool:
    global _press, _click, _available, _backend_name
    try:
        import pyautogui

        pyautogui.FAILSAFE = True
        _press = pyautogui.press
        _click = pyautogui.click
        _available = True
        _backend_name = "pyautogui"
        log.info("Input backend selected: pyautogui")
        return True
    except Exception as exc:
        log.debug("pyautogui unavailable: %s", exc)
        return False


if _mode == "pydirectinput":
    _load_pydirectinput() or _load_pyautogui()
elif _mode == "pyautogui":
    _load_pyautogui() or _load_pydirectinput()
else:
    _load_pydirectinput() or _load_pyautogui()


def is_available() -> bool:
    return _available


def backend_name() -> str:
    return _backend_name


def _is_tibia_active_window() -> bool:
    """Return True only when the foreground window is a detected Tibia client.

    Fail closed to avoid global key spam when window detection is unavailable.
    """
    try:
        from ..perception.window import find_tibia_window

        handle = find_tibia_window()
        if handle is None:
            return False
        foreground = int(ctypes.windll.user32.GetForegroundWindow())  # type: ignore[attr-defined]
        return foreground != 0 and foreground == int(handle.hwnd)
    except Exception:
        return False


def _can_dispatch_input() -> bool:
    if not _available:
        return False
    if not _require_focus:
        return True
    return _is_tibia_active_window()


def press(key: str) -> None:
    if not _can_dispatch_input():
        return
    _press(key)


def click(x: int, y: int) -> None:
    if not _can_dispatch_input():
        return
    _click(x, y)
