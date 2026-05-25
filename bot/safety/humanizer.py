"""AGENT 5: Humanization — random delays, bezier mouse paths."""
from __future__ import annotations
import random
import time
import math


def human_delay(min_ms: int = 50, max_ms: int = 200) -> None:
    """Sleep for a normally-distributed random duration."""
    mean = (min_ms + max_ms) / 2
    sigma = (max_ms - min_ms) / 6
    delay_ms = max(min_ms, min(max_ms, random.gauss(mean, sigma)))
    time.sleep(delay_ms / 1000)


def bezier_path(start: tuple[int, int], end: tuple[int, int],
                steps: int = 20) -> list[tuple[int, int]]:
    """Generate a quadratic bezier curve between two screen points."""
    cx = (start[0] + end[0]) // 2 + random.randint(-40, 40)
    cy = (start[1] + end[1]) // 2 + random.randint(-40, 40)
    path = []
    for i in range(steps + 1):
        t = i / steps
        x = int((1-t)**2 * start[0] + 2*(1-t)*t * cx + t**2 * end[0])
        y = int((1-t)**2 * start[1] + 2*(1-t)*t * cy + t**2 * end[1])
        path.append((x, y))
    return path


def move_mouse_human(start: tuple[int, int], end: tuple[int, int]) -> None:
    """Move mouse along bezier curve (requires pyautogui)."""
    try:
        import pyautogui
        path = bezier_path(start, end)
        for x, y in path:
            pyautogui.moveTo(x, y, duration=0)
            time.sleep(random.uniform(0.005, 0.015))
    except Exception:
        pass
