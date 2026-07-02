param(
    [string]$Url = $env:CTOA_CONTROL_CENTER_URL
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($Url)) {
    $Url = "http://127.0.0.1:3000/control-center"
}

Write-Host "Opening CTOAi Control Center: $Url"
Start-Process $Url
