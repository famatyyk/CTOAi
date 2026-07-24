from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WINDOWS = ROOT / "scripts" / "windows"
BOOTSTRAP = WINDOWS / "otclient_p14_stage_bootstrap.ps1"
HOST = WINDOWS / "otclient_p14_stage_host.ps1"
SETUP_COMPLETE = WINDOWS / "otclient_p14_stage_setupcomplete.cmd"
PROVISION = WINDOWS / "otclient_p14_guest_provision.ps1"
CONTRACT = ROOT / "docs" / "otclient" / "P14_STAGE_ONLY_BOOTSTRAP_CONTRACT.md"
RUNBOOK = ROOT / "docs" / "otclient" / "P14_APPLIANCE_BOOTSTRAP_RUNBOOK.md"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _assert_no_remote_or_staged_execution(source: str) -> None:
    lowered = source.lower()
    for forbidden in (
        "guestcontrol",
        "keyboardputscancode",
        "mouseput",
        "sendkeys",
        "invoke-expression",
        "start-process",
        "copy-item",
        "otclient_p14_baseline_capture.ps1",
        "otclient_p14_guest_provision.ps1",
        "otclient_p14_guest_broker.ps1",
        "stage-bundle",
    ):
        assert forbidden not in lowered


def test_guest_bootstrap_is_fixed_system_manifest_copy_only() -> None:
    source = _source(BOOTSTRAP)

    assert "param(\n    [switch]$Install,\n\n    [switch]$Run" in source
    assert "$P14BootstrapScript = 'C:\\Windows\\Setup\\Scripts\\ctoa_p14_stage_bootstrap.ps1'" in source
    assert "$P14ShareRoot = '\\\\VBOXSVR\\CTOA_P14_STAGE'" in source
    assert "$P14ManifestPath = '\\\\VBOXSVR\\CTOA_P14_STAGE\\p14-stage-manifest.json'" in source
    assert "$P14RunnerRoot = 'C:\\P14Runner'" in source
    assert "$P14AllowedRoots = @('repo', 'client', 'toolchain')" in source
    assert "Assert-P14SystemBootstrap" in source
    assert "identity.User.Value -ne 'S-1-5-18'" in source
    assert "New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest" in source
    assert "Get-NetAdapter -ErrorAction Stop" in source
    assert "Assert-P14NoDuplicateJsonKeys" in source
    assert "duplicate_json_key" in source
    assert "HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)" in source
    assert "manifest_path_duplicate_or_case_collision" in source
    assert "Assert-P14ShareMatchesManifest" in source
    assert "share_manifest_path_set_invalid" in source
    assert "share_reparse_point_rejected" in source
    assert "Get-P14FileDigest $Source" in source
    assert "Get-P14FileDigest $Destination" in source
    assert "copy_hash_or_size_mismatch" in source
    assert "Unregister-ScheduledTask -TaskName $P14BootstrapTaskName -Confirm:$false" in source
    assert "Set-P14StageStatus 'staged' $receiptSha256" in source
    assert "staged_content_executed = $false" in source
    assert "baseline_created = $false" in source
    assert "provisioned = $false" in source
    assert "[string]$Password" not in source
    _assert_no_remote_or_staged_execution(source)


def test_host_coordinator_uses_one_readonly_share_and_verifies_teardown() -> None:
    source = _source(HOST)

    assert "param(\n    [switch]$Apply" in source
    assert "$P14ApplianceVmName = 'CTOA-P14-Runner-Fresh-20260724'" in source
    assert "$P14StageHostRoot = 'C:\\P14Transport\\ctoa-p14-stage'" in source
    assert "$P14StageShareName = 'CTOA_P14_STAGE'" in source
    assert "$P14AllowedRoots = @('repo', 'client', 'toolchain')" in source
    assert "Assert-P14TransportTopLevel" in source
    assert "transport_manifest_already_exists" in source
    assert "transport_path_case_collision" in source
    assert "sharedfolder" in source
    assert "'add'" in source
    assert "'--readonly'" in source
    assert "'--automount'" in source
    assert "'remove'" in source
    assert "finally {" in source
    assert "'acpipowerbutton'" in source
    assert "Assert-P14NoSharedFolders (Get-P14Machine $vbox)" in source
    assert "guest_receipt_sha256 = $result['value']" in source
    assert "staged_content_executed = $false" in source
    assert "baseline_created = $false" in source
    assert "provisioned = $false" in source
    assert "[string]$VmUuid" not in source
    assert "[string]$HostPath" not in source
    assert "[string]$Password" not in source
    _assert_no_remote_or_staged_execution(source)


def test_host_wait_budget_covers_bootstrap_share_wait_and_task_limit() -> None:
    host = _source(HOST)
    bootstrap = _source(BOOTSTRAP)

    host_wait = int(re.search(r"\$P14StageWaitSeconds = (\d+)", host).group(1))
    share_attempts = int(
        re.search(r"\$P14ShareWaitAttempts = (\d+)", bootstrap).group(1)
    )
    share_wait = int(re.search(r"\$P14ShareWaitSeconds = (\d+)", bootstrap).group(1))
    task_minutes = int(
        re.search(
            r"ExecutionTimeLimit \(New-TimeSpan -Minutes (\d+)\)", bootstrap
        ).group(1)
    )

    assert host_wait >= (share_attempts * share_wait) + (task_minutes * 60)


def test_answer_iso_hook_installs_only_the_fixed_system_bootstrap() -> None:
    source = _source(SETUP_COMPLETE).lower()

    assert "ctoa_p14_stage_bootstrap.ps1" in source
    assert " -install" in source
    assert "powershell.exe" in source
    assert "password" not in source
    assert "guestcontrol" not in source


def test_guest_provision_uses_explicit_portable_toolchain_paths() -> None:
    source = _source(PROVISION)

    assert "$P14ToolchainRoot = 'C:\\P14Runner\\toolchain'" in source
    assert "$P14PythonExe = 'C:\\P14Runner\\toolchain\\python\\python.exe'" in source
    assert "$P14GitExe = 'C:\\P14Runner\\toolchain\\git\\cmd\\git.exe'" in source
    assert "$P14PortableGitEnvironment = 'CTOA_P14_PORTABLE_GIT_EXE'" in source
    assert "Assert-P14PortableToolchain" in source
    assert "& $P14GitExe -C $P14RepoRoot rev-parse HEAD" in source
    assert "[Environment]::SetEnvironmentVariable($P14PortableGitEnvironment, $P14GitExe, 'Process')" in source
    assert "[Environment]::SetEnvironmentVariable($P14PortableGitEnvironment, $previousPortableGit, 'Process')" in source
    assert "& $P14PythonExe $P14SandboxExecutor stage-bundle" in source
    assert "Get-Command python.exe" not in source


def test_stage_docs_keep_the_transfer_and_acceptance_boundaries_distinct() -> None:
    contract = _source(CONTRACT)
    runbook = _source(RUNBOOK)

    assert "P14_STAGE_ONLY_BOOTSTRAP_CONTRACT.md" in runbook
    assert "file-copy boundary only" in contract
    assert "No staged file is invoked" in contract
    assert "removes the share" in contract
    assert "baseline_created" in contract
    assert "provisioned" in contract
    assert "must not be inferred from the stage\nreceipt" in contract


def test_stage_windows_scripts_parse_without_execution() -> None:
    powershell = shutil.which("powershell.exe") or shutil.which("pwsh")
    if not powershell:
        return

    for script in (BOOTSTRAP, HOST, PROVISION):
        escaped_path = str(script).replace("'", "''")
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


def test_guest_bootstrap_duplicate_json_guard_executes_fail_closed() -> None:
    powershell = shutil.which("powershell.exe") or shutil.which("pwsh")
    if not powershell:
        return

    escaped_path = str(BOOTSTRAP).replace("'", "''")
    command = (
        "$ErrorActionPreference='Continue'; "
        f"$scriptPath='{escaped_path}'; "
        "$text=[IO.File]::ReadAllText($scriptPath); "
        "$marker='if (($Install -and $Run) -or (-not $Install -and -not $Run)) {'; "
        "$prefix=$text.Substring(0,$text.IndexOf($marker)); "
        ". ([scriptblock]::Create($prefix)); "
        "Assert-P14NoDuplicateJsonKeys '{\"nested\":{\"ok\":true},\"items\":[1,2]}'; "
        "try { Assert-P14NoDuplicateJsonKeys '{\"same\":1,\"same\":2}'; throw 'duplicate accepted' } "
        "catch { if ($_.Exception.Message -notmatch '^p14_stage_bootstrap:duplicate_json_key$') { throw } }; "
        "exit 0"
    )
    result = subprocess.run(
        [powershell, "-NoLogo", "-NoProfile", "-Command", command],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr
