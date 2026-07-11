from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ops" / "watch-mythibia-client-sync.ps1"


def _script_text() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_mythibia_watcher_uses_strict_mode_and_log_child_path_guard():
    script = _script_text()

    assert "Set-StrictMode -Version Latest" in script
    assert "function Assert-LogChildPath" in script
    assert "$rootPrefix = $resolvedRoot.TrimEnd($trimChars) + [System.IO.Path]::DirectorySeparatorChar" in script
    assert "Refusing log archive path outside log directory" in script


def test_mythibia_watcher_log_rotation_uses_literal_paths():
    script = _script_text()

    assert "Test-Path -LiteralPath $LogPath" in script
    assert "Get-Item -LiteralPath $LogPath" in script
    assert "Add-Content -LiteralPath $LogPath" in script
    assert "Move-Item -LiteralPath $LogPath -Destination $archivePath -Force" in script
    assert "Remove-Item -LiteralPath $archiveToRemove -Force" in script
    assert "Remove-Item -Force" not in script.replace("Remove-Item -LiteralPath $archiveToRemove -Force", "")
    assert "Move-Item -Path $LogPath" not in script


def test_mythibia_watcher_archives_are_checked_before_delete():
    script = _script_text()
    rotation = script.split("function Rotate-LogIfNeeded", 1)[1].split('Write-Log "watcher started', 1)[0]

    assert "Assert-LogChildPath -Root $logDir -Candidate (Join-Path $logDir" in rotation
    assert "Assert-LogChildPath -Root $logDir -Candidate $_.FullName" in rotation


def test_mythibia_watcher_sync_script_path_is_repo_local_ps1():
    script = _script_text()

    assert "function Resolve-RepoScriptPath" in script
    assert "Resolve-Path -LiteralPath $Candidate" in script
    assert "SyncScriptPath must stay under $repoRoot" in script
    assert "GetExtension($resolved) -ne '.ps1'" in script
    assert "$SyncScriptPath = Resolve-RepoScriptPath -Candidate $SyncScriptPath" in script
