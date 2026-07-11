import importlib
from pathlib import Path

import pytest


def _load_app(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("CTOA_ENV", raising=False)
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


def _source_dir(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    source.mkdir()
    (source / "auto_heal.lua").write_text("print('heal')\n", encoding="utf-8")
    return source


def test_client_sync_keeps_writes_inside_configured_client_root(monkeypatch, tmp_path) -> None:
    module = _load_app(monkeypatch, tmp_path)
    source = _source_dir(tmp_path)
    client_root = tmp_path / "client" / "scripts"
    init_file = client_root / "init.lua"
    init_file.parent.mkdir(parents=True)
    init_file.write_text("-- init\n", encoding="utf-8")

    monkeypatch.setenv("CTOA_CLIENT_SYNC_ENABLED", "true")
    monkeypatch.setenv("CTOA_CLIENT_SCRIPTS_DIR", str(client_root))
    monkeypatch.setenv("CTOA_CLIENT_TARGET_SLUG", "intel_target")
    monkeypatch.setenv("CTOA_CLIENT_AUTOLOADER_NAME", "ctoa_intel_autoload.lua")
    monkeypatch.setenv("CTOA_CLIENT_INIT_FILE", str(init_file))

    result = module._sync_intel_to_client(source)

    assert result["ok"] is True
    target_file = client_root / "intel_target" / "auto_heal.lua"
    autoload_file = client_root / "ctoa_intel_autoload.lua"
    assert target_file.exists()
    assert autoload_file.exists()
    assert 'dofile(BASE .. "/auto_heal.lua")' in autoload_file.read_text(encoding="utf-8")
    assert f'dofile("{autoload_file.as_posix()}")' in init_file.read_text(encoding="utf-8")


def test_client_sync_rejects_target_slug_path_traversal_before_writing(monkeypatch, tmp_path) -> None:
    module = _load_app(monkeypatch, tmp_path)
    source = _source_dir(tmp_path)
    client_root = tmp_path / "client" / "scripts"

    monkeypatch.setenv("CTOA_CLIENT_SYNC_ENABLED", "true")
    monkeypatch.setenv("CTOA_CLIENT_SCRIPTS_DIR", str(client_root))
    monkeypatch.setenv("CTOA_CLIENT_TARGET_SLUG", "../outside")

    result = module._sync_intel_to_client(source)

    assert result["ok"] is False
    assert "CTOA_CLIENT_TARGET_SLUG must stay inside CTOA_CLIENT_SCRIPTS_DIR" in result["detail"]
    assert not (tmp_path / "client" / "outside").exists()
    assert not client_root.exists()


def test_client_sync_rejects_autoloader_path_traversal_before_writing(monkeypatch, tmp_path) -> None:
    module = _load_app(monkeypatch, tmp_path)
    source = _source_dir(tmp_path)
    client_root = tmp_path / "client" / "scripts"

    monkeypatch.setenv("CTOA_CLIENT_SYNC_ENABLED", "true")
    monkeypatch.setenv("CTOA_CLIENT_SCRIPTS_DIR", str(client_root))
    monkeypatch.setenv("CTOA_CLIENT_TARGET_SLUG", "intel_target")
    monkeypatch.setenv("CTOA_CLIENT_AUTOLOADER_NAME", "../outside.lua")

    result = module._sync_intel_to_client(source)

    assert result["ok"] is False
    assert "CTOA_CLIENT_AUTOLOADER_NAME must stay inside CTOA_CLIENT_SCRIPTS_DIR" in result["detail"]
    assert not (tmp_path / "client" / "outside.lua").exists()
    assert not (client_root / "intel_target").exists()


def test_client_sync_rejects_init_file_path_traversal_before_writing(monkeypatch, tmp_path) -> None:
    module = _load_app(monkeypatch, tmp_path)
    source = _source_dir(tmp_path)
    client_root = tmp_path / "client" / "scripts"

    monkeypatch.setenv("CTOA_CLIENT_SYNC_ENABLED", "true")
    monkeypatch.setenv("CTOA_CLIENT_SCRIPTS_DIR", str(client_root))
    monkeypatch.setenv("CTOA_CLIENT_TARGET_SLUG", "intel_target")
    monkeypatch.setenv("CTOA_CLIENT_INIT_FILE", "../init.lua")

    result = module._sync_intel_to_client(source)

    assert result["ok"] is False
    assert "CTOA_CLIENT_INIT_FILE must stay inside CTOA_CLIENT_SCRIPTS_DIR" in result["detail"]
    assert not (tmp_path / "client" / "init.lua").exists()
    assert not (client_root / "intel_target").exists()


def test_client_sync_rejects_oversized_init_file_before_writing(monkeypatch, tmp_path) -> None:
    module = _load_app(monkeypatch, tmp_path)
    source = _source_dir(tmp_path)
    client_root = tmp_path / "client" / "scripts"
    init_file = client_root / "init.lua"
    init_file.parent.mkdir(parents=True)
    init_file.write_text("x" * (module.CLIENT_SYNC_INIT_MAX_BYTES + 1), encoding="utf-8")

    monkeypatch.setenv("CTOA_CLIENT_SYNC_ENABLED", "true")
    monkeypatch.setenv("CTOA_CLIENT_SCRIPTS_DIR", str(client_root))
    monkeypatch.setenv("CTOA_CLIENT_TARGET_SLUG", "intel_target")
    monkeypatch.setenv("CTOA_CLIENT_AUTOLOADER_NAME", "ctoa_intel_autoload.lua")
    monkeypatch.setenv("CTOA_CLIENT_INIT_FILE", str(init_file))

    result = module._sync_intel_to_client(source)

    assert result["ok"] is False
    assert result["detail"] == "CTOA_CLIENT_INIT_FILE is too large"
    assert not (client_root / "intel_target").exists()
    assert not (client_root / "ctoa_intel_autoload.lua").exists()


def test_client_sync_rejects_symlinked_init_file_before_writing(monkeypatch, tmp_path) -> None:
    module = _load_app(monkeypatch, tmp_path)
    source = _source_dir(tmp_path)
    client_root = tmp_path / "client" / "scripts"
    init_file = client_root / "init.lua"
    outside_init = tmp_path / "outside-init.lua"
    init_file.parent.mkdir(parents=True)
    outside_init.write_text("-- outside\n", encoding="utf-8")
    try:
        init_file.symlink_to(outside_init)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    monkeypatch.setenv("CTOA_CLIENT_SYNC_ENABLED", "true")
    monkeypatch.setenv("CTOA_CLIENT_SCRIPTS_DIR", str(client_root))
    monkeypatch.setenv("CTOA_CLIENT_TARGET_SLUG", "intel_target")
    monkeypatch.setenv("CTOA_CLIENT_AUTOLOADER_NAME", "ctoa_intel_autoload.lua")
    monkeypatch.setenv("CTOA_CLIENT_INIT_FILE", str(init_file))

    result = module._sync_intel_to_client(source)

    assert result["ok"] is False
    assert result["detail"] == "CTOA_CLIENT_INIT_FILE must not be a symlink"
    assert outside_init.read_text(encoding="utf-8") == "-- outside\n"
    assert not (client_root / "intel_target").exists()
    assert not (client_root / "ctoa_intel_autoload.lua").exists()


def test_client_sync_rejects_symlinked_lua_source_before_writing(monkeypatch, tmp_path) -> None:
    module = _load_app(monkeypatch, tmp_path)
    source = tmp_path / "source"
    source.mkdir()
    outside_source = tmp_path / "outside-source.lua"
    outside_source.write_text("print('secret')\n", encoding="utf-8")
    try:
        (source / "auto_heal.lua").symlink_to(outside_source)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
    client_root = tmp_path / "client" / "scripts"

    monkeypatch.setenv("CTOA_CLIENT_SYNC_ENABLED", "true")
    monkeypatch.setenv("CTOA_CLIENT_SCRIPTS_DIR", str(client_root))
    monkeypatch.setenv("CTOA_CLIENT_TARGET_SLUG", "intel_target")

    result = module._sync_intel_to_client(source)

    assert result["ok"] is False
    assert result["detail"] == "Client sync source Lua must not be a symlink"
    assert not client_root.exists()


def test_client_sync_rejects_oversized_lua_source_before_writing(monkeypatch, tmp_path) -> None:
    module = _load_app(monkeypatch, tmp_path)
    source = _source_dir(tmp_path)
    (source / "auto_heal.lua").write_text("x" * 32, encoding="utf-8")
    monkeypatch.setattr(module, "CLIENT_SYNC_LUA_MAX_BYTES", 16)
    client_root = tmp_path / "client" / "scripts"

    monkeypatch.setenv("CTOA_CLIENT_SYNC_ENABLED", "true")
    monkeypatch.setenv("CTOA_CLIENT_SCRIPTS_DIR", str(client_root))
    monkeypatch.setenv("CTOA_CLIENT_TARGET_SLUG", "intel_target")

    result = module._sync_intel_to_client(source)

    assert result["ok"] is False
    assert result["detail"] == "Client sync source Lua is too large"
    assert not client_root.exists()


def test_client_sync_rejects_symlinked_lua_destination_before_writing(monkeypatch, tmp_path) -> None:
    module = _load_app(monkeypatch, tmp_path)
    source = _source_dir(tmp_path)
    client_root = tmp_path / "client" / "scripts"
    target_dir = client_root / "intel_target"
    target_dir.mkdir(parents=True)
    outside_destination = tmp_path / "outside-destination.lua"
    outside_destination.write_text("-- outside\n", encoding="utf-8")
    try:
        (target_dir / "auto_heal.lua").symlink_to(outside_destination)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    monkeypatch.setenv("CTOA_CLIENT_SYNC_ENABLED", "true")
    monkeypatch.setenv("CTOA_CLIENT_SCRIPTS_DIR", str(client_root))
    monkeypatch.setenv("CTOA_CLIENT_TARGET_SLUG", "intel_target")

    result = module._sync_intel_to_client(source)

    assert result["ok"] is False
    assert result["detail"] == "Client sync destination Lua must not be a symlink"
    assert outside_destination.read_text(encoding="utf-8") == "-- outside\n"
    assert not (client_root / "ctoa_intel_autoload.lua").exists()


def test_client_sync_uses_default_autoloader_when_env_is_blank(monkeypatch, tmp_path) -> None:
    module = _load_app(monkeypatch, tmp_path)
    source = _source_dir(tmp_path)
    client_root = tmp_path / "client" / "scripts"

    monkeypatch.setenv("CTOA_CLIENT_SYNC_ENABLED", "true")
    monkeypatch.setenv("CTOA_CLIENT_SCRIPTS_DIR", str(client_root))
    monkeypatch.setenv("CTOA_CLIENT_AUTOLOADER_NAME", " ")

    result = module._sync_intel_to_client(source)

    assert result["ok"] is True
    assert (client_root / "ctoa_intel_autoload.lua").exists()
