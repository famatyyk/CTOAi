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
import re
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

try:
    import easyocr
    _EASYOCR_AVAILABLE = True
except ImportError:
    easyocr = None
    _EASYOCR_AVAILABLE = False

# ---- Default UI regions (x, y, w, h) in 1280x720 Tibia OTS client ----
# The current KingsVale client renders the bars on the very top HUD strip.
_DEFAULT_HP_REGION   = (366, 6, 589, 9)
_DEFAULT_MP_REGION   = (1079, 4, 470, 3)
_DEFAULT_LEVEL_REGION = (660, 18, 100, 14)

# Default colour ranges (BGR, tolerant +-25 for gamma/monitor variance)
# This client uses a green HP bar and a blue MP bar.
_DEFAULT_HP_LOW  = (0,  100, 0)
_DEFAULT_HP_HIGH = (80, 255, 80)
_DEFAULT_MP_LOW  = (100, 0,  0)
_DEFAULT_MP_HIGH = (255, 50, 50)

# Target HP indicator in battle list
_DEFAULT_TARGET_HP_REGION = (482, 288, 158, 4)
_DEFAULT_TARGET_HP_LOW    = (0,   0,  100)
_DEFAULT_TARGET_HP_HIGH   = (80,  80, 255)

_BASE_CAPTURE_WIDTH = 1280
_BASE_CAPTURE_HEIGHT = 720

_CALIB_FILE = Path(os.environ.get("BOT_CALIB_FILE", "calibration_config.json"))


def _parse_region(raw: str) -> tuple[int, int, int, int] | None:
    try:
        vals = [int(v.strip()) for v in raw.split(",")]
    except ValueError:
        return None
    if len(vals) != 4:
        return None
    return vals[0], vals[1], vals[2], vals[3]


def _scale_region(region: tuple[int, int, int, int], frame) -> tuple[int, int, int, int]:
    """Scale a baseline 1280x720 region to the current frame size."""
    if frame is None or not hasattr(frame, "shape"):
        return region
    try:
        frame_height = int(frame.shape[0])
        frame_width = int(frame.shape[1])
    except Exception:
        return region
    if frame_width <= 0 or frame_height <= 0:
        return region
    if frame_width == _BASE_CAPTURE_WIDTH and frame_height == _BASE_CAPTURE_HEIGHT:
        return region

    x, y, w, h = region
    scale_x = frame_width / _BASE_CAPTURE_WIDTH
    scale_y = frame_height / _BASE_CAPTURE_HEIGHT
    return (
        max(0, int(round(x * scale_x))),
        max(0, int(round(y * scale_y))),
        max(1, int(round(w * scale_x))),
        max(1, int(round(h * scale_y))),
    )


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

_TARGET_TEMPLATE_PATH = os.environ.get("BOT_TARGET_TEMPLATE", "").strip()
_TARGET_TEMPLATE_THRESHOLD = float(os.environ.get("BOT_TARGET_TEMPLATE_THRESHOLD", "0.86"))
_TARGET_TEMPLATE_REGION = _parse_region(os.environ.get("BOT_TARGET_TEMPLATE_REGION", ""))
_TARGET_TEMPLATE = None
_OCR_READER = None
_RESOURCE_ZERO_GUARD_MIN_PREV_PCT = float(os.environ.get("BOT_RESOURCE_ZERO_GUARD_MIN_PREV_PCT", "20"))


def _rescale_from_pct(pct: float, max_value: int) -> int:
    return max(0, min(int(max_value), int(round((pct / 100.0) * max_value))))


def _stabilize_resource_value(current: int, current_max: int, prev: int, prev_max: int) -> int:
    if current_max <= 0 or prev_max <= 0:
        return current
    prev_pct = (prev / prev_max) * 100.0
    if current == 0 and prev_pct >= _RESOURCE_ZERO_GUARD_MIN_PREV_PCT:
        return _rescale_from_pct(prev_pct, current_max)
    return current

if _CV2_AVAILABLE and _TARGET_TEMPLATE_PATH:
    try:
        _tmpl_path = Path(_TARGET_TEMPLATE_PATH)
        if _tmpl_path.exists():
            _TARGET_TEMPLATE = cv2.imread(str(_tmpl_path), cv2.IMREAD_COLOR)
            if _TARGET_TEMPLATE is None:
                logger.warning("Template image unreadable: %s", _tmpl_path)
            else:
                logger.info("Target template loaded: %s", _tmpl_path)
        else:
            logger.warning("Target template not found: %s", _tmpl_path)
    except Exception as exc:
        logger.warning("Could not load target template %s: %s", _TARGET_TEMPLATE_PATH, exc)


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
    if total <= 0:
        return 100
    exact_pct = min(100, int(filled / total * 100)) if filled > 0 else 0
    if exact_pct >= 50:
        return exact_pct

    # Fallback: detect a dominant colour channel when exact thresholding fails.
    if high[1] >= high[0] and high[1] >= high[2]:
        dominant = (crop[:, :, 1] > crop[:, :, 0] + 10) & (crop[:, :, 1] > crop[:, :, 2] + 10) & (crop[:, :, 1] > 35)
    elif high[2] >= high[0] and high[2] >= high[1]:
        dominant = (crop[:, :, 2] > crop[:, :, 1] + 10) & (crop[:, :, 2] > crop[:, :, 0] + 10) & (crop[:, :, 2] > 35)
    else:
        dominant = (crop[:, :, 0] > crop[:, :, 1] + 10) & (crop[:, :, 0] > crop[:, :, 2] + 10) & (crop[:, :, 0] > 35)
    dominant_pct = min(100, int(float(np.count_nonzero(dominant)) / total * 100))
    return max(exact_pct, dominant_pct)


def _has_target(frame, region: tuple[int, int, int, int] = TARGET_HP_REGION) -> bool:
    """Detect if battle list has an active target (red HP indicator present)."""
    if frame is None or not _CV2_AVAILABLE:
        return False
    pct = _bar_percentage(frame, region, TARGET_HP_LOW, TARGET_HP_HIGH)
    return pct > 5


def _target_hp_pct(frame, region: tuple[int, int, int, int] = TARGET_HP_REGION) -> int:
    """Estimate target HP% from battle-list HP bar."""
    if frame is None or not _CV2_AVAILABLE:
        return 0
    return _bar_percentage(frame, region, TARGET_HP_LOW, TARGET_HP_HIGH)


def _template_target_match(frame) -> tuple[bool, float]:
    """Return (is_match, score) based on optional template matching."""
    if frame is None or not _CV2_AVAILABLE or _TARGET_TEMPLATE is None:
        return False, 0.0
    try:
        haystack = frame
        if _TARGET_TEMPLATE_REGION is not None:
            x, y, w, h = _TARGET_TEMPLATE_REGION
            if frame.shape[0] >= y + h and frame.shape[1] >= x + w:
                haystack = frame[y:y+h, x:x+w]
        if haystack.shape[0] < _TARGET_TEMPLATE.shape[0] or haystack.shape[1] < _TARGET_TEMPLATE.shape[1]:
            return False, 0.0
        match = cv2.matchTemplate(haystack, _TARGET_TEMPLATE, cv2.TM_CCOEFF_NORMED)
        _, score, _, _ = cv2.minMaxLoc(match)
        return score >= _TARGET_TEMPLATE_THRESHOLD, float(score)
    except Exception:
        return False, 0.0


def _ocr_reader():
    global _OCR_READER
    if not _EASYOCR_AVAILABLE:
        return None
    if _OCR_READER is None:
        try:
            _OCR_READER = easyocr.Reader(['en'], gpu=False)
        except Exception:
            _OCR_READER = False
    return _OCR_READER if _OCR_READER is not False else None


def _ocr_extract_ratios(frame) -> list[tuple[float, float]]:
    """Extract numeric HP/MP values from the top HUD via OCR."""
    reader = _ocr_reader()
    if reader is None or frame is None or not _CV2_AVAILABLE:
        return []
    try:
        top = frame[:28, :, :]
        if top.shape[0] == 0 or top.shape[1] == 0:
            return []
        # Crop to the center/top HUD band where the HP/MP numbers live.
        left = max(0, top.shape[1] // 8)
        right = min(top.shape[1], top.shape[1] - left)
        hud = top[:, left:right, :]
        results = reader.readtext(hud, detail=1, paragraph=False)
        parsed: list[tuple[float, float]] = []
        for box, text, _score in results:
            digits = re.findall(r"\d+", str(text))
            if not digits or len(digits[0]) < 4:
                continue
            value = float(digits[0])
            x0 = float(min(point[0] for point in box))
            parsed.append((x0, value))
        parsed.sort(key=lambda item: item[0])
        values = [value for _x0, value in parsed[:4]]
        if len(values) >= 4:
            return [(values[0], values[1]), (values[2], values[3])]
        if len(values) >= 2:
            return [(values[0], values[1])]
        return []
    except Exception:
        return []


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

        ocr_ratios = _ocr_extract_ratios(frame)
        if len(ocr_ratios) >= 2:
            (hp_current, hp_max), (mp_current, mp_max) = ocr_ratios[:2]
            state.hp_max = max(1, int(round(hp_max)))
            state.mp_max = max(1, int(round(mp_max)))
            state.hp = max(0, min(state.hp_max, int(round(hp_current))))
            state.mp = max(0, min(state.mp_max, int(round(mp_current))))
        else:
            hp_region = _scale_region(HP_BAR_REGION, frame)
            mp_region = _scale_region(MP_BAR_REGION, frame)
            target_region = _scale_region(TARGET_HP_REGION, frame)

            hp_pct = _bar_percentage(frame, hp_region, HP_COLOR_LOW, HP_COLOR_HIGH)
            mp_pct = _bar_percentage(frame, mp_region, MP_COLOR_LOW, MP_COLOR_HIGH)

            state.hp_max = 100
            state.mp_max = 100
            state.hp = hp_pct
            state.mp = mp_pct

        if prev_state is not None:
            state.hp = _stabilize_resource_value(state.hp, state.hp_max, prev_state.hp, prev_state.hp_max)
            state.mp = _stabilize_resource_value(state.mp, state.mp_max, prev_state.mp, prev_state.mp_max)

        target_region = _scale_region(TARGET_HP_REGION, frame)

        has_hp_target = _has_target(frame, target_region)
        has_template_target, template_score = _template_target_match(frame)

        if has_hp_target or has_template_target:
            state.target_id     = 1
            state.target_hp_pct = _target_hp_pct(frame, target_region) if has_hp_target else int(template_score * 100)
        else:
            state.target_id     = None
            state.target_hp_pct = 0

    except Exception as e:
        logger.warning("parse_game_state error: %s -- using defaults", e)
        state.hp = state.hp_max = 100
        state.mp = state.mp_max = 100

    return state
