[CmdletBinding()]
param(
    [switch]$Apply,

    [string]$SnapshotId,

    [string]$VisualBaselineSha256
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
    New-Item -ItemType Directory -LiteralPath $Path -Force | Out-Null
}

function Get-P14RegularFileHash([string]$Path) {
    if (
        -not (Test-Path -LiteralPath $Path -PathType Leaf) -or
        (Test-P14ReparsePoint $Path) -or
        (Get-Item -LiteralPath $Path -Force).Length -gt 2MB
    ) {
        Stop-P14GuestProvision 'immutable_input_invalid'
    }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
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
    if ($VisualBaselineSha256 -notmatch '^[a-f0-9]{64}$') {
        Stop-P14GuestProvision 'visual_baseline_invalid'
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
        required_inputs = @('snapshot_id', 'visual_baseline_sha256')
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
Stage-P14Bundle

$revision = Get-P14SourceRevision
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
    visual_baseline_sha256 = $VisualBaselineSha256
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
    visual_baseline_sha256 = $VisualBaselineSha256
    guest_evidence_key_id = $P14EvidenceKeyId
    guest_evidence_public_cert_b64 = ConvertTo-P14CertificatePemB64 $certificate
    manifest_read_only = $true
    autostart = 'current_standard_guest_user_only'
    authority = $manifest.authority
} | ConvertTo-Json -Depth 8
