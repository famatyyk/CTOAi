import importlib
import tempfile
from pathlib import Path

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
    monkeypatch.setenv("CTOA_TRAINING_REPORT_DIR", str(tmp_path / "training-reports"))
    monkeypatch.setenv("CTOA_GENERATED_DIR", str(tmp_path / "generated"))
    monkeypatch.setenv("CTOA_PRODUCT_STATE_DIR", str(tmp_path / ".ctoa-local"))
    monkeypatch.setenv("CTOA_PRODUCT_USER_CONFIG", str(tmp_path / ".ctoa-local" / "user-config.json"))
    monkeypatch.setenv("CTOA_PACKAGE_TIER", "studio")

    import mobile_console.app as mobile_app

    return importlib.reload(mobile_app)


def _login_token(client: TestClient, username: str = "ctoa-bot", password: str = "test-operator-pass") -> str:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return str(response.json()["token"])


def test_operator_file_metadata_uses_display_safe_paths(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmp_path = Path(tmp)
        module = _load_app_module(monkeypatch, tmp_path)
        client = TestClient(module.app)

        token = _login_token(client)
        headers = {"Authorization": f"Bearer {token}"}

        settings = client.get("/api/admin/settings", headers=headers)
        assert settings.status_code == 200
        settings_payload = settings.json()
        assert settings_payload["path"] == "admin-settings.json"
        assert str(tmp_path) not in settings_payload["path"]

        ideas = client.get("/api/ideas", headers=headers)
        assert ideas.status_code == 200
        ideas_payload = ideas.json()
        assert ideas_payload["path"] == "idea-parking.json"
        assert str(tmp_path) not in ideas_payload["path"]

        trainer = client.get("/api/agents/auto-trainer/latest", headers=headers)
        assert trainer.status_code == 200
        trainer_payload = trainer.json()
        assert trainer_payload["exists"] is False
        assert trainer_payload["path"] == "training-reports"
        assert str(tmp_path) not in trainer_payload["path"]


def test_auto_trainer_latest_reads_markdown_with_size_bound(
    monkeypatch: MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmp_path = Path(tmp)
        reports_dir = tmp_path / "training-reports"
        reports_dir.mkdir()
        (reports_dir / "latest.md").write_text(
            "A" * 50_010 + "SECRET-TAIL",
            encoding="utf-8",
        )
        module = _load_app_module(monkeypatch, tmp_path)
        client = TestClient(module.app)

        token = _login_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/agents/auto-trainer/latest", headers=headers)

        assert response.status_code == 200
        payload = response.json()
        assert payload["exists"] is True
        assert payload["markdown_truncated"] is True
        assert payload["markdown"].endswith("\n\n... [truncated]")
        assert "SECRET-TAIL" not in payload["markdown"]


def test_auto_trainer_latest_rejects_oversized_json_report(
    monkeypatch: MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmp_path = Path(tmp)
        reports_dir = tmp_path / "training-reports"
        reports_dir.mkdir()
        (reports_dir / "latest.md").write_text("# ok\n", encoding="utf-8")
        (reports_dir / "latest.json").write_text(
            '{"padding":"' + ("x" * 200_100) + '"}',
            encoding="utf-8",
        )
        module = _load_app_module(monkeypatch, tmp_path)
        client = TestClient(module.app)

        token = _login_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/agents/auto-trainer/latest", headers=headers)

        assert response.status_code == 200
        payload = response.json()
        assert payload["json"] == {
            "parse_error": "report_json_too_large",
            "max_bytes": module.AUTO_TRAINER_JSON_MAX_BYTES,
        }


def test_auto_trainer_latest_returns_stable_invalid_json_error(
    monkeypatch: MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmp_path = Path(tmp)
        reports_dir = tmp_path / "training-reports"
        reports_dir.mkdir()
        (reports_dir / "latest.md").write_text("# ok\n", encoding="utf-8")
        (reports_dir / "latest.json").write_text(
            "{ token=secret-token-value",
            encoding="utf-8",
        )
        module = _load_app_module(monkeypatch, tmp_path)
        client = TestClient(module.app)

        token = _login_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/agents/auto-trainer/latest", headers=headers)

        assert response.status_code == 200
        payload = response.json()
        assert payload["json"] == {"parse_error": "invalid_json"}
        assert "secret-token-value" not in str(payload)


def test_local_disk_probe_uses_display_safe_repo_path(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        module = _load_app_module(monkeypatch, Path(tmp))
        monkeypatch.setattr(module, "_command_exists", lambda name: False)

        result = module._disk_probe()
        payload = result["stdout"]

        assert result["code"] == 0
        assert '"path": "."' in payload
        assert str(module.ROOT) not in payload


def test_client_sync_response_uses_display_safe_paths(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmp_path = Path(tmp)
        module = _load_app_module(monkeypatch, tmp_path)
        source_dir = tmp_path / "generated" / "target"
        source_dir.mkdir(parents=True)
        (source_dir / "probe.lua").write_text("-- probe\n", encoding="utf-8")
        client_root = tmp_path / "external-client"

        monkeypatch.setenv("CTOA_CLIENT_SYNC_ENABLED", "true")
        monkeypatch.setenv("CTOA_CLIENT_SCRIPTS_DIR", str(client_root))
        monkeypatch.setenv("CTOA_CLIENT_TARGET_SLUG", "intel_target")
        monkeypatch.setenv("CTOA_CLIENT_AUTOLOADER_NAME", "ctoa_intel_autoload.lua")
        monkeypatch.delenv("CTOA_CLIENT_INIT_FILE", raising=False)

        result = module._sync_intel_to_client(source_dir)

        assert result["ok"] is True
        assert result["target_dir"] == "intel_target"
        assert result["autoload"] == "ctoa_intel_autoload.lua"
        assert str(tmp_path) not in str(result)


def test_client_sync_generic_errors_do_not_expose_local_paths(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmp_path = Path(tmp)
        module = _load_app_module(monkeypatch, tmp_path)
        source_dir = tmp_path / "generated" / "target"
        source_dir.mkdir(parents=True)
        (source_dir / "probe.lua").write_text("-- probe\n", encoding="utf-8")
        client_root = tmp_path / "external-client"

        monkeypatch.setenv("CTOA_CLIENT_SYNC_ENABLED", "true")
        monkeypatch.setenv("CTOA_CLIENT_SCRIPTS_DIR", str(client_root))
        monkeypatch.setenv("CTOA_CLIENT_TARGET_SLUG", "intel_target")
        monkeypatch.setenv("CTOA_CLIENT_AUTOLOADER_NAME", "ctoa_intel_autoload.lua")
        monkeypatch.setattr(
            module,
            "_atomic_write_bytes",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError(f"denied {client_root}")),
        )

        result = module._sync_intel_to_client(source_dir)

        assert result["ok"] is False
        assert result["detail"] == "Client sync failed"
        assert str(tmp_path) not in str(result)
