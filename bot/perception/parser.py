"""AGENT 7: Game state parser (OpenCV-based, with stubs for CI)."""
from __future__ import annotations
import time
from .state import GameState, Position

try:
    import cv2
    import numpy as np
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False

# UI element pixel positions (1280x720, Tibia 7.4 OTS)
HP_BAR_REGION = (660, 40, 100, 8)   # x, y, w, h
MP_BAR_REGION = (660, 52, 100, 8)
HP_BAR_COLOR  = (192, 0, 0)          # dark red
MP_BAR_COLOR  = (0, 0, 192)          # dark blue


def _read_bar_percentage(img_array, region: tuple, bar_color: tuple) -> int:
    """Read a HP/MP bar percentage by counting colored pixels."""
    if not _CV2_AVAILABLE or img_array is None:
        return 100
    x, y, w, h = region
    bar = img_array[y:y+h, x:x+w]
    mask = cv2.inRange(bar, np.array(bar_color) - 20, np.array(bar_color) + 20)
    filled = cv2.countNonZero(mask)
    return min(100, int(filled / (w * h) * 100 * 3))


def parse_game_state(screenshot_pixels) -> GameState:
    """Parse a GameState from a numpy pixel array.
    Returns a default 'healthy' state if parsing is unavailable.
    """
    state = GameState(timestamp=time.time())

    if not _CV2_AVAILABLE or screenshot_pixels is None:
        # Stub for testing / CI — return healthy defaults
        state.hp = 100
        state.hp_max = 100
        state.mp = 100
        state.mp_max = 100
        return state

    state.hp_max = 100
    state.mp_max = 100
    state.hp = _read_bar_percentage(screenshot_pixels, HP_BAR_REGION, HP_BAR_COLOR)
    state.mp = _read_bar_percentage(screenshot_pixels, MP_BAR_REGION, MP_BAR_COLOR)
    return state
