"""Unit tests for bot input backend adapter."""

from bot.action import input_backend


def test_press_and_click_noop_when_unavailable(monkeypatch):
    monkeypatch.setattr(input_backend, "_available", False)
    called = {"press": 0, "click": 0}

    def _press(_key):
        called["press"] += 1

    def _click(_x, _y):
        called["click"] += 1

    monkeypatch.setattr(input_backend, "_press", _press)
    monkeypatch.setattr(input_backend, "_click", _click)

    input_backend.press("space")
    input_backend.click(10, 20)

    assert called["press"] == 0
    assert called["click"] == 0


def test_press_and_click_forward_when_available(monkeypatch):
    monkeypatch.setattr(input_backend, "_available", True)
    monkeypatch.setattr(input_backend, "_require_focus", False)
    calls = {"key": None, "xy": None}

    def _press(key):
        calls["key"] = key

    def _click(x, y):
        calls["xy"] = (x, y)

    monkeypatch.setattr(input_backend, "_press", _press)
    monkeypatch.setattr(input_backend, "_click", _click)

    input_backend.press("f1")
    input_backend.click(123, 456)

    assert calls["key"] == "f1"
    assert calls["xy"] == (123, 456)


def test_backend_introspection(monkeypatch):
    monkeypatch.setattr(input_backend, "_available", True)
    monkeypatch.setattr(input_backend, "_backend_name", "pyautogui")

    assert input_backend.is_available() is True
    assert input_backend.backend_name() == "pyautogui"


def test_press_blocked_when_focus_required_and_inactive(monkeypatch):
    monkeypatch.setattr(input_backend, "_available", True)
    monkeypatch.setattr(input_backend, "_require_focus", True)
    monkeypatch.setattr(input_backend, "_is_tibia_active_window", lambda: False)

    called = {"press": 0}

    def _press(_key):
        called["press"] += 1

    monkeypatch.setattr(input_backend, "_press", _press)
    input_backend.press("f1")

    assert called["press"] == 0


def test_press_forwards_when_focus_required_and_active(monkeypatch):
    monkeypatch.setattr(input_backend, "_available", True)
    monkeypatch.setattr(input_backend, "_require_focus", True)
    monkeypatch.setattr(input_backend, "_is_tibia_active_window", lambda: True)

    called = {"press": 0}

    def _press(_key):
        called["press"] += 1

    monkeypatch.setattr(input_backend, "_press", _press)
    input_backend.press("f1")

    assert called["press"] == 1
