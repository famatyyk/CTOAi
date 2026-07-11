import importlib
import json
import tempfile
from pathlib import Path

from _pytest.monkeypatch import MonkeyPatch
from fastapi.testclient import TestClient


def _load_app_module(monkeypatch: MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("CTOA_MOBILE_TOKEN", "test-mobile-token")
    monkeypatch.setenv("CTOA_OWNER_USER", "CTO")
    monkeypatch.setenv("CTOA_OWNER_PASSWORD", "test-owner-pass")
    monkeypatch.setenv("CTOA_OPERATOR_USER", "ctoa-bot")
    monkeypatch.setenv("CTOA_OPERATOR_PASSWORD", "test-operator-pass")
    monkeypatch.setenv("CTOA_ADMIN_SETTINGS_FILE", str(tmp_path / "admin-settings.json"))
    monkeypatch.setenv("CTOA_IDEA_PARKING_FILE", str(tmp_path / "idea-parking.json"))
    monkeypatch.setenv("CTOA_GENERATED_DIR", str(tmp_path / "generated"))
    monkeypatch.setenv("CTOA_PRODUCT_STATE_DIR", str(tmp_path / ".ctoa-local"))
    monkeypatch.setenv("CTOA_PRODUCT_USER_CONFIG", str(tmp_path / ".ctoa-local" / "user-config.json"))
    monkeypatch.setenv("CTOA_PACKAGE_TIER", "studio")

    import mobile_console.app as mobile_app

    return importlib.reload(mobile_app)


def _audit_records(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_intel_launch_requires_confirmation_before_side_effects(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmp_path = Path(tmp)
        module = _load_app_module(monkeypatch, tmp_path)
        audit_log = tmp_path / "mobile-console-audit.log"
        monkeypatch.setattr(module, "AUDIT_LOG", audit_log)

        def unexpected_side_effect(*_args, **_kwargs):
            raise AssertionError("guarded action must not touch runtime without confirmation")

        monkeypatch.setattr(module, "_db_exec", unexpected_side_effect)
        monkeypatch.setattr(module, "_trigger_orchestrator_start", unexpected_side_effect)

        client = TestClient(module.app)
        response = client.post(
            "/api/agents/intel/launch",
            headers={"X-CTOA-Token": "test-mobile-token"},
            json={
                "urls": ["https://tibiantis.online"],
                "force_rescout": True,
                "trigger_now": True,
                "confirm": False,
                "reason": "manual launch",
            },
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "intel_launch requires explicit confirmation and audit reason"
        records = _audit_records(audit_log)
        assert records[-1]["command"] == "intel_launch:denied:missing_confirmation"
        assert records[-1]["actor_role"] == "owner"


def test_one_click_execution_requires_confirmation_before_side_effects(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmp_path = Path(tmp)
        module = _load_app_module(monkeypatch, tmp_path)
        audit_log = tmp_path / "mobile-console-audit.log"
        monkeypatch.setattr(module, "AUDIT_LOG", audit_log)

        def unexpected_side_effect(*_args, **_kwargs):
            raise AssertionError("one-click execution must not touch runtime without confirmation")

        monkeypatch.setattr(module, "_db_exec", unexpected_side_effect)
        monkeypatch.setattr(module, "_trigger_orchestrator_start", unexpected_side_effect)

        client = TestClient(module.app)
        response = client.post(
            "/api/agents/execution/run",
            headers={"X-CTOA-Token": "test-mobile-token"},
            json={},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "agent_execution_one_click requires explicit confirmation and audit reason"
        records = _audit_records(audit_log)
        assert records[-1]["command"] == "agent_execution_one_click:denied:missing_confirmation"
        assert records[-1]["actor_role"] == "owner"


def test_confirmed_intel_launch_audits_redacted_reason(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmp_path = Path(tmp)
        module = _load_app_module(monkeypatch, tmp_path)
        audit_log = tmp_path / "mobile-console-audit.log"
        monkeypatch.setattr(module, "AUDIT_LOG", audit_log)
        monkeypatch.setattr(module, "_db_exec", lambda *_args, **_kwargs: {"code": 0, "stdout": "1|NEW", "stderr": ""})
        monkeypatch.setattr(
            module,
            "_trigger_orchestrator_start",
            lambda *_args, **_kwargs: {"code": 0, "stdout": "triggered", "stderr": ""},
        )

        client = TestClient(module.app)
        response = client.post(
            "/api/agents/intel/launch",
            headers={"X-CTOA-Token": "test-mobile-token"},
            json={
                "urls": ["https://tibiantis.online"],
                "force_rescout": True,
                "trigger_now": True,
                "confirm": True,
                "reason": "manual launch token=secret-token-value",
            },
        )

        assert response.status_code == 200
        assert response.json()["triggered"] is True
        records = _audit_records(audit_log)
        assert records[-1]["command"] == "intel_launch:1:reason=manual launch token=[redacted]"
        assert "secret-token-value" not in json.dumps(records)


def test_confirmed_one_click_execution_audits_reason(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmp_path = Path(tmp)
        module = _load_app_module(monkeypatch, tmp_path)
        audit_log = tmp_path / "mobile-console-audit.log"
        monkeypatch.setattr(module, "AUDIT_LOG", audit_log)
        monkeypatch.setattr(module.time, "sleep", lambda *_args, **_kwargs: None)
        monkeypatch.setattr(module, "_db_exec", lambda *_args, **_kwargs: {"code": 0, "stdout": "1|NEW", "stderr": ""})
        monkeypatch.setattr(
            module,
            "_trigger_orchestrator_start",
            lambda *_args, **_kwargs: {"code": 0, "stdout": "triggered", "stderr": ""},
        )

        client = TestClient(module.app)
        response = client.post(
            "/api/agents/execution/run",
            headers={"X-CTOA-Token": "test-mobile-token"},
            json={"confirm": True, "reason": "manual one-click"},
        )

        assert response.status_code == 200
        assert response.json()["ok"] is True
        records = _audit_records(audit_log)
        assert records[-1]["command"] == "agent_execution_one_click:reason=manual one-click"
        assert records[-1]["actor_role"] == "owner"
