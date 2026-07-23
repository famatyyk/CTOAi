[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-f0-9]{40}$')]
    [string]$SourceRevision,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-f0-9]{16}$')]
    [string]$RunId
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# This reviewer has no caller-selected evidence path and cannot launch a client.
# It validates only the fixed capture outputs produced inside the isolated guest.
$P14EvidenceRoot = 'C:\P14Runner\evidence'
$P14RunEvidenceRoot = Join-Path $P14EvidenceRoot ("capture-$RunId")
$P14TrustManifest = 'C:\P14Runner\trust\p14-snapshot-manifest.json'
$P14MaxJsonBytes = 2MB

function Stop-P14EvidenceReview([string]$Code) {
    throw "p14_evidence_review:$Code"
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

function ConvertTo-P14Hashtable(
    [object]$Value,
    [int]$CurrentDepth = 0,
    [int]$MaximumDepth = 10
) {
    # Windows PowerShell 5.1 lacks the hashtable and depth switches on its JSON reader.
    # Keep the same bounded, recursively indexed data contract locally.
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

function Get-P14Json([string]$Path) {
    if (
        -not (Test-Path -LiteralPath $Path -PathType Leaf) -or
        (Test-P14ReparsePoint $Path) -or
        (Get-Item -LiteralPath $Path -Force).Length -gt $P14MaxJsonBytes
    ) {
        Stop-P14EvidenceReview 'evidence_json_invalid'
    }
    try {
        $parsed = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json -ErrorAction Stop
        $value = ConvertTo-P14Hashtable -Value $parsed -MaximumDepth 10
        if ($value -isnot [hashtable]) {
            Stop-P14EvidenceReview 'evidence_json_invalid'
        }
        return $value
    } catch {
        Stop-P14EvidenceReview 'evidence_json_invalid'
    }
}

function Get-P14FileHash([string]$Path) {
    if (
        -not (Test-Path -LiteralPath $Path -PathType Leaf) -or
        (Test-P14ReparsePoint $Path) -or
        (Get-Item -LiteralPath $Path -Force).Length -le 0
    ) {
        Stop-P14EvidenceReview 'evidence_file_invalid'
    }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Get-P14CanonicalHash([hashtable]$Value) {
    $json = $Value | ConvertTo-Json -Depth 10 -Compress
    $bytes = [Text.Encoding]::UTF8.GetBytes($json)
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        return ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-', '').ToLowerInvariant()
    } finally {
        $sha.Dispose()
    }
}

function Assert-P14Isolation([hashtable]$Isolation) {
    $expected = [ordered]@{
        isolated_environment = $true
        operator_workstation_focus_used = $false
        operator_workstation_input_used = $false
        network_dispatch_used = $false
        live_client_accessed = $false
        promotion_attempted = $false
        capture_context = 'guest'
    }
    if ($Isolation -isnot [hashtable] -or @($Isolation.Keys).Count -ne @($expected.Keys).Count) {
        Stop-P14EvidenceReview 'capture_isolation_invalid'
    }
    foreach ($entry in $expected.GetEnumerator()) {
        if (-not $Isolation.ContainsKey($entry.Key) -or $Isolation[$entry.Key] -ne $entry.Value) {
            Stop-P14EvidenceReview 'capture_isolation_invalid'
        }
    }
}

function Get-P14Artifact([object[]]$Artifacts, [string]$Kind, [string]$ExpectedName, [string]$Path) {
    $matches = @($Artifacts | Where-Object {
            $_ -is [hashtable] -and $_['kind'] -eq $Kind
        })
    if ($matches.Count -ne 1) {
        Stop-P14EvidenceReview 'capture_artifact_invalid'
    }
    $artifact = $matches[0]
    if (
        $artifact['path'] -ne $ExpectedName -or
        $artifact['bytes'] -ne (Get-Item -LiteralPath $Path -Force).Length -or
        $artifact['sha256'] -ne (Get-P14FileHash $Path)
    ) {
        Stop-P14EvidenceReview 'capture_artifact_invalid'
    }
    return $artifact
}

function Get-P14VisualBaseline {
    $manifest = Get-P14Json $P14TrustManifest
    $expected = @(
        'schema_version', 'source_revision', 'snapshot_id', 'endpoint_profile',
        'visual_baseline_sha256', 'evidence', 'files', 'authority'
    )
    if (
        @($manifest.Keys).Count -ne $expected.Count -or
        @($expected | Where-Object { -not $manifest.ContainsKey($_) }).Count -ne 0 -or
        $manifest['schema_version'] -ne 'ctoa.p14-guest-snapshot.v1' -or
        $manifest['source_revision'] -ne $SourceRevision -or
        $manifest['visual_baseline_sha256'] -notmatch '^[a-f0-9]{64}$'
    ) {
        Stop-P14EvidenceReview 'snapshot_visual_baseline_invalid'
    }
    return [string]$manifest['visual_baseline_sha256']
}

if (-not (Test-P14PathWithin $P14RunEvidenceRoot $P14EvidenceRoot)) {
    Stop-P14EvidenceReview 'run_evidence_path_invalid'
}
if (-not (Test-Path -LiteralPath $P14RunEvidenceRoot -PathType Container) -or (Test-P14ReparsePoint $P14RunEvidenceRoot)) {
    Stop-P14EvidenceReview 'run_evidence_path_invalid'
}

$captureReportPath = Join-Path $P14RunEvidenceRoot 'capture-report.json'
$imageName = "p14-in-world-$SourceRevision.png"
$imagePath = Join-Path $P14RunEvidenceRoot $imageName
$capabilitiesPath = Join-Path $P14RunEvidenceRoot 'client-capabilities.json'
$reviewPath = Join-Path $P14RunEvidenceRoot 'evidence-review.json'
if (
    -not (Test-P14PathWithin $captureReportPath $P14RunEvidenceRoot) -or
    -not (Test-P14PathWithin $imagePath $P14RunEvidenceRoot) -or
    -not (Test-P14PathWithin $capabilitiesPath $P14RunEvidenceRoot) -or
    -not (Test-P14PathWithin $reviewPath $P14RunEvidenceRoot)
) {
    Stop-P14EvidenceReview 'evidence_path_invalid'
}

$capture = Get-P14Json $captureReportPath
if (
    $capture['schema_version'] -ne 'ctoa.p14-vm-capture.v1' -or
    $capture['status'] -ne 'observed_pass' -or
    $capture['source_revision'] -ne $SourceRevision -or
    $capture['run_id'] -ne $RunId
) {
    Stop-P14EvidenceReview 'capture_report_binding_invalid'
}
Assert-P14Isolation $capture['isolation']
$marker = $capture['online_marker']
if (
    $marker -isnot [hashtable] -or
    $marker['online'] -ne $true -or
    $marker['status'] -ne 'known_build' -or
    $marker['build_id'] -notmatch '^[a-z0-9][a-z0-9._-]{0,127}$'
) {
    Stop-P14EvidenceReview 'in_world_marker_invalid'
}

$artifacts = @($capture['artifacts'])
$imageArtifact = Get-P14Artifact $artifacts 'in_world_capture' $imageName $imagePath
$capabilityArtifact = Get-P14Artifact $artifacts 'helper_runtime_marker' 'client-capabilities.json' $capabilitiesPath
$expectedImageSha256 = Get-P14VisualBaseline
if ($imageArtifact['sha256'] -ne $expectedImageSha256) {
    Stop-P14EvidenceReview 'visual_baseline_mismatch'
}

Add-Type -AssemblyName System.Drawing
$image = [Drawing.Image]::FromFile($imagePath)
try {
    if ($image.Width -lt 640 -or $image.Height -lt 480) {
        Stop-P14EvidenceReview 'visual_capture_dimensions_invalid'
    }
} finally {
    $image.Dispose()
}

$capabilities = Get-P14Json $capabilitiesPath
if (
    $capabilities['online'] -ne $true -or
    $capabilities['status'] -ne 'known_build' -or
    $capabilities['runtime_actions'] -ne $false
) {
    Stop-P14EvidenceReview 'helper_runtime_state_invalid'
}
$runtimeCore = $capabilities['runtime_core']
if ($runtimeCore -isnot [hashtable] -or $runtimeCore['runtime_actions'] -ne $false) {
    Stop-P14EvidenceReview 'helper_runtime_state_invalid'
}

$visualEvidence = [ordered]@{
    capture_report_sha256 = Get-P14FileHash $captureReportPath
    image_sha256 = $imageArtifact['sha256']
    image_bytes = $imageArtifact['bytes']
    expected_image_sha256 = $expectedImageSha256
}
$inWorldEvidence = [ordered]@{
    capture_report_sha256 = Get-P14FileHash $captureReportPath
    marker_sha256 = $capabilityArtifact['sha256']
    marker_bytes = $capabilityArtifact['bytes']
    build_id = $marker['build_id']
}
$review = [ordered]@{
    schema_version = 'ctoa.p14-evidence-review.v1'
    status = 'passed'
    run_id = $RunId
    source_revision = $SourceRevision
    isolation = [ordered]@{
        isolated_environment = $true
        operator_workstation_focus_used = $false
        operator_workstation_input_used = $false
        network_dispatch_used = $false
        live_client_accessed = $false
        promotion_attempted = $false
    }
    visual = [ordered]@{
        proof_id = 'independent_visual_review'
        status = 'passed'
        artifact_count = 2
        evidence_sha256 = Get-P14CanonicalHash $visualEvidence
    }
    in_world = [ordered]@{
        proof_id = 'independent_in_world_review'
        status = 'passed'
        artifact_count = 2
        evidence_sha256 = Get-P14CanonicalHash $inWorldEvidence
    }
    authority = [ordered]@{
        runtime_actions = $false
        live_authority = $false
        promotion_approved = $false
    }
}

$temporary = "$reviewPath.tmp"
$review | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $temporary -Encoding UTF8 -NoNewline
Move-Item -LiteralPath $temporary -Destination $reviewPath -Force
$review | ConvertTo-Json -Depth 8
