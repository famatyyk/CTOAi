import importlib
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "api"))


def _reload_api_module(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    allow_seed_accounts: bool = False,
    bootstrap_code: str | None = None,
    ctoa_env: str | None = None,
    env_name: str | None = None,
    cors_origins: str = "*",
    jwt_secret: str | None = "x" * 48,
):
    monkeypatch.setenv("CTOA_AUTH_STORE_FILE", str(tmp_path / "auth_store.json"))
    monkeypatch.setenv("CTOA_ALLOW_SEED_ACCOUNTS", "true" if allow_seed_accounts else "false")
    monkeypatch.setenv("CTOA_CORS_ORIGINS", cors_origins)

    if bootstrap_code is None:
        monkeypatch.delenv("CTOA_AUTH_BOOTSTRAP_CODE", raising=False)
    else:
        monkeypatch.setenv("CTOA_AUTH_BOOTSTRAP_CODE", bootstrap_code)

    if ctoa_env is None:
        monkeypatch.delenv("CTOA_ENV", raising=False)
    else:
        monkeypatch.setenv("CTOA_ENV", ctoa_env)

    if env_name is None:
        monkeypatch.delenv("ENV", raising=False)
    else:
        monkeypatch.setenv("ENV", env_name)

    if jwt_secret is None:
        monkeypatch.delenv("CTOA_JWT_SECRET", raising=False)
    else:
        monkeypatch.setenv("CTOA_JWT_SECRET", jwt_secret)

    import main as api_main

    return importlib.reload(api_main)


def test_bootstrap_owner_only_once(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    api_main = _reload_api_module(
        monkeypatch,
        tmp_path,
        bootstrap_code="boot-123",
    )
    client = TestClient(api_main.app)

    first = client.post(
        "/api/auth/bootstrap",
        json={"username": "root", "password": "OwnerPass123!", "bootstrap_code": "boot-123"},
    )
    assert first.status_code == 200
    assert first.json()["user"]["role"] == "owner"

    second = client.post(
        "/api/auth/bootstrap",
        json={"username": "root2", "password": "OwnerPass123!", "bootstrap_code": "boot-123"},
    )
    assert second.status_code == 409


def test_bootstrap_rejects_missing_or_invalid_code(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    misconfigured = _reload_api_module(monkeypatch, tmp_path, bootstrap_code=None)
    client = TestClient(misconfigured.app)
    no_code = client.post(
        "/api/auth/bootstrap",
        json={"username": "root", "password": "OwnerPass123!", "bootstrap_code": "anything"},
    )
    assert no_code.status_code == 503

    configured = _reload_api_module(monkeypatch, tmp_path, bootstrap_code="boot-123")
    client = TestClient(configured.app)
    bad_code = client.post(
        "/api/auth/bootstrap",
        json={"username": "root", "password": "OwnerPass123!", "bootstrap_code": "wrong"},
    )
    assert bad_code.status_code == 403


def test_seed_accounts_disabled_by_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    api_main = _reload_api_module(monkeypatch, tmp_path, allow_seed_accounts=False)
    client = TestClient(api_main.app)

    login = client.post(
        "/api/auth/login",
        json={"username": "famatyyk", "password": "ctoa-owner"},
    )
    assert login.status_code == 401

    stored = json.loads((tmp_path / "auth_store.json").read_text(encoding="utf-8"))
    assert stored["users"] == {}
    assert stored["activity"][0]["meta"]["seeded_users"] == 0


def test_seed_accounts_can_be_explicitly_enabled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    api_main = _reload_api_module(monkeypatch, tmp_path, allow_seed_accounts=True)
    client = TestClient(api_main.app)

    login = client.post(
        "/api/auth/login",
        json={"username": "famatyyk", "password": "ctoa-owner"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["role"] == "owner"


def test_public_register_cannot_create_privileged_user_without_owner(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    api_main = _reload_api_module(monkeypatch, tmp_path, bootstrap_code="boot-123")
    client = TestClient(api_main.app)

    denied = client.post(
        "/api/auth/register",
        json={"username": "user1", "password": "UserPass123!", "role": "operator"},
    )
    assert denied.status_code == 401

    boot = client.post(
        "/api/auth/bootstrap",
        json={"username": "owner", "password": "OwnerPass123!", "bootstrap_code": "boot-123"},
    )
    assert boot.status_code == 200
    owner_token = boot.json()["token"]

    owner_register = client.post(
        "/api/auth/register",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"username": "operator1", "password": "OperatorPass123!", "role": "operator"},
    )
    assert owner_register.status_code == 200
    assert owner_register.json()["user"]["role"] == "operator"

    member_register = client.post(
        "/api/auth/register",
        json={"username": "member1", "password": "MemberPass123!"},
    )
    assert member_register.status_code == 200
    assert member_register.json()["user"]["role"] == "member"


def test_prod_rejects_wildcard_cors(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    with pytest.raises(RuntimeError, match="wildcard CORS"):
        _reload_api_module(
            monkeypatch,
            tmp_path,
            ctoa_env="prod",
            cors_origins="*",
            jwt_secret="z" * 48,
        )


def test_prod_rejects_missing_or_weak_jwt_secret(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    with pytest.raises(RuntimeError, match="weak CTOA_JWT_SECRET"):
        _reload_api_module(
            monkeypatch,
            tmp_path,
            ctoa_env="prod",
            cors_origins="https://example.com",
            jwt_secret="change-me-ctoa-jwt-secret",
        )

    with pytest.raises(RuntimeError, match="weak CTOA_JWT_SECRET"):
        _reload_api_module(
            monkeypatch,
            tmp_path,
            ctoa_env="prod",
            cors_origins="https://example.com",
            jwt_secret=None,
        )


def test_non_prod_generates_ephemeral_jwt_when_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    api_main = _reload_api_module(
        monkeypatch,
        tmp_path,
        ctoa_env="dev",
        cors_origins="*",
        jwt_secret=None,
    )
    assert api_main.JWT_SECRET
    assert api_main._is_weak_secret(api_main.JWT_SECRET) is False
