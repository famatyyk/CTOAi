[CmdletBinding()]
param(
    [int]$ApiPort = 8011,
    [int]$MobilePort = 8787,
    [int]$WebPort = 3011
)

$ErrorActionPreference = "Stop"

function Test-PortListening {
    param([int]$Port)
    return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

function Wait-HttpOk {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 20
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            $resp = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 3
            if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500) {
                return $true
            }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    } while ((Get-Date) -lt $deadline)

    return $false
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
$webDir = Join-Path $repoRoot "web"
$envPath = Join-Path $repoRoot ".env"

if (-not (Test-Path $pythonExe)) {
    throw "Missing Python interpreter at $pythonExe"
}

if (Test-Path $envPath) {
    Get-Content $envPath |
        Where-Object { $_ -and -not $_.StartsWith("#") -and $_ -match "=" } |
        ForEach-Object {
            $name, $value = $_ -split "=", 2
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
}

if ([string]::IsNullOrWhiteSpace($env:CTOA_MOBILE_TOKEN)) {
    Set-Item -Path Env:CTOA_MOBILE_TOKEN -Value "local-dev-token"
}
$env:CTOA_CAPABILITY_MOBILE_CONSOLE = "1"

if (-not (Test-PortListening -Port $ApiPort)) {
    Start-Process -FilePath $pythonExe `
        -ArgumentList "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "$ApiPort" `
        -WorkingDirectory $repoRoot `
        -WindowStyle Hidden | Out-Null
}

if (-not (Test-PortListening -Port $MobilePort)) {
    Start-Process -FilePath $pythonExe `
        -ArgumentList "-m", "uvicorn", "mobile_console.app:app", "--host", "127.0.0.1", "--port", "$MobilePort" `
        -WorkingDirectory $repoRoot `
        -WindowStyle Hidden | Out-Null
}

if (-not (Test-PortListening -Port $WebPort)) {
    $cmd = "set VPS_API_URL=http://127.0.0.1:$ApiPort&& set NEXT_PUBLIC_API_URL=http://127.0.0.1:$ApiPort&& npm run dev -- --port $WebPort"
    Start-Process -FilePath "cmd.exe" `
        -ArgumentList "/d", "/c", $cmd `
        -WorkingDirectory $webDir `
        -WindowStyle Hidden | Out-Null
}

$apiOk = Wait-HttpOk -Url "http://127.0.0.1:$ApiPort/api/status" -TimeoutSeconds 20
$mobileOk = Wait-HttpOk -Url "http://127.0.0.1:$MobilePort" -TimeoutSeconds 20
$webOk = Wait-HttpOk -Url "http://127.0.0.1:$WebPort/api/status" -TimeoutSeconds 25

Write-Output "API:    http://127.0.0.1:$ApiPort/api/status  => $apiOk"
Write-Output "Mobile: http://127.0.0.1:$MobilePort           => $mobileOk"
Write-Output "Web:    http://127.0.0.1:$WebPort              => $webOk"
