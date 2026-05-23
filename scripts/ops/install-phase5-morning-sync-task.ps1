param(
    [string]$TaskName = 'CTOA-Phase5-MorningSync',
    [string]$StartTime = '07:10'
)

$ErrorActionPreference = 'Stop'

if ($StartTime -notmatch '^\d{2}:\d{2}$') {
    throw 'StartTime must be HH:mm format, e.g. 07:10'
}

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$runnerScript = Join-Path $repoRoot 'scripts\ops\run-phase5-morning-sync.ps1'

if (-not (Test-Path $runnerScript)) {
    throw "Runner script not found: $runnerScript"
}

$taskCommand = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$runnerScript`""

& schtasks /Create /F /TN $TaskName /SC DAILY /ST $StartTime /TR $taskCommand | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create scheduled task (exit code $LASTEXITCODE)"
}

$taskInfo = & schtasks /Query /TN $TaskName /V /FO LIST
if ($LASTEXITCODE -ne 0) {
    throw "Task created but query failed (exit code $LASTEXITCODE)"
}

Write-Output "[phase5-task] installed"
Write-Output "[phase5-task] name=$TaskName"
Write-Output "[phase5-task] start_time=$StartTime"
Write-Output "[phase5-task] command=$taskCommand"
Write-Output "[phase5-task] query_start"
Write-Output $taskInfo
Write-Output "[phase5-task] query_end"
