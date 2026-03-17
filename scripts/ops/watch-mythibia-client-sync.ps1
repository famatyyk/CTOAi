param(
    [int]$IntervalSeconds = 15,
    [string]$LogPath = "$env:LOCALAPPDATA\CTOA\logs\mythibia-sync-watcher.log",
    [string]$SyncScriptPath = "",
    [int]$MaxLogSizeMB = 5,
    [int]$MaxArchives = 10
)

$ErrorActionPreference = 'Stop'

if ($IntervalSeconds -lt 5) {
    throw 'IntervalSeconds must be >= 5'
}

if ($MaxLogSizeMB -lt 1) {
    throw 'MaxLogSizeMB must be >= 1'
}

if ($MaxArchives -lt 1) {
    throw 'MaxArchives must be >= 1'
}

if ([string]::IsNullOrWhiteSpace($SyncScriptPath)) {
    $repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
    $SyncScriptPath = Join-Path $repoRoot 'scripts\ops\sync-mythibia-client.ps1'
}

if (-not (Test-Path $SyncScriptPath)) {
    throw "Sync script not found: $SyncScriptPath"
}

$logDir = Split-Path -Parent $LogPath
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

$mutexName = 'Global\CTOA_Mythibia_Watcher'
$createdNew = $false
$mutex = New-Object System.Threading.Mutex($true, $mutexName, [ref]$createdNew)
if (-not $createdNew) {
    exit 0
}

function Write-Log {
    param([string]$Message)
    Rotate-LogIfNeeded
    $ts = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    Add-Content -Path $LogPath -Value "[$ts] $Message" -Encoding UTF8
}

function Rotate-LogIfNeeded {
    if (-not (Test-Path $LogPath)) {
        return
    }

    $maxBytes = $MaxLogSizeMB * 1MB
    $logFile = Get-Item -Path $LogPath -ErrorAction SilentlyContinue
    if (-not $logFile -or $logFile.Length -lt $maxBytes) {
        return
    }

    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($LogPath)
    $ext = [System.IO.Path]::GetExtension($LogPath)
    $stamp = (Get-Date).ToString('yyyyMMdd-HHmmss')
    $archivePath = Join-Path $logDir ("{0}-{1}{2}" -f $baseName, $stamp, $ext)

    Move-Item -Path $LogPath -Destination $archivePath -Force
    New-Item -ItemType File -Path $LogPath -Force | Out-Null

    $pattern = "{0}-*{1}" -f $baseName, $ext
    $archives = Get-ChildItem -Path $logDir -Filter $pattern -File | Sort-Object LastWriteTime -Descending
    if ($archives.Count -gt $MaxArchives) {
        $archives | Select-Object -Skip $MaxArchives | Remove-Item -Force
    }
}

Write-Log "watcher started interval=${IntervalSeconds}s sync=$SyncScriptPath"

try {
    while ($true) {
        $start = Get-Date
        try {
            & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $SyncScriptPath *> $null
            if ($LASTEXITCODE -ne 0) {
                Write-Log "sync failed exit_code=$LASTEXITCODE"
            } else {
                $elapsed = [int]((Get-Date) - $start).TotalMilliseconds
                Write-Log "sync ok duration_ms=$elapsed"
            }
        }
        catch {
            $msg = $_.Exception.Message
            Write-Log "sync exception message=$msg"
        }

        Start-Sleep -Seconds $IntervalSeconds
    }
}
finally {
    Write-Log 'watcher stopped'
    $mutex.ReleaseMutex() | Out-Null
    $mutex.Dispose()
}
