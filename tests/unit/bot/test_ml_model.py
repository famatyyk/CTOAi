"""Tests for Agent 4 Double Q-learning model (Sprint 6)."""
import pytest
from bot.perception.state import GameState
from bot.decision.ml_model import (
    predict_action, update_q, compute_reward,
    _state_key, _Q_A, _Q_B, ACTIONS
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
    """update_q must change at least one Q-table."""
    import bot.decision.ml_model as m
    s = make_state(hp=80, hp_max=100)
    ns = make_state(hp=60, hp_max=100)
    key = _state_key(s)
    before_a = m._Q_A.get(key, {}).get("attack", 0.0)
    before_b = m._Q_B.get(key, {}).get("attack", 0.0)
    # Run many updates so both tables get touched
    for _ in range(20):
        update_q(s, "attack", 10.0, ns)
    after_a = m._Q_A.get(key, {}).get("attack", 0.0)
    after_b = m._Q_B.get(key, {}).get("attack", 0.0)
    assert after_a != before_a or after_b != before_b


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
