import json
from pathlib import Path

import pytest

from desktop_console.api_client import ApiError, normalize_base_url
from desktop_console.app import DesktopSettings, _load_settings, _safe_normalize_url, _save_settings
from desktop_console.update_client import (
    GitHubReleaseUpdater,
    UpdateError,
    UpdateInfo,
    _select_windows_asset,
)

ROOT = Path(__file__).resolve().parents[1]


def test_desktop_api_url_allows_local_http_and_remote_https() -> None:
    assert normalize_base_url("127.0.0.1:8787/") == "http://127.0.0.1:8787"
    assert normalize_base_url("http://localhost:8787///") == "http://localhost:8787"
    assert normalize_base_url("https://api.example.test/base///") == "https://api.example.test/base"


@pytest.mark.parametrize(
    ("raw_url", "message"),
    [
        ("", "API base URL is required"),
        ("file:///tmp/ctoa.sock", "API base URL must be an absolute HTTP(S) URL"),
        ("https://user:secret-token@example.test", "API base URL must not include credentials"),
        ("https://api.example.test?token=secret-token", "API base URL must not include query strings or fragments"),
        ("https://api.example.test/#secret-token", "API base URL must not include query strings or fragments"),
        ("http://api.example.test", "API base URL must use https:// for non-local hosts"),
        ("http://192.168.1.50:8787", "API base URL must use https:// for non-local hosts"),
    ],
)
def test_desktop_api_url_rejects_unsafe_values_without_echoing_secret(raw_url: str, message: str) -> None:
    with pytest.raises(ApiError) as exc_info:
        normalize_base_url(raw_url)

    error_text = str(exc_info.value)
    assert error_text == message
    assert "secret-token" not in error_text


def test_desktop_settings_normalizer_drops_unsafe_urls() -> None:
    assert _safe_normalize_url("https://api.example.test/") == "https://api.example.test"
    assert _safe_normalize_url("https://user:secret-token@example.test") == ""
    assert _safe_normalize_url("http://api.example.test") == ""


def test_desktop_settings_save_uses_atomic_hidden_temp_paths(tmp_path, monkeypatch) -> None:
    settings_path = tmp_path / "desktop-settings.json"
    monkeypatch.setattr("desktop_console.app.SETTINGS_FILE", settings_path)

    _save_settings(DesktopSettings(username="operator"))

    payload = json.loads(settings_path.read_text(encoding="utf-8"))
    assert payload["username"] == "operator"
    assert not list(tmp_path.glob("*.tmp"))
    assert not list(tmp_path.glob(".*.tmp"))


def test_desktop_settings_save_replaces_symlink_without_touching_target(tmp_path, monkeypatch) -> None:
    outside_target = tmp_path / "outside-settings.json"
    outside_target.write_text('{"username": "outside"}\n', encoding="utf-8")
    settings_path = tmp_path / "desktop-settings.json"
    try:
        settings_path.symlink_to(outside_target)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    monkeypatch.setattr("desktop_console.app.SETTINGS_FILE", settings_path)

    _save_settings(DesktopSettings(username="operator"))

    assert json.loads(outside_target.read_text(encoding="utf-8"))["username"] == "outside"
    assert not settings_path.is_symlink()
    assert json.loads(settings_path.read_text(encoding="utf-8"))["username"] == "operator"


def test_desktop_settings_load_rejects_non_object_json(tmp_path, monkeypatch) -> None:
    settings_path = tmp_path / "desktop-settings.json"
    settings_path.write_text('["not", "settings"]', encoding="utf-8")
    monkeypatch.setattr("desktop_console.app.SETTINGS_FILE", settings_path)

    settings = _load_settings()

    assert settings.username == ""
    assert settings.base_url == "http://127.0.0.1:8787"


def test_desktop_settings_load_rejects_oversized_json(tmp_path, monkeypatch) -> None:
    import desktop_console.app as app_module

    settings_path = tmp_path / "desktop-settings.json"
    settings_path.write_text(
        '{"username":"' + ("x" * (app_module.SETTINGS_MAX_BYTES + 1)) + '"}',
        encoding="utf-8",
    )
    monkeypatch.setattr("desktop_console.app.SETTINGS_FILE", settings_path)

    settings = _load_settings()

    assert settings.username == ""
    assert settings.base_url == "http://127.0.0.1:8787"


def test_desktop_settings_load_rejects_symlink_without_reading_target(tmp_path, monkeypatch) -> None:
    outside_target = tmp_path / "outside-settings.json"
    outside_target.write_text('{"username": "outside"}\n', encoding="utf-8")
    settings_path = tmp_path / "desktop-settings.json"
    try:
        settings_path.symlink_to(outside_target)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    monkeypatch.setattr("desktop_console.app.SETTINGS_FILE", settings_path)

    settings = _load_settings()

    assert settings.username == ""


def test_desktop_settings_source_uses_atomic_hidden_temp_and_fsync() -> None:
    source = (ROOT / "desktop_console" / "app.py").read_text(encoding="utf-8")

    assert "SETTINGS_FILE.read_text" not in source
    assert "SETTINGS_FILE.write_text" not in source
    assert "_read_settings_payload" in source
    assert "uuid.uuid4().hex" in source
    assert "os.fsync(handle.fileno())" in source


def test_desktop_update_asset_selection_rejects_unsafe_names_and_urls() -> None:
    name, url = _select_windows_asset(
        [
            {
                "name": "..\\evil.exe",
                "browser_download_url": "https://github.com/famatyyk/CTOAi/releases/download/v1/evil.exe",
            },
            {
                "name": "CTOA-Desktop.exe",
                "browser_download_url": "http://github.com/famatyyk/CTOAi/releases/download/v1/CTOA-Desktop.exe",
            },
            {
                "name": "CTOA-Desktop-0.3.1.exe",
                "browser_download_url": "https://github.com/famatyyk/CTOAi/releases/download/v1/CTOA-Desktop-0.3.1.exe",
            },
        ]
    )

    assert name == "CTOA-Desktop-0.3.1.exe"
    assert url == "https://github.com/famatyyk/CTOAi/releases/download/v1/CTOA-Desktop-0.3.1.exe"


def test_desktop_update_download_rejects_unsafe_asset_before_network(tmp_path, monkeypatch) -> None:
    def fail_get(*_args, **_kwargs):
        raise AssertionError("unsafe update must be rejected before network")

    monkeypatch.setattr("desktop_console.update_client.requests.get", fail_get)
    updater = GitHubReleaseUpdater()
    update = UpdateInfo(
        current_version="0.3.0",
        latest_version="0.3.1",
        release_name="0.3.1",
        release_notes_url="https://github.com/famatyyk/CTOAi/releases/tag/v0.3.1",
        published_at="2026-07-06T00:00:00Z",
        api_url="https://api.github.com/repos/famatyyk/CTOAi/releases/latest",
        download_url="https://github.com/famatyyk/CTOAi/releases/download/v0.3.1/CTOA-Desktop.exe",
        asset_name="..\\CTOA-Desktop.exe",
    )

    with pytest.raises(UpdateError, match="asset name is unsafe"):
        updater.download_update(update, tmp_path)


def test_desktop_update_download_rejects_untrusted_url_before_network(tmp_path, monkeypatch) -> None:
    def fail_get(*_args, **_kwargs):
        raise AssertionError("untrusted update URL must be rejected before network")

    monkeypatch.setattr("desktop_console.update_client.requests.get", fail_get)
    updater = GitHubReleaseUpdater()
    update = UpdateInfo(
        current_version="0.3.0",
        latest_version="0.3.1",
        release_name="0.3.1",
        release_notes_url="",
        published_at="2026-07-06T00:00:00Z",
        api_url="https://api.github.com/repos/famatyyk/CTOAi/releases/latest",
        download_url="https://download.example.test/CTOA-Desktop.exe?token=secret-token",
        asset_name="CTOA-Desktop.exe",
    )

    with pytest.raises(UpdateError) as exc_info:
        updater.download_update(update, tmp_path)

    error_text = str(exc_info.value)
    assert "trusted GitHub HTTPS host" in error_text
    assert "secret-token" not in error_text


def test_desktop_update_download_accepts_signed_github_asset_redirect(tmp_path, monkeypatch) -> None:
    class FakeResponse:
        url = "https://objects.githubusercontent.com/github-production-release-asset/file.exe?X-Amz-Signature=secret-token"
        content = b"binary"

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def raise_for_status(self) -> None:
            return None

        def iter_content(self, chunk_size: int):
            assert chunk_size > 0
            yield b"binary"

    monkeypatch.setattr("desktop_console.update_client.requests.get", lambda *_args, **_kwargs: FakeResponse())
    updater = GitHubReleaseUpdater()
    update = UpdateInfo(
        current_version="0.3.0",
        latest_version="0.3.1",
        release_name="0.3.1",
        release_notes_url="",
        published_at="2026-07-06T00:00:00Z",
        api_url="https://api.github.com/repos/famatyyk/CTOAi/releases/latest",
        download_url="https://github.com/famatyyk/CTOAi/releases/download/v0.3.1/CTOA-Desktop.exe",
        asset_name="CTOA-Desktop.exe",
    )

    output = updater.download_update(update, tmp_path)

    assert output.name == "CTOA-Desktop.exe"
    assert output.read_bytes() == b"binary"


def test_desktop_update_download_rejects_untrusted_final_redirect_without_echoing_query(tmp_path, monkeypatch) -> None:
    class FakeResponse:
        url = "https://evil.example.test/CTOA-Desktop.exe?token=secret-token"
        content = b"binary"

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def raise_for_status(self) -> None:
            return None

        def iter_content(self, chunk_size: int):
            yield b"binary"

    monkeypatch.setattr("desktop_console.update_client.requests.get", lambda *_args, **_kwargs: FakeResponse())
    updater = GitHubReleaseUpdater()
    update = UpdateInfo(
        current_version="0.3.0",
        latest_version="0.3.1",
        release_name="0.3.1",
        release_notes_url="",
        published_at="2026-07-06T00:00:00Z",
        api_url="https://api.github.com/repos/famatyyk/CTOAi/releases/latest",
        download_url="https://github.com/famatyyk/CTOAi/releases/download/v0.3.1/CTOA-Desktop.exe",
        asset_name="CTOA-Desktop.exe",
    )

    with pytest.raises(UpdateError) as exc_info:
        updater.download_update(update, tmp_path)

    error_text = str(exc_info.value)
    assert "trusted GitHub HTTPS host" in error_text
    assert "secret-token" not in error_text
    assert not (tmp_path / "CTOA-Desktop.exe").exists()


def test_desktop_update_download_rejects_oversized_content_length_before_write(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("desktop_console.update_client.MAX_UPDATE_DOWNLOAD_BYTES", 8)

    class FakeResponse:
        url = "https://objects.githubusercontent.com/github-production-release-asset/file.exe?X-Amz-Signature=signature"
        headers = {"Content-Length": "9"}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def raise_for_status(self) -> None:
            return None

        def iter_content(self, chunk_size: int):
            raise AssertionError("oversized content length must be rejected before streaming")

    monkeypatch.setattr("desktop_console.update_client.requests.get", lambda *_args, **_kwargs: FakeResponse())
    updater = GitHubReleaseUpdater()
    update = UpdateInfo(
        current_version="0.3.0",
        latest_version="0.3.1",
        release_name="0.3.1",
        release_notes_url="",
        published_at="2026-07-06T00:00:00Z",
        api_url="https://api.github.com/repos/famatyyk/CTOAi/releases/latest",
        download_url="https://github.com/famatyyk/CTOAi/releases/download/v0.3.1/CTOA-Desktop.exe",
        asset_name="CTOA-Desktop.exe",
    )

    with pytest.raises(UpdateError, match="maximum allowed size"):
        updater.download_update(update, tmp_path)

    assert not (tmp_path / "CTOA-Desktop.exe").exists()
    assert not (tmp_path / "CTOA-Desktop.exe.download").exists()


def test_desktop_update_download_removes_partial_temp_file_when_stream_exceeds_limit(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("desktop_console.update_client.MAX_UPDATE_DOWNLOAD_BYTES", 8)

    class FakeResponse:
        url = "https://objects.githubusercontent.com/github-production-release-asset/file.exe?X-Amz-Signature=signature"
        headers = {}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def raise_for_status(self) -> None:
            return None

        def iter_content(self, chunk_size: int):
            yield b"a" * 8
            yield b"b"

    monkeypatch.setattr("desktop_console.update_client.requests.get", lambda *_args, **_kwargs: FakeResponse())
    updater = GitHubReleaseUpdater()
    update = UpdateInfo(
        current_version="0.3.0",
        latest_version="0.3.1",
        release_name="0.3.1",
        release_notes_url="",
        published_at="2026-07-06T00:00:00Z",
        api_url="https://api.github.com/repos/famatyyk/CTOAi/releases/latest",
        download_url="https://github.com/famatyyk/CTOAi/releases/download/v0.3.1/CTOA-Desktop.exe",
        asset_name="CTOA-Desktop.exe",
    )

    with pytest.raises(UpdateError, match="maximum allowed size"):
        updater.download_update(update, tmp_path)

    assert not (tmp_path / "CTOA-Desktop.exe").exists()
    assert not (tmp_path / "CTOA-Desktop.exe.download").exists()


def test_desktop_update_download_replaces_final_file_only_after_complete_stream(tmp_path, monkeypatch) -> None:
    existing = tmp_path / "CTOA-Desktop.exe"
    existing.write_bytes(b"old")

    class FakeResponse:
        url = "https://objects.githubusercontent.com/github-production-release-asset/file.exe?X-Amz-Signature=signature"
        headers = {"Content-Length": "3"}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def raise_for_status(self) -> None:
            return None

        def iter_content(self, chunk_size: int):
            yield b"new"

    monkeypatch.setattr("desktop_console.update_client.requests.get", lambda *_args, **_kwargs: FakeResponse())
    updater = GitHubReleaseUpdater()
    update = UpdateInfo(
        current_version="0.3.0",
        latest_version="0.3.1",
        release_name="0.3.1",
        release_notes_url="",
        published_at="2026-07-06T00:00:00Z",
        api_url="https://api.github.com/repos/famatyyk/CTOAi/releases/latest",
        download_url="https://github.com/famatyyk/CTOAi/releases/download/v0.3.1/CTOA-Desktop.exe",
        asset_name="CTOA-Desktop.exe",
    )

    output = updater.download_update(update, tmp_path)

    assert output == existing
    assert existing.read_bytes() == b"new"
    assert not (tmp_path / "CTOA-Desktop.exe.download").exists()


def test_desktop_update_check_sanitizes_release_notes_url(monkeypatch) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "tag_name": "v0.3.1",
                "name": "v0.3.1",
                "html_url": "https://evil.example.test/release?token=secret-token",
                "published_at": "2026-07-06T00:00:00Z",
                "assets": [
                    {
                        "name": "CTOA-Desktop-0.3.1.exe",
                        "browser_download_url": "https://github.com/famatyyk/CTOAi/releases/download/v0.3.1/CTOA-Desktop.exe",
                    }
                ],
            }

    monkeypatch.setattr("desktop_console.update_client.requests.get", lambda *_args, **_kwargs: FakeResponse())

    info = GitHubReleaseUpdater().check_for_update("0.3.0")

    assert info.release_notes_url == ""
    assert info.download_url == "https://github.com/famatyyk/CTOAi/releases/download/v0.3.1/CTOA-Desktop.exe"


def test_desktop_update_repo_must_be_owner_repo() -> None:
    with pytest.raises(UpdateError, match="owner/repo"):
        GitHubReleaseUpdater(repo="https://github.com/famatyyk/CTOAi")


def test_desktop_admin_console_is_preset_only() -> None:
    source = (ROOT / "desktop_console" / "app.py").read_text(encoding="utf-8")

    assert "Pick or type a command first" not in source
    assert "state=\"readonly\"" in source
    assert "allowed_presets" in source
    assert "This console only runs presets loaded from /api/presets." in source
