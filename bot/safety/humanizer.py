"""AGENT 5: Humanization — random delays, bezier mouse, combat micro-pauses.

Sprint 4 additions:
- combat_pause(): random micro-delay between attacks (70-350ms, gaussian)
- reaction_delay(): simulate human reaction time before acting (80-400ms)
- misclick_jitter(): occasional mouse position jitter (1-3% chance)
- think_pause(): longer pause simulating decision hesitation (300-1500ms, rare)
"""
from __future__ import annotations
import random
import time
import math
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Basic delays
# ---------------------------------------------------------------------------

def human_delay(min_ms: int = 50, max_ms: int = 200) -> None:
    """Sleep for a normally-distributed random duration."""
    mean  = (min_ms + max_ms) / 2
    sigma = (max_ms - min_ms) / 6
    delay_ms = max(min_ms, min(max_ms, random.gauss(mean, sigma)))
    time.sleep(delay_ms / 1000)


def reaction_delay() -> None:
    """Simulate human reaction time before taking action (80-400ms)."""
    human_delay(80, 400)


def combat_pause() -> None:
    """Micro-pause between combat actions — mimics human click cadence.

    Profile:
    - 80% of the time: short pause 70-200ms (engaged combat)
    - 15% of the time: medium pause 200-500ms (reacting, repositioning)
    -  5% of the time: long pause 500-1200ms (distracted / checking inventory)
    """
    roll = random.random()
    if roll < 0.80:
        human_delay(70, 200)
    elif roll < 0.95:
        human_delay(200, 500)
    else:
        human_delay(500, 1200)
        logger.debug("Humanizer: long combat pause")


def think_pause() -> None:
    """Rare hesitation pause (1.5% chance) — simulates player distraction."""
    if random.random() < 0.015:
        duration_ms = random.uniform(300, 1500)
        logger.debug("Humanizer: think_pause %.0fms", duration_ms)
        time.sleep(duration_ms / 1000)


def loot_delay() -> None:
    """Delay before/after looting — 100-600ms (reading loot window)."""
    human_delay(100, 600)


def potion_delay() -> None:
    """Delay after using a potion — 80-250ms (natural reaction time)."""
    human_delay(80, 250)


# ---------------------------------------------------------------------------
# Mouse movement
# ---------------------------------------------------------------------------

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


def misclick_jitter(x: int, y: int) -> tuple[int, int]:
    """Add tiny random jitter to click target (1-4px) simulating imprecision."""
    return (x + random.randint(-4, 4), y + random.randint(-4, 4))


def move_mouse_human(start: tuple[int, int], end: tuple[int, int]) -> None:
    """Move mouse along bezier curve with optional misclick jitter."""
    try:
        import pyautogui
        target = misclick_jitter(*end)
        path = bezier_path(start, target)
        for px, py in path:
            pyautogui.moveTo(px, py, duration=0)
            time.sleep(random.uniform(0.004, 0.012))
        think_pause()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Session-level randomness
# ---------------------------------------------------------------------------

def random_afk_twitch() -> None:
    """Occasionally move mouse slightly to simulate idle human presence (0.5% chance)."""
    if random.random() < 0.005:
        try:
            import pyautogui
            x, y = pyautogui.position()
            dx = random.randint(-15, 15)
            dy = random.randint(-15, 15)
            move_mouse_human((x, y), (x + dx, y + dy))
        except Exception:
            pass
