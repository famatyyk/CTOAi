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

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$PythonExe = Join-Path $RepoRoot '.venv\Scripts\python.exe'
$RuntimeDir = Join-Path $RepoRoot 'runtime'
$LogsDir = Join-Path $RepoRoot 'logs'
$PidFile = Join-Path $RuntimeDir 'orchestrator-loop.pid'
$LogFile = Join-Path $LogsDir 'orchestrator-loop.log'
$NightReportScript = Join-Path $RepoRoot 'scripts\ops\night-report.py'
$NightReportFile = Join-Path $RuntimeDir 'night-report.md'
$LoopWorkerScript = Join-Path $RepoRoot 'scripts\ops\orchestrator-loop-worker.ps1'

New-Item -ItemType Directory -Path $RuntimeDir -Force | Out-Null
New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
$EffectiveDbPassword = if ($env:DB_PASSWORD) { $env:DB_PASSWORD } else { 'ctoa_local_dev' }

function Assert-ChildPath {
    param(
        [Parameter(Mandatory = $true)][string]$BasePath,
        [Parameter(Mandatory = $true)][string]$ChildPath,
        [Parameter(Mandatory = $true)][string]$Label
    )

    $resolvedBase = [System.IO.Path]::GetFullPath((Resolve-Path -LiteralPath $BasePath).Path).TrimEnd([char[]]@('\', '/'))
    $resolvedChild = [System.IO.Path]::GetFullPath($ChildPath)
    $baseWithSeparator = $resolvedBase + [System.IO.Path]::DirectorySeparatorChar

    if (
        -not $resolvedChild.Equals($resolvedBase, [System.StringComparison]::OrdinalIgnoreCase) -and
        -not $resolvedChild.StartsWith($baseWithSeparator, [System.StringComparison]::OrdinalIgnoreCase)
    ) {
        throw "$Label must stay under $resolvedBase; got $resolvedChild"
    }

    return $resolvedChild
}

$PidFile = Assert-ChildPath -BasePath $RuntimeDir -ChildPath $PidFile -Label 'PidFile'
$LogFile = Assert-ChildPath -BasePath $LogsDir -ChildPath $LogFile -Label 'LogFile'
$NightReportFile = Assert-ChildPath -BasePath $RuntimeDir -ChildPath $NightReportFile -Label 'NightReportFile'
$NightReportScript = Assert-ChildPath -BasePath $RepoRoot -ChildPath $NightReportScript -Label 'NightReportScript'
$LoopWorkerScript = Assert-ChildPath -BasePath $RepoRoot -ChildPath $LoopWorkerScript -Label 'LoopWorkerScript'
$PythonExe = Assert-ChildPath -BasePath $RepoRoot -ChildPath $PythonExe -Label 'PythonExe'

function Test-LoopCommandLine {
    param([Parameter(Mandatory = $true)][int]$ProcessId)

    try {
        $procInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction Stop
    }
    catch {
        return $false
    }

    if ($null -eq $procInfo -or [string]::IsNullOrWhiteSpace($procInfo.CommandLine)) {
        return $false
    }

    return (
        $procInfo.CommandLine.IndexOf($LoopWorkerScript, [System.StringComparison]::OrdinalIgnoreCase) -ge 0 -or
        $procInfo.CommandLine.IndexOf('orchestrator-loop-worker.ps1', [System.StringComparison]::OrdinalIgnoreCase) -ge 0
    )
}

function Get-LoopProcess {
    if (-not (Test-Path -LiteralPath $PidFile)) {
        return $null
    }

    $pidText = (Get-Content -LiteralPath $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
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

    if (-not (Test-LoopCommandLine -ProcessId $pidNum)) {
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

    if (-not (Test-Path -LiteralPath $PythonExe)) {
        throw "Python executable not found: $PythonExe"
    }

    if (-not (Test-Path -LiteralPath $LoopWorkerScript)) {
        throw "Loop worker script not found: $LoopWorkerScript"
    }

    $env:DB_HOST = $DbHost
    $env:DB_PORT = $DbPort
    $env:DB_NAME = $DbName
    $env:DB_USER = $DbUser
    $env:DB_PASSWORD = $EffectiveDbPassword

    $proc = Start-Process -FilePath 'powershell.exe' -ArgumentList @(
        '-NoProfile',
        '-ExecutionPolicy',
        'Bypass',
        '-WindowStyle',
        'Hidden',
        '-File',
        $LoopWorkerScript,
        '-IntervalSeconds',
        $IntervalSeconds,
        '-ReportIntervalMinutes',
        $ReportIntervalMinutes
    ) -PassThru
    Set-Content -LiteralPath $PidFile -Value $proc.Id -Encoding ascii

    Write-Output "orchestrator-loop started (PID=$($proc.Id))"
    Write-Output "log: $LogFile"
}

function Stop-Loop {
    $proc = Get-LoopProcess
    if ($null -eq $proc) {
        if (Test-Path -LiteralPath $PidFile) {
            Remove-Item -LiteralPath $PidFile -Force
        }
        Write-Output 'orchestrator-loop is not running'
        return
    }

    Stop-Process -Id $proc.Id -Force
    if (Test-Path -LiteralPath $PidFile) {
        Remove-Item -LiteralPath $PidFile -Force
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
    if (-not (Test-Path -LiteralPath $LogFile)) {
        Write-Output "log file not found: $LogFile"
        return
    }
    Get-Content -LiteralPath $LogFile -Tail 80
}

switch ($Action) {
    'start' { Start-Loop }
    'stop' { Stop-Loop }
    'status' { Show-Status }
    'tail' { Get-LogTail }
}
