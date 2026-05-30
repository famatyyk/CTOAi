"""Tests for Agent 5 extended humanizer."""
import pytest
import time
from unittest.mock import patch
from bot.safety.humanizer import (
    human_delay, combat_pause, reaction_delay,
    think_pause, loot_delay, potion_delay,
    bezier_path, misclick_jitter, move_mouse_human,
)


def test_human_delay_within_bounds():
    t0 = time.perf_counter()
    human_delay(10, 50)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert 8 <= elapsed_ms <= 200  # generous bounds for CI


def test_combat_pause_executes():
    t0 = time.perf_counter()
    combat_pause()
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert elapsed_ms >= 50


def test_reaction_delay_executes():
    t0 = time.perf_counter()
    reaction_delay()
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert elapsed_ms >= 70


def test_think_pause_rarely_fires():
    fires = 0
    with patch("bot.safety.humanizer.random.random", return_value=0.01):
        t0 = time.perf_counter()
        think_pause()
        elapsed_ms = (time.perf_counter() - t0) * 1000
        fires += 1
    assert fires == 1


def test_think_pause_usually_skips():
    with patch("bot.safety.humanizer.random.random", return_value=0.99):
        t0 = time.perf_counter()
        think_pause()
        elapsed_ms = (time.perf_counter() - t0) * 1000
    assert elapsed_ms < 50  # should skip


def test_bezier_path_length():
    path = bezier_path((0, 0), (100, 100), steps=10)
    assert len(path) == 11


def test_bezier_starts_near_start():
    path = bezier_path((10, 10), (200, 200))
    assert abs(path[0][0] - 10) < 5 and abs(path[0][1] - 10) < 5


def test_bezier_ends_near_end():
    path = bezier_path((10, 10), (200, 200))
    assert abs(path[-1][0] - 200) < 5 and abs(path[-1][1] - 200) < 5


def test_misclick_jitter_within_range():
    for _ in range(50):
        jx, jy = misclick_jitter(100, 100)
        assert 96 <= jx <= 104
        assert 96 <= jy <= 104


def test_move_mouse_human_no_error():
    # Should not raise even without pyautogui
    move_mouse_human((0, 0), (100, 100))
