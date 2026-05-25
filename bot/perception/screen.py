"""AGENT 7: Screen capture module (mss-based)."""
from __future__ import annotations
import time
try:
    import mss
    import mss.tools
    _MSS_AVAILABLE = True
except ImportError:
    _MSS_AVAILABLE = False

# Default capture region — Tibia client 1280x720
DEFAULT_REGION = {"top": 0, "left": 0, "width": 1280, "height": 720}


def capture_screen(region: dict | None = None) -> bytes | None:
    """Capture screen region and return raw PNG bytes.
    Falls back to None if mss is not available (CI environment).
    """
    if not _MSS_AVAILABLE:
        return None

    region = region or DEFAULT_REGION
    with mss.mss() as sct:
        screenshot = sct.grab(region)
        return mss.tools.to_png(screenshot.rgb, screenshot.size)


def capture_region_pixels(region: dict | None = None):
    """Return numpy array of screen pixels (requires numpy+mss)."""
    if not _MSS_AVAILABLE:
        return None

    try:
        import numpy as np
        region = region or DEFAULT_REGION
        with mss.mss() as sct:
            shot = sct.grab(region)
            return np.array(shot)
    except ImportError:
        return None
