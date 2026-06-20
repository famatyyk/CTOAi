import tempfile
from pathlib import Path
from urllib.error import URLError

from _pytest.monkeypatch import MonkeyPatch
from fastapi.testclient import TestClient


class _FakeResponse:
    def __init__(self, body: str, status: int = 200) -> None:
        self._body = body.encode("utf-8")
        self.status = status

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _load_app_module(monkeypatch: MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("CTOA_MOBILE_TOKEN", "test-mobile-token")
    monkeypatch.setenv("CTOA_OWNER_USER", "CTO")
    monkeypatch.setenv("CTOA_OWNER_PASSWORD", "ownerpass123")
    monkeypatch.setenv("CTOA_OPERATOR_USER", "ctoa-bot")
    monkeypatch.setenv("CTOA_OPERATOR_PASSWORD", "jakpod22")
    monkeypatch.setenv("CTOA_ADMIN_SETTINGS_FILE", str(tmp_path / "admin-settings.json"))
    monkeypatch.setenv("CTOA_IDEA_PARKING_FILE", str(tmp_path / "idea-parking.json"))
    monkeypatch.setenv("CTOA_GENERATED_DIR", str(tmp_path / "generated"))
    monkeypatch.setenv("CTOA_PRODUCT_STATE_DIR", str(tmp_path / ".ctoa-local"))
    monkeypatch.setenv("CTOA_PRODUCT_USER_CONFIG", str(tmp_path / ".ctoa-local" / "user-config.json"))
    monkeypatch.setenv("CTOA_PACKAGE_TIER", "studio")
    monkeypatch.setenv("CTOA_INTEL_API_EXPECTED", "true")

    import mobile_console.app as mobile_app

    return mobile_app


def _auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": "CTO", "password": "ownerpass123"})
    assert response.status_code == 200
    token = response.json().get("token")
    assert token
    return {"Authorization": f"Bearer {token}"}


def test_intel_status_proxy_success(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))

        def fake_urlopen(url: str, timeout: int = 5):
            assert url.endswith("/api/intel/status")
            return _FakeResponse('{"watcher":{"current_count":2},"ok":true}', status=200)

        monkeypatch.setattr(module, "urlopen", fake_urlopen)

        client = TestClient(module.app)
        headers = _auth_headers(client)
        response = client.get("/api/intel/status", headers=headers)

        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["status"] == 200
        assert payload["body"]["watcher"]["current_count"] == 2


def test_intel_status_proxy_unavailable(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))

        def fake_urlopen(_url: str, timeout: int = 5):
            raise URLError("connection refused")

        monkeypatch.setattr(module, "urlopen", fake_urlopen)

        client = TestClient(module.app)
        headers = _auth_headers(client)
        response = client.get("/api/intel/status", headers=headers)

        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is False
        assert "error" in payload


def test_intel_state_and_diff_proxy_success(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))

        def fake_urlopen(_url: str, timeout: int = 5):
            return _FakeResponse('{"ok":true}', status=200)

        monkeypatch.setattr(module, "urlopen", fake_urlopen)

        client = TestClient(module.app)
        headers = _auth_headers(client)

        state_response = client.get("/api/intel/state", headers=headers)
        diff_response = client.get("/api/intel/diff", headers=headers)

        assert state_response.status_code == 200
        assert diff_response.status_code == 200

        state_payload = state_response.json()
        diff_payload = diff_response.json()

        assert state_payload["ok"] is True
        assert diff_payload["ok"] is True
        assert state_payload["path"] == "/api/intel/state"
        assert diff_payload["path"] == "/api/intel/diff"


