[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-f0-9]{40}$')]
    [string]$SourceRevision,

    [string]$ClientPath = $(if ($env:CTOA_P14_CLIENT_PATH) { $env:CTOA_P14_CLIENT_PATH } else { 'C:\P14Runner\client\otclient.exe' }),
    [string]$EvidenceRoot = $(if ($env:CTOA_P14_EVIDENCE_ROOT) { $env:CTOA_P14_EVIDENCE_ROOT } else { 'C:\P14Runner\evidence' }),
    [int]$TimeoutSeconds = 120
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Stop-P14Capture([string]$Code) {
    throw "p14_vm_capture:$Code"
}

function Require-IsolatedFlag([string]$Name, [string]$Expected) {
    $value = [Environment]::GetEnvironmentVariable($Name, 'Process')
    if ($value -ne $Expected) {
        Stop-P14Capture("isolation_flag_invalid:$Name")
    }
}

function Get-StrictPath([string]$Path, [string]$Root, [string]$Code) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        Stop-P14Capture("${Code}_missing")
    }
    $resolved = (Resolve-Path -LiteralPath $Path).Path
    $rootResolved = [IO.Path]::GetFullPath($Root).TrimEnd('\') + '\'
    if (-not $resolved.StartsWith($rootResolved, [StringComparison]::OrdinalIgnoreCase)) {
        Stop-P14Capture("${Code}_outside_allowlist")
    }
    return $resolved
}

function Get-Sha256([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

foreach ($flag in @{
        CTOA_P14_ISOLATED_ENVIRONMENT = 'true'
        CTOA_P14_OPERATOR_WORKSTATION_FOCUS_USED = 'false'
        CTOA_P14_OPERATOR_WORKSTATION_INPUT_USED = 'false'
        CTOA_P14_NETWORK_DISPATCH_USED = 'false'
        CTOA_P14_LIVE_CLIENT_ACCESSED = 'false'
        CTOA_P14_PROMOTION_ATTEMPTED = 'false'
        CTOA_P14_CAPTURE_CONTEXT = 'guest'
    }.GetEnumerator()) {
    Require-IsolatedFlag $flag.Key $flag.Value
}

if ($TimeoutSeconds -lt 10 -or $TimeoutSeconds -gt 600) {
    Stop-P14Capture('timeout_out_of_range')
}

$clientRoot = if ($env:CTOA_P14_CLIENT_ROOT) { $env:CTOA_P14_CLIENT_ROOT } else { 'C:\P14Runner\client' }
$client = Get-StrictPath $ClientPath $clientRoot 'client'
if (-not [Environment]::UserInteractive) {
    Stop-P14Capture('interactive_desktop_required')
}

$explorer = Get-Process -Name explorer -ErrorAction SilentlyContinue |
    Where-Object { $_.SessionId -eq [System.Diagnostics.Process]::GetCurrentProcess().SessionId } |
    Select-Object -First 1
if (-not $explorer) {
    Stop-P14Capture('guest_desktop_session_missing')
}

New-Item -ItemType Directory -Path $EvidenceRoot -Force | Out-Null
$evidence = (Resolve-Path -LiteralPath $EvidenceRoot).Path
$reporter = Join-Path $clientRoot 'mods\ctoa_otclient\ctoa_client_capabilities.json'
$timestamp = [DateTime]::UtcNow.ToString('o')
$process = $null

try {
    $process = Start-Process -FilePath $client -WorkingDirectory $clientRoot -PassThru -WindowStyle Normal
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    $onlineMarker = $null
    while ([DateTime]::UtcNow -lt $deadline) {
        $process.Refresh()
        if ($process.HasExited) {
            Stop-P14Capture('client_exited_before_in_world')
        }
        if (Test-Path -LiteralPath $reporter -PathType Leaf) {
            try {
                $candidate = Get-Content -Raw -LiteralPath $reporter | ConvertFrom-Json
                if ($candidate.online -eq $true -and $candidate.status -eq 'known_build') {
                    $onlineMarker = $candidate
                    break
                }
            } catch {
                # The helper reporter is written atomically; retry while it is changing.
            }
        }
        Start-Sleep -Milliseconds 500
    }
    if (-not $onlineMarker) {
        Stop-P14Capture('in_world_marker_timeout')
    }

    Add-Type -AssemblyName System.Drawing
    Add-Type -AssemblyName System.Windows.Forms
    $bounds = [Windows.Forms.Screen]::PrimaryScreen.Bounds
    if ($bounds.Width -lt 640 -or $bounds.Height -lt 480) {
        Stop-P14Capture('display_bounds_invalid')
    }
    $imagePath = Join-Path $evidence ("p14-in-world-$SourceRevision.png")
    $bitmap = New-Object Drawing.Bitmap $bounds.Width, $bounds.Height
    try {
        $graphics = [Drawing.Graphics]::FromImage($bitmap)
        try {
            $graphics.CopyFromScreen($bounds.Left, $bounds.Top, 0, 0, $bitmap.Size)
            $bitmap.Save($imagePath, [Drawing.Imaging.ImageFormat]::Png)
        } finally {
            $graphics.Dispose()
        }
    } finally {
        $bitmap.Dispose()
    }

    $capabilityCopy = Join-Path $evidence 'client-capabilities.json'
    Copy-Item -LiteralPath $reporter -Destination $capabilityCopy -Force
    $artifacts = @(
        [ordered]@{
            kind = 'in_world_capture'
            path = [IO.Path]::GetFileName($imagePath)
            bytes = (Get-Item -LiteralPath $imagePath).Length
            sha256 = Get-Sha256 $imagePath
        },
        [ordered]@{
            kind = 'helper_runtime_marker'
            path = [IO.Path]::GetFileName($capabilityCopy)
            bytes = (Get-Item -LiteralPath $capabilityCopy).Length
            sha256 = Get-Sha256 $capabilityCopy
        }
    )
    $logPath = Join-Path $clientRoot 'otclient.log'
    if (Test-Path -LiteralPath $logPath -PathType Leaf) {
        $logCopy = Join-Path $evidence 'otclient.log'
        Copy-Item -LiteralPath $logPath -Destination $logCopy -Force
        $artifacts += [ordered]@{
            kind = 'client_log'
            path = [IO.Path]::GetFileName($logCopy)
            bytes = (Get-Item -LiteralPath $logCopy).Length
            sha256 = Get-Sha256 $logCopy
        }
    }

    $sessionId = (Get-Process -Id $process.Id).SessionId
    $report = [ordered]@{
        schema_version = 'ctoa.p14-vm-capture.v1'
        status = 'observed_pass'
        captured_at = $timestamp
        source_revision = $SourceRevision
        client_version = [string]$onlineMarker.build_id
        client_pid = $process.Id
        client_session_id = $sessionId
        isolation = [ordered]@{
            isolated_environment = $true
            operator_workstation_focus_used = $false
            operator_workstation_input_used = $false
            network_dispatch_used = $false
            live_client_accessed = $false
            promotion_attempted = $false
            capture_context = 'guest'
        }
        online_marker = [ordered]@{
            status = [string]$onlineMarker.status
            online = [bool]$onlineMarker.online
            build_id = [string]$onlineMarker.build_id
            observed_at = [string]$onlineMarker.observed_at
        }
        artifacts = $artifacts
    }
    $reportPath = Join-Path $evidence 'capture-report.json'
    $report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportPath -Encoding UTF8
    $report
} finally {
    if ($process -and -not $process.HasExited) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    }
}
