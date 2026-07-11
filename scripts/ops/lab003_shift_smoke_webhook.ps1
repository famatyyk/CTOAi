param(
    [string]$BaseUrl = "http://127.0.0.1:8787",
    [string]$AlertWebhookUrl = "",
    [string]$LogPath = "$env:LOCALAPPDATA\CTOA\logs\lab003-shift-smoke-webhook.log",
    [int]$DurationHours = 1,
    [int]$IntervalMinutes = 30,
    [switch]$AlertOnEveryFailure
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($DurationHours -lt 1) {
    throw "DurationHours must be >= 1"
}

if ($IntervalMinutes -lt 1) {
    throw "IntervalMinutes must be >= 1"
}

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

function Assert-AlertWebhookUrl {
    param(
        [string]$Value,
        [string]$Name
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return ""
    }

    $candidate = $Value.Trim()
    if ($candidate -match "[\r\n\t ]") {
        throw "$Name must not contain whitespace."
    }

    [Uri]$uri = $null
    if (-not [Uri]::TryCreate($candidate, [UriKind]::Absolute, [ref]$uri)) {
        throw "$Name must be an absolute HTTP(S) URL."
    }
    if ($uri.Scheme -notin @("http", "https")) {
        throw "$Name must use http:// or https://."
    }
    if ($uri.Scheme -eq "http" -and -not (Test-CtoaLoopbackHost $uri.Host)) {
        throw "$Name must use https:// for non-local webhook hosts."
    }
    if ($uri.UserInfo) {
        throw "$Name must not include credentials."
    }
    if ($uri.Fragment) {
        throw "$Name must not include fragments."
    }

    return $candidate
}

function Get-CurrentPowerShellPath {
    $exeName = if ($PSVersionTable.PSEdition -eq "Core") { "pwsh.exe" } else { "powershell.exe" }
    $candidate = Join-Path $PSHOME $exeName
    if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
        throw "Current PowerShell executable was not found."
    }
    return $candidate
}

$BaseUrl = Assert-LocalApiBaseUrl -Value $BaseUrl -Name "BaseUrl"
$powerShell = Get-CurrentPowerShellPath

$shiftGuardScript = Join-Path $PSScriptRoot "lab003_shift_guard.ps1"
if (-not (Test-Path -LiteralPath $shiftGuardScript -PathType Leaf)) {
    throw "Shift guard script not found: $shiftGuardScript"
}

function Resolve-OptionalValue {
    param(
        [string]$Current,
        [string]$EnvName
    )

    if (-not [string]::IsNullOrWhiteSpace($Current)) {
        return $Current
    }

    $value = [Environment]::GetEnvironmentVariable($EnvName, "Process")
    if ([string]::IsNullOrWhiteSpace($value)) {
        $value = [Environment]::GetEnvironmentVariable($EnvName, "User")
    }
    if ([string]::IsNullOrWhiteSpace($value)) {
        $value = [Environment]::GetEnvironmentVariable($EnvName, "Machine")
    }

    if ([string]::IsNullOrWhiteSpace($value)) {
        return ""
    }

    return $value
}

$resolvedWebhookUrl = Resolve-OptionalValue -Current $AlertWebhookUrl -EnvName "CTOA_LAB003_ALERT_WEBHOOK_URL"
if ([string]::IsNullOrWhiteSpace($resolvedWebhookUrl)) {
    throw "Alert webhook URL is required. Provide -AlertWebhookUrl or set CTOA_LAB003_ALERT_WEBHOOK_URL."
}
$resolvedWebhookUrl = Assert-AlertWebhookUrl -Value $resolvedWebhookUrl -Name "AlertWebhookUrl"

$args = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $shiftGuardScript,
    "-DurationHours", $DurationHours.ToString(),
    "-IntervalMinutes", $IntervalMinutes.ToString(),
    "-BaseUrl", $BaseUrl,
    "-LogPath", $LogPath
)

if ($AlertOnEveryFailure.IsPresent) {
    $args += "-AlertOnEveryFailure"
}

# Keep webhook out of child process command-line arguments.
$previousWebhook = [Environment]::GetEnvironmentVariable("CTOA_LAB003_ALERT_WEBHOOK_URL", "Process")
[Environment]::SetEnvironmentVariable("CTOA_LAB003_ALERT_WEBHOOK_URL", $resolvedWebhookUrl, "Process")

try {
    & $powerShell @args
    $exitCode = $LASTEXITCODE
}
finally {
    if ([string]::IsNullOrWhiteSpace($previousWebhook)) {
        [Environment]::SetEnvironmentVariable("CTOA_LAB003_ALERT_WEBHOOK_URL", $null, "Process")
    }
    else {
        [Environment]::SetEnvironmentVariable("CTOA_LAB003_ALERT_WEBHOOK_URL", $previousWebhook, "Process")
    }
}

if ($exitCode -ne 0) {
    exit $exitCode
}
