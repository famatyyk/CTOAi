import importlib
from pathlib import Path


def _load_app(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("CTOA_ENV", raising=False)
    monkeypatch.setenv("CTOA_MOBILE_TOKEN", "test-mobile-token")
    monkeypatch.setenv("CTOA_OWNER_PASSWORD", "test-owner-pass")
    monkeypatch.setenv("CTOA_OPERATOR_PASSWORD", "test-operator-pass")
    monkeypatch.setenv("CTOA_ADMIN_SETTINGS_FILE", str(tmp_path / "admin-settings.json"))
    monkeypatch.setenv("CTOA_IDEA_PARKING_FILE", str(tmp_path / "idea-parking.json"))
    monkeypatch.setenv("CTOA_PRODUCT_STATE_DIR", str(tmp_path / ".ctoa-local"))
    monkeypatch.setenv("CTOA_PRODUCT_USER_CONFIG", str(tmp_path / ".ctoa-local" / "user-config.json"))

    import mobile_console.app as mobile_app

    return importlib.reload(mobile_app)


def test_db_exec_psql_fallback_does_not_put_password_in_argv(monkeypatch, tmp_path):
    module = _load_app(monkeypatch, tmp_path)
    monkeypatch.setattr(module, "psycopg2", None)
    monkeypatch.setenv("DB_PASSWORD", "super-secret-db-pass")
    monkeypatch.setenv("DB_HOST", "db.local")
    monkeypatch.setenv("DB_PORT", "15432")
    monkeypatch.setenv("DB_USER", "ctoa_user")
    monkeypatch.setenv("DB_NAME", "ctoa_db")
    monkeypatch.setattr(module, "_command_exists", lambda name: name == "psql")

    captured = {}

    def fake_run_argv(args, timeout=20, cwd=None, env=None):
        captured["args"] = args
        captured["env"] = env or {}
        return {"code": 0, "stdout": "1", "stderr": ""}

    monkeypatch.setattr(module, "_run_argv", fake_run_argv)

    result = module._db_exec("SELECT %s", ("ok",), timeout=7)

    assert result["code"] == 0
    assert "super-secret-db-pass" not in " ".join(captured["args"])
    assert captured["env"]["PGPASSWORD"] == "super-secret-db-pass"
    assert captured["args"][:2] == ["psql", "-h"]
    assert "postgresql://" not in " ".join(captured["args"])


def test_db_exec_docker_fallback_passes_password_by_env_name_only(monkeypatch, tmp_path):
    module = _load_app(monkeypatch, tmp_path)
    monkeypatch.setattr(module, "psycopg2", None)
    monkeypatch.setenv("DB_PASSWORD", "super-secret-db-pass")
    monkeypatch.setattr(module, "_command_exists", lambda name: name == "docker")

    captured = {}

    def fake_run_argv(args, timeout=20, cwd=None, env=None):
        captured["args"] = args
        captured["env"] = env or {}
        return {"code": 0, "stdout": "1", "stderr": ""}

    monkeypatch.setattr(module, "_run_argv", fake_run_argv)

    result = module._db_exec("SELECT %s", ("ok",), timeout=7)

    assert result["code"] == 0
    assert "super-secret-db-pass" not in " ".join(captured["args"])
    assert captured["env"]["PGPASSWORD"] == "super-secret-db-pass"
    assert ["-e", "PGPASSWORD"] == captured["args"][3:5]


def test_run_argv_resolves_executable_before_launch(monkeypatch, tmp_path):
    module = _load_app(monkeypatch, tmp_path)
    captured = {}

    def fake_resolve(name):
        captured["resolve"] = name
        return "/trusted/tool"

    class FakeProc:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return FakeProc()

    monkeypatch.setattr(module.process_safety, "resolve_executable", fake_resolve)
    monkeypatch.setattr(module.process_safety, "run_trusted", fake_run)

    result = module._run_argv(["tool", "arg1"], timeout=9, cwd=str(tmp_path), env={"PGPASSWORD": "secret"})

    assert result == {"code": 0, "stdout": "ok", "stderr": ""}
    assert captured["resolve"] == "tool"
    assert captured["command"] == ["/trusted/tool", "arg1"]
    assert captured["kwargs"]["timeout"] == 9
    assert captured["kwargs"]["cwd"] == str(tmp_path)
    assert captured["kwargs"]["env"]["PGPASSWORD"] == "secret"
