import importlib
import json
import logging
from pathlib import Path
from typing import Callable

import pytest


@pytest.fixture
def runtime_profile_loader(monkeypatch: pytest.MonkeyPatch) -> Callable[[Path], object]:
    import bot.config.runtime_profile as runtime_profile

    def _load(config_path: Path) -> object:
        monkeypatch.setenv("BOT_CLIENT_CONFIG_FILE", str(config_path))
        return importlib.reload(runtime_profile)

    yield _load

    monkeypatch.delenv("BOT_CLIENT_CONFIG_FILE", raising=False)
    importlib.reload(runtime_profile)


def test_invalid_runtime_profile_json_is_diagnostic_not_silent(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    runtime_profile_loader: Callable[[Path], object],
) -> None:
    config_path = tmp_path / "client_profiles.json"
    config_path.write_text("{not-json", encoding="utf-8")
    module = runtime_profile_loader(config_path)

    with caplog.at_level(logging.WARNING, logger="bot.config.runtime_profile"):
        assert module.get_str("BOT_FOLLOW_KEY", "F12") == "F12"

    assert module.last_config_error() == "invalid_json"
    assert "invalid JSON" in caplog.text


def test_runtime_profile_save_uses_atomic_temp_and_cleanup(
    tmp_path: Path,
    runtime_profile_loader: Callable[[Path], object],
) -> None:
    config_path = tmp_path / "client_profiles.json"
    module = runtime_profile_loader(config_path)

    module.save_profile_values("sandbox", {"BOT_FOLLOW_KEY": "F9"})

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload["profiles"]["sandbox"]["BOT_FOLLOW_KEY"] == "F9"
    assert list(tmp_path.glob(".*.tmp")) == []

    source = Path(module.__file__).read_text(encoding="utf-8")
    assert "except Exception" not in source
    assert "_CONFIG_PATH.write_text" not in source
    assert "uuid.uuid4().hex" in source
    assert "os.fsync(handle.fileno())" in source
