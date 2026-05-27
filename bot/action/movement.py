"""AGENT 7: Movement actions."""
from __future__ import annotations
import time

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    _GUI_AVAILABLE = True
except Exception:
    _GUI_AVAILABLE = False


def walk_to(x: int, y: int) -> None:
    """Click on minimap position to walk. Stub if pyautogui unavailable."""
    if not _GUI_AVAILABLE:
        return
    # Convert world coords → minimap screen coords (Agent 6 supplies offsets)
    screen_x = 1215 + (x // 4)
    screen_y = 170  + (y // 4)
    pyautogui.click(screen_x, screen_y)
    time.sleep(0.05)


def idle_move() -> None:
    """Small random movement to appear human while searching."""
    if not _GUI_AVAILABLE:
        return
    import random
    dx, dy = random.randint(-2, 2), random.randint(-2, 2)
    walk_to(dx, dy)
