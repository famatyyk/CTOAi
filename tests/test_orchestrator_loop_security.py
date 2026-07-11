from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = REPO_ROOT / "scripts" / "ops" / "orchestrator-loop.ps1"
WORKER = REPO_ROOT / "scripts" / "ops" / "orchestrator-loop-worker.ps1"


def test_orchestrator_loop_launcher_avoids_encoded_inline_command() -> None:
    script = LAUNCHER.read_text(encoding="utf-8")

    assert "-EncodedCommand" not in script
    assert "ToBase64String" not in script
    assert "orchestrator-loop-worker.ps1" in script
    assert "'-File'," in script
    assert "$LoopWorkerScript" in script


def test_orchestrator_loop_launcher_keeps_password_out_of_process_arguments() -> None:
    script = LAUNCHER.read_text(encoding="utf-8")
    start_process_section = script.split("$proc = Start-Process", maxsplit=1)[1].split(
        "Set-Content -LiteralPath $PidFile",
        maxsplit=1,
    )[0]

    assert "DB_PASSWORD" not in start_process_section
    assert "$EffectiveDbPassword" not in start_process_section
    assert "$env:DB_PASSWORD = $EffectiveDbPassword" in script


def test_orchestrator_loop_launcher_verifies_pid_owner_before_stop() -> None:
    script = LAUNCHER.read_text(encoding="utf-8")

    assert "Set-StrictMode -Version Latest" in script
    assert "function Test-LoopCommandLine" in script
    assert "Get-CimInstance Win32_Process" in script
    assert "Test-LoopCommandLine -ProcessId $pidNum" in script
    assert "Get-Content -LiteralPath $PidFile" in script
    assert "Set-Content -LiteralPath $PidFile" in script
    assert "Remove-Item -LiteralPath $PidFile -Force" in script
    assert "Remove-Item $PidFile" not in script


def test_orchestrator_loop_worker_uses_literal_paths_and_inherited_env() -> None:
    script = WORKER.read_text(encoding="utf-8")

    assert "Set-StrictMode -Version Latest" in script
    assert "-EncodedCommand" not in script
    assert "DB_PASSWORD" not in script
    assert "Set-Location -LiteralPath $RepoRoot" in script
    assert "Add-Content -LiteralPath $LogFile" in script
    assert "Test-Path -LiteralPath $NightReportFile" in script
    assert "Get-Item -LiteralPath $NightReportFile" in script
