import importlib
import tempfile
from pathlib import Path

from _pytest.monkeypatch import MonkeyPatch
from fastapi.testclient import TestClient


def _load_app_module(monkeypatch: MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("CTOA_MOBILE_TOKEN", "test-mobile-token")
    monkeypatch.setenv("CTOA_OWNER_USER", "cto")
    monkeypatch.setenv("CTOA_OWNER_PASSWORD", "ownerpass123")
    monkeypatch.setenv("CTOA_OPERATOR_USER", "ctoa-bot")
    monkeypatch.setenv("CTOA_OPERATOR_PASSWORD", "operpass123")
    monkeypatch.setenv("CTOA_ADMIN_SETTINGS_FILE", str(tmp_path / "admin-settings.json"))
    monkeypatch.setenv("CTOA_IDEA_PARKING_FILE", str(tmp_path / "idea-parking.json"))
    monkeypatch.setenv("CTOA_PRODUCT_STATE_DIR", str(tmp_path / ".ctoa-local"))
    monkeypatch.setenv("CTOA_PRODUCT_USER_CONFIG", str(tmp_path / ".ctoa-local" / "user-config.json"))
    monkeypatch.setenv("CTOA_PACKAGE_TIER", "studio")

    import mobile_console.app as mobile_app
    return importlib.reload(mobile_app)


def test_self_register_disabled_by_default(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        client = TestClient(module.app)

        response = client.post(
            "/api/auth/register",
            json={"username": "member1", "password": "MemberPass123!", "registration_code": ""},
        )
        assert response.status_code == 403
        assert "disabled" in response.json()["detail"].lower()


def test_self_register_requires_code_when_enabled(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("CTOA_SELF_REGISTER_ENABLED", "true")
        monkeypatch.delenv("CTOA_SELF_REGISTER_CODE", raising=False)
        module = _load_app_module(monkeypatch, Path(tmp))
        client = TestClient(module.app)

        response = client.post(
            "/api/auth/register",
            json={"username": "member1", "password": "MemberPass123!", "registration_code": ""},
        )
        assert response.status_code == 503
        assert "not configured" in response.json()["detail"].lower()


def test_self_register_creates_member_role_only(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("CTOA_SELF_REGISTER_ENABLED", "true")
        monkeypatch.setenv("CTOA_SELF_REGISTER_CODE", "invite-123")
        module = _load_app_module(monkeypatch, Path(tmp))

        captured: dict[str, str] = {}

        def fake_create(username: str, password: str, role: str, created_by: str) -> dict:
            captured["username"] = username
            captured["role"] = role
            captured["created_by"] = created_by
            return {"username": username, "role": role, "created_by": created_by}

        monkeypatch.setattr(module, "_db_create_account", fake_create)

        client = TestClient(module.app)
        response = client.post(
            "/api/auth/register",
            json={"username": "member1", "password": "MemberPass123!", "registration_code": "invite-123"},
        )
        assert response.status_code == 200
        assert response.json()["ok"] is True
        assert captured["role"] == "member"
        assert captured["created_by"] == "self-register"


def test_login_cookie_is_secure_in_production(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("CTOA_ENV", "prod")
        monkeypatch.setenv("DB_PASSWORD", "dbpass123")
        monkeypatch.setenv("CTOA_CORS_ORIGINS", "https://console.example.com")
        module = _load_app_module(monkeypatch, Path(tmp))
        client = TestClient(module.app)

        response = client.post(
            "/api/auth/login",
            json={"username": "cto", "password": "ownerpass123"},
        )
        assert response.status_code == 200
        set_cookie = response.headers.get("set-cookie", "")
        assert "Secure" in set_cookie
