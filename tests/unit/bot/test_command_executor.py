from types import SimpleNamespace


def _make_executor(monkeypatch):
    from runner.hybrid_bot import command_executor as ce

    class FakeKeyboard:
        def __init__(self):
            self.events = []

        def press(self, key):
            self.events.append(("press", key))

        def release(self, key):
            self.events.append(("release", key))

        def type(self, text):
            self.events.append(("type", text))

    class FakeMouse:
        def __init__(self):
            self.events = []

        def press(self, btn):
            self.events.append(("press", btn))

        def release(self, btn):
            self.events.append(("release", btn))

    fake_key = SimpleNamespace(
        enter="enter",
        shift="shift",
        ctrl="ctrl",
        space="space",
        tab="tab",
        esc="esc",
        alt="alt",
        l="l",
        f1="f1",
        f2="f2",
        f3="f3",
        f4="f4",
        f5="f5",
    )

    monkeypatch.setattr(ce, "HAS_PYNPUT", True)
    monkeypatch.setattr(ce, "Key", fake_key)
    monkeypatch.setattr(ce, "KeyboardController", lambda: FakeKeyboard())
    monkeypatch.setattr(ce, "MouseController", lambda: FakeMouse())
    return ce, FakeKeyboard, FakeMouse


def test_command_executor_supports_named_key_combo_and_wait(monkeypatch):
    ce, _, _ = _make_executor(monkeypatch)
    sleeps = []
    monkeypatch.setattr(ce.time, "sleep", lambda value: sleeps.append(value))

    executor = ce.CommandExecutor(enable_delays=False)

    assert executor.execute("key f1") is True
    assert executor.keyboard.events[:2] == [("press", "f1"), ("release", "f1")]

    assert executor.execute("combo ctrl+shift+l") is True
    assert executor.keyboard.events[2:8] == [
        ("press", "ctrl"),
        ("press", "shift"),
        ("press", "l"),
        ("release", "l"),
        ("release", "shift"),
        ("release", "ctrl"),
    ]

    assert executor.execute("wait 100") is True
    assert sleeps == [0.1]


def test_command_executor_supports_say_and_pause_alias(monkeypatch):
    ce, _, _ = _make_executor(monkeypatch)
    sleeps = []
    monkeypatch.setattr(ce.time, "sleep", lambda value: sleeps.append(value))

    executor = ce.CommandExecutor(enable_delays=False)
    assert executor.execute("say exura") is True
    assert executor.keyboard.events[0] == ("type", "exura")

    assert executor.execute("pause 50") is True
    assert sleeps == [0.05]


def test_batch_command_executor_supports_bare_wait_and_pause(monkeypatch):
    ce, _, _ = _make_executor(monkeypatch)
    sleeps = []
    
    async def fake_sleep(value):
        sleeps.append(value)

    monkeypatch.setattr(ce.asyncio, "sleep", fake_sleep)

    executor = ce.CommandExecutor(enable_delays=False)

    async def fake_execute_async(command):
        raise AssertionError(f"unexpected command execution: {command}")

    monkeypatch.setattr(executor, "execute_async", fake_execute_async)

    batch = ce.BatchCommandExecutor(executor)
    batch.add("wait", duration_ms=250)
    batch.add("pause", duration_ms=500)

    assert ce.asyncio.run(batch.execute()) is True
    assert sleeps == [0.25, 0.5]
