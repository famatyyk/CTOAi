"""AGENT 8: Unit tests for safety / humanizer."""
import pytest
import time
from bot.safety.humanizer import human_delay, bezier_path


def test_human_delay_within_range():
    t0 = time.perf_counter()
    human_delay(10, 50)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert 5 <= elapsed_ms <= 200  # generous tolerance for CI


def test_bezier_path_length():
    path = bezier_path((0, 0), (100, 100), steps=10)
    assert len(path) == 11


def test_bezier_path_starts_near_start():
    path = bezier_path((0, 0), (100, 100))
    assert path[0] == (0, 0)


def test_bezier_path_ends_near_end():
    path = bezier_path((0, 0), (100, 100))
    assert path[-1] == (100, 100)
