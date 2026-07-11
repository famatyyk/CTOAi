import importlib
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from _pytest.monkeypatch import MonkeyPatch
from fastapi.testclient import TestClient


def _load_app_module(monkeypatch: MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("CTOA_MOBILE_TOKEN", "test-mobile-token")
    monkeypatch.setenv("CTOA_OWNER_USER", "CTO")
    monkeypatch.setenv("CTOA_OWNER_PASSWORD", "test-owner-pass")
    monkeypatch.setenv("CTOA_OPERATOR_USER", "ctoa-bot")
    monkeypatch.setenv("CTOA_OPERATOR_PASSWORD", "test-operator-pass")
    monkeypatch.setenv(
        "CTOA_ADMIN_SETTINGS_FILE", str(tmp_path / "admin-settings.json")
    )
    monkeypatch.setenv("CTOA_IDEA_PARKING_FILE", str(tmp_path / "idea-parking.json"))
    monkeypatch.setenv("CTOA_GENERATED_DIR", str(tmp_path / "generated"))
    monkeypatch.setenv("CTOA_PRODUCT_STATE_DIR", str(tmp_path / ".ctoa-local"))
    monkeypatch.setenv(
        "CTOA_PRODUCT_USER_CONFIG", str(tmp_path / ".ctoa-local" / "user-config.json")
    )
    monkeypatch.setenv("CTOA_PACKAGE_TIER", "studio")
    monkeypatch.delenv("CTOA_MOBILE_FULL_ACCESS", raising=False)

    import mobile_console.app as mobile_app

    return importlib.reload(mobile_app)


def test_safe_preset_command_executes_as_structured_argv(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        client = TestClient(module.app)
        command = (
            "cd /opt/ctoa; CTOA_BACKLOG_FILE=/opt/ctoa/workflows/backlog-sprint-004.yaml "
            "python3 runner/runner.py report"
        )
        captured = {}

        def fake_run_argv(args, timeout=20, cwd=None, env=None, redact_output=False):
            captured["args"] = args
            captured["timeout"] = timeout
            captured["cwd"] = cwd
            captured["env"] = env or {}
            captured["redact_output"] = redact_output
            return {"code": 0, "stdout": "ok", "stderr": ""}

        def unexpected_run(*_args, **_kwargs):
            raise AssertionError(
                "safe preset should not execute through raw command text"
            )

        monkeypatch.setattr(module, "_run_argv", fake_run_argv)
        monkeypatch.setattr(module, "_run", unexpected_run)
        audit_log = Path(tmp) / "mobile-console-audit.log"
        monkeypatch.setattr(module, "AUDIT_LOG", audit_log)

        response = client.post(
            "/api/command",
            headers={"X-CTOA-Token": "test-mobile-token"},
            json={"command": command, "timeout": 7, "cwd": "/tmp/ignored"},
        )

        assert response.status_code == 200
        assert response.json()["stdout"] == "ok"
        assert captured["args"] == ["python3", "runner/runner.py", "report"]
        assert captured["timeout"] == 7
        assert captured["cwd"] == "/opt/ctoa"
        assert captured["env"] == {
            "CTOA_BACKLOG_FILE": "/opt/ctoa/workflows/backlog-sprint-004.yaml"
        }
        assert captured["redact_output"] is True
        audit = json.loads(audit_log.read_text(encoding="utf-8").strip())
        assert audit["actor"] == "CTO"
        assert audit["actor_role"] == "owner"
        assert audit["auth_mode"] == "legacy_token"
        assert audit["auth_transport"] == "unknown"
        assert "session_token" not in audit


def test_safe_mode_rejects_non_preset_without_launching(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        client = TestClient(module.app)

        def unexpected_launch(*_args, **_kwargs):
            raise AssertionError("non-preset command must not launch in safe mode")

        monkeypatch.setattr(module, "_run_argv", unexpected_launch)
        monkeypatch.setattr(module, "_run", unexpected_launch)

        response = client.post(
            "/api/command",
            headers={"X-CTOA-Token": "test-mobile-token"},
            json={"command": "python3 -c print(123)", "timeout": 7},
        )

        assert response.status_code == 403
        assert (
            response.json()["detail"]
            == "Command not allowed. Use one of /api/presets."
        )


def test_full_access_env_does_not_enable_arbitrary_command_execution(
    monkeypatch: MonkeyPatch,
):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        monkeypatch.setenv("CTOA_MOBILE_FULL_ACCESS", "true")
        client = TestClient(module.app)

        def unexpected_launch(*_args, **_kwargs):
            raise AssertionError("full access flag must not launch arbitrary command text")

        monkeypatch.setattr(module, "_run_argv", unexpected_launch)
        monkeypatch.setattr(module, "_run", unexpected_launch)

        response = client.post(
            "/api/command",
            headers={"X-CTOA-Token": "test-mobile-token"},
            json={"command": "python3 -c print(123)", "timeout": 7, "cwd": "/tmp"},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Command not allowed. Use one of /api/presets."


def test_full_access_env_is_not_reported_as_shell_mode(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        monkeypatch.setenv("CTOA_MOBILE_FULL_ACCESS", "true")
        client = TestClient(module.app)

        auto_check = client.get(
            "/api/auth/auto-check",
            headers={"X-CTOA-Token": "test-mobile-token"},
        )
        health = client.get(
            "/api/health",
            headers={"X-CTOA-Token": "test-mobile-token"},
        )

        assert auto_check.status_code == 200
        assert auto_check.json()["full_access"] is False
        assert auto_check.json()["command_mode"] == "presets"
        assert health.status_code == 200
        assert health.json()["full_access"] is False
        assert health.json()["command_mode"] == "presets"


def test_command_output_is_redacted_before_return(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))

        monkeypatch.setattr(
            module.process_safety, "resolve_executable", lambda name: f"/usr/bin/{name}"
        )
        monkeypatch.setattr(
            module.process_safety,
            "run_trusted",
            lambda *_args, **_kwargs: SimpleNamespace(
                returncode=0,
                stdout="ready token=secret-token-value Bearer abcdefghijklmnopqrstuvwxyz",
                stderr="warning password=hunter2 glpat-secretshouldnotleak",
            ),
        )

        result = module._run_safe_command(
            "systemctl status ctoa-runner.timer --no-pager -l",
            timeout=7,
        )

        payload = json.dumps(result)
        assert result["code"] == 0
        assert "token=[redacted]" in result["stdout"]
        assert "Bearer [redacted]" in result["stdout"]
        assert "password=[redacted]" in result["stderr"]
        assert "secret-token-value" not in payload
        assert "abcdefghijklmnopqrstuvwxyz" not in payload
        assert "hunter2" not in payload
        assert "glpat-secretshouldnotleak" not in payload


def test_logs_fallback_reads_bounded_tail_and_redacts_output(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmp_path = Path(tmp)
        module = _load_app_module(monkeypatch, tmp_path)
        monkeypatch.setattr(module, "_is_windows_host", lambda: True)
        monkeypatch.setattr(module, "_command_exists", lambda _name: False)
        monkeypatch.setattr(module, "ROOT", tmp_path)
        monkeypatch.setattr(module, "LOG_TAIL_MAX_BYTES", 80)

        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()
        (logs_dir / "runner.log").write_text(
            "old secret-token-value\n"
            + "\n".join(f"line-{idx:03d}" for idx in range(20))
            + "\nlatest token=visible-secret\n",
            encoding="utf-8",
        )
        client = TestClient(module.app)

        response = client.get(
            "/api/logs?target=runner&lines=10",
            headers={"X-CTOA-Token": "test-mobile-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["code"] == 0
        assert "... [truncated to last 80 bytes]" in payload["stdout"]
        assert "latest token=[redacted]" in payload["stdout"]
        assert "visible-secret" not in payload["stdout"]
        assert "old secret-token-value" not in payload["stdout"]


def test_logs_rejects_symlinked_log_without_reading_target(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmp_path = Path(tmp)
        module = _load_app_module(monkeypatch, tmp_path)
        monkeypatch.setattr(module, "_is_windows_host", lambda: True)
        monkeypatch.setattr(module, "ROOT", tmp_path)

        outside = tmp_path / "outside-secret.log"
        outside.write_text("token=secret-token-value\n", encoding="utf-8")
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()
        try:
            (logs_dir / "runner.log").symlink_to(outside)
        except OSError as exc:
            pytest.skip(f"symlink creation unavailable: {exc}")

        client = TestClient(module.app)
        response = client.get(
            "/api/logs?target=runner&lines=10",
            headers={"X-CTOA-Token": "test-mobile-token"},
        )

        assert response.status_code == 200
        assert response.json()["stdout"] == "(log unavailable)"
        assert "secret-token-value" not in json.dumps(response.json())
