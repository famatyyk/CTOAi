param(
    [string]$TaskName = 'CTOA-Phase5-MorningSync'
)

$ErrorActionPreference = 'Stop'

& schtasks /End /TN $TaskName | Out-Null
& schtasks /Delete /F /TN $TaskName | Out-Null

Write-Output "[phase5-task] removed"
Write-Output "[phase5-task] name=$TaskName"
