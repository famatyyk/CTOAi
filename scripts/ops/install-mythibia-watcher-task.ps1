param(
    [string]$TaskName = 'CTOA-Mythibia-Watcher',
    [int]$IntervalSeconds = 15,
    [string]$LogPath = "$env:LOCALAPPDATA\CTOA\logs\mythibia-sync-watcher.log",
    [string]$RunKeyName = 'CTOA-Mythibia-Watcher'
)

$ErrorActionPreference = 'Stop'

if ($IntervalSeconds -lt 5) {
    throw 'IntervalSeconds must be >= 5'
}

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$watcherScript = Join-Path $repoRoot 'scripts\ops\watch-mythibia-client-sync.ps1'

if (-not (Test-Path $watcherScript)) {
    throw "Watcher script not found: $watcherScript"
}

$taskCommand = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$watcherScript`" -IntervalSeconds $IntervalSeconds -LogPath `"$LogPath`""

# Start at user logon and keep a single watcher process running continuously.
& schtasks /Create /F /TN $TaskName /SC ONLOGON /TR $taskCommand | Out-Null
$taskCreateExit = $LASTEXITCODE
$autostartMode = 'scheduled-task'

if ($taskCreateExit -ne 0) {
    # Fallback for environments where ONLOGON scheduled task creation is restricted.
    $runKeyPath = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
    Set-ItemProperty -Path $runKeyPath -Name $RunKeyName -Value $taskCommand
    $autostartMode = 'hkcu-run'
}

$taskInfo = ''
if ($autostartMode -eq 'scheduled-task') {
    & schtasks /Run /TN $TaskName | Out-Null
    $taskInfo = & schtasks /Query /TN $TaskName /V /FO LIST
} else {
    Start-Process -WindowStyle Hidden -FilePath 'powershell.exe' -ArgumentList @(
        '-NoProfile',
        '-ExecutionPolicy',
        'Bypass',
        '-File',
        $watcherScript,
        '-IntervalSeconds',
        $IntervalSeconds,
        '-LogPath',
        $LogPath
    ) | Out-Null
}

Write-Output "[watcher-task] installed"
Write-Output "[watcher-task] name=$TaskName"
Write-Output "[watcher-task] interval_seconds=$IntervalSeconds"
Write-Output "[watcher-task] log_path=$LogPath"
Write-Output "[watcher-task] autostart_mode=$autostartMode"
Write-Output "[watcher-task] command=$taskCommand"
if ($autostartMode -eq 'scheduled-task') {
    Write-Output "[watcher-task] query_start"
    Write-Output $taskInfo
    Write-Output "[watcher-task] query_end"
} else {
    Write-Output "[watcher-task] run_key=$RunKeyName"
}
