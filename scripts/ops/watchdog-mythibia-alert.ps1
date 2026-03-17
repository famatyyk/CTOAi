param(
    [string]$ClientRoot = "$env:APPDATA\Mythibia\MythibiaV2",
    [string]$ReportName = 'manifest_vs_disk_report.txt'
)

$ErrorActionPreference = 'Stop'

$reportPath = Join-Path $ClientRoot $ReportName
$statePath = Join-Path $ClientRoot 'watchdog_alert.state'

if (-not (Test-Path $ClientRoot)) {
    New-Item -ItemType Directory -Path $ClientRoot -Force | Out-Null
}

if (-not (Test-Path $reportPath)) {
    exit 0
}

$content = Get-Content $reportPath -Raw
$missing = 0
$match = [regex]::Match($content, 'MissingOnDiskCount:\s*(\d+)')
if ($match.Success) {
    $missing = [int]$match.Groups[1].Value
}

$previous = -1
if (Test-Path $statePath) {
    $raw = Get-Content $statePath -ErrorAction SilentlyContinue
    if ($raw -match '^\d+$') { $previous = [int]$raw }
}

Set-Content -Path $statePath -Value "$missing" -Encoding ASCII

# Alert only on transition from healthy to degraded to avoid spam.
if ($missing -gt 0 -and $previous -le 0) {
    $alertLog = Join-Path $ClientRoot 'watchdog_alert.log'
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ALERT MissingOnDiskCount=$missing report=$reportPath"
    Add-Content -Path $alertLog -Value $line -Encoding UTF8
}
