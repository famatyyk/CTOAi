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
    monkeypatch.setenv("CTOA_PRODUCT_STATE_DIR", str(tmp_path / ".ctoa-local"))
    monkeypatch.setenv("CTOA_PRODUCT_USER_CONFIG", str(tmp_path / ".ctoa-local" / "user-config.json"))
    monkeypatch.setenv("CTOA_PACKAGE_TIER", "studio")

    import mobile_console.app as mobile_app

    return importlib.reload(mobile_app)


def _login_token(client: TestClient, username: str, password: str) -> str:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    return str(payload["token"])


def test_live_dashboard_profile_requires_auth(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        client = TestClient(module.app)

        response = client.get("/api/live-dashboard/profile")
        assert response.status_code == 401


def test_live_dashboard_profile_get_and_put(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        client = TestClient(module.app)

        profile_store: dict[str, dict] = {}

        def fake_load(username: str, role: str) -> dict:
            profile = profile_store.get(username) or {
                "api_base": "",
                "refresh_seconds": 10,
            }
            profile_store[username] = profile
            return {
                "username": username,
                "role": role,
                "profile": profile,
                "created_at": None,
                "updated_at": None,
            }

        def fake_save(username: str, role: str, payload: dict) -> dict:
            normalized = module._normalize_live_dashboard_profile(payload)
            profile_store[username] = normalized
            return normalized

        monkeypatch.setattr(module, "_load_live_dashboard_profile", fake_load)
        monkeypatch.setattr(module, "_save_live_dashboard_profile", fake_save)

        operator_token = _login_token(client, "ctoa-bot", "jakpod22")
        headers = {"Authorization": f"Bearer {operator_token}"}

        first = client.get("/api/live-dashboard/profile", headers=headers)
        assert first.status_code == 200
        payload = first.json()
        assert payload["ok"] is True
        assert payload["username"] == "ctoa-bot"
        assert payload["profile"]["refresh_seconds"] == 10

        update = client.put(
            "/api/live-dashboard/profile",
            headers=headers,
            json={
                "api_base": "http://127.0.0.1:8787/",
                "refresh_seconds": 15,
            },
        )
        assert update.status_code == 200
        updated_payload = update.json()
        assert updated_payload["profile"]["api_base"] == "http://127.0.0.1:8787"
        assert updated_payload["profile"]["refresh_seconds"] == 15

        second = client.get("/api/live-dashboard/profile", headers=headers)
        assert second.status_code == 200
        second_payload = second.json()
        assert second_payload["profile"]["api_base"] == "http://127.0.0.1:8787"
        assert second_payload["profile"]["refresh_seconds"] == 15
