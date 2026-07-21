from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "scripts/windows/solteria_helper_test_env.ps1"
MODULES = ROOT / "scripts/lua/otclient/ctoa_helper_modules.lua"
SOURCE_ROOT = ROOT / "scripts/lua/otclient"
LEGACY = {
    "ctoa_native_combat.lua",
    "ctoa_native_heal.lua",
    "ctoa_native_loot.lua",
}


def _function(source: str, name: str, next_name: str) -> str:
    return source.split(f"function {name}", 1)[1].split(f"function {next_name}", 1)[0]


def test_official_helper_package_excludes_unloaded_legacy_standalones() -> None:
    wrapper = WRAPPER.read_text(encoding="utf-8")
    package = _function(wrapper, "Get-DevPackageFiles", "Get-DevPackageSourcePath")
    sync = _function(wrapper, "Sync-CtoaRuntimeFiles", "Ensure-CtoaBootHook")
    stage = _function(wrapper, "New-DevPackage", "Invoke-DevValidation")
    boot_manifest = MODULES.read_text(encoding="utf-8")

    for name in LEGACY:
        assert f'mods/ctoa_otclient/{name}' not in package
        assert f'"{name}"' not in sync
        assert f'"{name}"' not in stage
        assert f'file = "{name}"' not in boot_manifest


def test_local_legacy_sources_are_explicitly_non_distributable_references() -> None:
    for name in LEGACY:
        source = (SOURCE_ROOT / name).read_text(encoding="utf-8")
        assert "LOCAL SOURCE ONLY" in source
        assert "not loaded or shipped by CTOAi Helper" in source


def test_legacy_cleanup_removes_enabled_and_disabled_copies() -> None:
    wrapper = WRAPPER.read_text(encoding="utf-8")
    cleanup = _function(wrapper, "Get-LiveLegacyFiles", "Get-LiveClientSummary")

    for name in LEGACY:
        assert f'"mods/ctoa_otclient/{name}"' in cleanup
        assert f'"mods/ctoa_otclient/{name}.disabled"' in cleanup


def test_wrapper_derives_all_active_module_inventories_from_package_owner() -> None:
    wrapper = WRAPPER.read_text(encoding="utf-8")
    inventory = _function(wrapper, "Get-DevModuleFileNames", "Get-DevPackageSourcePath")

    assert 'foreach ($relative in Get-DevPackageFiles)' in inventory
    assert 'StartsWith("mods/ctoa_otclient/"' in inventory
    assert wrapper.count("$moduleFiles = @(Get-DevModuleFileNames)") == 2
    assert wrapper.count("$files = @(Get-DevModuleFileNames)") == 1
    assert wrapper.count("$enableFiles = @(Get-DevModuleFileNames)") == 1
