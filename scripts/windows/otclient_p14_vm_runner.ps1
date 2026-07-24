[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-f0-9]{16}$')]
    [string]$RunId,

    [ValidateRange(30, 900)]
    [int]$WaitSeconds = 600,

    [switch]$Execute
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# The appliance selection comes only from a local, immutable B1 binding made
# after the fresh offline snapshot exists. Neither a caller nor this source
# file can select a VM UUID, snapshot UUID, guest path, credential, or command.
# The prior appliance is intentionally not a fallback and is never targeted.
$P14ApplianceVmName = 'CTOA-P14-Runner-Fresh-20260724'
$P14BindingDirectory = 'C:\ProgramData\CTOAi\P14'
$P14BindingPath = 'C:\ProgramData\CTOAi\P14\p14-appliance-binding.json'
$P14GuestRunIdProperty = '/CTOAi/P14/RunId'
$P14GuestStatusProperty = '/CTOAi/P14/Status'
$P14GuestEnvelopeProperty = '/CTOAi/P14/EvidenceEnvelopeB64'
$P14GuestEnvelopeSha256Property = '/CTOAi/P14/EvidenceEnvelopeSha256'
$P14GuestApplianceBindingSha256Property = '/CTOAi/P14/ApplianceBindingSha256'
$P14GuestSnapshotManifestSha256Property = '/CTOAi/P14/SnapshotManifestSha256'
$P14GuestSnapshotManifestB64Property = '/CTOAi/P14/SnapshotManifestB64'
$P14EndpointProfileKey = 'CTOA/P14/EndpointProfile'
$P14EndpointProfile = 'p14-offline-replay-v1'
$P14MaxBindingBytes = 64KB
$P14MaxGuestPropertyBytes = 32KB

function Stop-P14VmRunner([string]$Code) {
    throw "p14_vm_runner:$Code"
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
    # Windows PowerShell 5.1 lacks the hashtable and depth switches on its JSON
    # reader, so keep the external binding bounded and indexed locally.
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
        Stop-P14VmRunner $Code
    }
    $actual = @($Value.Keys | ForEach-Object { [string]$_ })
    if (@(Compare-Object -ReferenceObject $Expected -DifferenceObject $actual).Count -ne 0) {
        Stop-P14VmRunner $Code
    }
}

function Assert-P14Sha256([object]$Value, [string]$Code) {
    if ($Value -isnot [string] -or $Value -notmatch '^[a-f0-9]{64}$') {
        Stop-P14VmRunner $Code
    }
}

function Assert-P14Uuid([object]$Value, [string]$Code) {
    if ($Value -isnot [string] -or $Value -notmatch '^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$') {
        Stop-P14VmRunner $Code
    }
}

function Assert-P14ApplianceBinding([hashtable]$Binding) {
    Assert-P14ExactKeys $Binding @('schema_version', 'created_at', 'appliance', 'guest', 'evidence', 'authority') 'appliance_binding_invalid'
    if ($Binding['schema_version'] -ne 'ctoa.p14-appliance-binding.v1' -or [string]::IsNullOrWhiteSpace([string]$Binding['created_at'])) {
        Stop-P14VmRunner 'appliance_binding_invalid'
    }

    $appliance = $Binding['appliance']
    if ($appliance -isnot [hashtable]) {
        Stop-P14VmRunner 'appliance_binding_invalid'
    }
    Assert-P14ExactKeys $appliance @('vm_name', 'vm_uuid', 'snapshot_uuid', 'snapshot_id', 'snapshot_state', 'endpoint_profile') 'appliance_binding_invalid'
    if (
        $appliance['vm_name'] -ne $P14ApplianceVmName -or
        $appliance['snapshot_id'] -notmatch '^[a-z0-9][a-z0-9._-]{2,63}$' -or
        $appliance['snapshot_state'] -ne 'saved' -or
        $appliance['endpoint_profile'] -ne $P14EndpointProfile
    ) {
        Stop-P14VmRunner 'appliance_binding_invalid'
    }
    Assert-P14Uuid $appliance['vm_uuid'] 'appliance_binding_invalid'
    Assert-P14Uuid $appliance['snapshot_uuid'] 'appliance_binding_invalid'

    $guest = $Binding['guest']
    if ($guest -isnot [hashtable]) {
        Stop-P14VmRunner 'appliance_binding_invalid'
    }
    Assert-P14ExactKeys $guest @('source_revision', 'snapshot_manifest_sha256', 'bundle_manifest_sha256', 'visual_baseline_sha256') 'appliance_binding_invalid'
    if ($guest['source_revision'] -notmatch '^[a-f0-9]{40}$') {
        Stop-P14VmRunner 'appliance_binding_invalid'
    }
    foreach ($name in @('snapshot_manifest_sha256', 'bundle_manifest_sha256', 'visual_baseline_sha256')) {
        Assert-P14Sha256 $guest[$name] 'appliance_binding_invalid'
    }

    $evidence = $Binding['evidence']
    if ($evidence -isnot [hashtable]) {
        Stop-P14VmRunner 'appliance_binding_invalid'
    }
    Assert-P14ExactKeys $evidence @('key_id', 'certificate_sha256', 'certificate_thumbprint') 'appliance_binding_invalid'
    if ($evidence['key_id'] -notmatch '^[a-z0-9][a-z0-9._-]{2,63}$' -or $evidence['certificate_thumbprint'] -notmatch '^[a-f0-9]{40}$') {
        Stop-P14VmRunner 'appliance_binding_invalid'
    }
    Assert-P14Sha256 $evidence['certificate_sha256'] 'appliance_binding_invalid'

    $authority = $Binding['authority']
    if ($authority -isnot [hashtable]) {
        Stop-P14VmRunner 'appliance_binding_invalid'
    }
    $expectedAuthority = [ordered]@{
        runtime_actions = $false
        live_authority = $false
        promotion_approved = $false
        network_dispatch_used = $false
    }
    Assert-P14ExactKeys $authority @($expectedAuthority.Keys) 'appliance_binding_invalid'
    foreach ($entry in $expectedAuthority.GetEnumerator()) {
        if ($authority[$entry.Key] -ne $entry.Value) {
            Stop-P14VmRunner 'appliance_binding_invalid'
        }
    }
}

function Get-P14ApplianceBinding {
    if (-not (Test-Path -LiteralPath $P14BindingPath)) {
        return $null
    }
    foreach ($path in @('C:\ProgramData', 'C:\ProgramData\CTOAi', $P14BindingDirectory, $P14BindingPath)) {
        if (-not (Test-Path -LiteralPath $path) -or (Test-P14ReparsePoint $path)) {
            Stop-P14VmRunner 'appliance_binding_invalid'
        }
    }
    $item = Get-Item -LiteralPath $P14BindingPath -Force
    if (-not $item.IsReadOnly -or $item.PSIsContainer -or $item.Length -lt 1 -or $item.Length -gt $P14MaxBindingBytes) {
        Stop-P14VmRunner 'appliance_binding_invalid'
    }
    $raw = [IO.File]::ReadAllBytes($P14BindingPath)
    if ($raw.Length -ne $item.Length) {
        Stop-P14VmRunner 'appliance_binding_invalid'
    }
    try {
        $parsed = [Text.Encoding]::UTF8.GetString($raw).TrimStart([char]0xFEFF) | ConvertFrom-Json -ErrorAction Stop
        $binding = ConvertTo-P14Hashtable -Value $parsed
    } catch {
        Stop-P14VmRunner 'appliance_binding_invalid'
    }
    if ($binding -isnot [hashtable]) {
        Stop-P14VmRunner 'appliance_binding_invalid'
    }
    Assert-P14ApplianceBinding $binding
    return [ordered]@{
        value = $binding
        sha256 = Get-P14RawSha256 $raw
    }
}

function Get-P14VBoxManage {
    $candidates = @(
        'C:\Program Files\Oracle\VirtualBox\VBoxManage.exe',
        'C:\Program Files (x86)\Oracle\VirtualBox\VBoxManage.exe'
    )
    $path = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
    if (-not $path) {
        Stop-P14VmRunner 'vboxmanage_missing'
    }
    return $path
}

function Invoke-P14VBoxRead([string]$VBoxManage, [string[]]$Arguments) {
    $result = & $VBoxManage @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        Stop-P14VmRunner 'vbox_read_failed'
    }
    return @($result | ForEach-Object { [string]$_ })
}

function Invoke-P14VBoxWrite([string]$VBoxManage, [string[]]$Arguments) {
    $result = & $VBoxManage @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        Stop-P14VmRunner 'vbox_write_failed'
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

function Get-P14VmState([string]$VBoxManage, [hashtable]$Binding) {
    $machine = Invoke-P14VBoxRead $VBoxManage @('showvminfo', $Binding['appliance']['vm_uuid'], '--machinereadable')
    $state = Get-P14MachineValue $machine 'VMState'
    if ([string]::IsNullOrWhiteSpace($state) -or $state -notmatch '^[a-z_]+$') {
        Stop-P14VmRunner 'vm_state_invalid'
    }
    return $state
}

function Wait-P14VmState([string]$VBoxManage, [hashtable]$Binding, [string]$Expected, [int]$TimeoutSeconds = 30) {
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    do {
        # VBox reports transient `starting`, `stopping`, `saving`, and
        # `restoring` states around lifecycle commands.  Poll those states
        # rather than turning a normal transition into a stranded appliance.
        $machine = Invoke-P14VBoxRead $VBoxManage @('showvminfo', $Binding['appliance']['vm_uuid'], '--machinereadable')
        $state = Get-P14MachineValue $machine 'VMState'
        if ($state -eq $Expected) {
            return
        }
        Start-Sleep -Milliseconds 500
    } while ([DateTime]::UtcNow -lt $deadline)
    Stop-P14VmRunner "vm_state_timeout:$Expected"
}

function Assert-P14ApplianceIsolation([string]$VBoxManage, [hashtable]$Binding, [string]$ExpectedState) {
    if ($ExpectedState -notin @('saved', 'running')) {
        Stop-P14VmRunner 'vm_state_invalid'
    }
    $appliance = $Binding['appliance']
    $machine = Invoke-P14VBoxRead $VBoxManage @('showvminfo', $appliance['vm_uuid'], '--machinereadable')
    if (
        (Get-P14MachineValue $machine 'UUID') -ne $appliance['vm_uuid'] -or
        (Get-P14MachineValue $machine 'name') -ne $P14ApplianceVmName -or
        (Get-P14MachineValue $machine 'VMState') -ne $ExpectedState -or
        (Get-P14MachineValue $machine 'CurrentSnapshotUUID') -ne $appliance['snapshot_uuid']
    ) {
        Stop-P14VmRunner 'appliance_binding_mismatch'
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
        if ((Get-P14MachineValue $machine $setting.Key) -ne $setting.Value) {
            Stop-P14VmRunner("appliance_setting_invalid:$($setting.Key)")
        }
    }
    $cableConnected1 = Get-P14MachineValue $machine 'cableconnected1'
    if ($null -ne $cableConnected1 -and $cableConnected1 -ne 'off') {
        Stop-P14VmRunner 'appliance_setting_invalid:cableconnected1'
    }
    foreach ($line in $machine) {
        if ($line -match '^nic[0-9]+="(?<mode>[^"]+)"$' -and $Matches['mode'] -ne 'none') {
            Stop-P14VmRunner 'network_mode_not_isolated'
        }
        if ($line -match '^SharedFolderNameMachineMapping[0-9]+="') {
            Stop-P14VmRunner 'shared_folder_not_allowed'
        }
    }
    $endpoint = Invoke-P14VBoxRead $VBoxManage @('getextradata', $appliance['vm_uuid'], $P14EndpointProfileKey)
    if ($endpoint -notcontains "Value: $P14EndpointProfile") {
        Stop-P14VmRunner 'endpoint_profile_not_approved'
    }
}

function Get-P14GuestProperty([string]$VBoxManage, [hashtable]$Binding, [string]$Name) {
    $lines = Invoke-P14VBoxRead $VBoxManage @('guestproperty', 'get', $Binding['appliance']['vm_uuid'], $Name)
    $values = @($lines | Where-Object { $_ -match '^Value:\s*(?<value>.*)$' })
    if ($values.Count -eq 0) {
        return $null
    }
    if ($values.Count -ne 1 -or $values[0] -notmatch '^Value:\s*(?<value>.*)$') {
        Stop-P14VmRunner 'guest_property_invalid'
    }
    $value = [string]$Matches['value']
    if ($value -eq 'No value set!') {
        return $null
    }
    if ([string]::IsNullOrWhiteSpace($value) -or [Text.Encoding]::UTF8.GetByteCount($value) -gt $P14MaxGuestPropertyBytes) {
        Stop-P14VmRunner 'guest_property_invalid'
    }
    return $value
}

function Set-P14GuestProperty([string]$VBoxManage, [hashtable]$Binding, [string]$Name, [string]$Value) {
    if ($Name -eq $P14GuestRunIdProperty) {
        if ($Value -notmatch '^[a-f0-9]{16}$') { Stop-P14VmRunner 'guest_property_invalid' }
    } elseif ($Name -in @($P14GuestApplianceBindingSha256Property, $P14GuestSnapshotManifestSha256Property)) {
        if ($Value -notmatch '^[a-f0-9]{64}$') { Stop-P14VmRunner 'guest_property_invalid' }
    } else {
        Stop-P14VmRunner 'guest_property_invalid'
    }
    Invoke-P14VBoxWrite $VBoxManage @('guestproperty', 'set', $Binding['appliance']['vm_uuid'], $Name, $Value, '--flags', 'RDONLYGUEST') | Out-Null
    $lines = Invoke-P14VBoxRead $VBoxManage @('guestproperty', 'get', $Binding['appliance']['vm_uuid'], $Name, '--verbose')
    $values = @($lines | Where-Object { $_ -match '^Value:\s*(?<value>.*)$' })
    $flags = @($lines | Where-Object { $_ -match '^Flags:\s*(?<flags>.*)$' })
    if (
        $values.Count -ne 1 -or
        $flags.Count -ne 1 -or
        $values[0] -notmatch '^Value:\s*(?<value>.*)$' -or
        $Matches['value'] -cne $Value -or
        $flags[0] -notmatch '^Flags:\s*(?<flags>.*)$' -or
        $Matches['flags'] -notmatch '(^|,)RDONLYGUEST(,|$)'
    ) {
        Stop-P14VmRunner 'guest_property_write_invalid'
    }
}

function Clear-P14GuestProperties([string]$VBoxManage, [hashtable]$Binding) {
    foreach ($property in @(
            $P14GuestRunIdProperty,
            $P14GuestStatusProperty,
            $P14GuestEnvelopeProperty,
            $P14GuestEnvelopeSha256Property,
            $P14GuestApplianceBindingSha256Property,
            $P14GuestSnapshotManifestSha256Property,
            $P14GuestSnapshotManifestB64Property
        )) {
        Invoke-P14VBoxWrite $VBoxManage @('guestproperty', 'delete', $Binding['appliance']['vm_uuid'], $property) | Out-Null
    }
}

function Stop-AndRestoreP14Appliance([string]$VBoxManage, [hashtable]$Binding) {
    $state = Get-P14VmState $VBoxManage $Binding
    $settleDeadline = [DateTime]::UtcNow.AddSeconds(30)
    while ($state -notin @('poweroff', 'running', 'saved', 'aborted') -and [DateTime]::UtcNow -lt $settleDeadline) {
        Start-Sleep -Milliseconds 500
        $state = Get-P14VmState $VBoxManage $Binding
    }
    if ($state -eq 'running') {
        try {
            Clear-P14GuestProperties $VBoxManage $Binding
        } catch {
            # A restore below discards the temporary run; preserve it even if a
            # guest service disappears during shutdown.
        }
        Invoke-P14VBoxWrite $VBoxManage @('controlvm', $Binding['appliance']['vm_uuid'], 'poweroff') | Out-Null
        Wait-P14VmState $VBoxManage $Binding 'poweroff'
    } elseif ($state -notin @('poweroff', 'saved', 'aborted')) {
        Stop-P14VmRunner 'vm_state_invalid'
    }
    Invoke-P14VBoxWrite $VBoxManage @('snapshot', $Binding['appliance']['vm_uuid'], 'restore', $Binding['appliance']['snapshot_uuid']) | Out-Null
    Assert-P14ApplianceIsolation $VBoxManage $Binding 'saved'
}

$bindingRecord = Get-P14ApplianceBinding
if (-not $Execute) {
    [ordered]@{
        schema_version = 'ctoa.p14-vm-runner-plan.v3'
        status = if ($bindingRecord) { 'dry_run_bound' } else { 'dry_run_unbound' }
        run_id = $RunId
        wait_seconds = $WaitSeconds
        appliance_binding_state = if ($bindingRecord) { 'bound' } else { 'unbound' }
        endpoint_profile = $P14EndpointProfile
        would_start_headless = [bool]$bindingRecord
        would_set_guest_properties = @($P14GuestRunIdProperty, $P14GuestApplianceBindingSha256Property, $P14GuestSnapshotManifestSha256Property)
        would_collect_signed_envelope = [bool]$bindingRecord
        would_restore_saved_snapshot = [bool]$bindingRecord
        authority = [ordered]@{
            runtime_actions = $false
            live_authority = $false
            promotion_approved = $false
            operator_workstation_input_used = $false
        }
    } | ConvertTo-Json -Depth 6
    return
}

if (-not $bindingRecord) {
    Stop-P14VmRunner 'appliance_binding_missing'
}

$binding = $bindingRecord['value']
$vbox = Get-P14VBoxManage
$started = $false
try {
    Assert-P14ApplianceIsolation $vbox $binding 'saved'
    Invoke-P14VBoxWrite $vbox @('snapshot', $binding['appliance']['vm_uuid'], 'restore', $binding['appliance']['snapshot_uuid']) | Out-Null
    Assert-P14ApplianceIsolation $vbox $binding 'saved'
    Invoke-P14VBoxWrite $vbox @('startvm', $binding['appliance']['vm_uuid'], '--type', 'headless') | Out-Null
    $started = $true
    Wait-P14VmState $vbox $binding 'running'
    Assert-P14ApplianceIsolation $vbox $binding 'running'

    # VBox guest properties are a running-VM channel.  Clear stale values only
    # after the saved session resumes, then publish hashes before the run ID so
    # the persistent guest broker cannot consume a partially bound request.
    Clear-P14GuestProperties $vbox $binding
    Set-P14GuestProperty $vbox $binding $P14GuestSnapshotManifestSha256Property $binding['guest']['snapshot_manifest_sha256']
    Set-P14GuestProperty $vbox $binding $P14GuestApplianceBindingSha256Property $bindingRecord['sha256']
    Set-P14GuestProperty $vbox $binding $P14GuestRunIdProperty $RunId

    $deadline = [DateTime]::UtcNow.AddSeconds($WaitSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        $status = Get-P14GuestProperty $vbox $binding $P14GuestStatusProperty
        if ($status -eq "completed:$RunId") {
            $envelopeB64 = Get-P14GuestProperty $vbox $binding $P14GuestEnvelopeProperty
            $expectedEnvelopeSha256 = Get-P14GuestProperty $vbox $binding $P14GuestEnvelopeSha256Property
            if ($envelopeB64 -notmatch '^[A-Za-z0-9+/=]{16,32768}$' -or $expectedEnvelopeSha256 -notmatch '^[a-f0-9]{64}$') {
                Stop-P14VmRunner 'guest_envelope_invalid'
            }
            try {
                $envelopeRaw = [Convert]::FromBase64String($envelopeB64)
            } catch {
                Stop-P14VmRunner 'guest_envelope_invalid'
            }
            if ($envelopeRaw.Length -lt 1 -or $envelopeRaw.Length -gt 24KB -or (Get-P14RawSha256 $envelopeRaw) -ne $expectedEnvelopeSha256) {
                Stop-P14VmRunner 'guest_envelope_hash_invalid'
            }
            [ordered]@{
                schema_version = 'ctoa.p14-vm-runner-plan.v3'
                status = 'completed'
                run_id = $RunId
                endpoint_profile = $P14EndpointProfile
                acceptance_envelope_b64 = $envelopeB64
                acceptance_envelope_sha256 = $expectedEnvelopeSha256
                appliance_binding_sha256 = $bindingRecord['sha256']
                snapshot_manifest_sha256 = $binding['guest']['snapshot_manifest_sha256']
                authority = [ordered]@{
                    runtime_actions = $false
                    live_authority = $false
                    promotion_approved = $false
                    operator_workstation_input_used = $false
                }
            } | ConvertTo-Json -Depth 6
            return
        }
        if ($status -match "^blocked:${RunId}:(?<blocker>[a-z0-9_:-]{1,120})$") {
            [ordered]@{
                schema_version = 'ctoa.p14-vm-runner-plan.v3'
                status = 'blocked'
                run_id = $RunId
                endpoint_profile = $P14EndpointProfile
                blocker = [string]$Matches['blocker']
                appliance_binding_sha256 = $bindingRecord['sha256']
            } | ConvertTo-Json -Depth 5
            return
        }
        Start-Sleep -Milliseconds 500
    }
    Stop-P14VmRunner 'guest_evidence_timeout'
} finally {
    if ($started) {
        Stop-AndRestoreP14Appliance $vbox $binding
    }
}
