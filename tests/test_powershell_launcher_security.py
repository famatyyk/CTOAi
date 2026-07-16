import json
import subprocess
import shutil
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")
CTOA_CLI = ROOT / "ctoa.ps1"
COMMAND_DICTIONARY = ROOT / "schemas" / "ctoa-command-dictionary.json"
OPEN_CONTROL_CENTER = ROOT / "scripts" / "windows" / "open-control-center.ps1"
KAMIL_LAUNCHER = ROOT / "scripts" / "ops" / "launch_kamil_client_macro_studio.ps1"
MOBILE_CONSOLE_DOC = ROOT / "docs" / "MOBILE_CONSOLE.md"
DESKTOP_CONSOLE_APP = ROOT / "desktop_console" / "app.py"


def test_control_center_opener_restricts_url_protocols() -> None:
    script = OPEN_CONTROL_CENTER.read_text(encoding="utf-8")

    assert "Set-StrictMode -Version Latest" in script
    assert "function Resolve-ControlCenterUrl" in script
    assert "[System.Uri]::TryCreate" in script
    assert "$uri.Scheme -notin @('http', 'https')" in script
    assert "$uri.UserInfo" in script
    assert "$uri.Query" in script
    assert "$uri.Fragment" in script
    assert "Control Center URL must not include query strings or fragments." in script
    assert "$Candidate -match '\\\\'" in script
    assert "[System.Uri]::UnescapeDataString($uri.AbsolutePath)" in script
    assert "Control Center URL path must not contain traversal." in script
    assert "Non-local Control Center URLs must use https://" in script
    assert ": $Candidate" not in script
    assert "Start-Process -FilePath $Url" in script
    assert "Start-Process $Url" not in script


def test_ctoa_cli_control_center_restricts_url_before_probe_or_open() -> None:
    script = CTOA_CLI.read_text(encoding="utf-8")

    assert "function Resolve-ControlCenterUrl" in script
    assert "[System.Uri]::TryCreate" in script
    assert '$uri.Scheme -notin @("http", "https")' in script
    assert "$uri.UserInfo" in script
    assert "$uri.Query" in script
    assert "$uri.Fragment" in script
    assert "Control Center URL must not include query strings or fragments." in script
    assert '$Candidate -match "\\\\"' in script
    assert "[System.Uri]::UnescapeDataString($uri.AbsolutePath)" in script
    assert "Control Center URL path must not contain traversal." in script
    assert "Non-local Control Center URLs must use https://" in script
    assert ": $Candidate" not in script
    assert "$url = Resolve-ControlCenterUrl -Candidate $url" in script
    assert "Invoke-WebRequest -Uri $url" in script
    assert "Start-Process -FilePath $url" in script
    assert "Start-Process $url" not in script


def test_ctoa_cli_up_binds_mobile_console_to_loopback() -> None:
    script = CTOA_CLI.read_text(encoding="utf-8")
    start = script.index("function Invoke-Up")
    end = script.index("function Invoke-Test", start)
    block = script[start:end]

    assert '"--host",' in block
    assert '"127.0.0.1",' in block
    assert '"0.0.0.0",' not in block


def test_mobile_console_operator_docs_do_not_recommend_public_dev_bind() -> None:
    combined = MOBILE_CONSOLE_DOC.read_text(
        encoding="utf-8"
    ) + DESKTOP_CONSOLE_APP.read_text(encoding="utf-8")

    assert "mobile_console.app:app --host 127.0.0.1 --port 8787" in combined
    assert "mobile_console.app:app --host 0.0.0.0 --port 8787" not in combined


def test_ctoa_cli_uses_explicit_file_path_for_generated_helper_html() -> None:
    script = CTOA_CLI.read_text(encoding="utf-8")

    assert "Start-Process -FilePath $preview" in script
    assert "Start-Process -FilePath $mockup" in script
    assert "Start-Process $preview" not in script
    assert "Start-Process $mockup" not in script


def test_ctoa_cli_uses_official_wrapper_for_helper_operations() -> None:
    script = CTOA_CLI.read_text(encoding="utf-8")

    assert 'Join-Path $Root "scripts/windows/solteria_helper_test_env.ps1"' in script
    assert 'if ($Approval -cne "approve-live")' in script
    assert '"PromoteLiveCtoa"' in script
    assert '"-ApproveLiveDeploy"' in script
    assert '"ValidateDev"' in script
    assert '"BackgroundStatus"' in script
    assert '"BackgroundNoScreen"' in script
    assert '"otdeploy" { Invoke-OtHelperDeploy -Approval $Arg1; break }' in script
    assert '"otbg" { Invoke-OtBackgroundStatus; break }' in script
    assert '"otp9" { Invoke-OtConditionsShadowReplay; break }' in script
    assert (
        '"otp9accept" { Invoke-OtConditionsShadowAcceptance -Confirmation $Arg1; break }'
        in script
    )
    assert '"otp10" { Invoke-OtEquipmentShadowReplay; break }' in script
    assert '"otp10preview" { Invoke-OtEquipmentObservationPreview; break }' in script
    assert '"otp10catalog" { Invoke-OtEquipmentCandidateCatalog; break }' in script
    assert (
        '"otp10plan" { Invoke-OtEquipmentCaptureProfileChangePlan -EquippedItemId $Arg1 -CandidateItemId $Arg2 -CandidateContainerId $Arg3 -CandidateSlotIndex $Arg4 -Confirmation $Arg5; break }'
        in script
    )
    assert (
        '"otp10autoplan" { Invoke-OtEquipmentCaptureProfileChangePlan -EquippedItemId $Arg1 -CandidateItemId $Arg2 -Confirmation $Arg3 -RefreshPreview; break }'
        in script
    )
    assert (
        '"otp10apply" { Invoke-OtEquipmentCaptureProfileApply -PlanSha256 $Arg1 -Confirmation $Arg2; break }'
        in script
    )
    assert '"otp10preflight" { Invoke-OtEquipmentDependencyPreflight; break }' in script
    assert '"otp10ready" { Invoke-OtEquipmentOperatorReadiness; break }' in script
    assert '"otp10refresh" { Invoke-OtEquipmentOperatorRefresh; break }' in script
    assert (
        '"otp10doctor" { Invoke-OtEquipmentCaptureProfileDoctor -Action $Arg1; break }'
        in script
    )
    assert (
        '"otp10accept" { Invoke-OtEquipmentShadowAcceptance -Confirmation $Arg1; break }'
        in script
    )
    assert '"otp11catalog" { Invoke-OtHealFriendCandidateCatalog; break }' in script
    assert "function Invoke-OtEquipmentShadowReplay" in script
    assert "function Invoke-OtEquipmentShadowAcceptance" in script
    assert "function Invoke-OtEquipmentDependencyPreflight" in script
    assert "function Invoke-OtEquipmentOperatorReadiness" in script
    assert "function Invoke-OtEquipmentOperatorRefresh" in script
    assert "function Invoke-OtHealFriendCandidateCatalog" in script
    assert '"scripts\\ops\\otclient_equipment_shadow_snapshot.py"' in script
    assert '"scripts\\ops\\otclient_equipment_observation_preview.py"' in script
    assert '"scripts\\ops\\otclient_equipment_candidate_catalog.py"' in script
    assert '"scripts\\ops\\otclient_equipment_capture_profile_change_plan.py"' in script
    assert '"scripts\\ops\\otclient_equipment_dependency_preflight.py"' in script
    assert '"scripts\\ops\\otclient_equipment_operator_readiness.py"' in script
    assert '"scripts\\ops\\otclient_equipment_operator_refresh.py"' in script
    assert (
        'Invoke-FromRoot -FilePath $python -Arguments @($scriptPath, "--allow-blocked")'
        in script
    )
    preview_start = script.index("function Invoke-OtEquipmentObservationPreview")
    preview_end = script.index(
        "function Invoke-OtEquipmentCandidateCatalog", preview_start
    )
    preview_block = script[preview_start:preview_end]
    assert "--json-out" not in preview_block
    assert "--background" not in preview_block
    assert "--capture-profile" not in preview_block
    catalog_start = script.index("function Invoke-OtEquipmentCandidateCatalog")
    catalog_end = script.index(
        "function Invoke-OtEquipmentCaptureProfileChangePlan", catalog_start
    )
    catalog_block = script[catalog_start:catalog_end]
    assert "--preview" not in catalog_block
    assert "--json-out" not in catalog_block
    plan_start = catalog_end
    plan_end = script.index(
        "function Invoke-OtEquipmentCaptureProfileDoctor", plan_start
    )
    plan_block = script[plan_start:plan_end]
    assert '"--equipped-item-id"' in plan_block
    assert '"--candidate-item-id"' in plan_block
    assert '"--candidate-container-id"' in plan_block
    assert '"--candidate-slot-index"' in plan_block
    assert '"--confirm"' in plan_block
    assert "--json-out" not in plan_block
    assert "--capture-doctor" not in plan_block
    assert "--observation-preview" not in plan_block
    assert '"init" { $arguments += "--init-local" }' in script
    assert ".\\\\ctoa.ps1 otp10doctor [init]" in script
    refresh_start = script.index("function Invoke-OtEquipmentOperatorRefresh")
    refresh_end = script.index("function Invoke-OtConditionsShadowAcceptance")
    refresh_block = script[refresh_start:refresh_end]
    assert (
        "Invoke-FromRoot -FilePath $python -Arguments @($scriptPath)" in refresh_block
    )
    for forbidden in (
        "--allow-blocked",
        "--init-local",
        "--equipped-item-id",
        "--candidate-item-id",
        "--candidate-container-id",
        "--candidate-slot-index",
        "--confirm",
        "acceptance.py",
        "shadow_replay.py",
    ):
        assert forbidden not in refresh_block
    assert '"scripts\\ops\\otclient_equipment_shadow_acceptance.py"' in script
    assert '$env:CTOA_OPERATOR_MODE = "background_no_screen"' in script
    assert '"scripts\\ops\\otclient_conditions_shadow_replay.py"' in script
    assert '".venv\\Scripts\\python.exe"' in script
    assert "Invoke-FromRootCapture -FilePath $powershell" in script
    assert '$env:CTOA_OPERATOR_MODE = "background_no_screen"' in script
    assert "rejects stale or reparse-point BackgroundNoScreen output" in script
    assert 'Copy-Item -Path (Join-Path $source "*.lua")' not in script
    assert 'Copy-Item -Path (Join-Path $source "*.otmod")' not in script


def test_p9_shadow_command_is_in_shared_command_dictionary() -> None:
    dictionary = json.loads(COMMAND_DICTIONARY.read_text(encoding="utf-8"))
    commands = {item["command"]: item for item in dictionary["commands"]}

    assert commands["otp9"]["aliases"] == []
    assert "no-action Conditions shadow replay" in commands["otp9"]["description"]


def test_p10_shadow_command_is_in_shared_command_dictionary() -> None:
    dictionary = json.loads(COMMAND_DICTIONARY.read_text(encoding="utf-8"))
    commands = {item["command"]: item for item in dictionary["commands"]}

    assert commands["otp10"]["aliases"] == []
    assert commands["otp10doctor"]["aliases"] == []
    assert commands["otp10preview"]["aliases"] == []
    assert commands["otp10catalog"]["aliases"] == []
    assert commands["otp10plan"]["aliases"] == []
    assert commands["otp10autoplan"]["aliases"] == []
    assert commands["otp10apply"]["aliases"] == []
    assert "without selecting" in commands["otp10catalog"]["description"]
    assert "recommending" in commands["otp10catalog"]["description"]
    assert "hash-bound" in commands["otp10plan"]["description"]
    assert (
        "without reading or writing the local profile"
        in commands["otp10plan"]["description"]
    )
    assert "claiming readiness" in commands["otp10plan"]["description"]
    assert "exactly one fresh operational" in commands["otp10autoplan"]["description"]
    assert commands["otp10preflight"]["aliases"] == []
    assert commands["otp10ready"]["aliases"] == []
    assert commands["otp10refresh"]["aliases"] == []
    assert "sanitized" in commands["otp10preview"]["description"]
    assert "BackgroundNoScreen" in commands["otp10preview"]["description"]
    assert "without changing eligibility" in commands["otp10preflight"]["description"]
    assert "runtime/live actions" in commands["otp10preflight"]["description"]
    assert "ordered safe next commands" in commands["otp10ready"]["description"]
    assert "without changing eligibility" in commands["otp10ready"]["description"]
    assert "fixed repo-only P10" in commands["otp10refresh"]["description"]
    assert "without IDs" in commands["otp10refresh"]["description"]
    assert "local-profile writes" in commands["otp10refresh"]["description"]
    assert (
        "data-only P10 Equipment capture profile"
        in commands["otp10doctor"]["description"]
    )
    assert "exclusively initialize" in commands["otp10doctor"]["description"]
    assert commands["otp9accept"]["aliases"] == []
    assert "P9 Conditions shadow receipt" in commands["otp9accept"]["description"]
    assert "Equipment snapshot" in commands["otp10"]["description"]
    assert commands["otp10accept"]["aliases"] == []
    assert "P10 Equipment shadow receipt" in commands["otp10accept"]["description"]
    assert commands["otp11catalog"]["aliases"] == []
    assert "without selecting" in commands["otp11catalog"]["description"]


@pytest.mark.skipif(POWERSHELL is None, reason="PowerShell runtime is unavailable")
def test_control_center_opener_rejects_traversal_urls_at_runtime() -> None:
    result = subprocess.run(
        [
            POWERSHELL,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(OPEN_CONTROL_CENTER),
            "-Url",
            "http://127.0.0.1:3000/%2e%2e/admin",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "Control Center URL path must not contain traversal." in output
    assert "Opening CTOAi Control Center" not in output


@pytest.mark.skipif(POWERSHELL is None, reason="PowerShell runtime is unavailable")
def test_control_center_opener_rejects_backslash_urls_at_runtime() -> None:
    result = subprocess.run(
        [
            POWERSHELL,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(OPEN_CONTROL_CENTER),
            "-Url",
            r"http://127.0.0.1:3000\control-center",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "Control Center URL path must not include backslashes." in output
    assert "Opening CTOAi Control Center" not in output


@pytest.mark.skipif(POWERSHELL is None, reason="PowerShell runtime is unavailable")
def test_ctoa_cli_rejects_control_center_traversal_env_url_before_probe() -> None:
    result = subprocess.run(
        [
            POWERSHELL,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            "$env:CTOA_CONTROL_CENTER_URL='http://127.0.0.1:3000/%2e%2e/admin'; & .\\ctoa.ps1 cc",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "Control Center URL path must not contain traversal." in output
    assert "Invoke-WebRequest" not in output
    assert "Opening CTOAi Control Center" not in output


def test_kamil_launcher_restricts_client_path_and_profile_override() -> None:
    script = KAMIL_LAUNCHER.read_text(encoding="utf-8")

    assert "function Assert-BotProfileName" in script
    assert "$Profile -notmatch '^[A-Za-z0-9_.-]+$'" in script
    assert "function Resolve-ClientExecutablePath" in script
    assert "[System.IO.Path]::IsPathRooted($Path)" in script
    assert "Resolve-Path -LiteralPath $Path" in script
    assert "GetExtension($resolved) -ne '.exe'" in script
    assert "Start-Process -FilePath $resolvedPath" in script
    assert "Start-Process -FilePath $Path" not in script


def test_kamil_launcher_keeps_macro_studio_on_repo_local_python() -> None:
    script = KAMIL_LAUNCHER.read_text(encoding="utf-8")

    assert "function Get-PythonExe" in script
    assert ".venv\\Scripts\\python.exe" in script
    assert (
        "Start-Process -FilePath $python -ArgumentList @('-m', 'bot.overlay.macro_overlay')"
        in script
    )
    assert "Start-Process -FilePath 'python'" not in script
