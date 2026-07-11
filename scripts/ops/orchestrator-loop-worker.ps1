param(
    [ValidateRange(1, 86400)]
    [int]$IntervalSeconds = 600,
    [ValidateRange(1, 10080)]
    [int]$ReportIntervalMinutes = 30
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$PythonExe = Join-Path $RepoRoot '.venv\Scripts\python.exe'
$RuntimeDir = Join-Path $RepoRoot 'runtime'
$LogsDir = Join-Path $RepoRoot 'logs'
$LogFile = Join-Path $LogsDir 'orchestrator-loop.log'
$NightReportScript = Join-Path $RepoRoot 'scripts\ops\night-report.py'
$NightReportFile = Join-Path $RuntimeDir 'night-report.md'

New-Item -ItemType Directory -Path $RuntimeDir -Force | Out-Null
New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
Set-Location -LiteralPath $RepoRoot

function Write-LoopLog {
    param([Parameter(Mandatory = $true)][string]$Message)

    $ts = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ssK')
    Add-Content -LiteralPath $LogFile -Value "[$ts] $Message"
}

if (-not (Test-Path -LiteralPath $PythonExe)) {
    Write-LoopLog "ERROR python executable not found: $PythonExe"
    throw "Python executable not found: $PythonExe"
}

while ($true) {
    Write-LoopLog 'LOOP_TICK start'

    $code = 0
    try {
        $runOutput = & $PythonExe -m runner.agents.orchestrator 2>&1
        $code = $LASTEXITCODE
        if ($null -ne $runOutput) {
            $runOutput | ForEach-Object { Add-Content -LiteralPath $LogFile -Value ($_.ToString()) }
        }
    }
    catch {
        $code = 1
        Add-Content -LiteralPath $LogFile -Value $_.Exception.Message
    }

    Write-LoopLog "LOOP_TICK end exit=$code sleep=${IntervalSeconds}s"

    $reportDue = -not (Test-Path -LiteralPath $NightReportFile)
    if (-not $reportDue) {
        try {
            $reportAgeMinutes = ((Get-Date) - (Get-Item -LiteralPath $NightReportFile).LastWriteTime).TotalMinutes
            $reportDue = $reportAgeMinutes -ge $ReportIntervalMinutes
        }
        catch {
            $reportDue = $true
        }
    }

    if ($reportDue -and (Test-Path -LiteralPath $NightReportScript)) {
        try {
            $reportOutput = & $PythonExe $NightReportScript --log-file $LogFile --report-file $NightReportFile 2>&1
            if ($null -ne $reportOutput) {
                $reportOutput | ForEach-Object { Add-Content -LiteralPath $LogFile -Value ($_.ToString()) }
            }
        }
        catch {
            Add-Content -LiteralPath $LogFile -Value $_.Exception.Message
        }
    }

    Start-Sleep -Seconds $IntervalSeconds
}
