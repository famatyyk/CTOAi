param(
    [string]$TaskName = 'CTOA-Mythibia-AutoSync'
)

$ErrorActionPreference = 'Stop'

& schtasks /Delete /F /TN $TaskName | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to delete task $TaskName (exit code $LASTEXITCODE)"
}

Write-Output "[task] removed"
Write-Output "[task] name=$TaskName"
