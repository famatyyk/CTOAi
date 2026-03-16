param(
    [string]$TaskName = 'CTOA-Mythibia-WatchdogAlert',
    [int]$IntervalMinutes = 1
)

$ErrorActionPreference = 'Stop'

if ($IntervalMinutes -lt 1) {
    throw 'IntervalMinutes must be >= 1'
}

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$watchdogScript = Join-Path $repoRoot 'scripts\ops\watchdog-mythibia-alert.ps1'
$hiddenRunner = Join-Path $repoRoot 'scripts\ops\run-hidden.vbs'

if (-not (Test-Path $watchdogScript)) {
    throw "Watchdog script not found: $watchdogScript"
}

if (-not (Test-Path $hiddenRunner)) {
    throw "Hidden runner not found: $hiddenRunner"
}

$taskCommand = "wscript.exe //B //Nologo `"$hiddenRunner`" `"$watchdogScript`""

& schtasks /Create /F /TN $TaskName /SC MINUTE /MO $IntervalMinutes /TR $taskCommand | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create watchdog task (exit code $LASTEXITCODE)"
}

& schtasks /Run /TN $TaskName | Out-Null

$taskInfo = & schtasks /Query /TN $TaskName /V /FO LIST
if ($LASTEXITCODE -ne 0) {
    throw "Watchdog task created but query failed (exit code $LASTEXITCODE)"
}

Write-Output "[task] installed"
Write-Output "[task] name=$TaskName"
Write-Output "[task] interval_minutes=$IntervalMinutes"
Write-Output "[task] command=$taskCommand"
Write-Output "[task] query_start"
Write-Output $taskInfo
Write-Output "[task] query_end"
