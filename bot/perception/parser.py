"""AGENT 7 / AGENT 3: Game state parser — OpenCV HP/MP/target detection.

Sprint 5: Real pixel-based parsing for Tibia 7.4 OTS client (1280x720).
Sprint 9: Dynamic colour/region loading from calibration file + env vars.

Colour config priority (highest wins):
  1. Env vars: HP_BAR_BGR, MP_BAR_BGR (format: B,G,R  e.g. 0,0,192)
  2. calibration_config.json  (written by scripts/calibrate_colors.py)
  3. Hardcoded defaults below

UI Layout (measured from Tibia 7.4 OTS default skin):
  HP bar:  x=662, y=38,  w=92, h=6   -- filled with red   (BGR ~0,0,192)
  MP bar:  x=662, y=50,  w=92, h=6   -- filled with blue  (BGR ~192,0,0)
  Battle:  x=480, y=290, w=160, h=100 -- target/monster list area (future)

Fallback: returns healthy defaults when cv2 / pixels unavailable (CI).
"""
from __future__ import annotations
import json
import logging
import os
import time
from pathlib import Path

from .state import GameState, Position

logger = logging.getLogger(__name__)

try:
    import cv2
    import numpy as np
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False

# ---- Default UI regions (x, y, w, h) in 1280x720 Tibia OTS client ----
_DEFAULT_HP_REGION   = (662, 38,  92, 6)
_DEFAULT_MP_REGION   = (662, 50,  92, 6)
_DEFAULT_LEVEL_REGION = (660, 18, 100, 14)

# Default colour ranges (BGR, tolerant +-25 for gamma/monitor variance)
_DEFAULT_HP_LOW  = (0,   0,  130)
_DEFAULT_HP_HIGH = (50,  50, 255)
_DEFAULT_MP_LOW  = (100, 0,  0)
_DEFAULT_MP_HIGH = (255, 50, 50)

# Target HP indicator in battle list
_DEFAULT_TARGET_HP_REGION = (482, 288, 158, 4)
_DEFAULT_TARGET_HP_LOW    = (0,   0,  100)
_DEFAULT_TARGET_HP_HIGH   = (80,  80, 255)

_CALIB_FILE = Path(os.environ.get("BOT_CALIB_FILE", "calibration_config.json"))


def _load_calibration() -> dict:
    """Load HP/MP colour calibration from env vars or calibration_config.json."""
    cfg: dict = {}

    # Priority 1: env vars
    for env_key, cfg_key in (("HP_BAR_BGR", "hp"), ("MP_BAR_BGR", "mp")):
        raw = os.environ.get(env_key, "")
        if raw:
            try:
                parts = [int(v.strip()) for v in raw.split(",")]
                if len(parts) == 3:
                    cfg[cfg_key] = {"mean_bgr": parts}
            except ValueError:
                logger.warning("Invalid %s env var: %r", env_key, raw)

    for env_key, cfg_key in (("OTS_HP_BAR_REGION", "hp_region"), ("OTS_MP_BAR_REGION", "mp_region")):
        raw = os.environ.get(env_key, "")
        if raw:
            try:
                parts = [int(v.strip()) for v in raw.split(",")]
                if len(parts) == 4:
                    cfg[cfg_key] = tuple(parts)
            except ValueError:
                logger.warning("Invalid %s env var: %r", env_key, raw)

    # Priority 2: calibration file (only fills missing keys)
    if _CALIB_FILE.exists():
        try:
            data = json.loads(_CALIB_FILE.read_text(encoding="utf-8"))
            for bar in ("hp", "mp"):
                if bar not in cfg and bar in data:
                    cfg[bar] = data[bar]
            for key in ("hp_region", "mp_region"):
                if key not in cfg and key in data:
                    cfg[key] = tuple(data[key])
            logger.info("Calibration loaded from %s", _CALIB_FILE)
        except Exception as exc:
            logger.warning("Could not load %s: %s", _CALIB_FILE, exc)

    return cfg


def _bgr_range(mean_bgr: list[int], tolerance: int = 60) -> tuple[tuple, tuple]:
    """Build (low, high) BGR range from mean colour with +-tolerance."""
    b, g, r = mean_bgr
    low  = (max(0, b - tolerance), max(0, g - tolerance), max(0, r - tolerance))
    high = (min(255, b + tolerance), min(255, g + tolerance), min(255, r + tolerance))
    return low, high


# ---- Module-level effective config (loaded once at import) ---------------
_calib = _load_calibration()

HP_BAR_REGION  = _calib.get("hp_region") or _DEFAULT_HP_REGION
MP_BAR_REGION  = _calib.get("mp_region") or _DEFAULT_MP_REGION
LEVEL_REGION   = _DEFAULT_LEVEL_REGION

if "hp" in _calib:
    HP_COLOR_LOW, HP_COLOR_HIGH = _bgr_range(_calib["hp"]["mean_bgr"])
else:
    HP_COLOR_LOW, HP_COLOR_HIGH = _DEFAULT_HP_LOW, _DEFAULT_HP_HIGH

if "mp" in _calib:
    MP_COLOR_LOW, MP_COLOR_HIGH = _bgr_range(_calib["mp"]["mean_bgr"])
else:
    MP_COLOR_LOW, MP_COLOR_HIGH = _DEFAULT_MP_LOW, _DEFAULT_MP_HIGH

TARGET_HP_REGION = _DEFAULT_TARGET_HP_REGION
TARGET_HP_LOW    = _DEFAULT_TARGET_HP_LOW
TARGET_HP_HIGH   = _DEFAULT_TARGET_HP_HIGH


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


def reload_calibration() -> None:
    """Reload colour calibration at runtime (e.g. after running calibrate_colors.py)."""
    global HP_BAR_REGION, MP_BAR_REGION
    global HP_COLOR_LOW, HP_COLOR_HIGH, MP_COLOR_LOW, MP_COLOR_HIGH
    calib = _load_calibration()
    HP_BAR_REGION = calib.get("hp_region") or _DEFAULT_HP_REGION
    MP_BAR_REGION = calib.get("mp_region") or _DEFAULT_MP_REGION
    if "hp" in calib:
        HP_COLOR_LOW, HP_COLOR_HIGH = _bgr_range(calib["hp"]["mean_bgr"])
    else:
        HP_COLOR_LOW, HP_COLOR_HIGH = _DEFAULT_HP_LOW, _DEFAULT_HP_HIGH
    if "mp" in calib:
        MP_COLOR_LOW, MP_COLOR_HIGH = _bgr_range(calib["mp"]["mean_bgr"])
    else:
        MP_COLOR_LOW, MP_COLOR_HIGH = _DEFAULT_MP_LOW, _DEFAULT_MP_HIGH
    logger.info("Calibration reloaded: HP_region=%s MP_region=%s", HP_BAR_REGION, MP_BAR_REGION)


def parse_game_state(screenshot_pixels, prev_state: GameState | None = None) -> GameState:
    """Parse a GameState from a numpy BGR pixel array.

    Args:
        screenshot_pixels: numpy array from mss (BGRA) or None.
        prev_state: previous GameState -- used for level/position carry-over.

    Returns:
        Populated GameState; falls back to healthy defaults in CI/headless.
    """
    state = GameState(timestamp=time.time())

    if prev_state is not None:
        state.level           = prev_state.level
        state.position        = prev_state.position
        state.nearby_monsters = list(prev_state.nearby_monsters)

    if not _CV2_AVAILABLE or screenshot_pixels is None:
        state.hp = state.hp_max = 100
        state.mp = state.mp_max = 100
        return state

    try:
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

        if _has_target(frame):
            state.target_id     = 1
            state.target_hp_pct = _target_hp_pct(frame)
        else:
            state.target_id     = None
            state.target_hp_pct = 0

    except Exception as e:
        logger.warning("parse_game_state error: %s -- using defaults", e)
        state.hp = state.hp_max = 100
        state.mp = state.mp_max = 100

    return state
