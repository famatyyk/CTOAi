import importlib
import json
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
    monkeypatch.setenv("CTOA_GENERATED_DIR", str(tmp_path / "generated"))
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


def test_latest_generated_requires_auth(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        client = TestClient(module.app)

        response = client.get("/api/agents/generated/latest")
        assert response.status_code == 401


def test_latest_generated_reads_manifest(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        generated_dir = tmp_path / "generated"
        manifest_dir = generated_dir / "manifests" / "20260320T010203Z"
        manifest_dir.mkdir(parents=True, exist_ok=True)

        manifest_payload = {
            "run_id": "20260320T010203Z",
            "generated": [
                {
                    "task_id": "SRV001-AUTO_HEAL",
                    "server_id": 1,
                    "template": "auto_heal",
                    "output_file": "auto_heal.lua",
                    "output_path": str(generated_dir / "mythibia" / "auto_heal.lua"),
                    "queued_at": "2026-03-20T01:02:00+00:00",
                    "generated_at": "2026-03-20T01:02:03+00:00",
                }
            ],
            "failed": [],
        }
        (manifest_dir / "manifest.json").write_text(json.dumps(manifest_payload), encoding="utf-8")
        (generated_dir / "manifests" / "latest.json").write_text(
            json.dumps(
                {
                    "run_id": "20260320T010203Z",
                    "manifest_path": str(manifest_dir / "manifest.json"),
                }
            ),
            encoding="utf-8",
        )

        module = _load_app_module(monkeypatch, tmp_path)
        client = TestClient(module.app)

        operator_token = _login_token(client, "ctoa-bot", "jakpod22")
        headers = {"Authorization": f"Bearer {operator_token}"}

        response = client.get("/api/agents/generated/latest?limit=5", headers=headers)
        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["source"] == "manifest"
        assert payload["run_id"] == "20260320T010203Z"
        assert payload["count"] == 1
        assert payload["items"][0]["task_id"] == "SRV001-AUTO_HEAL"


def test_commands_dictionary_requires_operator_auth(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        client = TestClient(module.app)

        response = client.get("/api/commands/dictionary")
        assert response.status_code == 401


def test_commands_dictionary_reads_valid_payload(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        dictionary_file = tmp_path / "command-dictionary.json"
        dictionary_file.write_text(
            json.dumps(
                {
                    "version": "9.9.9",
                    "source": "test-fixture",
                    "commands": [{"command": "help", "aliases": ["h"], "description": "Show help"}],
                }
            ),
            encoding="utf-8",
        )

        module = _load_app_module(monkeypatch, tmp_path)
        monkeypatch.setattr(module, "COMMAND_DICTIONARY_FILE", dictionary_file)
        client = TestClient(module.app)

        operator_token = _login_token(client, "ctoa-bot", "jakpod22")
        headers = {"Authorization": f"Bearer {operator_token}"}

        response = client.get("/api/commands/dictionary", headers=headers)
        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["version"] == "9.9.9"
        assert payload["source"] == "test-fixture"
        assert payload["count"] == 1
        assert payload["commands"][0]["command"] == "help"


def test_commands_dictionary_handles_missing_or_invalid_file(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        module = _load_app_module(monkeypatch, tmp_path)
        client = TestClient(module.app)

        operator_token = _login_token(client, "ctoa-bot", "jakpod22")
        headers = {"Authorization": f"Bearer {operator_token}"}

        missing_file = tmp_path / "missing-dictionary.json"
        monkeypatch.setattr(module, "COMMAND_DICTIONARY_FILE", missing_file)

        missing_response = client.get("/api/commands/dictionary", headers=headers)
        assert missing_response.status_code == 200
        missing_payload = missing_response.json()
        assert missing_payload["ok"] is True
        assert missing_payload["version"] == "unknown"
        assert missing_payload["source"] == "shared-cli-web"
        assert missing_payload["count"] == 0
        assert missing_payload["commands"] == []

        invalid_file = tmp_path / "invalid-dictionary.json"
        invalid_file.write_text("{ this is not json", encoding="utf-8")
        monkeypatch.setattr(module, "COMMAND_DICTIONARY_FILE", invalid_file)

        invalid_response = client.get("/api/commands/dictionary", headers=headers)
        assert invalid_response.status_code == 200
        invalid_payload = invalid_response.json()
        assert invalid_payload["ok"] is True
        assert invalid_payload["version"] == "unknown"
        assert invalid_payload["source"] == "shared-cli-web"
        assert invalid_payload["count"] == 0
        assert invalid_payload["commands"] == []
