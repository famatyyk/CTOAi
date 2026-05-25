"""AGENT 7 / AGENT 3: Game state parser — OpenCV HP/MP/target detection.

Sprint 5: Real pixel-based parsing for Tibia 7.4 OTS client (1280×720).

UI Layout (measured from Tibia 7.4 OTS default skin):
  HP bar:  x=662, y=38,  w=92, h=6   — filled with red   (BGR ~0,0,192)
  MP bar:  x=662, y=50,  w=92, h=6   — filled with blue  (BGR ~192,0,0)
  Battle:  x=480, y=290, w=160, h=100 — target/monster list area (future)

Fallback: returns healthy defaults when cv2 / pixels unavailable (CI).
"""
from __future__ import annotations
import time
import logging
from .state import GameState, Position

logger = logging.getLogger(__name__)

try:
    import cv2
    import numpy as np
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False

# ── UI regions (x, y, w, h) in 1280×720 Tibia OTS client ──────────────────
HP_BAR_REGION  = (662, 38,  92, 6)
MP_BAR_REGION  = (662, 50,  92, 6)
LEVEL_REGION   = (660, 18, 100, 14)   # text area — reserved for OCR phase

# Colour ranges (BGR) — tolerant ±25 for gamma/monitor variance
HP_COLOR_LOW   = (0,   0,  130)
HP_COLOR_HIGH  = (50,  50, 255)
MP_COLOR_LOW   = (100, 0,  0)
MP_COLOR_HIGH  = (255, 50, 50)

# Target HP indicator: small coloured line above target name in battle list
TARGET_HP_REGION = (482, 288, 158, 4)
TARGET_HP_LOW    = (0,   0,  100)
TARGET_HP_HIGH   = (80, 80, 255)


def _bar_percentage(frame, region: tuple[int, int, int, int],
                    low: tuple, high: tuple) -> int:
    """Count pixels matching colour within region; return 0-100 percentage."""
    if frame is None or not _CV2_AVAILABLE:
        return 100
    x, y, w, h = region
    if frame.shape[0] < y + h or frame.shape[1] < x + w:
        return 100
    crop = frame[y:y+h, x:x+w]
    mask = cv2.inRange(crop, np.array(low, dtype=np.uint8),
                              np.array(high, dtype=np.uint8))
    filled = int(cv2.countNonZero(mask))
    total  = w * h
    return min(100, int(filled / total * 100)) if total > 0 else 100


def _has_target(frame) -> bool:
    """Detect if battle list has an active target (red HP indicator present)."""
    if frame is None or not _CV2_AVAILABLE:
        return False
    pct = _bar_percentage(frame, TARGET_HP_REGION, TARGET_HP_LOW, TARGET_HP_HIGH)
    return pct > 5


def _target_hp_pct(frame) -> int:
    """Estimate target HP% from battle-list HP bar."""
    if frame is None or not _CV2_AVAILABLE:
        return 0
    return _bar_percentage(frame, TARGET_HP_REGION, TARGET_HP_LOW, TARGET_HP_HIGH)


def parse_game_state(screenshot_pixels, prev_state: GameState | None = None) -> GameState:
    """Parse a GameState from a numpy BGR pixel array.

    Args:
        screenshot_pixels: numpy array from mss (BGRA) or None.
        prev_state: previous GameState — used for level/position carry-over.

    Returns:
        Populated GameState; falls back to healthy defaults in CI/headless.
    """
    state = GameState(timestamp=time.time())

    # Carry over non-visual fields from previous state
    if prev_state is not None:
        state.level          = prev_state.level
        state.position       = prev_state.position
        state.nearby_monsters = list(prev_state.nearby_monsters)

    if not _CV2_AVAILABLE or screenshot_pixels is None:
        state.hp = state.hp_max = 100
        state.mp = state.mp_max = 100
        return state

    try:
        # mss returns BGRA — drop alpha channel
        if screenshot_pixels.shape[2] == 4:
            frame = screenshot_pixels[:, :, :3]
        else:
            frame = screenshot_pixels

        hp_pct = _bar_percentage(frame, HP_BAR_REGION, HP_COLOR_LOW, HP_COLOR_HIGH)
        mp_pct = _bar_percentage(frame, MP_BAR_REGION, MP_COLOR_LOW, MP_COLOR_HIGH)

        state.hp_max = 100
        state.mp_max = 100
        state.hp = hp_pct
        state.mp = mp_pct

        # Target detection
        if _has_target(frame):
            state.target_id     = 1       # placeholder — real ID from memory read (Phase 3)
            state.target_hp_pct = _target_hp_pct(frame)
        else:
            state.target_id     = None
            state.target_hp_pct = 0

    except Exception as e:
        logger.warning("parse_game_state error: %s — using defaults", e)
        state.hp = state.hp_max = 100
        state.mp = state.mp_max = 100

    return state
