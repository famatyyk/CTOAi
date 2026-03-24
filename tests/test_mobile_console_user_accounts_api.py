"""Tests for /api/users/* endpoints (account registration and management).

All DB-access functions are monkeypatched to an in-memory store so no
real PostgreSQL connection is needed.  bcrypt hashes are generated at
rounds=4 for speed while keeping real cryptographic verification.
"""
import importlib
import tempfile
from pathlib import Path

import bcrypt as _bcrypt
from _pytest.monkeypatch import MonkeyPatch
from fastapi.testclient import TestClient


_FAST_ROUNDS = 4


def _make_hash(pw: str) -> str:
    return _bcrypt.hashpw(pw.encode(), _bcrypt.gensalt(rounds=_FAST_ROUNDS)).decode()


def _load_app_module(monkeypatch: MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("CTOA_MOBILE_TOKEN", "test-mobile-token")
    monkeypatch.setenv("CTOA_OWNER_USER", "cto")
    monkeypatch.setenv("CTOA_OWNER_PASSWORD", "ownerpass")
    monkeypatch.setenv("CTOA_OPERATOR_USER", "ctoa-bot")
    monkeypatch.setenv("CTOA_OPERATOR_PASSWORD", "operpass")
    monkeypatch.setenv("CTOA_ADMIN_SETTINGS_FILE", str(tmp_path / "admin-settings.json"))
    monkeypatch.setenv("CTOA_IDEA_PARKING_FILE", str(tmp_path / "idea-parking.json"))
    monkeypatch.setenv("CTOA_PRODUCT_STATE_DIR", str(tmp_path / ".ctoa-local"))
    monkeypatch.setenv("CTOA_PRODUCT_USER_CONFIG", str(tmp_path / ".ctoa-local" / "user-config.json"))
    monkeypatch.setenv("CTOA_PACKAGE_TIER", "studio")

    import mobile_console.app as mobile_app
    return importlib.reload(mobile_app)


def _patch_db(monkeypatch: MonkeyPatch, module) -> dict:
    """Replace all DB account helpers with an in-memory store.

    Returns the shared store dict so tests can inspect or pre-seed it.
    """
    store: dict[str, dict] = {}

    def fake_ensure() -> None:
        pass

    def fake_create(username: str, password: str, role: str, created_by: str) -> dict:
        if username in store:
            raise ValueError(f"Account '{username}' already exists")
        store[username] = {
            "username": username,
            "password_hash": _make_hash(password),
            "role": role,
            "active": True,
            "created_by": created_by,
            "created_at": None,
            "updated_at": None,
        }
        return {"username": username, "role": role, "created_by": created_by}

    def fake_get(username: str) -> dict | None:
        acc = store.get(username)
        return acc if (acc and acc.get("active")) else None

    def fake_list() -> list:
        return [
            {k: v for k, v in a.items() if k != "password_hash"}
            for a in store.values()
        ]

    def fake_update_pw(username: str, password: str) -> None:
        if username not in store:
            raise RuntimeError(f"Account not found: {username}")
        store[username]["password_hash"] = _make_hash(password)

    def fake_update_role(username: str, role: str) -> None:
        if username not in store:
            raise RuntimeError(f"Account not found: {username}")
        store[username]["role"] = role

    def fake_deactivate(username: str) -> None:
        if username not in store:
            raise RuntimeError(f"Account not found: {username}")
        store[username]["active"] = False

    monkeypatch.setattr(module, "_ensure_accounts_table", fake_ensure)
    monkeypatch.setattr(module, "_db_create_account", fake_create)
    monkeypatch.setattr(module, "_db_get_account", fake_get)
    monkeypatch.setattr(module, "_db_list_accounts", fake_list)
    monkeypatch.setattr(module, "_db_update_password", fake_update_pw)
    monkeypatch.setattr(module, "_db_update_role", fake_update_role)
    monkeypatch.setattr(module, "_db_deactivate_account", fake_deactivate)

    return store


def _login(client: TestClient, username: str, password: str) -> str:
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, f"Login failed ({r.status_code}): {r.text}"
    return str(r.json()["token"])


# ── Registration ─────────────────────────────────────────────────────────────

def test_register_requires_owner(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        _patch_db(monkeypatch, module)
        client = TestClient(module.app)

        op_token = _login(client, "ctoa-bot", "operpass")
        r = client.post(
            "/api/users/register",
            headers={"Authorization": f"Bearer {op_token}"},
            json={"username": "newguy", "password": "Pass1!", "role": "operator"},
        )
        assert r.status_code == 403


def test_register_creates_account(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        store = _patch_db(monkeypatch, module)
        client = TestClient(module.app)

        owner_token = _login(client, "cto", "ownerpass")
        r = client.post(
            "/api/users/register",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"username": "alice", "password": "AlicePass1!", "role": "operator"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        assert body["account"]["username"] == "alice"
        assert "alice" in store


def test_register_conflict_with_env_account(monkeypatch: MonkeyPatch):
    """Registering an env-reserved username must return 409."""
    with tempfile.TemporaryDirectory() as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        _patch_db(monkeypatch, module)
        client = TestClient(module.app)

        owner_token = _login(client, "cto", "ownerpass")
        r = client.post(
            "/api/users/register",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"username": "cto", "password": "whatever", "role": "operator"},
        )
        assert r.status_code == 409


def test_register_duplicate_rejected(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        _patch_db(monkeypatch, module)
        client = TestClient(module.app)

        owner_token = _login(client, "cto", "ownerpass")
        headers = {"Authorization": f"Bearer {owner_token}"}
        payload = {"username": "bob", "password": "BobPass1!", "role": "operator"}

        r1 = client.post("/api/users/register", headers=headers, json=payload)
        assert r1.status_code == 200

        r2 = client.post("/api/users/register", headers=headers, json=payload)
        assert r2.status_code == 409


def test_login_with_db_account(monkeypatch: MonkeyPatch):
    """Registering a DB account and then logging in with it must work."""
    with tempfile.TemporaryDirectory() as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        _patch_db(monkeypatch, module)
        client = TestClient(module.app)

        owner_token = _login(client, "cto", "ownerpass")
        client.post(
            "/api/users/register",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"username": "carol", "password": "CarolPass1!", "role": "operator"},
        )

        carol_token = _login(client, "carol", "CarolPass1!")
        me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {carol_token}"})
        assert me.status_code == 200
        assert me.json()["username"] == "carol"
        assert me.json()["role"] == "operator"


# ── Listing ──────────────────────────────────────────────────────────────────

def test_list_accounts_requires_owner(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        _patch_db(monkeypatch, module)
        client = TestClient(module.app)

        op_token = _login(client, "ctoa-bot", "operpass")
        r = client.get("/api/users", headers={"Authorization": f"Bearer {op_token}"})
        assert r.status_code == 403


def test_list_accounts_returns_env_and_db(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        _patch_db(monkeypatch, module)
        client = TestClient(module.app)

        owner_token = _login(client, "cto", "ownerpass")
        headers = {"Authorization": f"Bearer {owner_token}"}

        client.post(
            "/api/users/register",
            headers=headers,
            json={"username": "dave", "password": "DavePass1!", "role": "operator"},
        )

        r = client.get("/api/users", headers=headers)
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        usernames = [a["username"] for a in body["accounts"]]
        assert "dave" in usernames
        # Both env accounts must appear too.
        assert "cto" in usernames
        assert "ctoa-bot" in usernames


# ── Password change ───────────────────────────────────────────────────────────

def test_change_password_own_account(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        _patch_db(monkeypatch, module)
        client = TestClient(module.app)

        owner_token = _login(client, "cto", "ownerpass")
        client.post(
            "/api/users/register",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"username": "eve", "password": "EvePass1!", "role": "operator"},
        )

        eve_token = _login(client, "eve", "EvePass1!")
        r = client.put(
            "/api/users/eve/password",
            headers={"Authorization": f"Bearer {eve_token}"},
            json={"password": "EveNew1!"},
        )
        assert r.status_code == 200

        # Old password must be rejected.
        old = client.post("/api/auth/login", json={"username": "eve", "password": "EvePass1!"})
        assert old.status_code == 401

        # New password must succeed.
        new_token = _login(client, "eve", "EveNew1!")
        assert new_token


def test_change_password_other_requires_owner(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        store = _patch_db(monkeypatch, module)
        store["frank"] = {
            "username": "frank",
            "password_hash": _make_hash("FrankPass1!"),
            "role": "operator",
            "active": True,
            "created_by": "cto",
            "created_at": None,
            "updated_at": None,
        }
        store["grace"] = {
            "username": "grace",
            "password_hash": _make_hash("GracePass1!"),
            "role": "operator",
            "active": True,
            "created_by": "cto",
            "created_at": None,
            "updated_at": None,
        }
        client = TestClient(module.app)

        frank_token = _login(client, "frank", "FrankPass1!")
        r = client.put(
            "/api/users/grace/password",
            headers={"Authorization": f"Bearer {frank_token}"},
            json={"password": "HackedPass1!"},
        )
        assert r.status_code == 403


# ── Role change ───────────────────────────────────────────────────────────────

def test_change_role_requires_owner(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        store = _patch_db(monkeypatch, module)
        store["henry"] = {
            "username": "henry",
            "password_hash": _make_hash("HenryPass1!"),
            "role": "operator",
            "active": True,
            "created_by": "cto",
            "created_at": None,
            "updated_at": None,
        }
        client = TestClient(module.app)

        op_token = _login(client, "ctoa-bot", "operpass")
        r = client.put(
            "/api/users/henry/role",
            headers={"Authorization": f"Bearer {op_token}"},
            json={"role": "owner"},
        )
        assert r.status_code == 403


def test_change_role_promotes_account(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        store = _patch_db(monkeypatch, module)
        store["ivan"] = {
            "username": "ivan",
            "password_hash": _make_hash("IvanPass1!"),
            "role": "operator",
            "active": True,
            "created_by": "cto",
            "created_at": None,
            "updated_at": None,
        }
        client = TestClient(module.app)

        owner_token = _login(client, "cto", "ownerpass")
        r = client.put(
            "/api/users/ivan/role",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"role": "owner"},
        )
        assert r.status_code == 200
        assert store["ivan"]["role"] == "owner"


# ── Deactivation ─────────────────────────────────────────────────────────────

def test_deactivate_account(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        store = _patch_db(monkeypatch, module)
        store["jane"] = {
            "username": "jane",
            "password_hash": _make_hash("JanePass1!"),
            "role": "operator",
            "active": True,
            "created_by": "cto",
            "created_at": None,
            "updated_at": None,
        }
        client = TestClient(module.app)

        owner_token = _login(client, "cto", "ownerpass")
        r = client.delete(
            "/api/users/jane",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert r.status_code == 200
        assert store["jane"]["active"] is False

        # Login must fail after deactivation.
        login_r = client.post("/api/auth/login", json={"username": "jane", "password": "JanePass1!"})
        assert login_r.status_code == 401


def test_deactivate_self_fails(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        store = _patch_db(monkeypatch, module)
        store["kyle"] = {
            "username": "kyle",
            "password_hash": _make_hash("KylePass1!"),
            "role": "owner",
            "active": True,
            "created_by": "cto",
            "created_at": None,
            "updated_at": None,
        }
        client = TestClient(module.app)

        kyle_token = _login(client, "kyle", "KylePass1!")
        r = client.delete(
            "/api/users/kyle",
            headers={"Authorization": f"Bearer {kyle_token}"},
        )
        assert r.status_code == 400
