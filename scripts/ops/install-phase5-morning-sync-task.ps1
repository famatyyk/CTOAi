param(
    [string]$TaskName = 'CTOA-Phase5-MorningSync',
    [string]$StartTime = '07:10'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'windows-task-guard.ps1')

$TaskName = Assert-CtoaTaskName -TaskName $TaskName
$StartTime = Assert-CtoaStartTime -StartTime $StartTime

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$runnerScript = Resolve-RepoChildPath -RepoRoot $repoRoot -ChildPath (Join-Path $repoRoot 'scripts\ops\run-phase5-morning-sync.ps1') -Label 'RunnerScript' -RequireExists

$taskCommand = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File $(Format-CtoaCommandArgument -Value $runnerScript)"

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
