"""Unit tests for auto-follow movement action."""

from bot.perception.state import GameState, Position


def test_auto_follow_throttles(monkeypatch):
    from bot.action import movement

    monkeypatch.setattr(movement, "is_available", lambda: True)
    monkeypatch.setattr(movement, "_auto_follow_key", lambda: "f12")
    monkeypatch.setattr(movement, "_auto_follow_interval_ms", lambda: 1000)
    monkeypatch.setattr(movement, "_auto_follow_stuck_ms", lambda: 900)
    monkeypatch.setattr(movement, "_auto_follow_refresh_ms", lambda: 5000)
    monkeypatch.setattr(movement, "_last_follow_press_ts", 0.0)
    monkeypatch.setattr(movement, "_last_follow_position", None)
    monkeypatch.setattr(movement, "_last_follow_move_ts", 0.0)

    calls = []
    monkeypatch.setattr(movement, "press", lambda key: calls.append(key))

    t = {"value": 10.0}
    monkeypatch.setattr(movement.time, "monotonic", lambda: t["value"])

    movement.auto_follow(GameState(position=Position(x=100, y=100, z=7)))
    movement.auto_follow(GameState(position=Position(x=100, y=100, z=7)))
    t["value"] = 11.2
    movement.auto_follow(GameState(position=Position(x=100, y=100, z=7)))
    # Still below stuck threshold, should not re-press.
    t["value"] = 12.0
    movement.auto_follow(GameState(position=Position(x=100, y=100, z=7)))

    assert calls == ["f12", "f12"]


def test_auto_follow_suppresses_when_moving(monkeypatch):
    from bot.action import movement

    monkeypatch.setattr(movement, "is_available", lambda: True)
    monkeypatch.setattr(movement, "_auto_follow_key", lambda: "f12")
    monkeypatch.setattr(movement, "_auto_follow_interval_ms", lambda: 500)
    monkeypatch.setattr(movement, "_auto_follow_stuck_ms", lambda: 900)
    monkeypatch.setattr(movement, "_auto_follow_refresh_ms", lambda: 5000)
    monkeypatch.setattr(movement, "_last_follow_press_ts", 0.0)
    monkeypatch.setattr(movement, "_last_follow_position", None)
    monkeypatch.setattr(movement, "_last_follow_move_ts", 0.0)

    calls = []
    monkeypatch.setattr(movement, "press", lambda key: calls.append(key))

    t = {"value": 20.0}
    monkeypatch.setattr(movement.time, "monotonic", lambda: t["value"])

    movement.auto_follow(GameState(position=Position(x=100, y=100, z=7)))
    t["value"] = 20.7
    movement.auto_follow(GameState(position=Position(x=101, y=100, z=7)))
    t["value"] = 21.4
    movement.auto_follow(GameState(position=Position(x=102, y=100, z=7)))

    assert calls == ["f12"]


def test_auto_follow_refreshes_even_while_moving(monkeypatch):
    from bot.action import movement

    monkeypatch.setattr(movement, "is_available", lambda: True)
    monkeypatch.setattr(movement, "_auto_follow_key", lambda: "f12")
    monkeypatch.setattr(movement, "_auto_follow_interval_ms", lambda: 500)
    monkeypatch.setattr(movement, "_auto_follow_stuck_ms", lambda: 900)
    monkeypatch.setattr(movement, "_auto_follow_refresh_ms", lambda: 2000)
    monkeypatch.setattr(movement, "_last_follow_press_ts", 0.0)
    monkeypatch.setattr(movement, "_last_follow_position", None)
    monkeypatch.setattr(movement, "_last_follow_move_ts", 0.0)

    calls = []
    monkeypatch.setattr(movement, "press", lambda key: calls.append(key))

    t = {"value": 30.0}
    monkeypatch.setattr(movement.time, "monotonic", lambda: t["value"])

    movement.auto_follow(GameState(position=Position(x=200, y=200, z=7)))
    t["value"] = 31.0
    movement.auto_follow(GameState(position=Position(x=201, y=200, z=7)))
    t["value"] = 32.2
    movement.auto_follow(GameState(position=Position(x=202, y=200, z=7)))

    assert calls == ["f12", "f12"]
