[CmdletBinding()]
param(
    [switch]$Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# This bootstrap is deliberately guest-only.  It creates a local candidate
# visual baseline from the exact same fixed capture path used by the broker;
# it has no host, remote-control, credential, endpoint, or runtime-action
# input.  A later provisioning call still requires an owner to approve the
# resulting local image explicitly.
$P14RunnerRoot = 'C:\P14Runner'
$P14RepoRoot = 'C:\P14Runner\repo'
$P14ToolchainRoot = 'C:\P14Runner\toolchain'
$P14GitRoot = 'C:\P14Runner\toolchain\git'
$P14GitCmdRoot = 'C:\P14Runner\toolchain\git\cmd'
$P14GitExe = 'C:\P14Runner\toolchain\git\cmd\git.exe'
$P14ScriptsRoot = 'C:\P14Runner\repo\scripts\windows'
$P14CaptureScript = 'C:\P14Runner\repo\scripts\windows\otclient_p14_vm_capture.ps1'
$P14EvidenceRoot = 'C:\P14Runner\evidence'
$P14BaselineRoot = 'C:\P14Runner\baseline'
$P14BaselineReceipt = 'C:\P14Runner\baseline\baseline-receipt.json'
$P14MaximumImageBytes = 32MB

function Stop-P14BaselineCapture([string]$Code) {
    throw "p14_baseline_capture:$Code"
}

function Test-P14ReparsePoint([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        return $false
    }
    return (((Get-Item -LiteralPath $Path -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)
}

function Test-P14PathWithin([string]$Path, [string]$Root) {
    $candidate = [IO.Path]::GetFullPath($Path).TrimEnd('\')
    $allowed = [IO.Path]::GetFullPath($Root).TrimEnd('\')
    return $candidate.Equals($allowed, [StringComparison]::OrdinalIgnoreCase) -or
        $candidate.StartsWith($allowed + '\', [StringComparison]::OrdinalIgnoreCase)
}

function Assert-P14Directory([string]$Path, [string]$Code, [switch]$Create) {
    if ($Create -and -not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
    if (-not (Test-Path -LiteralPath $Path -PathType Container) -or (Test-P14ReparsePoint $Path)) {
        Stop-P14BaselineCapture $Code
    }
    return (Resolve-Path -LiteralPath $Path).Path
}

function Get-P14RegularFileHash(
    [string]$Path,
    [int64]$MaximumBytes = 2MB
) {
    if (
        -not (Test-Path -LiteralPath $Path -PathType Leaf) -or
        (Test-P14ReparsePoint $Path)
    ) {
        Stop-P14BaselineCapture 'file_invalid'
    }
    $item = Get-Item -LiteralPath $Path -Force
    if ($item.Length -lt 1 -or $item.Length -gt $MaximumBytes) {
        Stop-P14BaselineCapture 'file_size_invalid'
    }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Get-P14PortableGit {
    $toolchainRoot = Assert-P14Directory $P14ToolchainRoot 'portable_toolchain_invalid'
    $gitRoot = Assert-P14Directory $P14GitRoot 'portable_git_root_invalid'
    $gitCmdRoot = Assert-P14Directory $P14GitCmdRoot 'portable_git_cmd_root_invalid'
    if (
        -not (Test-Path -LiteralPath $P14GitExe -PathType Leaf) -or
        (Test-P14ReparsePoint $P14GitExe) -or
        -not (Test-P14PathWithin $P14GitExe $toolchainRoot) -or
        -not (Test-P14PathWithin $P14GitExe $gitRoot) -or
        -not (Test-P14PathWithin $P14GitExe $gitCmdRoot)
    ) {
        Stop-P14BaselineCapture 'portable_git_missing'
    }
    return (Resolve-Path -LiteralPath $P14GitExe).Path
}

function Get-P14SourceRevision {
    if (-not (Test-Path -LiteralPath (Join-Path $P14RepoRoot '.git') -PathType Container)) {
        Stop-P14BaselineCapture 'repository_missing'
    }
    $git = Get-P14PortableGit
    $revision = (& $git -C $P14RepoRoot rev-parse HEAD 2>$null | Select-Object -First 1).Trim().ToLowerInvariant()
    $dirty = @(& $git -C $P14RepoRoot status --porcelain 2>$null)
    if ($LASTEXITCODE -ne 0 -or $revision -notmatch '^[a-f0-9]{40}$' -or $dirty.Count -ne 0) {
        Stop-P14BaselineCapture 'source_revision_invalid'
    }
    return $revision
}

function Assert-P14GuestPrerequisites {
    if (-not [Environment]::UserInteractive) {
        Stop-P14BaselineCapture 'interactive_guest_session_required'
    }
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Stop-P14BaselineCapture 'dedicated_standard_user_required'
    }
    $guestServices = @(
        'C:\Program Files\Oracle\VirtualBox Guest Additions\VBoxService.exe',
        'C:\Windows\System32\VBoxService.exe'
    )
    if (-not ($guestServices | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf })) {
        Stop-P14BaselineCapture 'virtualbox_guest_additions_missing'
    }
    $activeAdapters = @(Get-NetAdapter -ErrorAction Stop | Where-Object { $_.Status -eq 'Up' })
    if ($activeAdapters.Count -ne 0) {
        Stop-P14BaselineCapture 'network_adapter_not_isolated'
    }
}

function Get-P14RunId {
    $bytes = New-Object byte[] 8
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $rng.GetBytes($bytes)
    } finally {
        $rng.Dispose()
    }
    return ([BitConverter]::ToString($bytes)).Replace('-', '').ToLowerInvariant()
}

function Save-P14ProcessEnvironment([string[]]$Names) {
    $saved = @{}
    foreach ($name in $Names) {
        $saved[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
    }
    return $saved
}

function Restore-P14ProcessEnvironment([hashtable]$Saved) {
    foreach ($entry in $Saved.GetEnumerator()) {
        if ($null -eq $entry.Value) {
            Remove-Item -LiteralPath ("Env:" + [string]$entry.Key) -ErrorAction SilentlyContinue
        } else {
            [Environment]::SetEnvironmentVariable([string]$entry.Key, [string]$entry.Value, 'Process')
        }
    }
}

function Set-P14CaptureEnvironment([string]$RunId) {
    $env:CTOA_P14_RUN_ID = $RunId
    $env:CTOA_P14_ISOLATED_ENVIRONMENT = 'true'
    $env:CTOA_P14_CAPTURE_CONTEXT = 'guest'
    $env:CTOA_P14_OPERATOR_WORKSTATION_FOCUS_USED = 'false'
    $env:CTOA_P14_OPERATOR_WORKSTATION_INPUT_USED = 'false'
    $env:CTOA_P14_NETWORK_DISPATCH_USED = 'false'
    $env:CTOA_P14_LIVE_CLIENT_ACCESSED = 'false'
    $env:CTOA_P14_PROMOTION_ATTEMPTED = 'false'
}

function ConvertTo-P14Hashtable(
    [object]$Value,
    [int]$CurrentDepth = 0,
    [int]$MaximumDepth = 10
) {
    if ($CurrentDepth -gt $MaximumDepth) {
        throw 'p14_json_depth_exceeded'
    }
    if ($null -eq $Value) {
        return $null
    }
    if ($Value -is [System.Collections.IDictionary]) {
        $converted = @{}
        foreach ($entry in $Value.GetEnumerator()) {
            $converted[[string]$entry.Key] = ConvertTo-P14Hashtable -Value $entry.Value -CurrentDepth ($CurrentDepth + 1) -MaximumDepth $MaximumDepth
        }
        return $converted
    }
    if ($Value -is [pscustomobject]) {
        $converted = @{}
        foreach ($property in $Value.PSObject.Properties) {
            $converted[[string]$property.Name] = ConvertTo-P14Hashtable -Value $property.Value -CurrentDepth ($CurrentDepth + 1) -MaximumDepth $MaximumDepth
        }
        return $converted
    }
    if ($Value -is [System.Collections.IEnumerable] -and $Value -isnot [string]) {
        $converted = [System.Collections.Generic.List[object]]::new()
        foreach ($item in $Value) {
            $converted.Add((ConvertTo-P14Hashtable -Value $item -CurrentDepth ($CurrentDepth + 1) -MaximumDepth $MaximumDepth)) | Out-Null
        }
        return ,$converted.ToArray()
    }
    return $Value
}

function Get-P14Json([string]$Path, [int64]$MaximumBytes = 2MB) {
    Get-P14RegularFileHash $Path $MaximumBytes | Out-Null
    try {
        $parsed = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json -ErrorAction Stop
        $value = ConvertTo-P14Hashtable -Value $parsed
    } catch {
        Stop-P14BaselineCapture 'evidence_json_invalid'
    }
    if ($value -isnot [hashtable]) {
        Stop-P14BaselineCapture 'evidence_json_invalid'
    }
    return $value
}

function Assert-P14ExactKeys([hashtable]$Value, [string[]]$Expected, [string]$Code) {
    if ($null -eq $Value) {
        Stop-P14BaselineCapture $Code
    }
    $actual = @($Value.Keys | ForEach-Object { [string]$_ })
    if (@(Compare-Object -ReferenceObject $Expected -DifferenceObject $actual).Count -ne 0) {
        Stop-P14BaselineCapture $Code
    }
}

function Assert-P14CaptureIsolation([hashtable]$Isolation) {
    $expected = [ordered]@{
        isolated_environment = $true
        operator_workstation_focus_used = $false
        operator_workstation_input_used = $false
        network_dispatch_used = $false
        live_client_accessed = $false
        promotion_attempted = $false
        capture_context = 'guest'
    }
    Assert-P14ExactKeys $Isolation @($expected.Keys) 'capture_isolation_invalid'
    foreach ($entry in $expected.GetEnumerator()) {
        if ($Isolation[$entry.Key] -ne $entry.Value) {
            Stop-P14BaselineCapture 'capture_isolation_invalid'
        }
    }
}

function Get-P14CaptureArtifact(
    [object[]]$Artifacts,
    [string]$Kind,
    [string]$ExpectedName,
    [string]$Path,
    [int64]$MaximumBytes = 2MB
) {
    $matches = @($Artifacts | Where-Object { $_ -is [hashtable] -and $_['kind'] -eq $Kind })
    if ($matches.Count -ne 1) {
        Stop-P14BaselineCapture 'capture_artifact_invalid'
    }
    $artifact = $matches[0]
    $hash = Get-P14RegularFileHash $Path $MaximumBytes
    $bytes = (Get-Item -LiteralPath $Path -Force).Length
    if (
        $artifact['path'] -ne $ExpectedName -or
        $artifact['sha256'] -ne $hash -or
        $artifact['bytes'] -ne $bytes
    ) {
        Stop-P14BaselineCapture 'capture_artifact_invalid'
    }
    return [ordered]@{
        sha256 = $hash
        bytes = $bytes
    }
}

function Assert-P14Image([string]$Path) {
    Add-Type -AssemblyName System.Drawing
    try {
        $image = [Drawing.Image]::FromFile($Path)
        try {
            if ($image.Width -lt 640 -or $image.Height -lt 480) {
                Stop-P14BaselineCapture 'visual_capture_dimensions_invalid'
            }
        } finally {
            $image.Dispose()
        }
    } catch {
        if ($_.Exception.Message -match '^p14_baseline_capture:') {
            throw
        }
        Stop-P14BaselineCapture 'visual_capture_invalid'
    }
}

function Assert-P14RuntimeMarker([hashtable]$Marker) {
    if (
        $Marker['online'] -ne $true -or
        $Marker['status'] -ne 'known_build' -or
        $Marker['runtime_actions'] -ne $false -or
        $Marker['runtime_core'] -isnot [hashtable] -or
        $Marker['runtime_core']['runtime_actions'] -ne $false
    ) {
        Stop-P14BaselineCapture 'helper_runtime_state_invalid'
    }
}

if (-not $Apply) {
    [ordered]@{
        schema_version = 'ctoa.p14-visual-baseline-plan.v1'
        status = 'dry_run'
        source_revision = 'derived_from_clean_guest_checkout'
        baseline_root = 'C:\P14Runner\baseline'
        receipt = 'baseline-receipt.json'
        creates_owner_approval = $false
        host_input = $false
        network_required = $false
        promotion_allowed = $false
    } | ConvertTo-Json -Depth 5
    return
}

if ((Resolve-Path -LiteralPath $PSScriptRoot).Path.TrimEnd('\') -ne $P14ScriptsRoot) {
    Stop-P14BaselineCapture 'guest_script_root_invalid'
}
Assert-P14GuestPrerequisites
Assert-P14Directory $P14RunnerRoot 'runner_root_invalid' | Out-Null
Assert-P14Directory $P14RepoRoot 'repository_root_invalid' | Out-Null
Assert-P14Directory $P14EvidenceRoot 'evidence_root_invalid' -Create | Out-Null
if (-not (Test-Path -LiteralPath $P14CaptureScript -PathType Leaf) -or (Test-P14ReparsePoint $P14CaptureScript)) {
    Stop-P14BaselineCapture 'capture_script_invalid'
}
if (Test-Path -LiteralPath $P14BaselineRoot) {
    Assert-P14Directory $P14BaselineRoot 'baseline_root_invalid' | Out-Null
    if (Get-ChildItem -LiteralPath $P14BaselineRoot -Force | Select-Object -First 1) {
        Stop-P14BaselineCapture 'baseline_root_not_empty'
    }
} else {
    New-Item -ItemType Directory -Path $P14BaselineRoot -Force | Out-Null
}

$sourceRevision = Get-P14SourceRevision
$runId = Get-P14RunId
$captureRoot = Join-Path $P14EvidenceRoot ("capture-$runId")
if (-not (Test-P14PathWithin $captureRoot $P14EvidenceRoot) -or (Test-Path -LiteralPath $captureRoot)) {
    Stop-P14BaselineCapture 'capture_root_invalid'
}
$environmentNames = @(
    'CTOA_P14_RUN_ID',
    'CTOA_P14_ISOLATED_ENVIRONMENT',
    'CTOA_P14_CAPTURE_CONTEXT',
    'CTOA_P14_OPERATOR_WORKSTATION_FOCUS_USED',
    'CTOA_P14_OPERATOR_WORKSTATION_INPUT_USED',
    'CTOA_P14_NETWORK_DISPATCH_USED',
    'CTOA_P14_LIVE_CLIENT_ACCESSED',
    'CTOA_P14_PROMOTION_ATTEMPTED'
)
$savedEnvironment = Save-P14ProcessEnvironment $environmentNames
try {
    Set-P14CaptureEnvironment $runId
    & $P14CaptureScript -SourceRevision $sourceRevision

    $captureReportPath = Join-Path $captureRoot 'capture-report.json'
    $imageName = "p14-in-world-$sourceRevision.png"
    $imagePath = Join-Path $captureRoot $imageName
    $markerPath = Join-Path $captureRoot 'client-capabilities.json'
    foreach ($path in @($captureReportPath, $imagePath, $markerPath)) {
        if (-not (Test-P14PathWithin $path $captureRoot)) {
            Stop-P14BaselineCapture 'capture_path_invalid'
        }
    }
    $capture = Get-P14Json $captureReportPath
    Assert-P14ExactKeys $capture @(
        'schema_version', 'status', 'captured_at', 'source_revision', 'run_id',
        'client_version', 'isolation', 'online_marker', 'artifacts'
    ) 'capture_report_invalid'
    if (
        $capture['schema_version'] -ne 'ctoa.p14-vm-capture.v1' -or
        $capture['status'] -ne 'observed_pass' -or
        $capture['source_revision'] -ne $sourceRevision -or
        $capture['run_id'] -ne $runId
    ) {
        Stop-P14BaselineCapture 'capture_report_binding_invalid'
    }
    Assert-P14CaptureIsolation $capture['isolation']
    if (
        $capture['online_marker'] -isnot [hashtable] -or
        $capture['online_marker']['online'] -ne $true -or
        $capture['online_marker']['status'] -ne 'known_build' -or
        $capture['online_marker']['build_id'] -notmatch '^[a-z0-9][a-z0-9._-]{0,127}$'
    ) {
        Stop-P14BaselineCapture 'in_world_marker_invalid'
    }
    $imageArtifact = Get-P14CaptureArtifact @($capture['artifacts']) 'in_world_capture' $imageName $imagePath $P14MaximumImageBytes
    $markerArtifact = Get-P14CaptureArtifact @($capture['artifacts']) 'helper_runtime_marker' 'client-capabilities.json' $markerPath
    Assert-P14Image $imagePath
    $marker = Get-P14Json $markerPath
    Assert-P14RuntimeMarker $marker

    $baselineImageName = "p14-baseline-$sourceRevision.png"
    $baselineImagePath = Join-Path $P14BaselineRoot $baselineImageName
    $baselineReportPath = Join-Path $P14BaselineRoot 'baseline-capture-report.json'
    $baselineMarkerPath = Join-Path $P14BaselineRoot 'baseline-client-capabilities.json'
    foreach ($path in @($baselineImagePath, $baselineReportPath, $baselineMarkerPath, $P14BaselineReceipt)) {
        if (-not (Test-P14PathWithin $path $P14BaselineRoot)) {
            Stop-P14BaselineCapture 'baseline_path_invalid'
        }
    }
    Copy-Item -LiteralPath $imagePath -Destination $baselineImagePath -ErrorAction Stop
    Copy-Item -LiteralPath $captureReportPath -Destination $baselineReportPath -ErrorAction Stop
    Copy-Item -LiteralPath $markerPath -Destination $baselineMarkerPath -ErrorAction Stop
    $baselineImageHash = Get-P14RegularFileHash $baselineImagePath $P14MaximumImageBytes
    $baselineReportHash = Get-P14RegularFileHash $baselineReportPath
    $baselineMarkerHash = Get-P14RegularFileHash $baselineMarkerPath
    if (
        $baselineImageHash -ne $imageArtifact['sha256'] -or
        (Get-Item -LiteralPath $baselineImagePath -Force).Length -ne $imageArtifact['bytes'] -or
        $baselineReportHash -ne (Get-P14RegularFileHash $captureReportPath) -or
        $baselineMarkerHash -ne $markerArtifact['sha256']
    ) {
        Stop-P14BaselineCapture 'baseline_copy_invalid'
    }

    $receipt = [ordered]@{
        schema_version = 'ctoa.p14-visual-baseline.v1'
        status = 'awaiting_owner_approval'
        source_revision = $sourceRevision
        image_name = $baselineImageName
        image_sha256 = $baselineImageHash
        image_bytes = (Get-Item -LiteralPath $baselineImagePath -Force).Length
        capture_report_sha256 = $baselineReportHash
        runtime_marker_sha256 = $baselineMarkerHash
        isolation = [ordered]@{
            isolated_environment = $true
            operator_workstation_focus_used = $false
            operator_workstation_input_used = $false
            network_dispatch_used = $false
            live_client_accessed = $false
            promotion_attempted = $false
            capture_context = 'guest'
        }
        authority = [ordered]@{
            runtime_actions = $false
            live_authority = $false
            promotion_approved = $false
            network_dispatch_used = $false
        }
    }
    $temporary = "$P14BaselineReceipt.tmp"
    $receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $temporary -Encoding UTF8 -NoNewline
    Move-Item -LiteralPath $temporary -Destination $P14BaselineReceipt -ErrorAction Stop
    $receipt | ConvertTo-Json -Depth 8
} finally {
    Restore-P14ProcessEnvironment $savedEnvironment
}
