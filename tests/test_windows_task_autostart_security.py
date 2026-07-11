from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OPS = ROOT / "scripts" / "ops"
GUARD = OPS / "windows-task-guard.ps1"


TASK_SCRIPTS = [
    OPS / "install-mythibia-watcher-task.ps1",
    OPS / "remove-mythibia-watcher-task.ps1",
    OPS / "install-mythibia-watchdog-task.ps1",
    OPS / "install-mythibia-autosync-task.ps1",
    OPS / "remove-mythibia-autosync-task.ps1",
    OPS / "install-phase5-morning-sync-task.ps1",
    OPS / "remove-phase5-morning-sync-task.ps1",
]


def test_windows_task_guard_constrains_names_paths_and_logs() -> None:
    script = GUARD.read_text(encoding="utf-8")

    assert "function Assert-CtoaTaskName" in script
    assert "function Assert-CtoaRunKeyName" in script
    assert "^CTOA-" in script
    assert "function Resolve-RepoChildPath" in script
    assert "StartsWith($baseWithSeparator" in script
    assert "Test-Path -LiteralPath $resolvedChild" in script
    assert "function Resolve-CtoaLogPath" in script
    assert "LOCALAPPDATA" in script
    assert "LogPath must stay under" in script
    assert "GetExtension($resolvedLog) -ne '.log'" in script
    assert "function Format-CtoaCommandArgument" in script


def test_task_installers_and_removers_use_shared_guard() -> None:
    for path in TASK_SCRIPTS:
        script = path.read_text(encoding="utf-8")
        assert "Set-StrictMode -Version Latest" in script, str(path)
        assert "windows-task-guard.ps1" in script, str(path)
        assert "Assert-CtoaTaskName -TaskName $TaskName" in script, str(path)


def test_watcher_autostart_fallback_is_constrained() -> None:
    install = (OPS / "install-mythibia-watcher-task.ps1").read_text(encoding="utf-8")
    remove = (OPS / "remove-mythibia-watcher-task.ps1").read_text(encoding="utf-8")

    assert "Assert-CtoaRunKeyName -RunKeyName $RunKeyName" in install
    assert "Resolve-CtoaLogPath -LogPath $LogPath" in install
    assert "Set-ItemProperty -LiteralPath $runKeyPath" in install
    assert "Format-CtoaCommandArgument -Value $watcherScript" in install
    assert "Format-CtoaCommandArgument -Value $LogPath" in install

    assert "Assert-CtoaRunKeyName -RunKeyName $RunKeyName" in remove
    assert "Get-ItemProperty -LiteralPath $runKeyPath" in remove
    assert "Remove-ItemProperty -LiteralPath $runKeyPath" in remove


def test_task_installers_quote_only_guarded_repo_child_paths() -> None:
    installers = [
        OPS / "install-mythibia-watchdog-task.ps1",
        OPS / "install-mythibia-autosync-task.ps1",
        OPS / "install-phase5-morning-sync-task.ps1",
    ]

    for path in installers:
        script = path.read_text(encoding="utf-8")
        assert "Resolve-RepoChildPath" in script, str(path)
        assert " -RequireExists" in script, str(path)
        assert "Format-CtoaCommandArgument -Value" in script, str(path)
        assert "Test-Path $" not in script, str(path)


def test_hidden_runner_accepts_only_repo_ps1_targets() -> None:
    script = (OPS / "run-hidden.vbs").read_text(encoding="utf-8")

    assert "GetAbsolutePathName(scriptPath)" in script
    assert 'GetExtensionName(scriptPath)) <> "ps1"' in script
    assert "FileExists(scriptPath)" in script
    assert 'repoRoot & "\\"' in script
    assert "WScript.Quit 4" in script
    assert 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File' in script
