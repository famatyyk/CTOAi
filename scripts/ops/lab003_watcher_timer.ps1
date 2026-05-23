param(
    [int]$IntervalSeconds = 300,
    [string]$LogPath = "$env:LOCALAPPDATA\CTOA\logs\lab003-watcher-timer.log",
    [string]$RepoRoot = "",
    [int]$MaxIterations = 0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($IntervalSeconds -lt 5) {
    throw "IntervalSeconds must be >= 5"
}

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
}

$pythonExe = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    throw "Python executable not found: $pythonExe"
}

$logDir = Split-Path -Parent $LogPath
if (-not [string]::IsNullOrWhiteSpace($logDir) -and -not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

function Write-Log {
    param([string]$Message)

    if ([string]::IsNullOrWhiteSpace($LogPath)) {
        return
    }

    $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    Add-Content -Path $LogPath -Value "[$ts] $Message" -Encoding UTF8
}

Write-Log "lab003 watcher timer started interval=${IntervalSeconds}s repo=$RepoRoot"

$iteration = 0
while ($true) {
    $iteration += 1
    $startedAt = Get-Date

    try {
        & $pythonExe -m labs.projects.intel_news_watcher.watcher --print-json
        $exitCode = $LASTEXITCODE
        $durationMs = [int]((Get-Date) - $startedAt).TotalMilliseconds

        if ($exitCode -ne 0) {
            Write-Log "tick failed iteration=$iteration exit_code=$exitCode duration_ms=$durationMs"
        } else {
            Write-Log "tick ok iteration=$iteration duration_ms=$durationMs"
        }
    }
    catch {
        $msg = $_.Exception.Message
        Write-Log "tick exception iteration=$iteration message=$msg"
    }

    if ($MaxIterations -gt 0 -and $iteration -ge $MaxIterations) {
        Write-Log "lab003 watcher timer finished after $iteration iterations"
        break
    }

    Start-Sleep -Seconds $IntervalSeconds
}
