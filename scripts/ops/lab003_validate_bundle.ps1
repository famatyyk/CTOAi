param(
    [string]$BaseUrl = "http://127.0.0.1:8787",
    [switch]$IncludeBody
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
$smokeScript = Join-Path $PSScriptRoot "lab003_mobile_proxy_smoke.ps1"

if (-not (Test-Path $pythonExe)) {
    throw "Python executable not found: $pythonExe"
}

if (-not (Test-Path $smokeScript)) {
    throw "Smoke script not found: $smokeScript"
}

& $pythonExe -m labs.projects.intel_news_watcher.watcher --print-json
$watcherExit = $LASTEXITCODE
if ($watcherExit -ne 0) {
    throw "Watcher tick failed with exit code $watcherExit"
}

$smokeArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $smokeScript,
    "-BaseUrl", $BaseUrl
)
if ($IncludeBody.IsPresent) {
    $smokeArgs += "-IncludeBody"
}

& powershell @smokeArgs
$smokeExit = $LASTEXITCODE
if ($smokeExit -ne 0) {
    throw "Mobile proxy smoke failed with exit code $smokeExit"
}

$result = [ordered]@{
    ok = $true
    checked_at = (Get-Date).ToString("o")
    base_url = $BaseUrl
    watcher_tick = "ok"
    mobile_proxy_smoke = "ok"
}

$result | ConvertTo-Json -Depth 6
