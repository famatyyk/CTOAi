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


def test_parse_game_state_template_target_fallback(monkeypatch):
    from bot.perception import parser

    class _Frame:
        shape = (1, 1, 3)

        def __getitem__(self, _item):
            return self

    monkeypatch.setattr(parser, "_CV2_AVAILABLE", True)
    monkeypatch.setattr(parser, "_bar_percentage", lambda *args, **kwargs: 80)
    monkeypatch.setattr(parser, "_has_target", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(parser, "_template_target_match", lambda _frame: (True, 0.91))
    monkeypatch.setattr(parser, "_target_hp_pct", lambda _frame: 33)

    state = parser.parse_game_state(_Frame())
    assert state.target_id == 1
    assert state.target_hp_pct == 91


def test_parse_game_state_hp_target_has_priority(monkeypatch):
    from bot.perception import parser

    class _Frame:
        shape = (1, 1, 3)

        def __getitem__(self, _item):
            return self

    monkeypatch.setattr(parser, "_CV2_AVAILABLE", True)
    monkeypatch.setattr(parser, "_bar_percentage", lambda *args, **kwargs: 75)
    monkeypatch.setattr(parser, "_has_target", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(parser, "_template_target_match", lambda _frame: (True, 0.99))
    monkeypatch.setattr(parser, "_target_hp_pct", lambda *_args, **_kwargs: 42)

    state = parser.parse_game_state(_Frame())
    assert state.target_id == 1
    assert state.target_hp_pct == 42


def test_scale_region_matches_frame_size():
    from bot.perception import parser

    class _Frame:
        shape = (1048, 1936, 3)

    assert parser._scale_region((662, 38, 92, 6), _Frame()) == (1001, 55, 139, 9)


def test_bar_percentage_green_hp_fallback(monkeypatch):
    from bot.perception import parser
    import numpy as np

    monkeypatch.setattr(parser, "_CV2_AVAILABLE", True)
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    frame[:, :, 1] = 220
    pct = parser._bar_percentage(frame, (0, 0, 10, 10), (0, 100, 0), (80, 255, 80))
    assert pct == 100


def test_parse_game_state_zero_hp_spike_guard(monkeypatch):
    from bot.perception import parser

    class _Frame:
        shape = (10, 10, 3)

        def __getitem__(self, _item):
            return self

    monkeypatch.setattr(parser, "_CV2_AVAILABLE", True)
    monkeypatch.setattr(parser, "_ocr_extract_ratios", lambda _frame: [(0.0, 100.0), (80.0, 100.0)])
    monkeypatch.setattr(parser, "_has_target", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(parser, "_template_target_match", lambda _frame: (False, 0.0))

    prev = GameState(hp=35, hp_max=100, mp=80, mp_max=100)
    state = parser.parse_game_state(_Frame(), prev_state=prev)

    assert state.hp == 35
    assert state.mp == 80


def test_parse_game_state_keeps_real_low_hp(monkeypatch):
    from bot.perception import parser

    class _Frame:
        shape = (10, 10, 3)

        def __getitem__(self, _item):
            return self

    monkeypatch.setattr(parser, "_CV2_AVAILABLE", True)
    monkeypatch.setattr(parser, "_ocr_extract_ratios", lambda _frame: [(5.0, 100.0), (70.0, 100.0)])
    monkeypatch.setattr(parser, "_has_target", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(parser, "_template_target_match", lambda _frame: (False, 0.0))

    prev = GameState(hp=18, hp_max=100, mp=80, mp_max=100)
    state = parser.parse_game_state(_Frame(), prev_state=prev)

    assert state.hp == 5
