param(
    [int]$IntervalSeconds = 15,
    [string]$LogPath = "$env:LOCALAPPDATA\CTOA\logs\mythibia-sync-watcher.log",
    [string]$SyncScriptPath = "",
    [int]$MaxLogSizeMB = 5,
    [int]$MaxArchives = 10
)

Set-StrictMode -Version Latest
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

function Resolve-RepoScriptPath {
    param([Parameter(Mandatory = $true)][string]$Candidate)

    $repoRoot = [System.IO.Path]::GetFullPath((Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path).TrimEnd([char[]]@('\', '/'))
    $resolved = [System.IO.Path]::GetFullPath((Resolve-Path -LiteralPath $Candidate).Path)
    $repoPrefix = $repoRoot + [System.IO.Path]::DirectorySeparatorChar

    if (-not $resolved.StartsWith($repoPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "SyncScriptPath must stay under $repoRoot; got $resolved"
    }
    if ([System.IO.Path]::GetExtension($resolved) -ne '.ps1') {
        throw "SyncScriptPath must point to a .ps1 file: $resolved"
    }

    return $resolved
}

$SyncScriptPath = Resolve-RepoScriptPath -Candidate $SyncScriptPath

$logDir = Split-Path -Parent $LogPath
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

function Assert-LogChildPath {
    param(
        [string]$Root,
        [string]$Candidate
    )

    $resolvedRoot = [System.IO.Path]::GetFullPath($Root)
    $resolvedCandidate = [System.IO.Path]::GetFullPath($Candidate)
    $trimChars = @([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
    $rootPrefix = $resolvedRoot.TrimEnd($trimChars) + [System.IO.Path]::DirectorySeparatorChar

    if (($resolvedCandidate -ne $resolvedRoot) -and (-not $resolvedCandidate.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase))) {
        throw "Refusing log archive path outside log directory: $resolvedCandidate"
    }

    return $resolvedCandidate
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
    Add-Content -LiteralPath $LogPath -Value "[$ts] $Message" -Encoding UTF8
}

function Rotate-LogIfNeeded {
    if (-not (Test-Path -LiteralPath $LogPath)) {
        return
    }

    $maxBytes = $MaxLogSizeMB * 1MB
    $logFile = Get-Item -LiteralPath $LogPath -ErrorAction SilentlyContinue
    if (-not $logFile -or $logFile.Length -lt $maxBytes) {
        return
    }

    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($LogPath)
    $ext = [System.IO.Path]::GetExtension($LogPath)
    $stamp = (Get-Date).ToString('yyyyMMdd-HHmmss')
    $archivePath = Assert-LogChildPath -Root $logDir -Candidate (Join-Path $logDir ("{0}-{1}{2}" -f $baseName, $stamp, $ext))

    Move-Item -LiteralPath $LogPath -Destination $archivePath -Force
    New-Item -ItemType File -Path $LogPath -Force | Out-Null

    $pattern = "{0}-*{1}" -f $baseName, $ext
    $archives = Get-ChildItem -Path $logDir -Filter $pattern -File | Sort-Object LastWriteTime -Descending
    if ($archives.Count -gt $MaxArchives) {
        $archives | Select-Object -Skip $MaxArchives | ForEach-Object {
            $archiveToRemove = Assert-LogChildPath -Root $logDir -Candidate $_.FullName
            Remove-Item -LiteralPath $archiveToRemove -Force
        }
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
