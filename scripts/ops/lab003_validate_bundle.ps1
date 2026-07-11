param(
    [string]$BaseUrl = "http://127.0.0.1:8787",
    [string]$Username = "",
    [string]$LogPath = "$env:LOCALAPPDATA\CTOA\logs\lab003-validate-bundle.log",
    [switch]$IncludeBody
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Test-CtoaLoopbackHost {
    param([string]$HostName)

    return $HostName -in @("localhost", "127.0.0.1", "::1")
}

function Assert-LocalApiBaseUrl {
    param(
        [string]$Value,
        [string]$Name
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        throw "$Name must not be empty."
    }

    $candidate = $Value.Trim()
    [Uri]$uri = $null
    if (-not [Uri]::TryCreate($candidate, [UriKind]::Absolute, [ref]$uri)) {
        throw "$Name must be an absolute local HTTP(S) URL."
    }
    if ($uri.Scheme -notin @("http", "https")) {
        throw "$Name must use http:// or https://."
    }
    if ($uri.UserInfo) {
        throw "$Name must not include credentials."
    }
    if ($uri.Query -or $uri.Fragment) {
        throw "$Name must not include query strings or fragments."
    }
    if ($uri.AbsolutePath -and $uri.AbsolutePath -ne "/") {
        throw "$Name must not include a path."
    }
    if (-not (Test-CtoaLoopbackHost $uri.Host)) {
        throw "$Name must use localhost, 127.0.0.1, or [::1]."
    }

    return $uri.GetLeftPart([UriPartial]::Authority).TrimEnd("/")
}

function Get-CurrentPowerShellPath {
    $exeName = if ($PSVersionTable.PSEdition -eq "Core") { "pwsh.exe" } else { "powershell.exe" }
    $candidate = Join-Path $PSHOME $exeName
    if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
        throw "Current PowerShell executable was not found."
    }
    return $candidate
}

function Write-Log {
    param([string]$Message)

    if ([string]::IsNullOrWhiteSpace($LogPath)) {
        return
    }

    $logDir = Split-Path -Parent $LogPath
    if (-not [string]::IsNullOrWhiteSpace($logDir) -and -not (Test-Path -LiteralPath $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }

    $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    Add-Content -LiteralPath $LogPath -Value "[$ts] $Message" -Encoding UTF8
}

$BaseUrl = Assert-LocalApiBaseUrl -Value $BaseUrl -Name "BaseUrl"
$powerShell = Get-CurrentPowerShellPath
$mobileProxySmoke = Join-Path $PSScriptRoot "lab003_mobile_proxy_smoke.ps1"

if (-not (Test-Path -LiteralPath $mobileProxySmoke -PathType Leaf)) {
    throw "Mobile proxy smoke script not found."
}

$startedAt = Get-Date
$args = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $mobileProxySmoke,
    "-BaseUrl", $BaseUrl
)

if (-not [string]::IsNullOrWhiteSpace($Username)) {
    $args += @("-Username", $Username)
}

if ($IncludeBody.IsPresent) {
    $args += "-IncludeBody"
}

Write-Log "bundle started base_url=$BaseUrl include_body=$($IncludeBody.IsPresent)"
& $powerShell @args
$mobileExitCode = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }
$durationMs = [int]((Get-Date) - $startedAt).TotalMilliseconds
$ok = ($mobileExitCode -eq 0)

Write-Log "bundle finished ok=$ok mobile_proxy_exit_code=$mobileExitCode duration_ms=$durationMs"

$summary = [ordered]@{
    ok = $ok
    base_url = $BaseUrl
    duration_ms = $durationMs
    checked_at = (Get-Date).ToString("o")
    checks = @(
        [ordered]@{
            name = "mobile_proxy_smoke"
            ok = $ok
            exit_code = $mobileExitCode
        }
    )
    log_path = $LogPath
}

$summary | ConvertTo-Json -Depth 8

if (-not $ok) {
    exit $mobileExitCode
}
