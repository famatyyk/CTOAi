"""CTOA-205: Sprint-041 dashboard ergonomics focused tests.

Verifies that /api/dashboard returns ergonomic status context
for healthy, degraded, and error operating modes.
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


def test_dashboard_healthy_returns_status_context(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        client = TestClient(module.app)

        def fake_db_exec(sql: str, params: tuple = (), timeout: int = 15):
            if "FROM servers" in sql:
                return {"code": 0, "stdout": "1|https://mythibia.online|READY|2026-05-11\n", "stderr": ""}
            if "FROM modules GROUP BY status" in sql:
                return {"code": 0, "stdout": "VALIDATED|6\n", "stderr": ""}
            if "FROM daily_stats" in sql:
                return {"code": 0, "stdout": "2026-05-11|10|5|92.0|f\n", "stderr": ""}
            if "FROM modules WHERE quality_score" in sql:
                return {"code": 0, "stdout": "T01|mod.lua|95|VALIDATED\n", "stderr": ""}
            raise AssertionError(f"Unexpected SQL: {sql}")

        monkeypatch.setattr(module, "_db_exec", fake_db_exec)

        token = _login_token(client, "ctoa-bot", "jakpod22")
        resp = client.get("/api/dashboard", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

        data = resp.json()
        context = data.get("status_context")
        assert data["status"] == "healthy"
        assert "operational" in data["status_message"].lower()
        assert isinstance(context, dict)
        assert context.get("severity") == "info"
        assert context.get("impacted_sections") == []
        assert isinstance(context.get("recommended_actions"), list)
        assert len(context.get("recommended_actions")) >= 1
        assert "successfully" in str(context.get("detail", "")).lower()


def test_dashboard_degraded_status_context_points_to_impacted_sections(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        client = TestClient(module.app)

        def fake_db_exec(sql: str, params: tuple = (), timeout: int = 15):
            if "FROM daily_stats" in sql:
                return {"code": 1, "stdout": "", "stderr": "query timeout"}
            if "FROM servers" in sql:
                return {"code": 0, "stdout": "1|https://mythibia.online|READY|2026-05-11\n", "stderr": ""}
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
        context = data.get("status_context")
        assert data["status"] == "degraded"
        assert isinstance(context, dict)
        assert context.get("severity") == "warning"
        assert "stats" in context.get("impacted_sections", [])
        assert "stats" in str(context.get("detail", "")).lower()
        actions = context.get("recommended_actions") or []
        assert any("query_diagnostics" in str(item) for item in actions)


def test_dashboard_error_status_context_highlights_critical_sections(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        client = TestClient(module.app)

        def fake_db_exec(sql: str, params: tuple = (), timeout: int = 15):
            if "FROM servers" in sql:
                return {"code": 1, "stdout": "", "stderr": "db unavailable"}
            if "FROM modules GROUP BY status" in sql:
                return {"code": 0, "stdout": "VALIDATED|4\n", "stderr": ""}
            if "FROM daily_stats" in sql:
                return {"code": 0, "stdout": "2026-05-11|10|5|92.0|f\n", "stderr": ""}
            if "FROM modules WHERE quality_score" in sql:
                return {"code": 0, "stdout": "T01|mod.lua|97|VALIDATED\n", "stderr": ""}
            raise AssertionError(f"Unexpected SQL: {sql}")

        monkeypatch.setattr(module, "_db_exec", fake_db_exec)

        token = _login_token(client, "ctoa-bot", "jakpod22")
        resp = client.get("/api/dashboard", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

        data = resp.json()
        context = data.get("status_context")
        assert data["status"] == "error"
        assert "critical" in data["status_message"].lower()
        assert isinstance(context, dict)
        assert context.get("severity") == "critical"
        assert "servers" in context.get("critical_sections", [])
        assert "servers" in str(context.get("detail", "")).lower()
