import importlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


SUBPROCESS_TIMEOUT_SECONDS = 30


def test_api_rejects_default_jwt_secret_in_production() -> None:
    env = os.environ.copy()
    env["CTOA_ENV"] = "production"
    env["CTOA_CORS_ORIGINS"] = "https://example.com"
    env.pop("CTOA_JWT_SECRET", None)

    proc = subprocess.run(
        [sys.executable, "-c", "import api.main"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
        timeout=SUBPROCESS_TIMEOUT_SECONDS,
    )

    assert proc.returncode != 0
    assert "missing or weak CTOA_JWT_SECRET" in (proc.stderr + proc.stdout)


def test_api_allows_non_default_jwt_secret_in_production() -> None:
    env = os.environ.copy()
    env["CTOA_ENV"] = "production"
    env["CTOA_CORS_ORIGINS"] = "https://example.com"
    env["CTOA_JWT_SECRET"] = "prod-secret-with-enough-entropy-for-test"

    proc = subprocess.run(
        [sys.executable, "-c", "import api.main; print(api.main.JWT_SECRET)"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
        timeout=SUBPROCESS_TIMEOUT_SECONDS,
    )

    assert proc.returncode == 0, proc.stderr
    assert "prod-secret-with-enough-entropy-for-test" in proc.stdout


def test_api_rejects_wildcard_cors_in_production() -> None:
    env = os.environ.copy()
    env["CTOA_ENV"] = "production"
    env["CTOA_JWT_SECRET"] = "prod-secret-with-enough-entropy-for-test"
    env["CTOA_CORS_ORIGINS"] = "*"

    proc = subprocess.run(
        [sys.executable, "-c", "import api.main"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
        timeout=SUBPROCESS_TIMEOUT_SECONDS,
    )

    assert proc.returncode != 0
    assert "CTOA_CORS_ORIGINS must be set" in (proc.stderr + proc.stdout)


def test_api_rejects_default_auth_account_seeding_in_production(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["CTOA_ENV"] = "production"
    env["CTOA_JWT_SECRET"] = "prod-secret-with-enough-entropy-for-test"
    env["CTOA_CORS_ORIGINS"] = "https://ctoa.example"
    env["CTOA_AUTH_STORE_FILE"] = str(tmp_path / "missing-auth-store.json")

    proc = subprocess.run(
        [sys.executable, "-c", "import api.main; api.main._load_auth_store()"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
        timeout=SUBPROCESS_TIMEOUT_SECONDS,
    )

    assert proc.returncode != 0
    assert "Refusing to seed default auth accounts" in (proc.stderr + proc.stdout)


def test_api_rejects_default_auth_account_seeding_without_explicit_opt_in(
    tmp_path: Path,
) -> None:
    env = os.environ.copy()
    env.pop("CTOA_ENV", None)
    env.pop("CTOA_ALLOW_SEED_ACCOUNTS", None)
    env["CTOA_AUTH_STORE_FILE"] = str(tmp_path / "missing-auth-store.json")

    proc = subprocess.run(
        [sys.executable, "-c", "import api.main; api.main._load_auth_store()"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
        timeout=SUBPROCESS_TIMEOUT_SECONDS,
    )

    assert proc.returncode != 0
    assert "Refusing to seed default auth accounts" in (proc.stderr + proc.stdout)


def test_api_allows_default_auth_account_seeding_only_with_explicit_opt_in(
    tmp_path: Path,
) -> None:
    auth_store = tmp_path / "auth-store.json"
    env = os.environ.copy()
    env.pop("CTOA_ENV", None)
    env["CTOA_ALLOW_SEED_ACCOUNTS"] = "true"
    env["CTOA_SEED_FAMATYYK_PASSWORD"] = "test-owner-seed-pass"
    env["CTOA_SEED_STRATEGOS_PASSWORD"] = "test-operator-seed-pass"
    env["CTOA_SEED_RECRUIT_PASSWORD"] = "test-member-seed-pass"
    env["CTOA_AUTH_STORE_FILE"] = str(auth_store)

    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            "import api.main; store = api.main._load_auth_store(); print(sorted(store['users']))",
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
        timeout=SUBPROCESS_TIMEOUT_SECONDS,
    )

    assert proc.returncode == 0, proc.stderr
    assert auth_store.exists()
    assert "famatyyk" in proc.stdout


def test_api_rejects_seed_account_opt_in_without_seed_passwords(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.pop("CTOA_ENV", None)
    env["CTOA_ALLOW_SEED_ACCOUNTS"] = "true"
    env["CTOA_AUTH_STORE_FILE"] = str(tmp_path / "auth-store.json")
    env.pop("CTOA_SEED_FAMATYYK_PASSWORD", None)
    env.pop("CTOA_SEED_STRATEGOS_PASSWORD", None)
    env.pop("CTOA_SEED_RECRUIT_PASSWORD", None)

    proc = subprocess.run(
        [sys.executable, "-c", "import api.main; api.main._load_auth_store()"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
        timeout=SUBPROCESS_TIMEOUT_SECONDS,
    )

    assert proc.returncode != 0
    assert "CTOA_SEED_FAMATYYK_PASSWORD must be set" in (proc.stderr + proc.stdout)


def test_public_seed_login_surfaces_do_not_embed_legacy_passwords() -> None:
    root = Path(__file__).resolve().parents[1]
    checked_paths = [
        root / "web" / "src" / "app" / "api" / "auth" / "seed-login" / "route.ts",
        root / "docs" / "site" / "script.js",
        root / "desktop_console" / "README.md",
        root / "scripts" / "ops" / "runtime_smoke_e2e_8001.py",
    ]

    for path in checked_paths:
        text = path.read_text(encoding="utf-8")
        assert "ctoa-owner" not in text, str(path)
        assert "ctoa-ops" not in text, str(path)
        assert "ctoa-community" not in text, str(path)
        assert "test-owner-pass" not in text, str(path)
        assert "test-operator-pass" not in text, str(path)


def test_db_password_is_not_documented_or_passed_in_cli_dsn() -> None:
    root = Path(__file__).resolve().parents[1]
    checked_paths = [
        root / "mobile_console" / "app.py",
        root / "docs" / "runbook-vps-agent-outputs.md",
        root / "scripts" / "ops" / "runtime_smoke_e2e_8001.py",
    ]

    forbidden_patterns = [
        "postgresql://ctoa:${DB_PASSWORD}",
        "postgresql://{os.getenv('DB_USER'",
        "PGPASSWORD={db_password}",
    ]
    for path in checked_paths:
        text = path.read_text(encoding="utf-8")
        for pattern in forbidden_patterns:
            assert pattern not in text, f"{pattern} in {path}"


def test_runtime_smoke_keeps_credentials_on_loopback_api() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "scripts" / "ops" / "runtime_smoke_e2e_8001.py").read_text(
        encoding="utf-8"
    )

    assert "require_loopback_http_url" in text
    assert "CTOA_RUNTIME_SMOKE_BASE" in text
    assert "require_http_url(base + path)" not in text
    assert "Authorization" in text


def test_api_release_evidence_sanitizes_paths_and_secrets(
    monkeypatch, tmp_path: Path
) -> None:
    evidence_file = tmp_path / "private" / "latest-approval.json"
    evidence_file.parent.mkdir(parents=True)
    repo_root = Path(__file__).resolve().parents[1]
    evidence_file.write_text(
        json.dumps(
            {
                "state": "READY",
                "live_client": r"C:\Users\zycie\AppData\Local\Solteria\client",
                "repo_path": str(repo_root / "runtime" / "release" / "latest.json"),
                "message": (
                    "ready token=secret-token-value "
                    "password=secret-password-value"
                ),
                "nested": {
                    "access_token": "json-token-value",
                    "note": 'Bearer abcdefghijklmnopqrstuvwxyz {"api_key":"json-api-key-value"}',
                },
            }
        ),
        encoding="utf-8",
    )

    import api.main as api_main

    module = importlib.reload(api_main)
    monkeypatch.setattr(module, "RELEASE_EVIDENCE_FILE", evidence_file)
    payload = module.release_evidence()
    serialized = json.dumps(payload)

    assert payload["ok"] is True
    assert payload["evidence_path"] == "[external]/latest-approval.json"
    assert payload["evidence"]["live_client"] == "[external]/client"
    assert payload["evidence"]["repo_path"] == "runtime/release/latest.json"
    assert "token=[redacted]" in serialized
    assert "password=[redacted]" in serialized
    assert '"access_token": "[redacted]"' in serialized
    assert "Bearer [redacted]" in serialized
    assert '{"api_key":"[redacted]"}' in payload["evidence"]["nested"]["note"]
    assert str(tmp_path) not in serialized
    assert "C:\\Users\\zycie" not in serialized
    assert "secret-token-value" not in serialized
    assert "secret-password-value" not in serialized
    assert "json-token-value" not in serialized
    assert "json-api-key-value" not in serialized


def test_api_release_evidence_rejects_oversized_file_without_leaking_content(
    monkeypatch, tmp_path: Path
) -> None:
    evidence_file = tmp_path / "private" / "oversized-approval.json"
    evidence_file.parent.mkdir(parents=True)
    evidence_file.write_text(
        json.dumps(
            {
                "state": "READY",
                "message": "token=secret-token-value",
                "padding": "x" * 2048,
            }
        ),
        encoding="utf-8",
    )

    import api.main as api_main

    module = importlib.reload(api_main)
    monkeypatch.setattr(module, "RELEASE_EVIDENCE_FILE", evidence_file)
    monkeypatch.setattr(module, "RELEASE_EVIDENCE_MAX_BYTES", 1024)
    payload = module.release_evidence()
    serialized = json.dumps(payload)

    assert payload["ok"] is False
    assert payload["state"] == "TOO_LARGE"
    assert payload["evidence_path"] == "[external]/oversized-approval.json"
    assert payload["message"] == "Release evidence file is too large to display safely."
    assert str(tmp_path) not in serialized
    assert "secret-token-value" not in serialized


def test_api_release_evidence_rejects_symlink_without_reading_target(
    monkeypatch, tmp_path: Path
) -> None:
    evidence_file = tmp_path / "private" / "latest-approval.json"
    evidence_file.parent.mkdir(parents=True)
    outside_file = tmp_path / "outside-approval.json"
    outside_file.write_text(
        json.dumps(
            {
                "state": "READY",
                "message": r"token=secret-token-value C:\Users\zycie\secret.txt",
            }
        ),
        encoding="utf-8",
    )
    try:
        evidence_file.symlink_to(outside_file)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    import api.main as api_main

    module = importlib.reload(api_main)
    monkeypatch.setattr(module, "RELEASE_EVIDENCE_FILE", evidence_file)
    payload = module.release_evidence()
    serialized = json.dumps(payload)

    assert payload["ok"] is False
    assert payload["state"] == "ERROR"
    assert payload["evidence_path"] == "[external]/latest-approval.json"
    assert payload["message"] == "Release evidence file could not be read safely."
    assert "secret-token-value" not in serialized
    assert r"C:\Users\zycie" not in serialized
    assert str(tmp_path) not in serialized


def test_mobile_console_requires_registration_code_when_self_register_enabled_in_production() -> (
    None
):
    env = os.environ.copy()
    env["CTOA_ENV"] = "production"
    env["CTOA_CORS_ORIGINS"] = "https://ctoa.example"
    env["CTOA_OWNER_PASSWORD"] = "ownerpass-strong"
    env["CTOA_OPERATOR_PASSWORD"] = "operpass-strong"
    env["CTOA_MOBILE_TOKEN"] = "mobile-token-strong"
    env["DB_PASSWORD"] = "db-password-strong"
    env["CTOA_SELF_REGISTER_ENABLED"] = "true"
    env.pop("CTOA_SELF_REGISTER_CODE", None)

    proc = subprocess.run(
        [sys.executable, "-c", "import mobile_console.app"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
        timeout=SUBPROCESS_TIMEOUT_SECONDS,
    )

    assert proc.returncode != 0
    assert "CTOA_SELF_REGISTER_CODE must be set" in (proc.stderr + proc.stdout)


def test_mobile_console_allows_production_start_with_self_register_disabled() -> None:
    env = os.environ.copy()
    env["CTOA_ENV"] = "production"
    env["CTOA_CORS_ORIGINS"] = "https://ctoa.example"
    env["CTOA_OWNER_PASSWORD"] = "ownerpass-strong"
    env["CTOA_OPERATOR_PASSWORD"] = "operpass-strong"
    env["CTOA_MOBILE_TOKEN"] = "mobile-token-strong"
    env["DB_PASSWORD"] = "db-password-strong"
    env["CTOA_SELF_REGISTER_ENABLED"] = "false"

    proc = subprocess.run(
        [sys.executable, "-c", "import mobile_console.app; print('ok')"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
        timeout=SUBPROCESS_TIMEOUT_SECONDS,
    )

    assert proc.returncode == 0, proc.stderr
    assert "ok" in proc.stdout


def test_mobile_console_login_sets_httponly_cookie_and_cookie_auth(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        monkeypatch.delenv("CTOA_ENV", raising=False)
        monkeypatch.setenv("CTOA_MOBILE_TOKEN", "legacy-token")
        monkeypatch.setenv("CTOA_OWNER_USER", "cto")
        monkeypatch.setenv("CTOA_OWNER_PASSWORD", "ownerpass")
        monkeypatch.setenv("CTOA_OPERATOR_USER", "ctoa-bot")
        monkeypatch.setenv("CTOA_OPERATOR_PASSWORD", "operpass")
        monkeypatch.setenv(
            "CTOA_ADMIN_SETTINGS_FILE", str(tmp_path / "admin-settings.json")
        )
        monkeypatch.setenv(
            "CTOA_IDEA_PARKING_FILE", str(tmp_path / "idea-parking.json")
        )
        monkeypatch.setenv("CTOA_PRODUCT_STATE_DIR", str(tmp_path / ".ctoa-local"))
        monkeypatch.setenv(
            "CTOA_PRODUCT_USER_CONFIG",
            str(tmp_path / ".ctoa-local" / "user-config.json"),
        )

        import mobile_console.app as mobile_app

        module = importlib.reload(mobile_app)
        client = TestClient(module.app)

        login = client.post(
            "/api/auth/login", json={"username": "cto", "password": "ownerpass"}
        )
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
