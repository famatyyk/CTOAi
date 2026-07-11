import importlib
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


def _login(client: TestClient) -> dict:
    response = client.post(
        "/api/auth/login",
        json={"username": "ctoa-bot", "password": "test-operator-pass"},
    )
    assert response.status_code == 200
    return response.json()


def test_cookie_authenticated_mutation_requires_csrf(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        client = TestClient(module.app)

        login = _login(client)

        missing_csrf = client.post("/api/ideas", json={"text": "csrf-protected"})
        assert missing_csrf.status_code == 403
        assert missing_csrf.json()["detail"] == "CSRF token missing or invalid"

        with_csrf = client.post(
            "/api/ideas",
            headers={"X-CSRF-Token": str(login["csrf_token"])},
            json={"text": "csrf-protected"},
        )
        assert with_csrf.status_code == 200
        assert with_csrf.json()["ok"] is True


def test_bearer_authenticated_mutation_does_not_require_csrf(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        client = TestClient(module.app)

        login = _login(client)

        response = client.post(
            "/api/ideas",
            headers={"Authorization": f"Bearer {login['token']}"},
            json={"text": "header-auth"},
        )
        assert response.status_code == 200
        assert response.json()["ok"] is True
