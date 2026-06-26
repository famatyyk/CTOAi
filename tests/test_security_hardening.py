import importlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient


def test_api_rejects_default_jwt_secret_in_production() -> None:
    env = os.environ.copy()
    env["CTOA_ENV"] = "production"
    env.pop("CTOA_JWT_SECRET", None)

    proc = subprocess.run(
        [sys.executable, "-c", "import api.main"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
        timeout=10,
    )

    assert proc.returncode != 0
    assert "CTOA_JWT_SECRET must be set" in (proc.stderr + proc.stdout)


def test_api_allows_non_default_jwt_secret_in_production() -> None:
    env = os.environ.copy()
    env["CTOA_ENV"] = "production"
    env["CTOA_JWT_SECRET"] = "prod-secret-with-enough-entropy-for-test"

    proc = subprocess.run(
        [sys.executable, "-c", "import api.main; print(api.main.JWT_SECRET)"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
        timeout=10,
    )

    assert proc.returncode == 0, proc.stderr
    assert "prod-secret-with-enough-entropy-for-test" in proc.stdout


def test_mobile_console_login_sets_httponly_cookie_and_cookie_auth(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        monkeypatch.delenv("CTOA_ENV", raising=False)
        monkeypatch.setenv("CTOA_MOBILE_TOKEN", "legacy-token")
        monkeypatch.setenv("CTOA_OWNER_USER", "cto")
        monkeypatch.setenv("CTOA_OWNER_PASSWORD", "ownerpass")
        monkeypatch.setenv("CTOA_OPERATOR_USER", "ctoa-bot")
        monkeypatch.setenv("CTOA_OPERATOR_PASSWORD", "operpass")
        monkeypatch.setenv("CTOA_ADMIN_SETTINGS_FILE", str(tmp_path / "admin-settings.json"))
        monkeypatch.setenv("CTOA_IDEA_PARKING_FILE", str(tmp_path / "idea-parking.json"))
        monkeypatch.setenv("CTOA_PRODUCT_STATE_DIR", str(tmp_path / ".ctoa-local"))
        monkeypatch.setenv("CTOA_PRODUCT_USER_CONFIG", str(tmp_path / ".ctoa-local" / "user-config.json"))

        import mobile_console.app as mobile_app

        module = importlib.reload(mobile_app)
        client = TestClient(module.app)

        login = client.post("/api/auth/login", json={"username": "cto", "password": "ownerpass"})
        assert login.status_code == 200, login.text
        set_cookie = login.headers.get("set-cookie", "")
        assert "ctoa_session=" in set_cookie
        assert "HttpOnly" in set_cookie
        csrf_token = str(login.json()["csrf_token"])
        assert csrf_token

        me = client.get("/api/auth/me")
        assert me.status_code == 200
        assert me.json()["username"] == "cto"
        assert me.json()["auth_mode"] == "session"
        assert me.json()["csrf_token"] == csrf_token

        rejected_logout = client.post("/api/auth/logout")
        assert rejected_logout.status_code == 403
        assert "CSRF" in rejected_logout.text

        logout = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf_token})
        assert logout.status_code == 200
        assert "ctoa_session=" in logout.headers.get("set-cookie", "")
