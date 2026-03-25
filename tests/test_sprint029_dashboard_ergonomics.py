"""CTOA-145: Sprint-029 dashboard ergonomics pass focused tests.

Verifies that /api/dashboard includes a human-readable status_message
for both healthy and degraded operating modes.
"""

from __future__ import annotations

import importlib
import tempfile
from pathlib import Path

from _pytest.monkeypatch import MonkeyPatch
from fastapi.testclient import TestClient


def _load_app_module(monkeypatch: MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("CTOA_MOBILE_TOKEN", "test-mobile-token")
    monkeypatch.setenv("CTOA_OWNER_USER", "CTO")
    monkeypatch.setenv("CTOA_OWNER_PASSWORD", "asdzxc12")
    monkeypatch.setenv("CTOA_OPERATOR_USER", "ctoa-bot")
    monkeypatch.setenv("CTOA_OPERATOR_PASSWORD", "jakpod22")
    monkeypatch.setenv("CTOA_ADMIN_SETTINGS_FILE", str(tmp_path / "admin-settings.json"))
    monkeypatch.setenv("CTOA_IDEA_PARKING_FILE", str(tmp_path / "idea-parking.json"))
    monkeypatch.setenv("CTOA_GENERATED_DIR", str(tmp_path / "generated"))
    monkeypatch.setenv("CTOA_PRODUCT_STATE_DIR", str(tmp_path / ".ctoa-local"))
    monkeypatch.setenv("CTOA_PRODUCT_USER_CONFIG", str(tmp_path / ".ctoa-local" / "user-config.json"))
    monkeypatch.setenv("CTOA_PACKAGE_TIER", "studio")
    import mobile_console.app as mobile_app
    return importlib.reload(mobile_app)


def _login_token(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return str(response.json()["token"])


def test_dashboard_healthy_has_operational_status_message(monkeypatch: MonkeyPatch):
    """Healthy dashboard must return 'All systems operational' status_message."""
    with tempfile.TemporaryDirectory() as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        client = TestClient(module.app)

        def fake_db_exec(sql: str, params: tuple = (), timeout: int = 15):
            if "FROM servers" in sql:
                return {"code": 0, "stdout": "1|https://mythibia.online|READY|2026-03-25\n", "stderr": ""}
            if "FROM modules GROUP BY status" in sql:
                return {"code": 0, "stdout": "VALIDATED|6\n", "stderr": ""}
            if "FROM daily_stats" in sql:
                return {"code": 0, "stdout": "2026-03-25|10|5|92.0|f\n", "stderr": ""}
            if "FROM modules WHERE quality_score" in sql:
                return {"code": 0, "stdout": "T01|mod.lua|95|VALIDATED\n", "stderr": ""}
            raise AssertionError(f"Unexpected SQL: {sql}")

        monkeypatch.setattr(module, "_db_exec", fake_db_exec)

        token = _login_token(client, "ctoa-bot", "jakpod22")
        resp = client.get("/api/dashboard", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

        data = resp.json()
        assert "status_message" in data, "status_message field missing from dashboard response"
        assert data["status"] == "healthy"
        assert "operational" in data["status_message"].lower(), (
            f"Expected 'operational' in message, got: {data['status_message']!r}"
        )


def test_dashboard_degraded_has_descriptive_status_message(monkeypatch: MonkeyPatch):
    """Degraded dashboard must return a non-trivial, human-readable status_message."""
    with tempfile.TemporaryDirectory() as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        client = TestClient(module.app)

        def fake_db_exec(sql: str, params: tuple = (), timeout: int = 15):
            if "FROM daily_stats" in sql:
                return {"code": 1, "stdout": "", "stderr": "query timeout"}
            if "FROM servers" in sql:
                return {"code": 0, "stdout": "1|https://mythibia.online|READY|2026-03-25\n", "stderr": ""}
            if "FROM modules GROUP BY status" in sql:
                return {"code": 0, "stdout": "VALIDATED|4\n", "stderr": ""}
            if "FROM modules WHERE quality_score" in sql:
                return {"code": 0, "stdout": "T01|mod.lua|97|VALIDATED\n", "stderr": ""}
            raise AssertionError(f"Unexpected SQL: {sql}")

        monkeypatch.setattr(module, "_db_exec", fake_db_exec)

        token = _login_token(client, "ctoa-bot", "jakpod22")
        resp = client.get("/api/dashboard", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

        data = resp.json()
        assert "status_message" in data, "status_message field missing from dashboard response"
        assert data["status"] == "degraded"
        assert len(data["status_message"]) > 10, (
            f"status_message too short for degraded mode: {data['status_message']!r}"
        )
        assert data["status_message"] != "healthy", "Degraded mode must not reuse healthy message"
