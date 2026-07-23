from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "windows" / "otclient_p14_vm_capture.ps1"


def test_vm_capture_is_guest_bound_and_fail_closed() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "CTOA_P14_CAPTURE_CONTEXT = 'guest'" in source
    assert "CTOA_P14_OPERATOR_WORKSTATION_FOCUS_USED = 'false'" in source
    assert "CTOA_P14_OPERATOR_WORKSTATION_INPUT_USED = 'false'" in source
    assert "CTOA_P14_NETWORK_DISPATCH_USED = 'false'" in source
    assert "CTOA_P14_LIVE_CLIENT_ACCESSED = 'false'" in source
    assert "CTOA_P14_PROMOTION_ATTEMPTED = 'false'" in source
    assert "candidate.online -eq $true" in source
    assert "CopyFromScreen" in source
    assert "[System.Diagnostics.Process]::Start($startInfo)" in source
    assert "Stop-P14Capture('in_world_marker_timeout')" in source
    assert "golden_vm_identity_missing" in source
    assert "VirtualBox Guest Additions" in source
    assert "C:\\Windows\\System32\\VBoxService.exe" in source
    assert "VBoxManage" not in source
    assert "CTOA_P14_RUN_ID" in source
    assert "run_id_invalid" in source
    assert "caller_path_override_rejected" in source


def test_vm_capture_keeps_client_and_evidence_roots_separate() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "Get-StrictPath $ClientPath $clientRoot 'client'" in source
    assert (
        "Get-StrictEvidenceRoot $EvidenceRoot $evidenceAllowlistRoot $clientRoot"
        in source
    )
    assert "$evidenceAllowlistRoot = 'C:\\P14Runner\\evidence'" in source
    assert "evidence_outside_allowlist" in source
    assert "evidence_overlaps_client_root" in source
    assert "Test-PathWithin $Path $AllowedRoot" in source
    assert "Test-PathWithin $ClientRoot $Path" in source
    assert "client-capabilities.json" in source
    assert "capture-report.json" in source
    assert "C:\\P14Runner\\client\\otclient.exe" in source
    assert "CTOA_P14_CLIENT_PATH) {" not in source
    assert "CTOA_P14_EVIDENCE_ROOT) {" not in source


def test_vm_capture_passes_a_bounded_helper_activation_and_reporter_target() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "$captureNonce = [Guid]::NewGuid().ToString('N')" in source
    assert '"p14-helper-runtime-$SourceRevision-$captureNonce.json"' in source
    assert "CTOA_P14_CAPTURE_HELPER_ACTIVATION" in source
    assert "CTOA_P14_CAPTURE_REPORT_PATH" in source
    assert "reporter_outside_evidence" in source
    assert (
        "$reporterRoot = (Resolve-Path -LiteralPath $evidenceAllowlistRoot).Path"
        in source
    )
    assert "Test-PathWithin $reporter $reporterRoot" in source
    assert (
        "$startInfo.EnvironmentVariables[$activationName] = 'helper-ui-only'" in source
    )
    assert "$startInfo.EnvironmentVariables[$reporterName] = $reporter" in source
    assert "$startInfo.UseShellExecute = $false" in source
    assert "SetEnvironmentVariable" not in source
    assert "Get-StrictPath $reporter $reporterRoot 'reporter'" in source
    assert "Copy-Item -LiteralPath $resolvedReporter" in source
    assert "reporter_artifact = [IO.Path]::GetFileName($capabilityCopy)" in source
    assert "mods\\ctoa_otclient\\ctoa_client_capabilities.json" not in source


def test_vm_capture_is_limited_to_the_client_window_and_not_log_export() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "Get-P14ClientWindowBounds" in source
    assert "client_window_missing" in source
    assert "client_window_bounds_invalid" in source
    assert "[CTOAiP14NativeWindow]::GetWindowRect" in source
    assert "System.Windows.Forms" not in source
    assert "otclient.log" not in source


def test_capture_reporter_override_requires_full_guest_context(tmp_path: Path) -> None:
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for P14 capture reporter validation"
    reporter = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_client_reporter.lua"
    target = (
        r"C:\P14Runner\evidence\p14-helper-runtime-"
        + "a" * 40
        + "-"
        + "b" * 32
        + ".json"
    )
    probe = tmp_path / "p14_capture_reporter_probe.lua"
    probe.write_text(
        """
local reporter = dofile(arg[1])
if arg[3] == "accepted" then
    assert(reporter.resolvePath(nil, nil) == arg[2])
else
    assert(reporter.resolvePath(nil, nil) == "ctoa_client_capabilities.json")
end
""",
        encoding="utf-8",
    )
    environment = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith("CTOA_P14_")
    }
    environment.update(
        {
            "CTOA_P14_CAPTURE_HELPER_ACTIVATION": "helper-ui-only",
            "CTOA_P14_ISOLATED_ENVIRONMENT": "true",
            "CTOA_P14_CAPTURE_CONTEXT": "guest",
            "CTOA_P14_OPERATOR_WORKSTATION_FOCUS_USED": "false",
            "CTOA_P14_OPERATOR_WORKSTATION_INPUT_USED": "false",
            "CTOA_P14_NETWORK_DISPATCH_USED": "false",
            "CTOA_P14_LIVE_CLIENT_ACCESSED": "false",
            "CTOA_P14_PROMOTION_ATTEMPTED": "false",
            "CTOA_P14_CAPTURE_REPORT_PATH": target,
        }
    )
    accepted = subprocess.run(
        [lua, str(probe), str(reporter), target, "accepted"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
        env=environment,
    )
    assert accepted.returncode == 0, accepted.stdout + accepted.stderr

    environment.pop("CTOA_P14_OPERATOR_WORKSTATION_INPUT_USED")
    rejected = subprocess.run(
        [lua, str(probe), str(reporter), target, "rejected"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
        env=environment,
    )
    assert rejected.returncode == 0, rejected.stdout + rejected.stderr

    environment["CTOA_P14_OPERATOR_WORKSTATION_INPUT_USED"] = "false"
    environment["CTOA_P14_CAPTURE_REPORT_PATH"] = (
        r"C:\P14Runner\evidence\poison\p14-helper-runtime-"
        + "a" * 40
        + "-"
        + "b" * 32
        + ".json"
    )
    poisoned = subprocess.run(
        [lua, str(probe), str(reporter), target, "rejected"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
        env=environment,
    )
    assert poisoned.returncode == 0, poisoned.stdout + poisoned.stderr
