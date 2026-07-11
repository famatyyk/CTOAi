import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


SUBPROCESS_TIMEOUT_SECONDS = 30


def _load_api(
    monkeypatch,
    tmp_path: Path,
    *,
    production: bool = True,
    self_register: bool | None = None,
    code: str | None = None,
    rate_limit: bool = False,
    trust_proxy_headers: bool = False,
    read_rate_limit: int | None = None,
):
    monkeypatch.setenv("CTOA_AUTH_STORE_FILE", str(tmp_path / "auth-store.json"))
    monkeypatch.setenv("CTOA_AUDIT_LOG_FILE", str(tmp_path / "http-audit.jsonl"))
    monkeypatch.setenv("CTOA_RATE_LIMIT_ENABLED", "true" if rate_limit else "false")
    monkeypatch.setenv("CTOA_TRUST_PROXY_HEADERS", "true" if trust_proxy_headers else "false")
    if read_rate_limit is None:
        monkeypatch.delenv("CTOA_READ_RATE_LIMIT_PER_MIN", raising=False)
    else:
        monkeypatch.setenv("CTOA_READ_RATE_LIMIT_PER_MIN", str(read_rate_limit))
    if production:
        monkeypatch.setenv("CTOA_ENV", "production")
        monkeypatch.setenv("CTOA_JWT_SECRET", "prod-secret-with-enough-entropy-for-test")
        monkeypatch.setenv("CTOA_CORS_ORIGINS", "https://ctoa.example")
    else:
        monkeypatch.delenv("CTOA_ENV", raising=False)
        monkeypatch.delenv("CTOA_JWT_SECRET", raising=False)
        monkeypatch.setenv("CTOA_CORS_ORIGINS", "*")

    if self_register is None:
        monkeypatch.delenv("CTOA_API_SELF_REGISTER_ENABLED", raising=False)
    else:
        monkeypatch.setenv("CTOA_API_SELF_REGISTER_ENABLED", "true" if self_register else "false")
    if code is None:
        monkeypatch.delenv("CTOA_API_SELF_REGISTER_CODE", raising=False)
    else:
        monkeypatch.setenv("CTOA_API_SELF_REGISTER_CODE", code)

    import api.main as api_main

    return importlib.reload(api_main)


def _write_auth_store(module, path: Path, users: dict | None = None) -> None:
    payload = {"users": users or {}, "invites": [], "activity": []}
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_api_rejects_production_self_register_enabled_without_code(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["CTOA_ENV"] = "production"
    env["CTOA_JWT_SECRET"] = "prod-secret-with-enough-entropy-for-test"
    env["CTOA_CORS_ORIGINS"] = "https://ctoa.example"
    env["CTOA_API_SELF_REGISTER_ENABLED"] = "true"
    env.pop("CTOA_API_SELF_REGISTER_CODE", None)
    env["CTOA_AUTH_STORE_FILE"] = str(tmp_path / "auth-store.json")

    proc = subprocess.run(
        [sys.executable, "-c", "import api.main"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
        timeout=SUBPROCESS_TIMEOUT_SECONDS,
    )

    assert proc.returncode != 0
    assert "CTOA_API_SELF_REGISTER_CODE must be set" in (proc.stderr + proc.stdout)


def test_api_self_register_is_disabled_by_default_in_production(monkeypatch, tmp_path) -> None:
    module = _load_api(monkeypatch, tmp_path)
    auth_store = tmp_path / "auth-store.json"
    _write_auth_store(module, auth_store)
    client = TestClient(module.app)

    response = client.post(
        "/api/auth/register",
        json={"username": "public-member", "password": "member-pass-123", "role": "member"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Public self-registration is disabled"


def test_api_self_register_requires_matching_code_in_production(monkeypatch, tmp_path) -> None:
    module = _load_api(monkeypatch, tmp_path, self_register=True, code="invite-code")
    auth_store = tmp_path / "auth-store.json"
    _write_auth_store(module, auth_store)
    client = TestClient(module.app)

    rejected = client.post(
        "/api/auth/register",
        json={"username": "public-member", "password": "member-pass-123", "role": "member"},
    )
    assert rejected.status_code == 403
    assert rejected.json()["detail"] == "Invalid registration code"

    accepted = client.post(
        "/api/auth/register",
        json={
            "username": "public-member",
            "password": "member-pass-123",
            "role": "member",
            "registration_code": "invite-code",
        },
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["user"]["role"] == "member"


def test_api_public_register_cannot_create_owner_when_auth_store_is_empty(monkeypatch, tmp_path) -> None:
    module = _load_api(monkeypatch, tmp_path, production=False)
    _write_auth_store(module, tmp_path / "auth-store.json")
    client = TestClient(module.app)

    response = client.post(
        "/api/auth/register",
        json={"username": "first-owner", "password": "owner-pass-123", "role": "owner"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing bearer token"


def test_api_auth_store_rejects_oversized_existing_file(monkeypatch, tmp_path) -> None:
    module = _load_api(monkeypatch, tmp_path, production=False)
    auth_store = tmp_path / "auth-store.json"
    auth_store.write_text(
        '{"users":{},"padding":"' + ("x" * (module.AUTH_STORE_MAX_BYTES + 1)) + '"}',
        encoding="utf-8",
    )
    monkeypatch.setenv("CTOA_ALLOW_SEED_ACCOUNTS", "true")

    with pytest.raises(RuntimeError, match="Invalid CTOA_AUTH_STORE_FILE"):
        module._load_auth_store()

    assert "padding" in auth_store.read_text(encoding="utf-8")


def test_api_auth_store_rejects_symlinked_existing_file(monkeypatch, tmp_path) -> None:
    module = _load_api(monkeypatch, tmp_path, production=False)
    auth_store = tmp_path / "auth-store.json"
    outside_store = tmp_path / "outside-auth-store.json"
    outside_store.write_text('{"users":{"leak":{}}}\n', encoding="utf-8")
    try:
        auth_store.symlink_to(outside_store)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
    monkeypatch.setenv("CTOA_ALLOW_SEED_ACCOUNTS", "true")

    with pytest.raises(RuntimeError, match="Invalid CTOA_AUTH_STORE_FILE"):
        module._load_auth_store()

    assert outside_store.read_text(encoding="utf-8") == '{"users":{"leak":{}}}\n'


def test_api_owner_token_can_create_privileged_account(monkeypatch, tmp_path) -> None:
    module = _load_api(monkeypatch, tmp_path, production=False)
    auth_store = tmp_path / "auth-store.json"
    owner = {
        "owner": {
            "username": "owner",
            "display_name": "Owner",
            "role": "owner",
            "password_hash": module._hash_password("owner-pass-123"),
            "created_at": module._utc_now_iso(),
        }
    }
    _write_auth_store(module, auth_store, owner)
    token = module._issue_token({"username": "owner", "role": "owner"})
    client = TestClient(module.app)

    response = client.post(
        "/api/auth/register",
        headers={"Authorization": f"Bearer {token}"},
        json={"username": "new-operator", "password": "operator-pass-123", "role": "operator"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["user"]["role"] == "operator"


def test_api_http_audit_redacts_spoofed_header_secrets(monkeypatch, tmp_path) -> None:
    module = _load_api(monkeypatch, tmp_path, production=False)
    audit_log = tmp_path / "http-audit.jsonl"
    _write_auth_store(module, tmp_path / "auth-store.json")
    client = TestClient(module.app)

    response = client.get(
        "/api/status",
        headers={
            "User-Agent": (
                "probe token=secret-token-value password=secret-password-value "
                r'Bearer abcdefghijklmnopqrstuvwxyz {"api_key":"json-api-key-value"} C:\Users\zycie\secret.txt'
            ),
            "X-Forwarded-For": r"203.0.113.1 password=spoofed-password C:\Users\zycie\secret.txt",
        },
    )

    assert response.status_code == 200
    records = [
        json.loads(line)
        for line in audit_log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert records
    serialized = json.dumps(records[-1])

    assert records[-1]["path"] == "/api/status"
    assert "token=[redacted]" in serialized
    assert "password=[redacted]" in serialized
    assert "Bearer [redacted]" in serialized
    assert '"api_key":"[redacted]"' in records[-1]["ua"]
    assert "[external]/secret.txt" in serialized
    assert "secret-token-value" not in serialized
    assert "secret-password-value" not in serialized
    assert "spoofed-password" not in serialized
    assert "json-api-key-value" not in serialized
    assert "203.0.113.1" not in serialized
    assert r"C:\Users\zycie" not in serialized


def test_api_rate_limit_ignores_x_forwarded_for_without_proxy_trust(
    monkeypatch, tmp_path
) -> None:
    module = _load_api(
        monkeypatch,
        tmp_path,
        production=False,
        rate_limit=True,
        trust_proxy_headers=False,
        read_rate_limit=1,
    )
    _write_auth_store(module, tmp_path / "auth-store.json")
    client = TestClient(module.app)

    first = client.get("/api/status", headers={"X-Forwarded-For": "203.0.113.10"})
    second = client.get("/api/status", headers={"X-Forwarded-For": "203.0.113.11"})

    assert first.status_code == 200
    assert second.status_code == 429
    audit_text = (tmp_path / "http-audit.jsonl").read_text(encoding="utf-8")
    assert "203.0.113.10" not in audit_text
    assert "203.0.113.11" not in audit_text


def test_api_rate_limit_uses_x_forwarded_for_only_with_proxy_trust(
    monkeypatch, tmp_path
) -> None:
    module = _load_api(
        monkeypatch,
        tmp_path,
        production=False,
        rate_limit=True,
        trust_proxy_headers=True,
        read_rate_limit=1,
    )
    _write_auth_store(module, tmp_path / "auth-store.json")
    client = TestClient(module.app)

    first = client.get("/api/status", headers={"X-Forwarded-For": "203.0.113.10"})
    second = client.get("/api/status", headers={"X-Forwarded-For": "203.0.113.11"})
    third = client.get("/api/status", headers={"X-Forwarded-For": "203.0.113.10"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    audit_text = (tmp_path / "http-audit.jsonl").read_text(encoding="utf-8")
    assert "203.0.113.10" in audit_text
    assert "203.0.113.11" in audit_text
