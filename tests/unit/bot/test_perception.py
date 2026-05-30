"""AGENT 8: Unit tests for perception modules."""
import pytest
from bot.perception.state import GameState, Position


def test_game_state_defaults():
    s = GameState()
    assert s.hp == 0
    assert s.hp_max == 100
    assert s.hp_pct == 0.0


def test_hp_pct():
    s = GameState(hp=75, hp_max=100)
    assert s.hp_pct == 75.0


def test_mp_pct():
    s = GameState(mp=30, mp_max=150)
    assert abs(s.mp_pct - 20.0) < 0.1


def test_is_low_hp_true():
    s = GameState(hp=20, hp_max=100)
    assert s.is_low_hp(30) is True


def test_is_low_hp_false():
    s = GameState(hp=50, hp_max=100)
    assert s.is_low_hp(30) is False


def test_is_low_mp():
    s = GameState(mp=10, mp_max=100)
    assert s.is_low_mp(20) is True


def test_parse_game_state_stub():
    """parse_game_state returns healthy defaults when mss/cv2 absent."""
    from bot.perception.parser import parse_game_state
    state = parse_game_state(None)
    assert state.hp == 100
    assert state.mp == 100
