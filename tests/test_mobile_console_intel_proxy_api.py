import tempfile
from pathlib import Path
from urllib.error import URLError

import pytest
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
    monkeypatch.setenv("CTOA_OWNER_PASSWORD", "test-owner-pass")
    monkeypatch.setenv("CTOA_OPERATOR_USER", "ctoa-bot")
    monkeypatch.setenv("CTOA_OPERATOR_PASSWORD", "test-operator-pass")
    monkeypatch.setenv(
        "CTOA_ADMIN_SETTINGS_FILE", str(tmp_path / "admin-settings.json")
    )
    monkeypatch.setenv("CTOA_IDEA_PARKING_FILE", str(tmp_path / "idea-parking.json"))
    monkeypatch.setenv("CTOA_GENERATED_DIR", str(tmp_path / "generated"))
    monkeypatch.setenv("CTOA_PRODUCT_STATE_DIR", str(tmp_path / ".ctoa-local"))
    monkeypatch.setenv(
        "CTOA_PRODUCT_USER_CONFIG", str(tmp_path / ".ctoa-local" / "user-config.json")
    )
    monkeypatch.setenv("CTOA_PACKAGE_TIER", "studio")
    monkeypatch.setenv("CTOA_INTEL_API_EXPECTED", "true")

    import mobile_console.app as mobile_app

    return mobile_app


def _auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/auth/login", json={"username": "CTO", "password": "test-owner-pass"}
    )
    assert response.status_code == 200
    token = response.json().get("token")
    assert token
    return {"Authorization": f"Bearer {token}"}


def test_intel_status_proxy_success(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))

        def fake_urlopen(url: str, timeout: int = 5):
            assert url.endswith("/api/intel/status")
            return _FakeResponse(
                '{"watcher":{"current_count":2},"ok":true}', status=200
            )

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
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
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


def test_runtime_proxy_errors_redact_secret_bearing_exception_text(
    monkeypatch: MonkeyPatch,
):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))

        def fake_urlopen(_url: str, timeout: int = 5):
            raise URLError(
                "connect failed token=secret-token-value "
                "password=secret-password-value"
            )

        monkeypatch.setattr(module, "urlopen", fake_urlopen)

        intel_payload = module._intel_api_proxy()
        ctoa_payload = module._ctoa_api_proxy()
        serialized = str({"intel": intel_payload, "ctoa": ctoa_payload})

        assert intel_payload["ok"] is False
        assert ctoa_payload["ok"] is False
        assert "secret-token-value" not in serialized
        assert "secret-password-value" not in serialized
        assert "token=[redacted]" in serialized
        assert "password=[redacted]" in serialized


def test_intel_status_proxy_rejects_unsafe_runtime_base_url(
    monkeypatch: MonkeyPatch,
):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        monkeypatch.setenv(
            "CTOA_INTEL_API_BASE_URL",
            "http://user:secret-token@127.0.0.1:8890?token=secret-token",
        )

        def fake_urlopen(_url: str, timeout: int = 5):
            raise AssertionError("unsafe Intel API base URL must not be fetched")

        monkeypatch.setattr(module, "urlopen", fake_urlopen)

        client = TestClient(module.app)
        headers = _auth_headers(client)
        response = client.get("/api/intel/status", headers=headers)

        assert response.status_code == 200
        payload = response.json()
        serialized = str(payload)
        assert payload["ok"] is False
        assert payload["url"] == "[invalid-local-runtime-api]"
        assert "credentials, query, or fragment" in payload["error"]
        assert "secret-token" not in serialized
        assert "user:" not in serialized


def test_release_evidence_proxy_rejects_remote_runtime_api_base_url(
    monkeypatch: MonkeyPatch,
):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        monkeypatch.setenv("CTOA_API_BASE_URL", "https://api.example.com?token=secret-token")

        def fake_urlopen(_url: str, timeout: int = 5):
            raise AssertionError("unsafe CTOA API base URL must not be fetched")

        monkeypatch.setattr(module, "urlopen", fake_urlopen)

        client = TestClient(module.app)
        headers = _auth_headers(client)
        response = client.get("/api/dashboard/release-evidence", headers=headers)

        assert response.status_code == 200
        payload = response.json()
        serialized = str(payload)
        assert payload["ok"] is False
        assert payload["status"]["url"] == "[invalid-local-runtime-api]"
        assert payload["release_evidence"]["url"] == "[invalid-local-runtime-api]"
        assert "credentials, query, or fragment" in payload["status"]["error"]
        assert "secret-token" not in serialized
        assert "api.example.com" not in serialized


@pytest.mark.parametrize(
    ("path", "error"),
    [
        (
            "https://evil.example.test/api/intel/status?token=secret-token",
            "relative API path",
        ),
        ("/api/intel/status?token=secret-token", "query or fragment"),
        ("/api/intel/status#token", "query or fragment"),
        ("/api/%2e%2e/status", "traversal"),
        ("/api/intel/%2fstatus", "encoded separators"),
        ("/api//status", "empty segments"),
        ("/admin/status", "under /api"),
        ("/api\\status", "backslashes"),
    ],
)
def test_runtime_proxy_rejects_unsafe_proxy_paths_before_urlopen(
    monkeypatch: MonkeyPatch,
    path: str,
    error: str,
):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))

        def fail_urlopen(_url: str, timeout: int = 5):
            raise AssertionError("unsafe proxy path must not be fetched")

        monkeypatch.setattr(module, "urlopen", fail_urlopen)

        intel_payload = module._intel_api_proxy(path)
        ctoa_payload = module._ctoa_api_proxy(path)
        serialized = str({"intel": intel_payload, "ctoa": ctoa_payload})

        assert intel_payload["ok"] is False
        assert ctoa_payload["ok"] is False
        assert intel_payload["path"] == "[invalid-local-runtime-path]"
        assert ctoa_payload["path"] == "[invalid-local-runtime-path]"
        assert error in intel_payload["error"]
        assert error in ctoa_payload["error"]
        assert "secret-token" not in serialized
        assert "evil.example.test" not in serialized


def test_intel_state_and_diff_proxy_success(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
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
