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

$shiftGuardScript = Join-Path $PSScriptRoot "lab003_shift_guard.ps1"
if (-not (Test-Path $shiftGuardScript)) {
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
    & powershell @args
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
