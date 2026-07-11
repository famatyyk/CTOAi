import importlib
import json
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


def _make_dir_symlink(link_path: Path, target_path: Path) -> None:
    try:
        link_path.symlink_to(target_path, target_is_directory=True)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"directory symlinks unavailable: {exc}")


def test_latest_generated_requires_auth(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        client = TestClient(module.app)

        response = client.get("/api/agents/generated/latest")
        assert response.status_code == 401


def test_latest_generated_reads_manifest(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
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

        operator_token = _login_token(client, "ctoa-bot", "test-operator-pass")
        headers = {"Authorization": f"Bearer {operator_token}"}

        response = client.get("/api/agents/generated/latest?limit=5", headers=headers)
        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["source"] == "manifest"
        assert payload["run_id"] == "20260320T010203Z"
        assert payload["manifest_path"] == "generated/manifests/20260320T010203Z/manifest.json"
        assert str(tmp_path) not in payload["manifest_path"]
        assert payload["count"] == 1
        assert payload["items"][0]["task_id"] == "SRV001-AUTO_HEAL"
        assert payload["items"][0]["output_path"] == "generated/mythibia/auto_heal.lua"
        assert str(tmp_path) not in payload["items"][0]["output_path"]


def test_latest_generated_rejects_external_latest_manifest_pointer(
    monkeypatch: MonkeyPatch,
):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmp_path = Path(tmp)
        generated_dir = tmp_path / "generated"
        manifests_dir = generated_dir / "manifests"
        manifests_dir.mkdir(parents=True, exist_ok=True)
        outside_manifest = tmp_path / "outside" / "manifest.json"
        outside_manifest.parent.mkdir()
        outside_manifest.write_text(
            json.dumps(
                {
                    "run_id": "outside",
                    "generated": [
                        {
                            "task_id": "SHOULD-NOT-LEAK",
                            "output_file": "leak.lua",
                            "output_path": str(tmp_path / "private" / "leak.lua"),
                        }
                    ],
                    "failed": [],
                }
            ),
            encoding="utf-8",
        )
        (manifests_dir / "latest.json").write_text(
            json.dumps(
                {
                    "run_id": "missing-safe-run",
                    "manifest_path": str(outside_manifest),
                }
            ),
            encoding="utf-8",
        )

        module = _load_app_module(monkeypatch, tmp_path)
        client = TestClient(module.app)

        operator_token = _login_token(client, "ctoa-bot", "test-operator-pass")
        headers = {"Authorization": f"Bearer {operator_token}"}

        response = client.get("/api/agents/generated/latest?limit=5", headers=headers)
        assert response.status_code == 200
        payload = response.json()
        serialized = json.dumps(payload)

        assert payload["ok"] is True
        assert payload["source"] == "scan"
        assert payload["manifest_path"] is None
        assert "SHOULD-NOT-LEAK" not in serialized
        assert str(outside_manifest) not in serialized


def test_latest_generated_rejects_oversized_latest_pointer(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmp_path = Path(tmp)
        generated_dir = tmp_path / "generated"
        manifests_dir = generated_dir / "manifests"
        manifests_dir.mkdir(parents=True, exist_ok=True)
        output_dir = generated_dir / "mythibia"
        output_dir.mkdir()
        (output_dir / "fallback.lua").write_text("-- fallback\n", encoding="utf-8")
        (manifests_dir / "latest.json").write_text(
            '{"run_id":"SHOULD-NOT-LEAK","padding":"' + ("x" * 120) + '"}',
            encoding="utf-8",
        )

        module = _load_app_module(monkeypatch, tmp_path)
        monkeypatch.setattr(module, "GENERATED_MANIFEST_JSON_MAX_BYTES", 80)
        client = TestClient(module.app)

        operator_token = _login_token(client, "ctoa-bot", "test-operator-pass")
        response = client.get(
            "/api/agents/generated/latest?limit=5",
            headers={"Authorization": f"Bearer {operator_token}"},
        )

        assert response.status_code == 200
        payload = response.json()
        serialized = json.dumps(payload)
        assert payload["source"] == "scan"
        assert payload["manifest_path"] is None
        assert payload["items"][0]["output_file"] == "fallback.lua"
        assert "SHOULD-NOT-LEAK" not in serialized


def test_execution_manifest_reads_skip_symlinked_run_dir_escape(
    monkeypatch: MonkeyPatch,
):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmp_path = Path(tmp)
        generated_dir = tmp_path / "generated"
        manifests_dir = generated_dir / "manifests"
        safe_manifest = manifests_dir / "run-safe" / "manifest.json"
        safe_manifest.parent.mkdir(parents=True, exist_ok=True)
        safe_manifest.write_text(
            json.dumps(
                {
                    "run_id": "run-safe",
                    "generated": [{"task_id": "SAFE_TASK"}],
                    "failed": [],
                }
            ),
            encoding="utf-8",
        )

        outside_manifest = tmp_path / "outside-run" / "manifest.json"
        outside_manifest.parent.mkdir()
        outside_manifest.write_text(
            json.dumps(
                {
                    "run_id": "SHOULD-NOT-LEAK",
                    "generated": [],
                    "failed": [{"task_id": "LEAK_TASK"}],
                }
            ),
            encoding="utf-8",
        )
        _make_dir_symlink(manifests_dir / "run-evil-link", outside_manifest.parent)

        module = _load_app_module(monkeypatch, tmp_path)
        client = TestClient(module.app)

        operator_token = _login_token(client, "ctoa-bot", "test-operator-pass")
        headers = {"Authorization": f"Bearer {operator_token}"}

        trend_response = client.get(
            "/api/agents/execution/trend?limit_runs=10",
            headers=headers,
        )
        assert trend_response.status_code == 200
        trend_payload = trend_response.json()
        trend_serialized = json.dumps(trend_payload)

        assert trend_payload["summary"]["runs_count"] == 1
        assert trend_payload["summary"]["ready_runs"] == 1
        assert trend_payload["summary"]["failed_runs"] == 0
        assert trend_payload["runs"][0]["run_id"] == "run-safe"
        assert "SHOULD-NOT-LEAK" not in trend_serialized
        assert str(outside_manifest) not in trend_serialized

        metrics_response = client.get(
            "/api/agents/execution/metrics?limit_runs=10",
            headers=headers,
        )
        assert metrics_response.status_code == 200
        metrics_payload = metrics_response.json()
        metrics_serialized = json.dumps(metrics_payload)

        assert metrics_payload["by_reason_code"] == {"ARTIFACTS_READY": 1}
        assert metrics_payload["alert_active"] is False
        assert "SHOULD-NOT-LEAK" not in metrics_serialized
        assert str(outside_manifest) not in metrics_serialized


def test_execution_manifest_reads_skip_oversized_manifest(
    monkeypatch: MonkeyPatch,
):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmp_path = Path(tmp)
        generated_dir = tmp_path / "generated"
        manifests_dir = generated_dir / "manifests"
        safe_manifest = manifests_dir / "run-safe" / "manifest.json"
        safe_manifest.parent.mkdir(parents=True, exist_ok=True)
        safe_manifest.write_text(
            json.dumps(
                {
                    "run_id": "run-safe",
                    "generated": [{"task_id": "SAFE_TASK"}],
                    "failed": [],
                }
            ),
            encoding="utf-8",
        )
        oversized_manifest = manifests_dir / "run-oversized" / "manifest.json"
        oversized_manifest.parent.mkdir()
        oversized_manifest.write_text(
            '{"run_id":"SHOULD-NOT-LEAK","failed":[{"task_id":"LEAK"}],"padding":"'
            + ("x" * 120)
            + '"}',
            encoding="utf-8",
        )

        module = _load_app_module(monkeypatch, tmp_path)
        monkeypatch.setattr(module, "GENERATED_MANIFEST_JSON_MAX_BYTES", 80)
        client = TestClient(module.app)

        operator_token = _login_token(client, "ctoa-bot", "test-operator-pass")
        headers = {"Authorization": f"Bearer {operator_token}"}

        trend_response = client.get(
            "/api/agents/execution/trend?limit_runs=10",
            headers=headers,
        )
        assert trend_response.status_code == 200
        trend_payload = trend_response.json()
        trend_serialized = json.dumps(trend_payload)

        assert trend_payload["summary"]["runs_count"] == 1
        assert trend_payload["runs"][0]["run_id"] == "run-safe"
        assert "SHOULD-NOT-LEAK" not in trend_serialized

        metrics_response = client.get(
            "/api/agents/execution/metrics?limit_runs=10",
            headers=headers,
        )
        assert metrics_response.status_code == 200
        metrics_serialized = json.dumps(metrics_response.json())
        assert "SHOULD-NOT-LEAK" not in metrics_serialized


def test_latest_generated_scan_uses_public_artifact_paths(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmp_path = Path(tmp)
        output_dir = tmp_path / "generated" / "mythibia"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "auto_heal.lua").write_text("-- generated\n", encoding="utf-8")

        module = _load_app_module(monkeypatch, tmp_path)
        client = TestClient(module.app)

        operator_token = _login_token(client, "ctoa-bot", "test-operator-pass")
        headers = {"Authorization": f"Bearer {operator_token}"}

        response = client.get("/api/agents/generated/latest?limit=5", headers=headers)
        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["source"] == "scan"
        assert payload["count"] == 1
        assert payload["items"][0]["output_file"] == "auto_heal.lua"
        assert payload["items"][0]["output_path"] == "generated/mythibia/auto_heal.lua"
        assert str(tmp_path) not in payload["items"][0]["output_path"]


def test_public_artifact_path_redacts_unknown_absolute_paths(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmp_path = Path(tmp)
        module = _load_app_module(monkeypatch, tmp_path)

        private_path = tmp_path / "private-runtime" / "tokenized-output.lua"
        assert module._public_artifact_path(private_path) == "tokenized-output.lua"
        assert module._public_artifact_path("..\\private-runtime\\tokenized-output.lua") == "tokenized-output.lua"


def test_commands_dictionary_requires_operator_auth(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        client = TestClient(module.app)

        response = client.get("/api/commands/dictionary")
        assert response.status_code == 401


def test_commands_dictionary_reads_valid_payload(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
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

        operator_token = _login_token(client, "ctoa-bot", "test-operator-pass")
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
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmp_path = Path(tmp)
        module = _load_app_module(monkeypatch, tmp_path)
        client = TestClient(module.app)

        operator_token = _login_token(client, "ctoa-bot", "test-operator-pass")
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


def test_commands_dictionary_rejects_oversized_payload(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmp_path = Path(tmp)
        dictionary_file = tmp_path / "command-dictionary.json"
        dictionary_file.write_text(
            '{"version":"9.9.9","commands":[],"padding":"'
            + ("x" * 200_001)
            + '"}',
            encoding="utf-8",
        )

        module = _load_app_module(monkeypatch, tmp_path)
        monkeypatch.setattr(module, "COMMAND_DICTIONARY_FILE", dictionary_file)
        client = TestClient(module.app)

        operator_token = _login_token(client, "ctoa-bot", "test-operator-pass")
        response = client.get(
            "/api/commands/dictionary",
            headers={"Authorization": f"Bearer {operator_token}"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["version"] == "unknown"
        assert payload["count"] == 0
        assert "9.9.9" not in json.dumps(payload)


def test_commands_dictionary_rejects_symlinked_payload(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmp_path = Path(tmp)
        outside = tmp_path / "outside-dictionary.json"
        outside.write_text(
            json.dumps({"version": "leak", "commands": [{"command": "secret"}]}),
            encoding="utf-8",
        )
        dictionary_file = tmp_path / "command-dictionary.json"
        try:
            dictionary_file.symlink_to(outside)
        except OSError as exc:
            pytest.skip(f"symlink creation unavailable: {exc}")

        module = _load_app_module(monkeypatch, tmp_path)
        monkeypatch.setattr(module, "COMMAND_DICTIONARY_FILE", dictionary_file)
        client = TestClient(module.app)

        operator_token = _login_token(client, "ctoa-bot", "test-operator-pass")
        response = client.get(
            "/api/commands/dictionary",
            headers={"Authorization": f"Bearer {operator_token}"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["version"] == "unknown"
        assert payload["commands"] == []
        assert "secret" not in json.dumps(payload)
