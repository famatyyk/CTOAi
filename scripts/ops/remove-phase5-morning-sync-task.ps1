param(
    [string]$TaskName = 'CTOA-Phase5-MorningSync'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'windows-task-guard.ps1')

$TaskName = Assert-CtoaTaskName -TaskName $TaskName

& schtasks /End /TN $TaskName | Out-Null
& schtasks /Delete /F /TN $TaskName | Out-Null

Write-Output "[phase5-task] removed"
Write-Output "[phase5-task] name=$TaskName"
