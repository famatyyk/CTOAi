[CmdletBinding()]
param(
    [switch]$Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# B1 is deliberately local and post-snapshot. The only appliance selection is
# this source-controlled fresh VM name; callers cannot supply a VM, snapshot,
# path, hash, credential, package, or command. The prior appliance is not a
# fallback and this binder never targets, renames, or removes it.
$P14ApplianceVmName = 'CTOA-P14-Runner-Fresh-20260724'
$P14BindingDirectory = 'C:\ProgramData\CTOAi\P14'
$P14BindingPath = 'C:\ProgramData\CTOAi\P14\p14-appliance-binding.json'
$P14GuestSnapshotManifestB64Property = '/CTOAi/P14/SnapshotManifestB64'
$P14GuestSnapshotManifestSha256Property = '/CTOAi/P14/SnapshotManifestSha256'
$P14GuestRunIdProperty = '/CTOAi/P14/RunId'
$P14GuestStatusProperty = '/CTOAi/P14/Status'
$P14GuestEnvelopeProperty = '/CTOAi/P14/EvidenceEnvelopeB64'
$P14GuestEnvelopeSha256Property = '/CTOAi/P14/EvidenceEnvelopeSha256'
$P14GuestApplianceBindingSha256Property = '/CTOAi/P14/ApplianceBindingSha256'
$P14EndpointProfileKey = 'CTOA/P14/EndpointProfile'
$P14EndpointProfile = 'p14-offline-replay-v1'
$P14MaxManifestBytes = 16KB
$P14MaxGuestPropertyBytes = 32KB

function Stop-P14ApplianceBind([string]$Code) {
    throw "p14_appliance_bind:$Code"
}

function Test-P14ReparsePoint([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        return $false
    }
    return (((Get-Item -LiteralPath $Path -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)
}

function Get-P14RawSha256([byte[]]$Bytes) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        return ([BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace('-', '').ToLowerInvariant()
    } finally {
        $sha.Dispose()
    }
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

function Assert-P14ExactKeys([hashtable]$Value, [string[]]$Expected, [string]$Code) {
    if ($null -eq $Value) {
        Stop-P14ApplianceBind $Code
    }
    $actual = @($Value.Keys | ForEach-Object { [string]$_ })
    if (@(Compare-Object -ReferenceObject $Expected -DifferenceObject $actual).Count -ne 0) {
        Stop-P14ApplianceBind $Code
    }
}

function Assert-P14Sha256([object]$Value, [string]$Code) {
    if ($Value -isnot [string] -or $Value -notmatch '^[a-f0-9]{64}$') {
        Stop-P14ApplianceBind $Code
    }
}

function Get-P14VBoxManage {
    $candidates = @(
        'C:\Program Files\Oracle\VirtualBox\VBoxManage.exe',
        'C:\Program Files (x86)\Oracle\VirtualBox\VBoxManage.exe'
    )
    $path = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
    if (-not $path) {
        Stop-P14ApplianceBind 'vboxmanage_missing'
    }
    return $path
}

function Invoke-P14VBoxRead([string]$VBoxManage, [string[]]$Arguments) {
    $result = & $VBoxManage @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        Stop-P14ApplianceBind 'vbox_read_failed'
    }
    return @($result | ForEach-Object { [string]$_ })
}

function Invoke-P14VBoxWrite([string]$VBoxManage, [string[]]$Arguments) {
    $result = & $VBoxManage @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        Stop-P14ApplianceBind 'vbox_write_failed'
    }
    return @($result | ForEach-Object { [string]$_ })
}

function Get-P14MachineValue([string[]]$Lines, [string]$Name) {
    $pattern = '^' + [regex]::Escape($Name) + '="(?<value>.*)"$'
    foreach ($line in $Lines) {
        if ($line -match $pattern) {
            return [string]$Matches['value']
        }
    }
    return $null
}

function Get-P14Machine([string]$VBoxManage) {
    return Invoke-P14VBoxRead $VBoxManage @('showvminfo', $P14ApplianceVmName, '--machinereadable')
}

function Assert-P14OfflineMachine([string[]]$Machine, [string]$ExpectedState, [switch]$RequireNoSnapshot) {
    if (
        (Get-P14MachineValue $Machine 'name') -ne $P14ApplianceVmName -or
        (Get-P14MachineValue $Machine 'UUID') -notmatch '^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$' -or
        (Get-P14MachineValue $Machine 'VMState') -ne $ExpectedState
    ) {
        Stop-P14ApplianceBind 'appliance_identity_invalid'
    }
    if ($RequireNoSnapshot -and -not [string]::IsNullOrWhiteSpace((Get-P14MachineValue $Machine 'CurrentSnapshotUUID'))) {
        Stop-P14ApplianceBind 'appliance_snapshot_already_exists'
    }
    $required = [ordered]@{
        clipboard = 'disabled'
        draganddrop = 'disabled'
        vrde = 'off'
        usb = 'off'
        recording_enabled = 'off'
        nic1 = 'none'
    }
    foreach ($setting in $required.GetEnumerator()) {
        if ((Get-P14MachineValue $Machine $setting.Key) -ne $setting.Value) {
            Stop-P14ApplianceBind("appliance_setting_invalid:$($setting.Key)")
        }
    }
    $cableConnected1 = Get-P14MachineValue $Machine 'cableconnected1'
    if ($null -ne $cableConnected1 -and $cableConnected1 -ne 'off') {
        Stop-P14ApplianceBind 'appliance_setting_invalid:cableconnected1'
    }
    foreach ($line in $Machine) {
        if ($line -match '^nic[0-9]+="(?<mode>[^"]+)"$' -and $Matches['mode'] -ne 'none') {
            Stop-P14ApplianceBind 'network_mode_not_isolated'
        }
        if ($line -match '^SharedFolderNameMachineMapping[0-9]+="') {
            Stop-P14ApplianceBind 'shared_folder_not_allowed'
        }
    }
}

function Assert-P14EndpointProfile([string]$VBoxManage, [string]$VmUuid) {
    $endpoint = Invoke-P14VBoxRead $VBoxManage @('getextradata', $VmUuid, $P14EndpointProfileKey)
    if ($endpoint -notcontains "Value: $P14EndpointProfile") {
        Stop-P14ApplianceBind 'endpoint_profile_not_approved'
    }
}

function Get-P14GuestProperty([string]$VBoxManage, [string]$VmUuid, [string]$Name) {
    $lines = Invoke-P14VBoxRead $VBoxManage @('guestproperty', 'get', $VmUuid, $Name)
    $values = @($lines | Where-Object { $_ -match '^Value:\s*(?<value>.*)$' })
    if ($values.Count -ne 1 -or $values[0] -notmatch '^Value:\s*(?<value>.*)$') {
        Stop-P14ApplianceBind 'guest_property_invalid'
    }
    $value = [string]$Matches['value']
    if ($value -eq 'No value set!' -or [string]::IsNullOrWhiteSpace($value) -or [Text.Encoding]::UTF8.GetByteCount($value) -gt $P14MaxGuestPropertyBytes) {
        Stop-P14ApplianceBind 'guest_property_missing'
    }
    return $value
}

function Remove-P14GuestProperties([string]$VBoxManage, [string]$VmUuid) {
    foreach ($property in @(
            $P14GuestSnapshotManifestB64Property,
            $P14GuestSnapshotManifestSha256Property,
            $P14GuestRunIdProperty,
            $P14GuestStatusProperty,
            $P14GuestEnvelopeProperty,
            $P14GuestEnvelopeSha256Property,
            $P14GuestApplianceBindingSha256Property
        )) {
        Invoke-P14VBoxWrite $VBoxManage @('guestproperty', 'delete', $VmUuid, $property) | Out-Null
    }
}

function Assert-P14GuestPropertiesAbsent([string]$VBoxManage, [string]$VmUuid) {
    foreach ($property in @(
            $P14GuestSnapshotManifestB64Property,
            $P14GuestSnapshotManifestSha256Property,
            $P14GuestRunIdProperty,
            $P14GuestStatusProperty,
            $P14GuestEnvelopeProperty,
            $P14GuestEnvelopeSha256Property,
            $P14GuestApplianceBindingSha256Property
        )) {
        $lines = Invoke-P14VBoxRead $VBoxManage @('guestproperty', 'get', $VmUuid, $property)
        if (@($lines | Where-Object { $_.Trim() -eq 'No value set!' }).Count -eq 1) {
            continue
        }
        $values = @($lines | Where-Object { $_ -match '^Value:\s*(?<value>.*)$' })
        if ($values.Count -ne 1 -or $values[0] -notmatch '^Value:\s*(?<value>.*)$' -or $Matches['value'] -ne 'No value set!') {
            Stop-P14ApplianceBind 'guest_property_clear_invalid'
        }
    }
}

function Get-P14SnapshotManifestExport([string]$VBoxManage, [string]$VmUuid) {
    $encoded = Get-P14GuestProperty $VBoxManage $VmUuid $P14GuestSnapshotManifestB64Property
    $expectedSha256 = Get-P14GuestProperty $VBoxManage $VmUuid $P14GuestSnapshotManifestSha256Property
    if ($encoded -notmatch '^[A-Za-z0-9+/=]{16,32768}$' -or $expectedSha256 -notmatch '^[a-f0-9]{64}$') {
        Stop-P14ApplianceBind 'snapshot_manifest_export_invalid'
    }
    try {
        $raw = [Convert]::FromBase64String($encoded)
    } catch {
        Stop-P14ApplianceBind 'snapshot_manifest_export_invalid'
    }
    if ($raw.Length -lt 1 -or $raw.Length -gt $P14MaxManifestBytes -or (Get-P14RawSha256 $raw) -ne $expectedSha256) {
        Stop-P14ApplianceBind 'snapshot_manifest_export_invalid'
    }
    try {
        $parsed = [Text.Encoding]::UTF8.GetString($raw).TrimStart([char]0xFEFF) | ConvertFrom-Json -ErrorAction Stop
        $manifest = ConvertTo-P14Hashtable -Value $parsed
    } catch {
        Stop-P14ApplianceBind 'snapshot_manifest_export_invalid'
    }
    if ($manifest -isnot [hashtable]) {
        Stop-P14ApplianceBind 'snapshot_manifest_export_invalid'
    }
    Assert-P14ExactKeys $manifest @('schema_version', 'source_revision', 'snapshot_id', 'endpoint_profile', 'visual_baseline_sha256', 'evidence', 'files', 'authority') 'snapshot_manifest_export_invalid'
    if (
        $manifest['schema_version'] -ne 'ctoa.p14-guest-snapshot.v1' -or
        $manifest['source_revision'] -notmatch '^[a-f0-9]{40}$' -or
        $manifest['snapshot_id'] -notmatch '^[a-z0-9][a-z0-9._-]{2,63}$' -or
        $manifest['endpoint_profile'] -ne $P14EndpointProfile
    ) {
        Stop-P14ApplianceBind 'snapshot_manifest_export_invalid'
    }
    Assert-P14Sha256 $manifest['visual_baseline_sha256'] 'snapshot_manifest_export_invalid'
    $evidence = $manifest['evidence']
    if ($evidence -isnot [hashtable]) { Stop-P14ApplianceBind 'snapshot_manifest_export_invalid' }
    Assert-P14ExactKeys $evidence @('key_id', 'certificate_sha256', 'certificate_thumbprint') 'snapshot_manifest_export_invalid'
    if ($evidence['key_id'] -notmatch '^[a-z0-9][a-z0-9._-]{2,63}$' -or $evidence['certificate_thumbprint'] -notmatch '^[a-f0-9]{40}$') {
        Stop-P14ApplianceBind 'snapshot_manifest_export_invalid'
    }
    Assert-P14Sha256 $evidence['certificate_sha256'] 'snapshot_manifest_export_invalid'
    $files = $manifest['files']
    if ($files -isnot [hashtable]) { Stop-P14ApplianceBind 'snapshot_manifest_export_invalid' }
    Assert-P14ExactKeys $files @('broker', 'capture', 'review', 'executor', 'bundle_manifest') 'snapshot_manifest_export_invalid'
    foreach ($name in @('broker', 'capture', 'review', 'executor', 'bundle_manifest')) {
        Assert-P14Sha256 $files[$name] 'snapshot_manifest_export_invalid'
    }
    $authority = $manifest['authority']
    if ($authority -isnot [hashtable]) { Stop-P14ApplianceBind 'snapshot_manifest_export_invalid' }
    $expectedAuthority = [ordered]@{
        runtime_actions = $false
        live_authority = $false
        promotion_approved = $false
        network_dispatch_used = $false
    }
    Assert-P14ExactKeys $authority @($expectedAuthority.Keys) 'snapshot_manifest_export_invalid'
    foreach ($entry in $expectedAuthority.GetEnumerator()) {
        if ($authority[$entry.Key] -ne $entry.Value) { Stop-P14ApplianceBind 'snapshot_manifest_export_invalid' }
    }
    return [ordered]@{
        value = $manifest
        sha256 = $expectedSha256
    }
}

function Wait-P14VmState([string]$VBoxManage, [string]$VmUuid, [string]$Expected, [int]$TimeoutSeconds = 60) {
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    do {
        $machine = Invoke-P14VBoxRead $VBoxManage @('showvminfo', $VmUuid, '--machinereadable')
        if ((Get-P14MachineValue $machine 'VMState') -eq $Expected) {
            return
        }
        Start-Sleep -Milliseconds 500
    } while ([DateTime]::UtcNow -lt $deadline)
    Stop-P14ApplianceBind "vm_state_timeout:$Expected"
}

function Write-P14Binding([hashtable]$Record) {
    if (Test-Path -LiteralPath $P14BindingPath) {
        Stop-P14ApplianceBind 'appliance_binding_exists'
    }
    if (-not (Test-Path -LiteralPath 'C:\ProgramData' -PathType Container) -or (Test-P14ReparsePoint 'C:\ProgramData')) {
        Stop-P14ApplianceBind 'binding_directory_invalid'
    }
    if (-not (Test-Path -LiteralPath $P14BindingDirectory)) {
        New-Item -ItemType Directory -Path $P14BindingDirectory -Force | Out-Null
    }
    foreach ($path in @('C:\ProgramData\CTOAi', $P14BindingDirectory)) {
        if (-not (Test-Path -LiteralPath $path -PathType Container) -or (Test-P14ReparsePoint $path)) {
            Stop-P14ApplianceBind 'binding_directory_invalid'
        }
    }
    $raw = [Text.UTF8Encoding]::new($false).GetBytes(($Record | ConvertTo-Json -Depth 8 -Compress))
    if ($raw.Length -lt 1 -or $raw.Length -gt 64KB) {
        Stop-P14ApplianceBind 'appliance_binding_invalid'
    }
    $temporary = Join-Path $P14BindingDirectory ('.p14-appliance-binding-' + [Guid]::NewGuid().ToString('N') + '.tmp')
    try {
        [IO.File]::WriteAllBytes($temporary, $raw)
        [IO.File]::Move($temporary, $P14BindingPath)
        $item = Get-Item -LiteralPath $P14BindingPath -Force
        $item.Attributes = $item.Attributes -bor [IO.FileAttributes]::ReadOnly
        $stored = [IO.File]::ReadAllBytes($P14BindingPath)
        if ((Get-P14RawSha256 $stored) -ne (Get-P14RawSha256 $raw) -or -not (Get-Item -LiteralPath $P14BindingPath -Force).IsReadOnly) {
            Stop-P14ApplianceBind 'appliance_binding_write_invalid'
        }
        return Get-P14RawSha256 $stored
    } finally {
        if (Test-Path -LiteralPath $temporary) {
            Remove-Item -LiteralPath $temporary -Force
        }
    }
}

if (-not $Apply) {
    [ordered]@{
        schema_version = 'ctoa.p14-appliance-bind-plan.v1'
        status = if (Test-Path -LiteralPath $P14BindingPath) { 'already_bound' } else { 'dry_run' }
        appliance_name = $P14ApplianceVmName
        binding_path = $P14BindingPath
        would_require_running_offline_guest = $true
        would_save_guest_session = $true
        would_create_snapshot_from_manifest = $true
        would_write_immutable_binding = $true
        authority = [ordered]@{
            runtime_actions = $false
            live_authority = $false
            promotion_approved = $false
            network_dispatch_used = $false
        }
    } | ConvertTo-Json -Depth 5
    return
}

if (Test-Path -LiteralPath $P14BindingPath) {
    Stop-P14ApplianceBind 'appliance_binding_exists'
}

$vbox = Get-P14VBoxManage
$machine = Get-P14Machine $vbox
Assert-P14OfflineMachine $machine 'running' -RequireNoSnapshot
$vmUuid = Get-P14MachineValue $machine 'UUID'
Assert-P14EndpointProfile $vbox $vmUuid
$manifestExport = Get-P14SnapshotManifestExport $vbox $vmUuid

# The manifest has now crossed its one fixed, non-secret guest-property bridge.
# Clear every temporary property while the VM is still running; the snapshot
# starts from an empty host-to-guest channel and the runner repopulates only its
# read-only commitments immediately before each rehearsal.
Remove-P14GuestProperties $vbox $vmUuid
Assert-P14GuestPropertiesAbsent $vbox $vmUuid
Invoke-P14VBoxWrite $vbox @('controlvm', $vmUuid, 'savestate') | Out-Null
Wait-P14VmState $vbox $vmUuid 'saved'
$savedMachine = Get-P14Machine $vbox
Assert-P14OfflineMachine $savedMachine 'saved' -RequireNoSnapshot
Assert-P14EndpointProfile $vbox $vmUuid

$manifest = $manifestExport['value']
Invoke-P14VBoxWrite $vbox @('snapshot', $vmUuid, 'take', $manifest['snapshot_id']) | Out-Null
$snapshottedMachine = Get-P14Machine $vbox
Assert-P14OfflineMachine $snapshottedMachine 'saved'
$snapshotUuid = Get-P14MachineValue $snapshottedMachine 'CurrentSnapshotUUID'
if ($snapshotUuid -notmatch '^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$') {
    Stop-P14ApplianceBind 'snapshot_uuid_invalid'
}
# `snapshot take` above accepts only the manifest-derived safe ID and returned
# success.  VBoxManage 7.x does not expose machine-readable snapshot showinfo;
# the current-snapshot UUID is the immutable selector used from here onward.

$record = [ordered]@{
    schema_version = 'ctoa.p14-appliance-binding.v1'
    created_at = [DateTime]::UtcNow.ToString('o')
    appliance = [ordered]@{
        vm_name = $P14ApplianceVmName
        vm_uuid = $vmUuid
        snapshot_uuid = $snapshotUuid
        snapshot_id = $manifest['snapshot_id']
        snapshot_state = 'saved'
        endpoint_profile = $P14EndpointProfile
    }
    guest = [ordered]@{
        source_revision = $manifest['source_revision']
        snapshot_manifest_sha256 = $manifestExport['sha256']
        bundle_manifest_sha256 = $manifest['files']['bundle_manifest']
        visual_baseline_sha256 = $manifest['visual_baseline_sha256']
    }
    evidence = [ordered]@{
        key_id = $manifest['evidence']['key_id']
        certificate_sha256 = $manifest['evidence']['certificate_sha256']
        certificate_thumbprint = $manifest['evidence']['certificate_thumbprint']
    }
    authority = [ordered]@{
        runtime_actions = $false
        live_authority = $false
        promotion_approved = $false
        network_dispatch_used = $false
    }
}
$bindingSha256 = Write-P14Binding $record

[ordered]@{
    schema_version = 'ctoa.p14-appliance-bind-plan.v1'
    status = 'bound'
    source_revision = $record['guest']['source_revision']
    snapshot_id = $record['appliance']['snapshot_id']
    snapshot_manifest_sha256 = $record['guest']['snapshot_manifest_sha256']
    appliance_binding_sha256 = $bindingSha256
    guest_evidence_key_id = $record['evidence']['key_id']
    authority = $record['authority']
} | ConvertTo-Json -Depth 6
