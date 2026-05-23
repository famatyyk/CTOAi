param(
    [string]$RepoRoot = ''
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
}

$repoRootResolved = (Resolve-Path $RepoRoot).Path
$pythonExe = Join-Path $repoRootResolved '.venv\Scripts\python.exe'
$syncScript = Join-Path $repoRootResolved 'scripts\ops\phase5_nightly_sync.py'
$jsonOut = Join-Path $repoRootResolved 'runtime\ci-artifacts\phase5-nightly-checklist.json'
$logDir = Join-Path $repoRootResolved 'runtime\logs'
$logFile = Join-Path $logDir 'phase5-morning-sync.log'

if (-not (Test-Path $pythonExe)) {
    throw "Python executable not found: $pythonExe"
}
if (-not (Test-Path $syncScript)) {
    throw "Sync script not found: $syncScript"
}
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

$startTs = (Get-Date).ToString('o')
"=== phase5-morning-sync start $startTs ===" | Add-Content -Path $logFile

& $pythonExe $syncScript --require-complete --auto-close-step9 --checklist-json-out $jsonOut 2>&1 | Tee-Object -FilePath $logFile -Append
$rc = $LASTEXITCODE

$endTs = (Get-Date).ToString('o')
"=== phase5-morning-sync end $endTs rc=$rc ===" | Add-Content -Path $logFile

exit $rc
