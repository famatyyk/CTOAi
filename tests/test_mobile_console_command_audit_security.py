import importlib
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from _pytest.monkeypatch import MonkeyPatch


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

    import mobile_console.app as mobile_app

    return importlib.reload(mobile_app)


def test_mobile_console_audit_redacts_command_secrets(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        command = (
            "curl -H 'Authorization: Bearer abcdefghijklmnopqrstuvwxyz' "
            "https://example.invalid?token=secret-token-value "
            "--password hunter2 sk-secret-should-not-leak"
        )

        redacted = module._redact_audit_text(command)

        assert "Bearer [redacted]" in redacted
        assert "token=[redacted]" in redacted
        assert "--password [redacted]" in redacted
        assert "secret-token-value" not in redacted
        assert "hunter2" not in redacted
        assert "sk-secret-should-not-leak" not in redacted


def test_mobile_console_audit_persists_redacted_command(
    monkeypatch: MonkeyPatch, tmp_path: Path
):
    module = _load_app_module(monkeypatch, tmp_path)
    audit_log = tmp_path / "mobile-console-audit.log"
    monkeypatch.setattr(module, "AUDIT_LOG", audit_log)
    request = SimpleNamespace(
        client=SimpleNamespace(host="127.0.0.1"),
        url=SimpleNamespace(path="/api/command"),
    )

    module._audit(
        request,
        "python tool.py --api-key abcdefghijklmnopqrstuvwxyz password=hunter2",
        0,
    )

    record = json.loads(audit_log.read_text(encoding="utf-8").strip())
    assert (
        record["command"] == "python tool.py --api-key [redacted] password=[redacted]"
    )
    assert record["actor"] == "anonymous"
    assert record["actor_role"] == "anonymous"
    assert record["auth_mode"] == "unknown"
    assert "abcdefghijklmnopqrstuvwxyz" not in json.dumps(record)
    assert "hunter2" not in json.dumps(record)
