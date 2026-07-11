param(
    [string]$TaskName = 'CTOA-Mythibia-AutoSync'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'windows-task-guard.ps1')

$TaskName = Assert-CtoaTaskName -TaskName $TaskName

& schtasks /Delete /F /TN $TaskName | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to delete task $TaskName (exit code $LASTEXITCODE)"
}

Write-Output "[task] removed"
Write-Output "[task] name=$TaskName"
