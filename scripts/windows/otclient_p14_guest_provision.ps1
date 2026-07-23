[CmdletBinding()]
param(
    [switch]$Apply,

    [string]$SnapshotId,

    [switch]$ApproveVisualBaseline
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# This is a one-time appliance provisioning script.  It runs only in the
# already logged-in dedicated standard guest account before a new isolated
# snapshot is created.  It neither creates accounts nor accepts credentials.
$P14RunnerRoot = 'C:\P14Runner'
$P14RepoRoot = 'C:\P14Runner\repo'
$P14ScriptsRoot = 'C:\P14Runner\repo\scripts\windows'
$P14TrustRoot = 'C:\P14Runner\trust'
$P14BundleRoot = 'C:\P14Runner\bundle'
$P14RunsRoot = 'C:\P14Runner\runs'
$P14EvidenceRoot = 'C:\P14Runner\evidence'
$P14BaselineRoot = 'C:\P14Runner\baseline'
$P14BaselineReceiptPath = 'C:\P14Runner\baseline\baseline-receipt.json'
$P14BaselineCaptureReportPath = 'C:\P14Runner\baseline\baseline-capture-report.json'
$P14BaselineRuntimeMarkerPath = 'C:\P14Runner\baseline\baseline-client-capabilities.json'
$P14BaselineImageMaximumBytes = 32MB
$P14ManifestPath = 'C:\P14Runner\trust\p14-snapshot-manifest.json'
$P14BrokerScript = 'C:\P14Runner\repo\scripts\windows\otclient_p14_guest_broker.ps1'
$P14SandboxExecutor = 'C:\P14Runner\repo\scripts\ops\otclient_p14_sandbox_executor.py'
$P14EndpointProfile = 'p14-offline-replay-v1'
$P14EvidenceKeyId = 'p14-guest-evidence'
$P14EvidenceCertificateSubject = 'CN=CTOAi P14 Guest Evidence'
$P14RunKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
$P14RunValue = 'CTOAiP14GuestBroker'

function Stop-P14GuestProvision([string]$Code) {
    throw "p14_guest_provision:$Code"
}

function Test-P14ReparsePoint([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        return $false
    }
    return (((Get-Item -LiteralPath $Path -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)
}

function Assert-P14Directory([string]$Path) {
    if (Test-Path -LiteralPath $Path) {
        if (-not (Test-Path -LiteralPath $Path -PathType Container) -or (Test-P14ReparsePoint $Path)) {
            Stop-P14GuestProvision 'directory_invalid'
        }
        return
    }
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
}

function Test-P14PathWithin([string]$Path, [string]$Root) {
    $candidate = [IO.Path]::GetFullPath($Path).TrimEnd('\')
    $allowed = [IO.Path]::GetFullPath($Root).TrimEnd('\')
    return $candidate.Equals($allowed, [StringComparison]::OrdinalIgnoreCase) -or
        $candidate.StartsWith($allowed + '\', [StringComparison]::OrdinalIgnoreCase)
}

function Get-P14RegularFileHash(
    [string]$Path,
    [int64]$MaximumBytes = 2MB
) {
    if (
        -not (Test-Path -LiteralPath $Path -PathType Leaf) -or
        (Test-P14ReparsePoint $Path) -or
        (Get-Item -LiteralPath $Path -Force).Length -lt 1 -or
        (Get-Item -LiteralPath $Path -Force).Length -gt $MaximumBytes
    ) {
        Stop-P14GuestProvision 'immutable_input_invalid'
    }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function ConvertTo-P14Hashtable(
    [object]$Value,
    [int]$CurrentDepth = 0,
    [int]$MaximumDepth = 10
) {
    # Windows PowerShell 5.1 lacks the hashtable and depth switches on its JSON reader.
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
        Stop-P14GuestProvision 'visual_baseline_evidence_invalid'
    }
    if ($value -isnot [hashtable]) {
        Stop-P14GuestProvision 'visual_baseline_evidence_invalid'
    }
    return $value
}

function Assert-P14ExactKeys([hashtable]$Value, [string[]]$Expected, [string]$Code) {
    if ($null -eq $Value) {
        Stop-P14GuestProvision $Code
    }
    $actual = @($Value.Keys | ForEach-Object { [string]$_ })
    if (@(Compare-Object -ReferenceObject $Expected -DifferenceObject $actual).Count -ne 0) {
        Stop-P14GuestProvision $Code
    }
}

function Assert-P14BaselineIsolation([hashtable]$Isolation) {
    $expected = [ordered]@{
        isolated_environment = $true
        operator_workstation_focus_used = $false
        operator_workstation_input_used = $false
        network_dispatch_used = $false
        live_client_accessed = $false
        promotion_attempted = $false
        capture_context = 'guest'
    }
    Assert-P14ExactKeys $Isolation @($expected.Keys) 'visual_baseline_isolation_invalid'
    foreach ($entry in $expected.GetEnumerator()) {
        if ($Isolation[$entry.Key] -ne $entry.Value) {
            Stop-P14GuestProvision 'visual_baseline_isolation_invalid'
        }
    }
}

function Assert-P14BaselineAuthority([hashtable]$Authority) {
    $expected = [ordered]@{
        runtime_actions = $false
        live_authority = $false
        promotion_approved = $false
        network_dispatch_used = $false
    }
    Assert-P14ExactKeys $Authority @($expected.Keys) 'visual_baseline_authority_invalid'
    foreach ($entry in $expected.GetEnumerator()) {
        if ($Authority[$entry.Key] -ne $entry.Value) {
            Stop-P14GuestProvision 'visual_baseline_authority_invalid'
        }
    }
}

function Get-P14CaptureArtifact(
    [object[]]$Artifacts,
    [string]$Kind,
    [string]$ExpectedName,
    [string]$ExpectedSha256,
    [int64]$ExpectedBytes
) {
    $matches = @($Artifacts | Where-Object { $_ -is [hashtable] -and $_['kind'] -eq $Kind })
    if ($matches.Count -ne 1) {
        Stop-P14GuestProvision 'visual_baseline_capture_artifact_invalid'
    }
    $artifact = $matches[0]
    Assert-P14ExactKeys $artifact @('kind', 'path', 'bytes', 'sha256') 'visual_baseline_capture_artifact_invalid'
    if (
        $artifact['path'] -ne $ExpectedName -or
        $artifact['sha256'] -ne $ExpectedSha256 -or
        $artifact['bytes'] -ne $ExpectedBytes
    ) {
        Stop-P14GuestProvision 'visual_baseline_capture_artifact_invalid'
    }
}

function Assert-P14VisualBaselineImage([string]$Path) {
    Add-Type -AssemblyName System.Drawing
    try {
        $image = [Drawing.Image]::FromFile($Path)
        try {
            if ($image.Width -lt 640 -or $image.Height -lt 480) {
                Stop-P14GuestProvision 'visual_baseline_dimensions_invalid'
            }
        } finally {
            $image.Dispose()
        }
    } catch {
        if ($_.Exception.Message -match '^p14_guest_provision:') {
            throw
        }
        Stop-P14GuestProvision 'visual_baseline_image_invalid'
    }
}

function Assert-P14BaselineContents([string]$ImageName) {
    $expected = @(
        'baseline-receipt.json',
        'baseline-capture-report.json',
        'baseline-client-capabilities.json',
        $ImageName
    )
    $entries = @(Get-ChildItem -LiteralPath $P14BaselineRoot -Force)
    $actual = @($entries | ForEach-Object { [string]$_.Name })
    if (@(Compare-Object -ReferenceObject $expected -DifferenceObject $actual).Count -ne 0) {
        Stop-P14GuestProvision 'visual_baseline_contents_invalid'
    }
    foreach ($entry in $entries) {
        if (
            $entry.PSIsContainer -or
            (($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)
        ) {
            Stop-P14GuestProvision 'visual_baseline_contents_invalid'
        }
    }
}

function Get-P14VisualBaseline([string]$SourceRevision) {
    if (-not (Test-Path -LiteralPath $P14BaselineRoot -PathType Container) -or (Test-P14ReparsePoint $P14BaselineRoot)) {
        Stop-P14GuestProvision 'visual_baseline_root_invalid'
    }
    $imageName = "p14-baseline-$SourceRevision.png"
    $imagePath = Join-Path $P14BaselineRoot $imageName
    Assert-P14BaselineContents $imageName
    foreach ($path in @($P14BaselineReceiptPath, $P14BaselineCaptureReportPath, $P14BaselineRuntimeMarkerPath, $imagePath)) {
        if (-not (Test-P14PathWithin $path $P14BaselineRoot)) {
            Stop-P14GuestProvision 'visual_baseline_path_invalid'
        }
    }

    $receipt = Get-P14Json $P14BaselineReceiptPath
    Assert-P14ExactKeys $receipt @(
        'schema_version', 'status', 'source_revision', 'image_name', 'image_sha256',
        'image_bytes', 'capture_report_sha256', 'runtime_marker_sha256', 'isolation', 'authority'
    ) 'visual_baseline_receipt_invalid'
    if (
        $receipt['schema_version'] -ne 'ctoa.p14-visual-baseline.v1' -or
        $receipt['status'] -ne 'awaiting_owner_approval' -or
        $receipt['source_revision'] -ne $SourceRevision -or
        $receipt['image_name'] -ne $imageName -or
        $receipt['image_sha256'] -notmatch '^[a-f0-9]{64}$' -or
        $receipt['image_bytes'] -isnot [long] -and $receipt['image_bytes'] -isnot [int] -or
        $receipt['image_bytes'] -lt 1 -or
        $receipt['image_bytes'] -gt $P14BaselineImageMaximumBytes -or
        $receipt['capture_report_sha256'] -notmatch '^[a-f0-9]{64}$' -or
        $receipt['runtime_marker_sha256'] -notmatch '^[a-f0-9]{64}$'
    ) {
        Stop-P14GuestProvision 'visual_baseline_receipt_invalid'
    }
    if ($receipt['isolation'] -isnot [hashtable] -or $receipt['authority'] -isnot [hashtable]) {
        Stop-P14GuestProvision 'visual_baseline_receipt_invalid'
    }
    Assert-P14BaselineIsolation $receipt['isolation']
    Assert-P14BaselineAuthority $receipt['authority']

    $imageHash = Get-P14RegularFileHash $imagePath $P14BaselineImageMaximumBytes
    $imageBytes = (Get-Item -LiteralPath $imagePath -Force).Length
    $captureReportHash = Get-P14RegularFileHash $P14BaselineCaptureReportPath
    $runtimeMarkerHash = Get-P14RegularFileHash $P14BaselineRuntimeMarkerPath
    if (
        $receipt['image_sha256'] -ne $imageHash -or
        $receipt['image_bytes'] -ne $imageBytes -or
        $receipt['capture_report_sha256'] -ne $captureReportHash -or
        $receipt['runtime_marker_sha256'] -ne $runtimeMarkerHash
    ) {
        Stop-P14GuestProvision 'visual_baseline_hash_mismatch'
    }
    Assert-P14VisualBaselineImage $imagePath

    $capture = Get-P14Json $P14BaselineCaptureReportPath
    Assert-P14ExactKeys $capture @(
        'schema_version', 'status', 'captured_at', 'source_revision', 'run_id',
        'client_version', 'isolation', 'online_marker', 'artifacts'
    ) 'visual_baseline_capture_invalid'
    if (
        $capture['schema_version'] -ne 'ctoa.p14-vm-capture.v1' -or
        $capture['status'] -ne 'observed_pass' -or
        $capture['source_revision'] -ne $SourceRevision -or
        $capture['run_id'] -notmatch '^[a-f0-9]{16}$' -or
        $capture['online_marker'] -isnot [hashtable]
    ) {
        Stop-P14GuestProvision 'visual_baseline_capture_invalid'
    }
    Assert-P14BaselineIsolation $capture['isolation']
    $onlineMarker = $capture['online_marker']
    Assert-P14ExactKeys $onlineMarker @('status', 'online', 'build_id', 'observed_at', 'reporter_artifact') 'visual_baseline_capture_invalid'
    if (
        $onlineMarker['status'] -ne 'known_build' -or
        $onlineMarker['online'] -ne $true -or
        $onlineMarker['build_id'] -notmatch '^[a-z0-9][a-z0-9._-]{0,127}$' -or
        $onlineMarker['reporter_artifact'] -ne 'client-capabilities.json'
    ) {
        Stop-P14GuestProvision 'visual_baseline_capture_invalid'
    }
    Get-P14CaptureArtifact @($capture['artifacts']) 'in_world_capture' "p14-in-world-$SourceRevision.png" $imageHash $imageBytes
    Get-P14CaptureArtifact @($capture['artifacts']) 'helper_runtime_marker' 'client-capabilities.json' $runtimeMarkerHash (Get-Item -LiteralPath $P14BaselineRuntimeMarkerPath -Force).Length

    $runtimeMarker = Get-P14Json $P14BaselineRuntimeMarkerPath
    if (
        $runtimeMarker['online'] -ne $true -or
        $runtimeMarker['status'] -ne 'known_build' -or
        $runtimeMarker['runtime_actions'] -ne $false -or
        $runtimeMarker['runtime_core'] -isnot [hashtable] -or
        $runtimeMarker['runtime_core']['runtime_actions'] -ne $false
    ) {
        Stop-P14GuestProvision 'visual_baseline_runtime_state_invalid'
    }
    return $imageHash
}

function Get-P14SourceRevision {
    if (-not (Test-Path -LiteralPath (Join-Path $P14RepoRoot '.git') -PathType Container)) {
        Stop-P14GuestProvision 'repository_missing'
    }
    $revision = (& git -C $P14RepoRoot rev-parse HEAD 2>$null | Select-Object -First 1).Trim().ToLowerInvariant()
    $dirty = @(& git -C $P14RepoRoot status --porcelain 2>$null)
    if ($LASTEXITCODE -ne 0 -or $revision -notmatch '^[a-f0-9]{40}$' -or $dirty.Count -ne 0) {
        Stop-P14GuestProvision 'source_revision_invalid'
    }
    return $revision
}

function Assert-P14GuestPrerequisites {
    if (-not [Environment]::UserInteractive) {
        Stop-P14GuestProvision 'interactive_guest_session_required'
    }
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Stop-P14GuestProvision 'dedicated_standard_user_required'
    }
    $guestServices = @(
        'C:\Program Files\Oracle\VirtualBox Guest Additions\VBoxService.exe',
        'C:\Windows\System32\VBoxService.exe'
    )
    if (-not ($guestServices | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf })) {
        Stop-P14GuestProvision 'virtualbox_guest_additions_missing'
    }
    $activeAdapters = @(Get-NetAdapter -ErrorAction Stop | Where-Object { $_.Status -eq 'Up' })
    if ($activeAdapters.Count -ne 0) {
        Stop-P14GuestProvision 'network_adapter_not_isolated'
    }
}

function Assert-P14ProvisionInputs {
    if ($SnapshotId -notmatch '^[a-z0-9][a-z0-9._-]{2,63}$') {
        Stop-P14GuestProvision 'snapshot_id_invalid'
    }
    if (-not $ApproveVisualBaseline) {
        Stop-P14GuestProvision 'visual_baseline_approval_required'
    }
}

function Stage-P14Bundle {
    if (Get-ChildItem -LiteralPath $P14BundleRoot -Force | Select-Object -First 1) {
        Stop-P14GuestProvision 'bundle_root_not_empty'
    }
    $python = Get-Command python.exe -CommandType Application -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if (-not $python) {
        Stop-P14GuestProvision 'python_runtime_missing'
    }
    & $python.Source $P14SandboxExecutor stage-bundle
    if ($LASTEXITCODE -ne 0) {
        Stop-P14GuestProvision 'bundle_stage_failed'
    }
}

function Get-P14EvidenceCertificate {
    $matches = @(
        Get-ChildItem -Path 'Cert:\CurrentUser\My' |
            Where-Object { $_.Subject -eq $P14EvidenceCertificateSubject }
    )
    if ($matches.Count -gt 1) {
        Stop-P14GuestProvision 'evidence_certificate_ambiguous'
    }
    if ($matches.Count -eq 0) {
        try {
            $certificate = New-SelfSignedCertificate `
                -Type Custom `
                -Subject $P14EvidenceCertificateSubject `
                -KeyAlgorithm ECDSA `
                -KeyLength 256 `
                -KeySpec Signature `
                -KeyUsage DigitalSignature `
                -HashAlgorithm SHA256 `
                -KeyExportPolicy NonExportable `
                -CertStoreLocation 'Cert:\CurrentUser\My' `
                -NotAfter (Get-Date).AddYears(2)
        } catch {
            Stop-P14GuestProvision 'evidence_certificate_create_failed'
        }
    } else {
        $certificate = $matches[0]
    }
    if (-not $certificate.HasPrivateKey) {
        Stop-P14GuestProvision 'evidence_certificate_private_key_missing'
    }
    $ecdsa = [Security.Cryptography.X509Certificates.ECDsaCertificateExtensions]::GetECDsaPrivateKey($certificate)
    if ($null -eq $ecdsa) {
        Stop-P14GuestProvision 'evidence_certificate_key_invalid'
    }
    try {
        if ($ecdsa.KeySize -ne 256) {
            Stop-P14GuestProvision 'evidence_certificate_key_invalid'
        }
    } finally {
        $ecdsa.Dispose()
    }
    return $certificate
}

function ConvertTo-P14CertificatePemB64([Security.Cryptography.X509Certificates.X509Certificate2]$Certificate) {
    $derB64 = [Convert]::ToBase64String($Certificate.RawData)
    $lines = [regex]::Matches($derB64, '.{1,64}') | ForEach-Object { $_.Value }
    $pem = "-----BEGIN CERTIFICATE-----`n$($lines -join "`n")`n-----END CERTIFICATE-----`n"
    return [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($pem))
}

function Get-P14RawSha256([byte[]]$Bytes) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        return ([BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace('-', '').ToLowerInvariant()
    } finally {
        $sha.Dispose()
    }
}

function Set-P14ImmutableTree([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        Stop-P14GuestProvision 'immutable_tree_missing'
    }
    Get-ChildItem -LiteralPath $Path -Force -Recurse | ForEach-Object {
        $_.Attributes = $_.Attributes -bor [IO.FileAttributes]::ReadOnly
    }
    (Get-Item -LiteralPath $Path -Force).Attributes =
        (Get-Item -LiteralPath $Path -Force).Attributes -bor [IO.FileAttributes]::ReadOnly
}

$expectedFiles = [ordered]@{
    broker = $P14BrokerScript
    capture = 'C:\P14Runner\repo\scripts\windows\otclient_p14_vm_capture.ps1'
    review = 'C:\P14Runner\repo\scripts\windows\otclient_p14_evidence_review.ps1'
    executor = $P14SandboxExecutor
    bundle_manifest = 'C:\P14Runner\bundle\helper-manifest.json'
}

if (-not $Apply) {
    [ordered]@{
        schema_version = 'ctoa.p14-guest-provision-plan.v2'
        status = 'dry_run'
        endpoint_profile = $P14EndpointProfile
        required_inputs = @('snapshot_id', 'approved_visual_baseline_receipt')
        owner_approval_required = $true
        baseline_receipt = 'C:\P14Runner\baseline\baseline-receipt.json'
        immutable_manifest = 'p14-snapshot-manifest.json'
        public_certificate_output = 'github_variable_ctoa_p14_guest_evidence_public_cert_b64'
        autostart = 'current_standard_guest_user_only'
        creates_accounts = $false
        accepts_credentials = $false
        host_input = $false
        network_required = $false
        promotion_allowed = $false
    } | ConvertTo-Json -Depth 6
    return
}

if ((Resolve-Path -LiteralPath $PSScriptRoot).Path.TrimEnd('\') -ne $P14ScriptsRoot) {
    Stop-P14GuestProvision 'guest_script_root_invalid'
}
Assert-P14ProvisionInputs
Assert-P14GuestPrerequisites

foreach ($root in @($P14RunnerRoot, $P14TrustRoot, $P14BundleRoot, $P14RunsRoot, $P14EvidenceRoot)) {
    Assert-P14Directory $root
}
$revision = Get-P14SourceRevision
$visualBaselineSha256 = Get-P14VisualBaseline $revision
Stage-P14Bundle

$certificate = Get-P14EvidenceCertificate
$hashes = [ordered]@{}
foreach ($entry in $expectedFiles.GetEnumerator()) {
    $hashes[$entry.Key] = Get-P14RegularFileHash $entry.Value
}

$manifest = [ordered]@{
    schema_version = 'ctoa.p14-guest-snapshot.v1'
    source_revision = $revision
    snapshot_id = $SnapshotId
    endpoint_profile = $P14EndpointProfile
    visual_baseline_sha256 = $visualBaselineSha256
    evidence = [ordered]@{
        key_id = $P14EvidenceKeyId
        certificate_sha256 = Get-P14RawSha256 $certificate.RawData
        certificate_thumbprint = $certificate.Thumbprint.ToLowerInvariant()
    }
    files = $hashes
    authority = [ordered]@{
        runtime_actions = $false
        live_authority = $false
        promotion_approved = $false
        network_dispatch_used = $false
    }
}

if (Test-Path -LiteralPath $P14ManifestPath) {
    Set-ItemProperty -LiteralPath $P14ManifestPath -Name IsReadOnly -Value $false
}
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $P14ManifestPath -Encoding UTF8 -NoNewline
Set-P14ImmutableTree $P14RepoRoot
Set-P14ImmutableTree $P14BundleRoot
Set-P14ImmutableTree $P14TrustRoot
Set-P14ImmutableTree $P14BaselineRoot

# HKCU Run starts only when the provisioned guest account has an interactive
# desktop.  No remote command channel, account name, password, or endpoint is
# stored in this entry.
$brokerCommand = "powershell.exe -NoLogo -NoProfile -WindowStyle Hidden -File `"$P14BrokerScript`""
New-Item -Path $P14RunKey -Force | Out-Null
New-ItemProperty -LiteralPath $P14RunKey -Name $P14RunValue -PropertyType String -Value $brokerCommand -Force | Out-Null

[ordered]@{
    schema_version = 'ctoa.p14-guest-provision-plan.v2'
    status = 'provisioned'
    source_revision = $revision
    snapshot_id = $SnapshotId
    endpoint_profile = $P14EndpointProfile
    visual_baseline_sha256 = $visualBaselineSha256
    baseline_owner_approved = $true
    guest_evidence_key_id = $P14EvidenceKeyId
    guest_evidence_public_cert_b64 = ConvertTo-P14CertificatePemB64 $certificate
    manifest_read_only = $true
    autostart = 'current_standard_guest_user_only'
    authority = $manifest.authority
} | ConvertTo-Json -Depth 8
