"""Tests for Agent 4 Q-learning model."""
import pytest
from bot.perception.state import GameState
from bot.decision.ml_model import (
    predict_action, update_q, compute_reward,
    _state_key, _get_row, ACTIONS
)


def make_state(**kwargs) -> GameState:
    s = GameState(hp=100, hp_max=100, mp=100, mp_max=100)
    for k, v in kwargs.items():
        setattr(s, k, v)
    return s


def test_predict_returns_valid_action():
    s = make_state()
    action = predict_action(s)
    assert action in ACTIONS


def test_state_key_format():
    s = make_state(hp=50, hp_max=100, mp=80, mp_max=100, level=15)
    key = _state_key(s)
    parts = key.split("_")
    assert len(parts) == 6
    assert all(p.isdigit() for p in parts)


def test_update_q_changes_value():
    s = make_state(hp=80, hp_max=100)
    ns = make_state(hp=60, hp_max=100)
    key = _state_key(s)
    before = _get_row(key).get("attack", 0.0)
    update_q(s, "attack", 10.0, ns)
    after = _get_row(key)["attack"]
    assert after != before


def test_compute_reward_kill():
    prev = make_state(target_id=1, target_hp_pct=50)
    curr = make_state(target_id=1, target_hp_pct=0)
    r = compute_reward(prev, "attack", "ok", curr)
    assert r > 10


def test_compute_reward_hp_loss():
    prev = make_state(hp=100, hp_max=100)
    curr = make_state(hp=60, hp_max=100)
    r = compute_reward(prev, "idle", "ok", curr)
    assert r < 0


def test_compute_reward_potion_waste():
    prev = make_state(hp=90, hp_max=100)
    curr = make_state(hp=90, hp_max=100)
    r = compute_reward(prev, "use_hp_potion", "ok", curr)
    assert r < 0


def test_compute_reward_loot():
    s = make_state()
    r = compute_reward(s, "loot", "ok", s)
    assert r > 0


def test_brain_uses_ml(monkeypatch):
    from bot.decision import brain
    from bot.decision.ml_model import predict_action as real_predict
    called = []
    def fake_predict(state):
        called.append(True)
        return "attack"
    monkeypatch.setattr("bot.decision.ml_model.predict_action", fake_predict)
    s = make_state()
    brain._USE_ML = True
    brain._prev_state = None
    from bot.decision.brain import decide_action
    result = decide_action(s)
    assert result == "attack"
