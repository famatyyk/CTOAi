import importlib
import tempfile
from pathlib import Path

from _pytest.monkeypatch import MonkeyPatch
from fastapi.testclient import TestClient


def _load_app_module(monkeypatch: MonkeyPatch, tmp_path: Path, *, package_tier: str = "studio", mobile_console_enabled: bool | None = None):
    monkeypatch.setenv("CTOA_MOBILE_TOKEN", "test-mobile-token")
    monkeypatch.setenv("CTOA_OWNER_USER", "CTO")
    monkeypatch.setenv("CTOA_OWNER_PASSWORD", "asdzxc12")
    monkeypatch.setenv("CTOA_OPERATOR_USER", "ctoa-bot")
    monkeypatch.setenv("CTOA_OPERATOR_PASSWORD", "jakpod22")
    monkeypatch.setenv("CTOA_ADMIN_SETTINGS_FILE", str(tmp_path / "admin-settings.json"))
    monkeypatch.setenv("CTOA_IDEA_PARKING_FILE", str(tmp_path / "idea-parking.json"))
    monkeypatch.setenv("CTOA_GENERATED_DIR", str(tmp_path / "generated"))
    monkeypatch.setenv("CTOA_PACKAGE_TIER", package_tier)
    if mobile_console_enabled is not None:
        monkeypatch.setenv("CTOA_CAPABILITY_MOBILE_CONSOLE", "true" if mobile_console_enabled else "false")

    import mobile_console.app as mobile_app

    return importlib.reload(mobile_app)


def test_mobile_console_api_blocked_for_core_tier(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        module = _load_app_module(monkeypatch, Path(tmp), package_tier="core")
        client = TestClient(module.app)

        response = client.post("/api/auth/login", json={"username": "CTO", "password": "asdzxc12"})
        assert response.status_code == 403
        assert response.json()["detail"] == "mobile_console capability requires Pro or Studio package"


def test_mobile_console_console_route_blocked_for_core_tier(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        module = _load_app_module(monkeypatch, Path(tmp), package_tier="core")
        client = TestClient(module.app)

        response = client.get("/console")
        assert response.status_code == 403


def test_mobile_console_api_allowed_for_pro_tier(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        module = _load_app_module(monkeypatch, Path(tmp), package_tier="pro")
        client = TestClient(module.app)

        response = client.post("/api/auth/login", json={"username": "CTO", "password": "asdzxc12"})
        assert response.status_code == 200
        assert response.json()["ok"] is True