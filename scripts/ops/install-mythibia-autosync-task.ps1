param(
    [string]$TaskName = 'CTOA-Mythibia-AutoSync',
    [int]$IntervalMinutes = 1
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'windows-task-guard.ps1')

if ($IntervalMinutes -lt 1) {
    throw 'IntervalMinutes must be >= 1'
}

$TaskName = Assert-CtoaTaskName -TaskName $TaskName

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$syncScript = Resolve-RepoChildPath -RepoRoot $repoRoot -ChildPath (Join-Path $repoRoot 'scripts\ops\sync-mythibia-client.ps1') -Label 'SyncScript' -RequireExists
$hiddenRunner = Resolve-RepoChildPath -RepoRoot $repoRoot -ChildPath (Join-Path $repoRoot 'scripts\ops\run-hidden.vbs') -Label 'HiddenRunner' -RequireExists

$taskCommand = "wscript.exe //B //Nologo $(Format-CtoaCommandArgument -Value $hiddenRunner) $(Format-CtoaCommandArgument -Value $syncScript)"

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
