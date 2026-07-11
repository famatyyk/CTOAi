import json
import importlib
import tempfile
from pathlib import Path

import pytest
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
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        client = TestClient(module.app)

        response = client.get("/api/ideas")
        assert response.status_code == 401


def test_ideas_crud_for_operator(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        client = TestClient(module.app)

        operator_token = _login_token(client, "ctoa-bot", "test-operator-pass")
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


def _make_file_symlink(link_path: Path, target_path: Path) -> None:
    try:
        link_path.symlink_to(target_path)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"file symlinks unavailable: {exc}")


def test_admin_settings_and_idea_parking_writes_are_atomic(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmp_path = Path(tmp)
        module = _load_app_module(monkeypatch, tmp_path)

        settings = module._write_admin_settings({"heroNote": "operator note"})
        ideas = module._write_idea_parking([{"text": "persist me", "author": "cto"}])

        settings_payload = json.loads(module.ADMIN_SETTINGS_FILE.read_text(encoding="utf-8"))
        ideas_payload = json.loads(module.IDEA_PARKING_FILE.read_text(encoding="utf-8"))

        assert settings["heroNote"] == "operator note"
        assert settings_payload["heroNote"] == "operator note"
        assert ideas[0]["text"] == "persist me"
        assert ideas_payload[0]["text"] == "persist me"
        assert not list(tmp_path.glob("*.tmp"))
        assert not list(tmp_path.glob(".*.tmp"))


def test_admin_settings_write_replaces_symlink_without_touching_target(
    monkeypatch: MonkeyPatch,
):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmp_path = Path(tmp)
        module = _load_app_module(monkeypatch, tmp_path)
        outside = tmp_path / "outside-admin-settings.json"
        outside.write_text('{"heroNote": "outside"}\n', encoding="utf-8")
        _make_file_symlink(module.ADMIN_SETTINGS_FILE, outside)

        module._write_admin_settings({"heroNote": "operator note"})

        assert json.loads(outside.read_text(encoding="utf-8"))["heroNote"] == "outside"
        assert not module.ADMIN_SETTINGS_FILE.is_symlink()
        assert (
            json.loads(module.ADMIN_SETTINGS_FILE.read_text(encoding="utf-8"))["heroNote"]
            == "operator note"
        )


def test_local_mobile_state_reads_are_bounded(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmp_path = Path(tmp)
        module = _load_app_module(monkeypatch, tmp_path)
        module.ADMIN_SETTINGS_FILE.write_text(
            '{"heroNote":"' + ("x" * (module.ADMIN_SETTINGS_MAX_BYTES + 1)) + '"}',
            encoding="utf-8",
        )
        module.IDEA_PARKING_FILE.write_text(
            '[{"text":"' + ("x" * (module.IDEA_PARKING_MAX_BYTES + 1)) + '"}]',
            encoding="utf-8",
        )

        assert module._read_admin_settings() == module._default_admin_settings()
        assert module._read_idea_parking() == []


def test_mobile_local_state_source_uses_atomic_bounded_json_helpers() -> None:
    source = (Path(__file__).resolve().parents[1] / "mobile_console" / "app.py").read_text(
        encoding="utf-8"
    )

    assert "ADMIN_SETTINGS_FILE.write_text" not in source
    assert "IDEA_PARKING_FILE.write_text" not in source
    assert "_read_local_json_bounded" in source
    assert "uuid.uuid4().hex" in source
    assert "os.fsync(handle.fileno())" in source
