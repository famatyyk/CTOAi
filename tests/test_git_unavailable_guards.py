from scripts.ops import bridge_replacement_readiness as bridge
from scripts.ops import runtime_path_guard as runtime_guard


def test_runtime_path_guard_returns_clear_error_when_git_unavailable(monkeypatch, capsys):
    monkeypatch.setattr(runtime_guard, "run_git", lambda *args, **kwargs: (_ for _ in ()).throw(runtime_guard.GitUnavailableError("git missing")))

    code = runtime_guard.main()

    assert code == 2
    out = capsys.readouterr().out
    assert "[FAIL] git missing" in out


def test_bridge_readiness_returns_clear_error_when_git_unavailable(monkeypatch, capsys):
    monkeypatch.setattr(bridge, "run_git", lambda *args, **kwargs: (_ for _ in ()).throw(bridge.GitUnavailableError("git missing")))

    code = bridge.main()

    assert code == 2
    out = capsys.readouterr().out
    assert "git_unavailable: git missing" in out
    assert "NOT READY: configure Git before running readiness checks." in out

