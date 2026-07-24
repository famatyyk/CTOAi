[CmdletBinding()]
param(
    [switch]$RunOnce
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# The host-to-guest inputs are an opaque run id and two fixed, bounded hashes
# in VBox guest properties.  The hashes bind this run to the host-only
# appliance record and to this exact immutable snapshot manifest.  This broker
# has no caller-selected command, path, revision, endpoint, credential, or
# package input.
$P14RunnerRoot = 'C:\P14Runner'
$P14RepoRoot = 'C:\P14Runner\repo'
$P14ToolchainRoot = 'C:\P14Runner\toolchain'
$P14PythonExe = 'C:\P14Runner\toolchain\python\python.exe'
$P14TrustManifest = 'C:\P14Runner\trust\p14-snapshot-manifest.json'
$P14BundleRoot = 'C:\P14Runner\bundle'
$P14BundleManifest = 'C:\P14Runner\bundle\helper-manifest.json'
$P14RunsRoot = 'C:\P14Runner\runs'
$P14EvidenceRoot = 'C:\P14Runner\evidence'
$P14CaptureScript = 'C:\P14Runner\repo\scripts\windows\otclient_p14_vm_capture.ps1'
$P14EvidenceReviewScript = 'C:\P14Runner\repo\scripts\windows\otclient_p14_evidence_review.ps1'
$P14SandboxExecutor = 'C:\P14Runner\repo\scripts\ops\otclient_p14_sandbox_executor.py'
$P14GuestRunIdProperty = '/CTOAi/P14/RunId'
$P14GuestStatusProperty = '/CTOAi/P14/Status'
$P14GuestEnvelopeProperty = '/CTOAi/P14/EvidenceEnvelopeB64'
$P14GuestEnvelopeSha256Property = '/CTOAi/P14/EvidenceEnvelopeSha256'
$P14GuestApplianceBindingSha256Property = '/CTOAi/P14/ApplianceBindingSha256'
$P14GuestSnapshotManifestSha256Property = '/CTOAi/P14/SnapshotManifestSha256'
$P14EndpointProfile = 'p14-offline-replay-v1'
$P14MaxManifestBytes = 64KB
$P14MaxEnvelopeRawBytes = 24KB
$P14MaxGuestPropertyBytes = 32KB
$P14SignatureDomain = [Text.Encoding]::ASCII.GetBytes("CTOAi-P14-guest-evidence-envelope/v1`0")

function Stop-P14GuestBroker([string]$Code) {
    throw "p14_guest_broker:$Code"
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

function Assert-P14Directory([string]$Path, [string]$Code) {
    if (-not (Test-Path -LiteralPath $Path -PathType Container) -or (Test-P14ReparsePoint $Path)) {
        Stop-P14GuestBroker $Code
    }
}

function Assert-P14PortableToolchain {
    Assert-P14Directory $P14ToolchainRoot 'portable_toolchain_missing'
    Assert-P14Directory (Join-Path $P14ToolchainRoot 'python') 'portable_toolchain_missing'
    if (
        -not (Test-Path -LiteralPath $P14PythonExe -PathType Leaf) -or
        (Test-P14ReparsePoint $P14PythonExe) -or
        -not (Test-P14PathWithin $P14PythonExe $P14ToolchainRoot)
    ) {
        Stop-P14GuestBroker 'portable_toolchain_missing'
    }
}

function Get-P14RegularFileHash([string]$Path, [int]$MaxBytes = 2MB) {
    if (
        -not (Test-Path -LiteralPath $Path -PathType Leaf) -or
        (Test-P14ReparsePoint $Path) -or
        (Get-Item -LiteralPath $Path -Force).Length -lt 1 -or
        (Get-Item -LiteralPath $Path -Force).Length -gt $MaxBytes
    ) {
        Stop-P14GuestBroker 'immutable_input_invalid'
    }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function ConvertTo-P14Hashtable(
    [object]$Value,
    [int]$CurrentDepth = 0,
    [int]$MaximumDepth = 12
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

function Get-P14Json([string]$Path, [int]$MaxBytes = 2MB) {
    Get-P14RegularFileHash $Path $MaxBytes | Out-Null
    try {
        $parsed = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json -ErrorAction Stop
        $value = ConvertTo-P14Hashtable -Value $parsed -MaximumDepth 12
    } catch {
        Stop-P14GuestBroker 'evidence_json_invalid'
    }
    if ($value -isnot [hashtable]) {
        Stop-P14GuestBroker 'evidence_json_invalid'
    }
    return $value
}

function Assert-P14ExactKeys([hashtable]$Value, [string[]]$Expected, [string]$Code) {
    if ($null -eq $Value) {
        Stop-P14GuestBroker $Code
    }
    $actual = @($Value.Keys | ForEach-Object { [string]$_ })
    if (@(Compare-Object -ReferenceObject $Expected -DifferenceObject $actual).Count -ne 0) {
        Stop-P14GuestBroker $Code
    }
}

function Get-P14SnapshotManifest {
    Assert-P14Directory $P14RunnerRoot 'runner_root_invalid'
    Assert-P14Directory $P14RepoRoot 'repository_root_invalid'
    Assert-P14Directory $P14BundleRoot 'bundle_root_invalid'
    Assert-P14Directory $P14RunsRoot 'runs_root_invalid'
    Assert-P14Directory $P14EvidenceRoot 'evidence_root_invalid'
    if (-not (Test-Path -LiteralPath $P14TrustManifest -PathType Leaf) -or (Test-P14ReparsePoint $P14TrustManifest)) {
        Stop-P14GuestBroker 'snapshot_manifest_missing'
    }
    $manifestItem = Get-Item -LiteralPath $P14TrustManifest -Force
    if (-not $manifestItem.IsReadOnly -or $manifestItem.Length -lt 1 -or $manifestItem.Length -gt $P14MaxManifestBytes) {
        Stop-P14GuestBroker 'snapshot_manifest_not_immutable'
    }
    $manifest = Get-P14Json $P14TrustManifest $P14MaxManifestBytes
    Assert-P14ExactKeys $manifest @(
        'schema_version', 'source_revision', 'snapshot_id', 'endpoint_profile',
        'visual_baseline_sha256', 'evidence', 'files', 'authority'
    ) 'snapshot_manifest_shape_invalid'
    if (
        $manifest['schema_version'] -ne 'ctoa.p14-guest-snapshot.v1' -or
        $manifest['source_revision'] -notmatch '^[a-f0-9]{40}$' -or
        $manifest['snapshot_id'] -notmatch '^[a-z0-9][a-z0-9._-]{2,63}$' -or
        $manifest['endpoint_profile'] -ne $P14EndpointProfile -or
        $manifest['visual_baseline_sha256'] -notmatch '^[a-f0-9]{64}$'
    ) {
        Stop-P14GuestBroker 'snapshot_manifest_binding_invalid'
    }
    $files = $manifest['files']
    if ($files -isnot [hashtable]) {
        Stop-P14GuestBroker 'snapshot_manifest_files_invalid'
    }
    Assert-P14ExactKeys $files @('broker', 'capture', 'review', 'executor', 'bundle_manifest') 'snapshot_manifest_files_invalid'
    $expectedFiles = [ordered]@{
        broker = $PSCommandPath
        capture = $P14CaptureScript
        review = $P14EvidenceReviewScript
        executor = $P14SandboxExecutor
        bundle_manifest = $P14BundleManifest
    }
    foreach ($entry in $expectedFiles.GetEnumerator()) {
        if ($files[$entry.Key] -notmatch '^[a-f0-9]{64}$' -or (Get-P14RegularFileHash $entry.Value) -ne $files[$entry.Key]) {
            Stop-P14GuestBroker "snapshot_manifest_hash_mismatch:$($entry.Key)"
        }
    }
    $evidence = $manifest['evidence']
    if ($evidence -isnot [hashtable]) {
        Stop-P14GuestBroker 'snapshot_manifest_evidence_invalid'
    }
    Assert-P14ExactKeys $evidence @('key_id', 'certificate_sha256', 'certificate_thumbprint') 'snapshot_manifest_evidence_invalid'
    if (
        $evidence['key_id'] -notmatch '^[a-z0-9][a-z0-9._-]{2,63}$' -or
        $evidence['certificate_sha256'] -notmatch '^[a-f0-9]{64}$' -or
        $evidence['certificate_thumbprint'] -notmatch '^[a-f0-9]{40}$'
    ) {
        Stop-P14GuestBroker 'snapshot_manifest_evidence_invalid'
    }
    $authority = $manifest['authority']
    if ($authority -isnot [hashtable]) {
        Stop-P14GuestBroker 'snapshot_manifest_authority_invalid'
    }
    Assert-P14ExactKeys $authority @('runtime_actions', 'live_authority', 'promotion_approved', 'network_dispatch_used') 'snapshot_manifest_authority_invalid'
    if (
        $authority['runtime_actions'] -ne $false -or
        $authority['live_authority'] -ne $false -or
        $authority['promotion_approved'] -ne $false -or
        $authority['network_dispatch_used'] -ne $false
    ) {
        Stop-P14GuestBroker 'snapshot_manifest_authority_invalid'
    }
    return $manifest
}

function Get-P14VBoxControl {
    $candidates = @(
        'C:\Program Files\Oracle\VirtualBox Guest Additions\VBoxControl.exe',
        'C:\Windows\System32\VBoxControl.exe'
    )
    $path = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } |
        Select-Object -First 1
    if (-not $path) {
        Stop-P14GuestBroker 'vboxcontrol_missing'
    }
    return $path
}

function Get-P14GuestRunId([string]$VBoxControl) {
    $lines = & $VBoxControl guestproperty get $P14GuestRunIdProperty 2>&1
    if ($LASTEXITCODE -ne 0) {
        Stop-P14GuestBroker 'guest_property_read_failed'
    }
    $values = @($lines | ForEach-Object { [string]$_ } | Where-Object { $_ -match '^Value:\s*(?<run_id>[a-f0-9]{16})\s*$' })
    if ($values.Count -eq 0) {
        return $null
    }
    if ($values.Count -ne 1 -or $values[0] -notmatch '^Value:\s*(?<run_id>[a-f0-9]{16})\s*$') {
        Stop-P14GuestBroker 'run_id_invalid'
    }
    return [string]$Matches['run_id']
}

function Get-P14GuestBindingSha256([string]$VBoxControl, [string]$Name) {
    if ($Name -notin @($P14GuestApplianceBindingSha256Property, $P14GuestSnapshotManifestSha256Property)) {
        Stop-P14GuestBroker 'binding_property_invalid'
    }
    $lines = & $VBoxControl guestproperty get $Name 2>&1
    if ($LASTEXITCODE -ne 0) {
        Stop-P14GuestBroker 'guest_property_read_failed'
    }
    $values = @($lines | ForEach-Object { [string]$_ } | Where-Object { $_ -match '^Value:\s*(?<sha256>[a-f0-9]{64})\s*$' })
    if ($values.Count -ne 1 -or $values[0] -notmatch '^Value:\s*(?<sha256>[a-f0-9]{64})\s*$') {
        Stop-P14GuestBroker 'appliance_binding_missing'
    }
    return [string]$Matches['sha256']
}

function Set-P14GuestProperty([string]$VBoxControl, [string]$Name, [string]$Value) {
    if (
        $Name -notin @($P14GuestStatusProperty, $P14GuestEnvelopeProperty, $P14GuestEnvelopeSha256Property) -or
        [string]::IsNullOrWhiteSpace($Value) -or
        [Text.Encoding]::UTF8.GetByteCount($Value) -gt $P14MaxGuestPropertyBytes
    ) {
        Stop-P14GuestBroker 'guest_property_value_invalid'
    }
    & $VBoxControl guestproperty set $Name $Value 2>$null
    if ($LASTEXITCODE -ne 0) {
        Stop-P14GuestBroker 'guest_property_write_failed'
    }
}

function Assert-P14GuestIsolation {
    if (-not [Environment]::UserInteractive) {
        Stop-P14GuestBroker 'interactive_guest_session_required'
    }
    $guestServices = @(
        'C:\Program Files\Oracle\VirtualBox Guest Additions\VBoxService.exe',
        'C:\Windows\System32\VBoxService.exe'
    )
    if (-not ($guestServices | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf })) {
        Stop-P14GuestBroker 'virtualbox_guest_additions_missing'
    }
    $activeAdapters = @(Get-NetAdapter -ErrorAction Stop | Where-Object { $_.Status -eq 'Up' })
    if ($activeAdapters.Count -ne 0) {
        Stop-P14GuestBroker 'network_adapter_not_isolated'
    }
}

function Set-P14ProcessIsolationFlags([string]$RunId) {
    foreach ($name in @(
            'CTOA_P14_CAPTURE_HELPER_ACTIVATION',
            'CTOA_P14_CAPTURE_REPORT_PATH',
            'CTOA_P14_CLIENT_PATH',
            'CTOA_P14_CLIENT_ROOT',
            'CTOA_P14_EVIDENCE_ROOT',
            'CTOA_P14_RUN_ID',
            'CTOA_P14_ISOLATED_ENVIRONMENT',
            'CTOA_P14_CAPTURE_CONTEXT',
            'CTOA_P14_OPERATOR_WORKSTATION_FOCUS_USED',
            'CTOA_P14_OPERATOR_WORKSTATION_INPUT_USED',
            'CTOA_P14_NETWORK_DISPATCH_USED',
            'CTOA_P14_LIVE_CLIENT_ACCESSED',
            'CTOA_P14_PROMOTION_ATTEMPTED'
        )) {
        Remove-Item -LiteralPath "Env:$name" -ErrorAction SilentlyContinue
    }
    $env:CTOA_P14_RUN_ID = $RunId
    $env:CTOA_P14_ISOLATED_ENVIRONMENT = 'true'
    $env:CTOA_P14_CAPTURE_CONTEXT = 'guest'
    $env:CTOA_P14_OPERATOR_WORKSTATION_FOCUS_USED = 'false'
    $env:CTOA_P14_OPERATOR_WORKSTATION_INPUT_USED = 'false'
    $env:CTOA_P14_NETWORK_DISPATCH_USED = 'false'
    $env:CTOA_P14_LIVE_CLIENT_ACCESSED = 'false'
    $env:CTOA_P14_PROMOTION_ATTEMPTED = 'false'
    $env:PYTHONDONTWRITEBYTECODE = '1'
}

function New-P14RunEvidenceRoot([string]$RunId) {
    $path = Join-Path $P14EvidenceRoot ("capture-$RunId")
    if (-not (Test-P14PathWithin $path $P14EvidenceRoot)) {
        Stop-P14GuestBroker 'run_evidence_path_invalid'
    }
    if (Test-Path -LiteralPath $path) {
        Stop-P14GuestBroker 'capture_evidence_run_already_exists'
    }
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    return (Resolve-Path -LiteralPath $path).Path
}

function Get-P14ArtifactHash([hashtable]$Capture, [string]$Kind, [string]$ExpectedPath, [string]$Root) {
    $matches = @($Capture['artifacts'] | Where-Object { $_ -is [hashtable] -and $_['kind'] -eq $Kind })
    if ($matches.Count -ne 1) {
        Stop-P14GuestBroker 'capture_artifact_invalid'
    }
    $artifact = $matches[0]
    $path = Join-Path $Root $ExpectedPath
    if (
        $artifact['path'] -ne $ExpectedPath -or
        $artifact['sha256'] -notmatch '^[a-f0-9]{64}$' -or
        $artifact['bytes'] -ne (Get-Item -LiteralPath $path -Force).Length -or
        $artifact['sha256'] -ne (Get-P14RegularFileHash $path)
    ) {
        Stop-P14GuestBroker 'capture_artifact_invalid'
    }
    return [string]$artifact['sha256']
}

function Get-P14PassedProof([hashtable]$Proof, [string]$ProofId) {
    if (
        $Proof -isnot [hashtable] -or
        $Proof['proof_id'] -ne $ProofId -or
        $Proof['status'] -ne 'passed' -or
        $Proof['artifact_count'] -lt 1 -or
        $Proof['artifact_count'] -gt 16 -or
        $Proof['evidence_sha256'] -notmatch '^[a-f0-9]{64}$'
    ) {
        Stop-P14GuestBroker 'review_proof_invalid'
    }
    return [ordered]@{
        proof_id = $ProofId
        status = 'passed'
        artifact_count = [int]$Proof['artifact_count']
        evidence_sha256 = [string]$Proof['evidence_sha256']
    }
}

function Get-P14EvidenceInputs([string]$RunId, [hashtable]$Manifest) {
    $captureRoot = Join-Path $P14EvidenceRoot ("capture-$RunId")
    $capturePath = Join-Path $captureRoot 'capture-report.json'
    $reviewPath = Join-Path $captureRoot 'evidence-review.json'
    $sandboxRoot = Join-Path $P14EvidenceRoot $RunId
    $sandboxPath = Join-Path $sandboxRoot 'sandbox-execution.json'
    foreach ($path in @($capturePath, $reviewPath, $sandboxPath)) {
        if (-not (Test-P14PathWithin $path $P14EvidenceRoot)) {
            Stop-P14GuestBroker 'evidence_path_invalid'
        }
    }
    $capture = Get-P14Json $capturePath
    $review = Get-P14Json $reviewPath
    $sandbox = Get-P14Json $sandboxPath
    if (
        $capture['schema_version'] -ne 'ctoa.p14-vm-capture.v1' -or
        $capture['status'] -ne 'observed_pass' -or
        $capture['run_id'] -ne $RunId -or
        $capture['source_revision'] -ne $Manifest['source_revision']
    ) {
        Stop-P14GuestBroker 'capture_binding_invalid'
    }
    $imageName = "p14-in-world-$($Manifest['source_revision']).png"
    $imageHash = Get-P14ArtifactHash $capture 'in_world_capture' $imageName $captureRoot
    $runtimeHash = Get-P14ArtifactHash $capture 'helper_runtime_marker' 'client-capabilities.json' $captureRoot
    if (
        $review['schema_version'] -ne 'ctoa.p14-evidence-review.v1' -or
        $review['status'] -ne 'passed' -or
        $review['run_id'] -ne $RunId -or
        $review['source_revision'] -ne $Manifest['source_revision'] -or
        $review['isolation']['network_dispatch_used'] -ne $false
    ) {
        Stop-P14GuestBroker 'review_binding_invalid'
    }
    $visualReview = Get-P14PassedProof $review['visual'] 'independent_visual_review'
    $inWorldReview = Get-P14PassedProof $review['in_world'] 'independent_in_world_review'
    if (
        $sandbox['schema_version'] -ne 'ctoa.p14-sandbox-rehearsal.v1' -or
        $sandbox['status'] -ne 'passed' -or
        $sandbox['run_id'] -ne $RunId -or
        $sandbox['source_manifest_sha256'] -notmatch '^[a-f0-9]{64}$' -or
        $sandbox['baseline_manifest_sha256'] -notmatch '^[a-f0-9]{64}$' -or
        $sandbox['changed_manifest_sha256'] -notmatch '^[a-f0-9]{64}$' -or
        $sandbox['restored_manifest_sha256'] -ne $sandbox['baseline_manifest_sha256'] -or
        $sandbox['changed_file_count'] -ne 1 -or
        $sandbox['canary_health'] -ne 'passed' -or
        $sandbox['rollback'] -ne 'rollback_verified'
    ) {
        Stop-P14GuestBroker 'sandbox_receipt_invalid'
    }
    return [ordered]@{
        capture_report_sha256 = Get-P14RegularFileHash $capturePath
        image_sha256 = $imageHash
        runtime_sha256 = $runtimeHash
        visual_review = $visualReview
        in_world_review = $inWorldReview
        sandbox_receipt_sha256 = Get-P14RegularFileHash $sandboxPath
        helper_manifest_sha256 = [string]$sandbox['source_manifest_sha256']
        baseline_manifest_sha256 = [string]$sandbox['baseline_manifest_sha256']
        changed_manifest_sha256 = [string]$sandbox['changed_manifest_sha256']
    }
}

function New-P14GuestReceipt(
    [string]$RunId,
    [hashtable]$Manifest,
    [hashtable]$Evidence,
    [string]$SnapshotManifestSha256,
    [string]$ApplianceBindingSha256
) {
    if (
        $SnapshotManifestSha256 -notmatch '^[a-f0-9]{64}$' -or
        $ApplianceBindingSha256 -notmatch '^[a-f0-9]{64}$'
    ) {
        Stop-P14GuestBroker 'appliance_binding_invalid'
    }
    $captureProof = [ordered]@{
        proof_id = 'isolated_visual_capture'
        status = 'passed'
        artifact_count = 1
        evidence_sha256 = $Evidence['image_sha256']
    }
    $clientLaunchProof = [ordered]@{
        proof_id = 'isolated_client_launch'
        status = 'passed'
        artifact_count = 1
        evidence_sha256 = $Evidence['capture_report_sha256']
    }
    $runtimeProof = [ordered]@{
        proof_id = 'helper_runtime_smoke'
        status = 'passed'
        artifact_count = 1
        evidence_sha256 = $Evidence['runtime_sha256']
    }
    $sandboxProof = [ordered]@{
        status = 'passed'
        artifact_count = 1
        evidence_sha256 = $Evidence['sandbox_receipt_sha256']
    }
    $canaryTransition = [ordered]@{
        baseline_manifest_sha256 = $Evidence['baseline_manifest_sha256']
        changed_manifest_sha256 = $Evidence['changed_manifest_sha256']
        restored_manifest_sha256 = $Evidence['changed_manifest_sha256']
        changed_file_count = 1
    }
    $rollbackTransition = [ordered]@{
        baseline_manifest_sha256 = $Evidence['baseline_manifest_sha256']
        changed_manifest_sha256 = $Evidence['changed_manifest_sha256']
        restored_manifest_sha256 = $Evidence['baseline_manifest_sha256']
        changed_file_count = 1
    }
    return [ordered]@{
        schema_version = 'ctoa.p14-guest-receipt.v2'
        receipt_id = "p14-guest-$RunId"
        generated_at = [DateTime]::UtcNow.ToString('o')
        binding = [ordered]@{
            source_revision = $Manifest['source_revision']
            helper_manifest_sha256 = $Evidence['helper_manifest_sha256']
            rollback_baseline_manifest_sha256 = $Evidence['baseline_manifest_sha256']
            snapshot_id = $Manifest['snapshot_id']
            snapshot_manifest_sha256 = $SnapshotManifestSha256
            appliance_binding_sha256 = $ApplianceBindingSha256
            run_id = $RunId
        }
        isolation = [ordered]@{
            isolated_environment = $true
            operator_workstation_focus_used = $false
            operator_workstation_input_used = $false
            network_dispatch_used = $false
            live_client_accessed = $false
            promotion_attempted = $false
        }
        capabilities = @(
            [ordered]@{
                capability = 'visual_regression'
                status = 'passed'
                proofs = @($captureProof, $Evidence['visual_review'])
                transition = $null
            },
            [ordered]@{
                capability = 'in_world_regression'
                status = 'passed'
                proofs = @($clientLaunchProof, $runtimeProof, $Evidence['in_world_review'])
                transition = $null
            },
            [ordered]@{
                capability = 'canary_rehearsal'
                status = 'passed'
                proofs = @(
                    [ordered]@{ proof_id = 'sandbox_canary_apply'; status = $sandboxProof['status']; artifact_count = $sandboxProof['artifact_count']; evidence_sha256 = $sandboxProof['evidence_sha256'] },
                    [ordered]@{ proof_id = 'canary_health_check'; status = $sandboxProof['status']; artifact_count = $sandboxProof['artifact_count']; evidence_sha256 = $sandboxProof['evidence_sha256'] }
                )
                transition = $canaryTransition
            },
            [ordered]@{
                capability = 'rollback_rehearsal'
                status = 'passed'
                proofs = @(
                    [ordered]@{ proof_id = 'rollback_apply'; status = $sandboxProof['status']; artifact_count = $sandboxProof['artifact_count']; evidence_sha256 = $sandboxProof['evidence_sha256'] },
                    [ordered]@{ proof_id = 'baseline_restore_verified'; status = $sandboxProof['status']; artifact_count = $sandboxProof['artifact_count']; evidence_sha256 = $sandboxProof['evidence_sha256'] }
                )
                transition = $rollbackTransition
            }
        )
    }
}

function Write-P14BigEndian([IO.Stream]$Stream, [UInt64]$Value, [int]$Width) {
    for ($index = $Width - 1; $index -ge 0; $index--) {
        $byte = [byte](($Value -shr (8 * $index)) -band 0xff)
        $Stream.WriteByte($byte)
    }
}

function Test-P14DerEcdsaSignature([byte[]]$Signature) {
    if ($Signature.Length -lt 8 -or $Signature.Length -gt 72 -or $Signature[0] -ne 0x30) {
        return $false
    }
    if ([int]$Signature[1] -ne $Signature.Length - 2) {
        return $false
    }
    $offset = 2
    foreach ($part in 1..2) {
        if ($offset + 2 -gt $Signature.Length -or $Signature[$offset] -ne 0x02) {
            return $false
        }
        $length = [int]$Signature[$offset + 1]
        if ($length -lt 1 -or $length -gt 33 -or $offset + 2 + $length -gt $Signature.Length) {
            return $false
        }
        # DER integers are positive and minimally encoded.
        if (($Signature[$offset + 2] -band 0x80) -ne 0) {
            return $false
        }
        if ($length -gt 1 -and $Signature[$offset + 2] -eq 0 -and ($Signature[$offset + 3] -band 0x80) -eq 0) {
            return $false
        }
        $offset += 2 + $length
    }
    return $offset -eq $Signature.Length
}

function Convert-P14EcdsaSignatureToDer([byte[]]$Signature) {
    # Windows CNG may return IEEE P1363 (r||s), while cryptography verifies the
    # RFC 3279 DER sequence used by the envelope contract.  Preserve a valid
    # DER result and otherwise convert precisely the expected 32+32 P-256 form.
    if (Test-P14DerEcdsaSignature $Signature) {
        return $Signature
    }
    if ($Signature.Length -ne 64) {
        Stop-P14GuestBroker 'evidence_signature_encoding_invalid'
    }
    $parts = @()
    foreach ($offset in @(0, 32)) {
        [byte[]]$part = $Signature[$offset..($offset + 31)]
        $first = 0
        while ($first -lt 31 -and $part[$first] -eq 0) {
            $first++
        }
        [byte[]]$trimmed = $part[$first..31]
        if (($trimmed[0] -band 0x80) -ne 0) {
            [byte[]]$padded = New-Object byte[] ($trimmed.Length + 1)
            [Array]::Copy($trimmed, 0, $padded, 1, $trimmed.Length)
            $trimmed = $padded
        }
        $parts += ,$trimmed
    }
    [byte[]]$r = $parts[0]
    [byte[]]$s = $parts[1]
    $bodyLength = 4 + $r.Length + $s.Length
    if ($bodyLength -gt 127) {
        Stop-P14GuestBroker 'evidence_signature_encoding_invalid'
    }
    $stream = [IO.MemoryStream]::new()
    try {
        $stream.WriteByte(0x30)
        $stream.WriteByte([byte]$bodyLength)
        $stream.WriteByte(0x02)
        $stream.WriteByte([byte]$r.Length)
        $stream.Write($r, 0, $r.Length)
        $stream.WriteByte(0x02)
        $stream.WriteByte([byte]$s.Length)
        $stream.Write($s, 0, $s.Length)
        return $stream.ToArray()
    } finally {
        $stream.Dispose()
    }
}

function New-P14GuestEnvelope([hashtable]$Manifest, [hashtable]$Receipt) {
    $evidence = $Manifest['evidence']
    $thumbprint = [string]$evidence['certificate_thumbprint']
    $certificates = @(
        Get-ChildItem -Path 'Cert:\CurrentUser\My' |
            Where-Object { $_.Thumbprint.ToLowerInvariant() -eq $thumbprint }
    )
    if ($certificates.Count -ne 1) {
        Stop-P14GuestBroker 'evidence_certificate_missing'
    }
    $certificate = $certificates[0]
    $rawCertificateHash = (Get-P14RawSha256 $certificate.RawData)
    if (-not $certificate.HasPrivateKey -or $rawCertificateHash -ne $evidence['certificate_sha256']) {
        Stop-P14GuestBroker 'evidence_certificate_binding_invalid'
    }
    $payload = [Text.UTF8Encoding]::new($false).GetBytes(($Receipt | ConvertTo-Json -Depth 12 -Compress))
    if ($payload.Length -lt 1 -or $payload.Length -gt 64KB) {
        Stop-P14GuestBroker 'receipt_payload_invalid'
    }
    $keyId = [string]$evidence['key_id']
    $keyBytes = [Text.Encoding]::ASCII.GetBytes($keyId)
    $stream = [IO.MemoryStream]::new()
    try {
        $stream.Write($P14SignatureDomain, 0, $P14SignatureDomain.Length)
        Write-P14BigEndian $stream ([UInt64]$keyBytes.Length) 2
        $stream.Write($keyBytes, 0, $keyBytes.Length)
        Write-P14BigEndian $stream ([UInt64]$payload.Length) 8
        $stream.Write($payload, 0, $payload.Length)
        $signatureInput = $stream.ToArray()
    } finally {
        $stream.Dispose()
    }
    $ecdsa = [Security.Cryptography.X509Certificates.ECDsaCertificateExtensions]::GetECDsaPrivateKey($certificate)
    if ($null -eq $ecdsa -or $ecdsa.KeySize -ne 256) {
        Stop-P14GuestBroker 'evidence_private_key_invalid'
    }
    try {
        $signature = $ecdsa.SignData($signatureInput, [Security.Cryptography.HashAlgorithmName]::SHA256)
    } finally {
        $ecdsa.Dispose()
    }
    if ($signature.Length -lt 1 -or $signature.Length -gt 1024) {
        Stop-P14GuestBroker 'evidence_signature_invalid'
    }
    $signature = Convert-P14EcdsaSignatureToDer $signature
    return [ordered]@{
        schema_version = 'ctoa.p14-guest-evidence-envelope.v1'
        algorithm = 'ecdsa-p256-sha256'
        key_id = $keyId
        payload_b64 = [Convert]::ToBase64String($payload)
        payload_sha256 = Get-P14RawSha256 $payload
        signature = [Convert]::ToBase64String($signature)
    }
}

function Get-P14RawSha256([byte[]]$Bytes) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        return ([BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace('-', '').ToLowerInvariant()
    } finally {
        $sha.Dispose()
    }
}

function Write-P14Envelope([string]$RunId, [hashtable]$Envelope) {
    $root = Join-Path $P14EvidenceRoot $RunId
    $path = Join-Path $root 'guest-evidence-envelope.json'
    if (-not (Test-P14PathWithin $path $P14EvidenceRoot) -or (Test-P14ReparsePoint $root)) {
        Stop-P14GuestBroker 'envelope_path_invalid'
    }
    $raw = [Text.UTF8Encoding]::new($false).GetBytes(($Envelope | ConvertTo-Json -Depth 6 -Compress))
    if ($raw.Length -lt 1 -or $raw.Length -gt $P14MaxEnvelopeRawBytes) {
        Stop-P14GuestBroker 'envelope_size_invalid'
    }
    $temporary = "$path.tmp"
    [IO.File]::WriteAllBytes($temporary, $raw)
    Move-Item -LiteralPath $temporary -Destination $path -Force
    return [ordered]@{
        envelope_b64 = [Convert]::ToBase64String($raw)
        envelope_sha256 = Get-P14RawSha256 $raw
    }
}

function Invoke-P14FixedSequence(
    [string]$RunId,
    [hashtable]$Manifest,
    [string]$VBoxControl,
    [string]$SnapshotManifestSha256,
    [string]$ApplianceBindingSha256
) {
    New-P14RunEvidenceRoot $RunId | Out-Null
    Set-P14ProcessIsolationFlags $RunId

    # Fixed scripts plus a source revision validated by the immutable snapshot
    # manifest.  There is no path or command selection at this boundary.
    & $P14CaptureScript -SourceRevision $Manifest['source_revision']
    & $P14EvidenceReviewScript -SourceRevision $Manifest['source_revision'] -RunId $RunId
    & $P14PythonExe $P14SandboxExecutor run --run-id $RunId
    if ($LASTEXITCODE -ne 0) {
        Stop-P14GuestBroker 'sandbox_executor_failed'
    }
    $evidence = Get-P14EvidenceInputs $RunId $Manifest
    $receipt = New-P14GuestReceipt $RunId $Manifest $evidence $SnapshotManifestSha256 $ApplianceBindingSha256
    $envelope = New-P14GuestEnvelope $Manifest $receipt
    $transport = Write-P14Envelope $RunId $envelope
    Set-P14GuestProperty $VBoxControl $P14GuestEnvelopeProperty $transport['envelope_b64']
    Set-P14GuestProperty $VBoxControl $P14GuestEnvelopeSha256Property $transport['envelope_sha256']
    Set-P14GuestProperty $VBoxControl $P14GuestStatusProperty "completed:$RunId"
}

function Get-P14SafeBlocker([Exception]$Exception) {
    $message = [string]$Exception.Message
    if ($message -match '^p14_guest_broker:(?<code>[a-z0-9_:-]{1,120})$') {
        return [string]$Matches['code']
    }
    return 'guest_sequence_failed'
}

$vboxControl = $null
$runId = $null
try {
    $vboxControl = Get-P14VBoxControl
    $runId = Get-P14GuestRunId $vboxControl
    # The provisioned appliance is snapshotted as a saved interactive standard
    # user session.  Keep this fixed, input-free broker alive across that saved
    # state so a later host runner can supply only its bounded binding values;
    # a five-minute wall-clock deadline would expire while the appliance was
    # intentionally powered down between isolated rehearsals.
    while (-not $runId -and -not $RunOnce) {
        Start-Sleep -Milliseconds 500
        $runId = Get-P14GuestRunId $vboxControl
    }
    if (-not $runId) {
        [ordered]@{
            schema_version = 'ctoa.p14-guest-broker-receipt.v2'
            status = 'idle'
            endpoint_profile = $P14EndpointProfile
        } | ConvertTo-Json -Depth 4
        exit 0
    }
    Set-P14GuestProperty $vboxControl $P14GuestStatusProperty "running:$runId"
    Assert-P14GuestIsolation
    Assert-P14PortableToolchain
    $manifest = Get-P14SnapshotManifest
    $snapshotManifestSha256 = Get-P14RegularFileHash $P14TrustManifest $P14MaxManifestBytes
    $expectedSnapshotManifestSha256 = Get-P14GuestBindingSha256 $vboxControl $P14GuestSnapshotManifestSha256Property
    if ($snapshotManifestSha256 -ne $expectedSnapshotManifestSha256) {
        Stop-P14GuestBroker 'snapshot_manifest_hash_mismatch'
    }
    $applianceBindingSha256 = Get-P14GuestBindingSha256 $vboxControl $P14GuestApplianceBindingSha256Property
    Invoke-P14FixedSequence $runId $manifest $vboxControl $snapshotManifestSha256 $applianceBindingSha256
    [ordered]@{
        schema_version = 'ctoa.p14-guest-broker-receipt.v2'
        status = 'completed'
        run_id = $runId
        source_revision = $manifest['source_revision']
        endpoint_profile = $P14EndpointProfile
        authority = $manifest['authority']
    } | ConvertTo-Json -Depth 6
} catch {
    $blocker = Get-P14SafeBlocker $_.Exception
    if ($vboxControl -and $runId) {
        try {
            Set-P14GuestProperty $vboxControl $P14GuestStatusProperty "blocked:${runId}:$blocker"
        } catch {
            # Preserve the original fail-closed result if the guest-property
            # transport itself is unavailable.
        }
    }
    [ordered]@{
        schema_version = 'ctoa.p14-guest-broker-receipt.v2'
        status = 'blocked'
        blocker = $blocker
        authority = [ordered]@{
            runtime_actions = $false
            live_authority = $false
            promotion_approved = $false
            network_dispatch_used = $false
        }
    } | ConvertTo-Json -Depth 5
    exit 2
}
