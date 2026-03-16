param(
    [string]$TaskName = 'CTOA-Mythibia-AutoSync',
    [int]$IntervalMinutes = 1
)

$ErrorActionPreference = 'Stop'

if ($IntervalMinutes -lt 1) {
    throw 'IntervalMinutes must be >= 1'
}

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$syncScript = Join-Path $repoRoot 'scripts\ops\sync-mythibia-client.ps1'
$hiddenRunner = Join-Path $repoRoot 'scripts\ops\run-hidden.vbs'

if (-not (Test-Path $syncScript)) {
    throw "Sync script not found: $syncScript"
}

if (-not (Test-Path $hiddenRunner)) {
    throw "Hidden runner not found: $hiddenRunner"
}

$taskCommand = "wscript.exe //B //Nologo `"$hiddenRunner`" `"$syncScript`""

# Create or overwrite a per-minute task to keep local client scripts in sync after one-click runs.
& schtasks /Create /F /TN $TaskName /SC MINUTE /MO $IntervalMinutes /TR $taskCommand | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create scheduled task (exit code $LASTEXITCODE)"
}

& schtasks /Run /TN $TaskName | Out-Null

$taskInfo = & schtasks /Query /TN $TaskName /V /FO LIST
if ($LASTEXITCODE -ne 0) {
    throw "Task created but query failed (exit code $LASTEXITCODE)"
}

Write-Output "[task] installed"
Write-Output "[task] name=$TaskName"
Write-Output "[task] interval_minutes=$IntervalMinutes"
Write-Output "[task] command=$taskCommand"
Write-Output "[task] query_start"
Write-Output $taskInfo
Write-Output "[task] query_end"
