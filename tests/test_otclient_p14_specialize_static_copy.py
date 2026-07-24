from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WINDOWS = ROOT / "scripts" / "windows"
COPY = WINDOWS / "otclient_p14_specialize_static_copy.ps1"
SETUP_COMPLETE = WINDOWS / "otclient_p14_stage_setupcomplete.cmd"
POST_OOBE = WINDOWS / "otclient_p14_post_oobe_bootstrap.ps1"
GUEST_ADDITIONS = WINDOWS / "otclient_p14_guest_additions_setup.cmd"
STAGE_BOOTSTRAP = WINDOWS / "otclient_p14_stage_bootstrap.ps1"
CONTRACT = ROOT / "docs" / "otclient" / "P14_SPECIALIZE_STATIC_COPY_CONTRACT.md"
STAGE_CONTRACT = ROOT / "docs" / "otclient" / "P14_STAGE_ONLY_BOOTSTRAP_CONTRACT.md"
GUEST_ADDITIONS_CONTRACT = (
    ROOT / "docs" / "otclient" / "P14_GUEST_ADDITIONS_SETUP_CONTRACT.md"
)


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_specialize_static_copy_is_fixed_system_hash_bound_and_copy_only() -> None:
    source = _source(COPY)
    lowered = source.lower()

    assert "param()" in source
    assert "$P14SourceScanLetters = @('D', 'E', 'F', 'G', 'H')" in source
    assert "$P14PayloadDirectoryName = 'P14Payload'" in source
    assert "$P14PayloadScriptName = 'copy.ps1'" in source
    assert "$P14DestinationDirectory = 'C:\\Windows\\Setup\\Scripts'" in source
    assert "identity.User.Value -ne 'S-1-5-18'" in source
    assert "return $candidates.ToArray()" in source
    assert "return ,$candidates.ToArray()" not in source
    assert "payload_media_ambiguous" in source
    assert "payload_source_hash_mismatch" in source
    assert "payload_destination_existing_mismatch" in source
    assert "[IO.File]::Move($temporary, $destination)" in source
    assert "specialize-static-copy-receipt.json" in source
    assert "specialize-static-copy-blocked.json" in source
    assert "[IO.FileMode]::CreateNew" in source
    assert "Write-P14Receipt 'copied' 'ok'" in source
    assert "Write-P14Receipt 'blocked' $code" in source

    expected_payloads = {
        "ctoa_p14_stage_bootstrap.ps1": STAGE_BOOTSTRAP,
        "ctoa_p14_guest_additions_setup.cmd": GUEST_ADDITIONS,
        "ctoa_p14_post_oobe_bootstrap.ps1": POST_OOBE,
        "SetupComplete.cmd": SETUP_COMPLETE,
    }
    for target_name, source_path in expected_payloads.items():
        assert f"'{target_name}' = '{_sha256(source_path)}'" in source

    assert source.index("'SetupComplete.cmd'") > source.index(
        "'ctoa_p14_post_oobe_bootstrap.ps1'"
    )
    for forbidden in (
        "vboxwindowsadditions.exe",
        "register-scheduledtask",
        "new-scheduledtask",
        "restart-computer",
        "start-process",
        "get-netadapter",
        "invoke-webrequest",
        "guestcontrol",
        "\\\\vboxsvr",
        "password",
    ):
        assert forbidden not in lowered


def test_static_copy_contract_has_bounded_specialize_commands_with_no_credentials() -> None:
    contract = _source(CONTRACT)
    commands = re.findall(r"<Path>(.*?)</Path>", contract)

    assert len(commands) == 2
    assert len(commands[0]) == 251
    assert len(commands[0]) <= 259
    assert 'for %D in (D E F G H)' in commands[0]
    assert '"%D:\\P14Payload\\copy.ps1"' in commands[0]
    assert '"C:\\ProgramData\\CTOAi\\P14\\specialize-static-copy-receipt.json"' in commands[1]
    assert "<settings pass=\"specialize\">" in contract
    assert "Microsoft-Windows-Deployment" in contract
    assert "<WillReboot>Never</WillReboot>" in contract
    assert "<Credentials>" not in contract
    assert "P14Payload\\copy.ps1" in contract
    assert "P14Payload\\SetupComplete.cmd" in contract
    assert "UseConfigurationSet` to `true`" in contract
    assert "does not install Guest\nAdditions" in contract
    assert "does not invoke this helper" in _source(GUEST_ADDITIONS_CONTRACT)
    assert "P14_SPECIALIZE_STATIC_COPY_CONTRACT.md" in _source(STAGE_CONTRACT)
    assert "automatic bootstrap logon" in contract
    assert "does not run\nstage, capture, client, canary, rollback, or release code" in contract


def test_specialize_static_copy_script_parses_without_execution() -> None:
    powershell = shutil.which("powershell.exe") or shutil.which("pwsh")
    if not powershell:
        return

    escaped_path = str(COPY).replace("'", "''")
    command = (
        "$ErrorActionPreference='Stop'; "
        f"$scriptPath='{escaped_path}'; "
        "[scriptblock]::Create([IO.File]::ReadAllText($scriptPath)) | Out-Null"
    )
    result = subprocess.run(
        [powershell, "-NoLogo", "-NoProfile", "-Command", command],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr
