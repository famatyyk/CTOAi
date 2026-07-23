from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
WINDOWS = ROOT / "scripts" / "windows"
HOST_RUNNER = WINDOWS / "otclient_p14_vm_runner.ps1"
GUEST_PROVISION = WINDOWS / "otclient_p14_guest_provision.ps1"
GUEST_BROKER = WINDOWS / "otclient_p14_guest_broker.ps1"
EVIDENCE_REVIEW = WINDOWS / "otclient_p14_evidence_review.ps1"
VM_CAPTURE = WINDOWS / "otclient_p14_vm_capture.ps1"
BASELINE_CAPTURE = WINDOWS / "otclient_p14_baseline_capture.ps1"
P14_WINDOWS_SCRIPTS = (
    HOST_RUNNER,
    GUEST_PROVISION,
    GUEST_BROKER,
    EVIDENCE_REVIEW,
    VM_CAPTURE,
    BASELINE_CAPTURE,
)


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _assert_no_interactive_or_remote_control(source: str) -> None:
    lowered = source.lower()
    for forbidden in (
        "guestcontrol",
        "keyboardputscancode",
        "mouseput",
        "sendkeys",
        "invoke-expression",
        "start-process",
        "clipboard-mode",
        "draganddrop-mode",
    ):
        assert forbidden not in lowered


def test_host_runner_is_fixed_to_the_p14_appliance_and_dry_run_by_default() -> None:
    source = _source(HOST_RUNNER)

    assert "$P14VmUuid = '68c47454-65cd-4211-ac24-9a3f8bc219b1'" in source
    assert "$P14SnapshotUuid = '60813f92-d982-44ee-95a8-833596672a1b'" in source
    assert "$P14EndpointProfile = 'p14-offline-replay-v1'" in source
    assert "[ValidatePattern('^[a-f0-9]{16}$')]" in source
    assert "if (-not $Execute)" in source
    assert "'guestproperty', 'set', $P14VmUuid, $P14GuestRunIdProperty, $RunId" in source
    assert "$P14GuestEnvelopeProperty = '/CTOAi/P14/EvidenceEnvelopeB64'" in source
    assert "Get-P14GuestProperty" in source
    assert "Stop-AndRestoreP14Appliance" in source
    assert "'controlvm', $P14VmUuid, 'poweroff'" in source
    assert "acceptance_envelope_b64" in source
    assert "CurrentSnapshotUUID') -ne $P14SnapshotUuid" in source
    assert "'snapshot', $P14VmUuid, 'restore', $P14SnapshotUuid" in source
    assert "'startvm', $P14VmUuid, '--type', 'headless'" in source
    assert "'getextradata', $P14VmUuid, $P14EndpointProfileKey" in source
    assert "recording_enabled = 'off'" in source
    assert "nic1 = 'none'" in source
    assert "Get-P14MachineValue $machine 'cableconnected1'" in source
    assert "appliance_setting_invalid:cableconnected1" in source
    assert "network_mode_not_isolated" in source
    assert "shared_folder_not_allowed" in source
    _assert_no_interactive_or_remote_control(source)


def test_guest_provision_uses_only_the_current_standard_guest_account() -> None:
    source = _source(GUEST_PROVISION)

    assert "[switch]$Apply" in source
    assert "dedicated_standard_user_required" in source
    assert "interactive_guest_session_required" in source
    assert "$P14RunKey = 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run'" in source
    assert "New-ItemProperty -LiteralPath $P14RunKey" in source
    assert "p14-snapshot-manifest.json" in source
    assert "Set-P14ImmutableTree $P14TrustRoot" in source
    assert "Stage-P14Bundle" in source
    assert "New-SelfSignedCertificate" in source
    assert "-KeyAlgorithm ECDSA" in source
    assert "-KeyExportPolicy NonExportable" in source
    assert "guest_evidence_public_cert_b64" in source
    assert "network_adapter_not_isolated" in source
    assert "C:\\P14Runner\\bundle\\helper-manifest.json" in source
    assert "C:\\P14Runner\\runs" in source
    assert "C:\\P14Runner\\evidence" in source
    assert "[switch]$ApproveVisualBaseline" in source
    assert "visual_baseline_approval_required" in source
    assert "baseline-receipt.json" in source
    assert "Get-P14VisualBaseline $revision" in source
    assert "Set-P14ImmutableTree $P14BaselineRoot" in source
    assert "VisualBaselineSha256" not in source
    assert "[string]$Password" not in source
    assert "Register-ScheduledTask" not in source
    _assert_no_interactive_or_remote_control(source)


def test_baseline_capture_is_guest_only_and_requires_later_owner_approval() -> None:
    source = _source(BASELINE_CAPTURE)

    assert "[switch]$Apply" in source
    assert "$P14BaselineRoot = 'C:\\P14Runner\\baseline'" in source
    assert "$P14BaselineReceipt = 'C:\\P14Runner\\baseline\\baseline-receipt.json'" in source
    assert "awaiting_owner_approval" in source
    assert "Get-P14RunId" in source
    assert "RandomNumberGenerator" in source
    assert "Set-P14CaptureEnvironment $runId" in source
    assert "& $P14CaptureScript -SourceRevision $sourceRevision" in source
    assert "network_adapter_not_isolated" in source
    assert "baseline_root_not_empty" in source
    assert "VisualBaselineSha256" not in source
    assert "VBoxManage" not in source
    _assert_no_interactive_or_remote_control(source)


@pytest.mark.parametrize("path", [GUEST_PROVISION, GUEST_BROKER, BASELINE_CAPTURE])
def test_p14_guest_directory_creation_uses_the_supported_path_parameter(
    path: Path,
) -> None:
    source = _source(path)

    assert "New-Item -ItemType Directory -LiteralPath" not in source
    assert "New-Item -ItemType Directory -Path" in source


def test_guest_broker_accepts_only_a_run_id_and_fixed_local_sequence() -> None:
    source = _source(GUEST_BROKER)

    assert "param(\n    [switch]$RunOnce" in source
    assert "$P14GuestRunIdProperty = '/CTOAi/P14/RunId'" in source
    assert "guestproperty get $P14GuestRunIdProperty" in source
    assert "[a-f0-9]{16}" in source
    assert "$P14BundleManifest = 'C:\\P14Runner\\bundle\\helper-manifest.json'" in source
    assert "$P14RunsRoot = 'C:\\P14Runner\\runs'" in source
    assert "$P14EvidenceRoot = 'C:\\P14Runner\\evidence'" in source
    assert "$P14SandboxExecutor = 'C:\\P14Runner\\repo\\scripts\\ops\\otclient_p14_sandbox_executor.py'" in source
    assert "Set-P14ProcessIsolationFlags $RunId" in source
    assert "& $P14CaptureScript -SourceRevision $Manifest['source_revision']" in source
    assert "-EvidenceRoot $evidenceRoot" not in source
    assert "& $P14EvidenceReviewScript -SourceRevision $Manifest['source_revision'] -RunId $RunId" in source
    assert "& python.exe $P14SandboxExecutor run --run-id $RunId" in source
    assert "$P14GuestEnvelopeProperty = '/CTOAi/P14/EvidenceEnvelopeB64'" in source
    assert "New-P14GuestEnvelope" in source
    assert "ECDsaCertificateExtensions" in source
    assert "Convert-P14EcdsaSignatureToDer" in source
    assert "CTOAi-P14-guest-evidence-envelope/v1" in source
    assert "snapshot_manifest_hash_mismatch" in source
    assert "network_adapter_not_isolated" in source
    assert "live_authority = $false" in source
    assert "promotion_approved = $false" in source
    _assert_no_interactive_or_remote_control(source)


@pytest.mark.parametrize("path", [GUEST_PROVISION, GUEST_BROKER, EVIDENCE_REVIEW, BASELINE_CAPTURE])
def test_p14_guest_json_is_compatible_with_windows_powershell_51(path: Path) -> None:
    source = _source(path)

    assert "ConvertFrom-Json -AsHashtable" not in source
    assert "ConvertFrom-Json -Depth" not in source
    assert "function ConvertTo-P14Hashtable" in source
    assert "p14_json_depth_exceeded" in source

    powershell = shutil.which("powershell.exe")
    if not powershell:
        pytest.skip("Windows PowerShell 5.1 is unavailable")

    escaped_path = str(path).replace("'", "''")
    command = (
        "$ErrorActionPreference='Stop'; "
        f"$scriptPath='{escaped_path}'; "
        "$text=[IO.File]::ReadAllText($scriptPath); "
        "$start=$text.IndexOf('function ConvertTo-P14Hashtable'); "
        "$end=$text.IndexOf('function Get-P14Json'); "
        "if ($start -lt 0 -or $end -le $start) { throw 'compatibility helper missing' }; "
        ". ([scriptblock]::Create($text.Substring($start, $end - $start))); "
        "$value=ConvertTo-P14Hashtable -Value ('{\"nested\":{\"flag\":true},\"items\":[{\"kind\":\"proof\"}],\"empty\":[]}' | ConvertFrom-Json); "
        "if ($value -isnot [hashtable] -or $value['nested'] -isnot [hashtable] -or "
        "$value['items'][0] -isnot [hashtable] -or $value['items'][0]['kind'] -ne 'proof' -or "
        "$value['empty'].Count -ne 0) { throw 'JSON conversion contract failed' }"
    )
    result = subprocess.run(
        [powershell, "-NoLogo", "-NoProfile", "-Command", command],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("path", P14_WINDOWS_SCRIPTS)
def test_p14_windows_json_readers_do_not_use_pscore_only_switches(path: Path) -> None:
    source = _source(path)

    assert not re.search(
        r"ConvertFrom-Json[^\r\n]*-(?:AsHashtable|Depth)\b", source
    ), path


def test_evidence_review_has_only_fixed_derived_evidence_paths() -> None:
    source = _source(EVIDENCE_REVIEW)

    assert "[ValidatePattern('^[a-f0-9]{40}$')]" in source
    assert "[ValidatePattern('^[a-f0-9]{16}$')]" in source
    assert '$P14RunEvidenceRoot = Join-Path $P14EvidenceRoot ("capture-$RunId")' in source
    assert "capture-report.json" in source
    assert '"p14-in-world-$SourceRevision.png"' in source
    assert "client-capabilities.json" in source
    assert "independent_visual_review" in source
    assert "independent_in_world_review" in source
    assert "capture_isolation_invalid" in source
    assert "helper_runtime_state_invalid" in source
    assert "CopyFromScreen" not in source
    _assert_no_interactive_or_remote_control(source)


@pytest.mark.parametrize(
    "path", P14_WINDOWS_SCRIPTS
)
def test_p14_windows_scripts_parse_in_windows_powershell_51(path: Path) -> None:
    powershell = shutil.which("powershell.exe") or shutil.which("pwsh")
    if not powershell:
        pytest.skip("PowerShell is unavailable")
    escaped_path = str(path).replace("'", "''")
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
