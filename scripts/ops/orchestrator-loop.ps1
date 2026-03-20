param(
    [ValidateSet('start','stop','status','tail')]
    [string]$Action = 'status',
    [int]$IntervalSeconds = 600,
    [int]$ReportIntervalMinutes = 30,
    [string]$DbHost = '127.0.0.1',
    [string]$DbPort = '5432',
    [string]$DbName = 'ctoa',
    [string]$DbUser = 'ctoa'
)

$ErrorActionPreference = 'Stop'

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$PythonExe = Join-Path $RepoRoot '.venv\Scripts\python.exe'
$RuntimeDir = Join-Path $RepoRoot 'runtime'
$LogsDir = Join-Path $RepoRoot 'logs'
$PidFile = Join-Path $RuntimeDir 'orchestrator-loop.pid'
$LogFile = Join-Path $LogsDir 'orchestrator-loop.log'
$NightReportScript = Join-Path $RepoRoot 'scripts\ops\night-report.py'
$NightReportFile = Join-Path $RuntimeDir 'night-report.md'

New-Item -ItemType Directory -Path $RuntimeDir -Force | Out-Null
New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
$EffectiveDbPassword = if ($env:DB_PASSWORD) { $env:DB_PASSWORD } else { 'ctoa_local_dev' }

function Get-LoopProcess {
    if (-not (Test-Path $PidFile)) {
        return $null
    }

    $pidText = (Get-Content $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
    if (-not $pidText) {
        return $null
    }

    $pidNum = 0
    if (-not [int]::TryParse($pidText, [ref]$pidNum)) {
        return $null
    }

    try {
        $proc = Get-Process -Id $pidNum -ErrorAction Stop
    }
    catch {
        return $null
    }

    return $proc
}

function Start-Loop {
    $existing = Get-LoopProcess
    if ($null -ne $existing) {
        Write-Output "orchestrator-loop already running (PID=$($existing.Id))"
        return
    }

    if (-not (Test-Path $PythonExe)) {
        throw "Python executable not found: $PythonExe"
    }

    $loopScript = @"
`$ErrorActionPreference = 'Continue'
Set-Location '$RepoRoot'
`$env:DB_HOST = '$DbHost'
`$env:DB_PORT = '$DbPort'
`$env:DB_NAME = '$DbName'
`$env:DB_USER = '$DbUser'
`$env:DB_PASSWORD = '$EffectiveDbPassword'

while (`$true) {
    `$ts = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ssK')
    Add-Content -Path '$LogFile' -Value "[`$ts] LOOP_TICK start"
    `$runOutput = & '$PythonExe' -m runner.agents.orchestrator 2>&1
    `$code = `$LASTEXITCODE
    if (`$null -ne `$runOutput) {
        `$runOutput | ForEach-Object { Add-Content -Path '$LogFile' -Value (`$_.ToString()) }
    }
    `$ts2 = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ssK')
    Add-Content -Path '$LogFile' -Value "[`$ts2] LOOP_TICK end exit=`$code sleep=${IntervalSeconds}s"

    `$reportDue = -not (Test-Path '$NightReportFile')
    if (-not `$reportDue) {
        try {
            `$reportAgeMinutes = ((Get-Date) - (Get-Item '$NightReportFile').LastWriteTime).TotalMinutes
            `$reportDue = `$reportAgeMinutes -ge ${ReportIntervalMinutes}
        }
        catch {
            `$reportDue = `$true
        }
    }

    if (`$reportDue -and (Test-Path '$NightReportScript')) {
        `$reportOutput = & '$PythonExe' '$NightReportScript' --log-file '$LogFile' --report-file '$NightReportFile' 2>&1
        if (`$null -ne `$reportOutput) {
            `$reportOutput | ForEach-Object { Add-Content -Path '$LogFile' -Value (`$_.ToString()) }
        }
    }

    Start-Sleep -Seconds $IntervalSeconds
}
"@

    $encoded = [Convert]::ToBase64String([System.Text.Encoding]::Unicode.GetBytes($loopScript))
    $proc = Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile','-WindowStyle','Hidden','-EncodedCommand',$encoded) -PassThru
    Set-Content -Path $PidFile -Value $proc.Id -Encoding ascii

    Write-Output "orchestrator-loop started (PID=$($proc.Id))"
    Write-Output "log: $LogFile"
}

function Stop-Loop {
    $proc = Get-LoopProcess
    if ($null -eq $proc) {
        if (Test-Path $PidFile) {
            Remove-Item $PidFile -Force
        }
        Write-Output 'orchestrator-loop is not running'
        return
    }

    Stop-Process -Id $proc.Id -Force
    if (Test-Path $PidFile) {
        Remove-Item $PidFile -Force
    }
    Write-Output "orchestrator-loop stopped (PID=$($proc.Id))"
}

function Show-Status {
    $proc = Get-LoopProcess
    if ($null -eq $proc) {
        Write-Output 'orchestrator-loop status: stopped'
    }
    else {
        Write-Output "orchestrator-loop status: running (PID=$($proc.Id), Start=$($proc.StartTime))"
    }
    Write-Output "log: $LogFile"
    Write-Output "night report: $NightReportFile"
}

function Get-LogTail {
    if (-not (Test-Path $LogFile)) {
        Write-Output "log file not found: $LogFile"
        return
    }
    Get-Content -Path $LogFile -Tail 80
}

switch ($Action) {
    'start' { Start-Loop }
    'stop' { Stop-Loop }
    'status' { Show-Status }
    'tail' { Get-LogTail }
}
