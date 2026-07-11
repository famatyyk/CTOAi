"""AGENT 7: Movement actions."""

from __future__ import annotations

import logging
import time

from ..config.runtime_profile import get_int, get_str
from ..safety import nonsecurity_random as random
from .input_backend import click, is_available, press

logger = logging.getLogger(__name__)

_last_follow_press_ts = 0.0
_last_follow_position: tuple[int, int, int] | None = None
_last_follow_move_ts = 0.0


def _auto_follow_key() -> str:
    return get_str("BOT_FOLLOW_KEY", "f12").strip().lower()


def _auto_follow_interval_ms() -> int:
    return get_int("BOT_AUTO_FOLLOW_INTERVAL_MS", 1500)


def _auto_follow_stuck_ms() -> int:
    return get_int("BOT_AUTO_FOLLOW_STUCK_MS", 900)


def _auto_follow_refresh_ms() -> int:
    return get_int("BOT_AUTO_FOLLOW_REFRESH_MS", 5000)


def walk_to(x: int, y: int) -> None:
    """Click on minimap position to walk. Stub if pyautogui unavailable."""
    if not is_available():
        return
    # Convert world coords → minimap screen coords (Agent 6 supplies offsets)
    screen_x = 1215 + (x // 4)
    screen_y = 170 + (y // 4)
    click(screen_x, screen_y)
    time.sleep(0.05)


def idle_move() -> None:
    """Small random movement to appear human while searching."""
    if not is_available():
        return

    dx, dy = random.randint(-2, 2), random.randint(-2, 2)
    walk_to(dx, dy)


def _state_position_tuple(state) -> tuple[int, int, int] | None:
    try:
        pos = getattr(state, "position", None)
        if pos is None:
            return None
        x = int(getattr(pos, "x", 0))
        y = int(getattr(pos, "y", 0))
        z = int(getattr(pos, "z", 7))
        # (0,0,7) is common parser default when coordinates are unavailable.
        if x == 0 and y == 0 and z == 7:
            return None
        return (x, y, z)
    except (TypeError, ValueError, AttributeError) as exc:
        logger.debug("state position unavailable: %s", exc)
        return None


def auto_follow(state=None) -> None:
    """Trigger follow hotkey with smart throttle.

    When position is available, re-press only when stuck (no movement for
    _AUTO_FOLLOW_STUCK_MS) or on periodic refresh.
    """
    global _last_follow_press_ts, _last_follow_position, _last_follow_move_ts
    if not is_available():
        return

    now = time.monotonic()
    since_last_press = now - _last_follow_press_ts
    if since_last_press < (_auto_follow_interval_ms() / 1000.0):
        return

    pos = _state_position_tuple(state)
    if pos is not None:
        if _last_follow_position is None or pos != _last_follow_position:
            _last_follow_position = pos
            _last_follow_move_ts = now

        since_move = now - _last_follow_move_ts
        if _last_follow_press_ts > 0.0:
            if since_move < (_auto_follow_stuck_ms() / 1000.0) and since_last_press < (
                _auto_follow_refresh_ms() / 1000.0
            ):
                return

        press(_auto_follow_key())
    _last_follow_press_ts = now
