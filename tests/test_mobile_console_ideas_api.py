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


def test_ideas_requires_auth(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        client = TestClient(module.app)

        response = client.get("/api/ideas")
        assert response.status_code == 401


def test_ideas_crud_for_operator(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        client = TestClient(module.app)

        operator_token = _login_token(client, "ctoa-bot", "jakpod22")
        headers = {"Authorization": f"Bearer {operator_token}"}

        create = client.post("/api/ideas", headers=headers, json={"text": "Nowy pomysl"})
        assert create.status_code == 200
        created_payload = create.json()
        assert created_payload["ok"] is True
        assert created_payload["idea"]["text"] == "Nowy pomysl"
        idea_id = created_payload["idea"]["id"]

        listing = client.get("/api/ideas", headers=headers)
        assert listing.status_code == 200
        listing_payload = listing.json()
        assert listing_payload["count"] == 1
        assert listing_payload["ideas"][0]["id"] == idea_id

        deleted = client.delete(f"/api/ideas/{idea_id}", headers=headers)
        assert deleted.status_code == 200
        assert deleted.json()["deleted"] == 1

        missing = client.delete(f"/api/ideas/{idea_id}", headers=headers)
        assert missing.status_code == 404

        create_again = client.post("/api/ideas", headers=headers, json={"text": "Do wyczyszczenia"})
        assert create_again.status_code == 200

        cleared = client.delete("/api/ideas", headers=headers)
        assert cleared.status_code == 200
        assert cleared.json()["count"] == 0

        empty_listing = client.get("/api/ideas", headers=headers)
        assert empty_listing.status_code == 200
        assert empty_listing.json()["count"] == 0
