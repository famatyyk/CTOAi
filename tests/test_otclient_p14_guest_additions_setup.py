from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts" / "windows" / "otclient_p14_guest_additions_setup.cmd"
CONTRACT = ROOT / "docs" / "otclient" / "P14_GUEST_ADDITIONS_SETUP_CONTRACT.md"


def _source() -> str:
    return HELPER.read_text(encoding="utf-8")


def test_guest_additions_helper_is_fixed_system_only_and_pretrusts_ga_media() -> None:
    source = _source()
    lowered = source.lower()

    assert source.startswith("@echo off\nsetlocal EnableExtensions DisableDelayedExpansion\n")
    assert 'if not "%~1"=="" exit /b 32' in source
    assert 'set "P14_EXPECTED_SCRIPT=%SystemRoot%\\Setup\\Scripts\\ctoa_p14_guest_additions_setup.cmd"' in source
    assert 'if /I not "%P14_SCRIPT_PATH%"=="%P14_EXPECTED_SCRIPT%" exit /b 31' in source
    assert "whoami /user /fo csv /nh" in source
    assert 'if not "%P14_CALLER_SID%"=="S-1-5-18" exit /b 30' in source
    assert 'VBoxWindowsAdditions.exe' in source
    assert 'VBoxCertUtil.exe' in source
    assert 'for %%C in ("%P14_GA_CERT_DIR%\\vbox*.cer") do (' in source
    assert 'add-trusted-publisher "%%~fC" --root "%%~fC"' in source
    assert '"%P14_GA_INSTALLER%" /S' in source
    assert 'if "%P14_INSTALL_EXIT%"=="3010" exit /b 3010' in source
    assert 'if "%P14_INSTALL_EXIT%"=="1641" exit /b 1641' in source

    for forbidden in (
        "guestcontrol",
        "keyboardputscancode",
        "mouseput",
        "clipboard",
        "curl",
        "bitsadmin",
        "invoke-webrequest",
        "net use",
        "shutdown",
        "password",
    ):
        assert forbidden not in lowered


def test_guest_additions_helper_is_not_a_specialize_action() -> None:
    source = _source().lower()

    assert "post-oobe local system task" in source
    assert "specialize runsynchronous" not in source


def test_guest_additions_helper_fails_before_any_installer_action_outside_fixed_path() -> None:
    result = subprocess.run(
        ["cmd.exe", "/d", "/c", "call", str(HELPER)],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert result.returncode == 31, result.stdout + result.stderr


def test_guest_additions_contract_matches_the_tracked_helper() -> None:
    contract = CONTRACT.read_text(encoding="utf-8")
    normalized_contract = " ".join(contract.split())

    assert "ctoa_p14_guest_additions_setup.cmd" in contract
    assert "Microsoft-Windows-Setup/UseConfigurationSet" in contract
    assert "<UseConfigurationSet>true</UseConfigurationSet>" in contract
    assert "omits the `$OEM$` payload" in normalized_contract
    assert "post_oobe_bootstrap" in contract
    assert "LOCAL SYSTEM" in contract
    assert "add-trusted-publisher" in contract
    assert "VBoxWindowsAdditions.exe /S" in contract
    assert "baseline" in contract
