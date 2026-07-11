param(
    [int]$DurationHours = 10,
    [int]$IntervalMinutes = 30,
    [string]$BaseUrl = "http://127.0.0.1:8787",
    [string]$LogPath = "$env:LOCALAPPDATA\CTOA\logs\lab003-shift-guard.log",
    [string]$AlertWebhookUrl = "",
    [switch]$IncludeBody,
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

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$validateScript = Join-Path $PSScriptRoot "lab003_validate_bundle.ps1"

if (-not (Test-Path -LiteralPath $validateScript -PathType Leaf)) {
    throw "Validation script not found: $validateScript"
}

$logDir = Split-Path -Parent $LogPath
if (-not [string]::IsNullOrWhiteSpace($logDir) -and -not (Test-Path -LiteralPath $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
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

function Write-Log {
    param([string]$Message)

    if ([string]::IsNullOrWhiteSpace($LogPath)) {
        return
    }

    $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    Add-Content -LiteralPath $LogPath -Value "[$ts] $Message" -Encoding UTF8
}

function Send-AlertWebhook {
    param(
        [string]$WebhookUrl,
        [int]$Iteration,
        [string]$ResultType,
        [int]$DurationMs,
        [int]$ExitCode = 0,
        [string]$ErrorMessage = ""
    )

    if ([string]::IsNullOrWhiteSpace($WebhookUrl)) {
        return
    }
    $safeWebhookUrl = Assert-AlertWebhookUrl -Value $WebhookUrl -Name "WebhookUrl"

    $payload = [ordered]@{
        project = "CTOAi"
        guard = "LAB-003 Shift Guard"
        severity = "error"
        timestamp = (Get-Date).ToString("o")
        iteration = $Iteration
        result = $ResultType
        duration_ms = $DurationMs
        base_url = $BaseUrl
        exit_code = $ExitCode
        message = $ErrorMessage
    }

    try {
        Invoke-RestMethod -Method Post -Uri $safeWebhookUrl -ContentType "application/json" -Body ($payload | ConvertTo-Json -Depth 8) | Out-Null
        Write-Log "alert_webhook=sent iteration=$Iteration result=$ResultType"
    }
    catch {
        Write-Log "alert_webhook=failed iteration=$Iteration result=$ResultType message=$($_.Exception.Message)"
    }
}

$resolvedWebhookUrl = Resolve-OptionalValue -Current $AlertWebhookUrl -EnvName "CTOA_LAB003_ALERT_WEBHOOK_URL"
$resolvedWebhookUrl = Assert-AlertWebhookUrl -Value $resolvedWebhookUrl -Name "AlertWebhookUrl"
$alertMode = if ($AlertOnEveryFailure.IsPresent) { "every_failure" } else { "first_failure" }
$alertSent = $false

$totalMinutes = $DurationHours * 60
$totalIterations = [Math]::Ceiling([double]$totalMinutes / [double]$IntervalMinutes)
$failures = 0

Write-Log "shift guard started duration_hours=$DurationHours interval_minutes=$IntervalMinutes iterations=$totalIterations base_url=$BaseUrl alert_mode=$alertMode webhook_configured=$(-not [string]::IsNullOrWhiteSpace($resolvedWebhookUrl))"

for ($iteration = 1; $iteration -le $totalIterations; $iteration++) {
    $startedAt = Get-Date

    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $validateScript,
        "-BaseUrl", $BaseUrl
    )

    if ($IncludeBody.IsPresent) {
        $args += "-IncludeBody"
    }

    try {
        & $powerShell @args
        $exitCode = $LASTEXITCODE
        $durationMs = [int]((Get-Date) - $startedAt).TotalMilliseconds

        if ($exitCode -ne 0) {
            $failures += 1
            Write-Log "iteration=$iteration result=fail exit_code=$exitCode duration_ms=$durationMs"

            $shouldAlert = (-not [string]::IsNullOrWhiteSpace($resolvedWebhookUrl)) -and ($AlertOnEveryFailure.IsPresent -or -not $alertSent)
            if ($shouldAlert) {
                Send-AlertWebhook -WebhookUrl $resolvedWebhookUrl -Iteration $iteration -ResultType "fail" -DurationMs $durationMs -ExitCode $exitCode -ErrorMessage "Validation bundle returned non-zero exit code."
                $alertSent = $true
            }
        }
        else {
            Write-Log "iteration=$iteration result=ok duration_ms=$durationMs"
        }
    }
    catch {
        $failures += 1
        $durationMs = [int]((Get-Date) - $startedAt).TotalMilliseconds
        $exceptionMessage = $_.Exception.Message
        Write-Log "iteration=$iteration result=exception duration_ms=$durationMs message=$exceptionMessage"

        $shouldAlert = (-not [string]::IsNullOrWhiteSpace($resolvedWebhookUrl)) -and ($AlertOnEveryFailure.IsPresent -or -not $alertSent)
        if ($shouldAlert) {
            Send-AlertWebhook -WebhookUrl $resolvedWebhookUrl -Iteration $iteration -ResultType "exception" -DurationMs $durationMs -ErrorMessage $exceptionMessage
            $alertSent = $true
        }
    }

    if ($iteration -lt $totalIterations) {
        Start-Sleep -Seconds ($IntervalMinutes * 60)
    }
}

Write-Log "shift guard finished iterations=$totalIterations failures=$failures alert_sent=$alertSent"

$summary = [ordered]@{
    ok = ($failures -eq 0)
    duration_hours = $DurationHours
    interval_minutes = $IntervalMinutes
    iterations = $totalIterations
    failures = $failures
    alert_mode = $alertMode
    alert_webhook_configured = (-not [string]::IsNullOrWhiteSpace($resolvedWebhookUrl))
    alert_sent = $alertSent
    log_path = $LogPath
    finished_at = (Get-Date).ToString("o")
}

$summary | ConvertTo-Json -Depth 6

if ($failures -gt 0) {
    exit 1
}
