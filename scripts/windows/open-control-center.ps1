param(
    [string]$Url = $env:CTOA_CONTROL_CENTER_URL
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-ControlCenterUrl {
    param([Parameter(Mandatory = $true)][string]$Candidate)

    if ([string]::IsNullOrWhiteSpace($Candidate)) {
        throw 'Control Center URL must not be empty.'
    }

    if ($Candidate -match '\\') {
        throw 'Control Center URL path must not include backslashes.'
    }

    $decodedCandidate = [System.Uri]::UnescapeDataString($Candidate)
    $rawTraversalSegments = @($decodedCandidate -split '/' | Where-Object { $_ -eq '.' -or $_ -eq '..' })
    if ($rawTraversalSegments.Count -gt 0) {
        throw 'Control Center URL path must not contain traversal.'
    }

    $uri = $null
    if (-not [System.Uri]::TryCreate($Candidate, [System.UriKind]::Absolute, [ref]$uri)) {
        throw 'Control Center URL must be absolute.'
    }

    if ($uri.Scheme -notin @('http', 'https')) {
        throw 'Control Center URL must use http:// or https://.'
    }

    if (-not [string]::IsNullOrWhiteSpace($uri.UserInfo)) {
        throw 'Control Center URL must not include credentials.'
    }

    if (-not [string]::IsNullOrWhiteSpace($uri.Query) -or -not [string]::IsNullOrWhiteSpace($uri.Fragment)) {
        throw 'Control Center URL must not include query strings or fragments.'
    }

    $decodedPath = [System.Uri]::UnescapeDataString($uri.AbsolutePath)
    if ($decodedPath -match '\\') {
        throw 'Control Center URL path must not include backslashes.'
    }
    $traversalSegments = @($decodedPath -split '/' | Where-Object { $_ -eq '.' -or $_ -eq '..' })
    if ($traversalSegments.Count -gt 0) {
        throw 'Control Center URL path must not contain traversal.'
    }

    $hostName = $uri.Host.ToLowerInvariant()
    $isLocalHost = $hostName -in @('localhost', '127.0.0.1', '::1')
    if ($uri.Scheme -eq 'http' -and -not $isLocalHost) {
        throw 'Non-local Control Center URLs must use https://.'
    }

    return $uri.AbsoluteUri
}

if ([string]::IsNullOrWhiteSpace($Url)) {
    $Url = "http://127.0.0.1:3000/control-center"
}

$Url = Resolve-ControlCenterUrl -Candidate $Url

Write-Host "Opening CTOAi Control Center: $Url"
Start-Process -FilePath $Url
