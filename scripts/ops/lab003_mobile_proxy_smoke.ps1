param(
    [string]$BaseUrl = "http://127.0.0.1:8787",
    [string]$Username = "",
    [System.Management.Automation.PSCredential]$Credential,
    [switch]$IncludeBody
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-InputValue {
    param(
        [string]$Current,
        [string]$EnvName,
        [string]$DefaultValue = ""
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
        return $DefaultValue
    }

    return $value
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

$normalizedBaseUrl = Assert-LocalApiBaseUrl -Value $BaseUrl -Name "BaseUrl"
$resolvedUser = Resolve-InputValue -Current $Username -EnvName "CTOA_OWNER_USER" -DefaultValue "CTO"
$resolvedPassword = ""

if ($Credential) {
    if ([string]::IsNullOrWhiteSpace($Username)) {
        $resolvedUser = [string]$Credential.UserName
    }
    $resolvedPassword = [string]$Credential.GetNetworkCredential().Password
}
else {
    $resolvedPassword = Resolve-InputValue -Current "" -EnvName "CTOA_OWNER_PASSWORD"
}

if ([string]::IsNullOrWhiteSpace($resolvedPassword)) {
    throw "Missing password. Provide -Credential or set CTOA_OWNER_PASSWORD."
}

$loginResponse = Invoke-RestMethod -Method Post -Uri "$normalizedBaseUrl/api/auth/login" -ContentType "application/json" -Body (@{
    username = $resolvedUser
    password = $resolvedPassword
} | ConvertTo-Json -Depth 4)

$token = [string]$loginResponse.token
if ([string]::IsNullOrWhiteSpace($token)) {
    throw "Login response did not include token."
}

$headers = @{ Authorization = "Bearer $token" }
$paths = @(
    "/api/intel/status",
    "/api/intel/state",
    "/api/intel/diff"
)

$allOk = $true
$results = @()

foreach ($path in $paths) {
    $requestUrl = "$normalizedBaseUrl$path"

    try {
        $response = Invoke-RestMethod -Method Get -Uri $requestUrl -Headers $headers
        $entry = [ordered]@{
            endpoint = $path
            ok = [bool]$response.ok
            status = if ($response.PSObject.Properties.Name -contains "status") { $response.status } else { $null }
            proxy_url = if ($response.PSObject.Properties.Name -contains "url") { $response.url } else { $requestUrl }
            error = if ($response.PSObject.Properties.Name -contains "error") { $response.error } else { $null }
        }

        if ($IncludeBody.IsPresent -and ($response.PSObject.Properties.Name -contains "body")) {
            $entry.body = $response.body
        }

        if (-not $entry.ok) {
            $allOk = $false
        }

        $results += [pscustomobject]$entry
    }
    catch {
        $allOk = $false
        $results += [pscustomobject]([ordered]@{
            endpoint = $path
            ok = $false
            status = $null
            proxy_url = $requestUrl
            error = $_.Exception.Message
        })
    }
}

$summary = [ordered]@{
    ok = $allOk
    base_url = $normalizedBaseUrl
    checked_at = (Get-Date).ToString("o")
    results = $results
}

$summary | ConvertTo-Json -Depth 12

if (-not $allOk) {
    exit 1
}
