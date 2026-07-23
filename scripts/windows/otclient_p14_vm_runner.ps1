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

# Appliance selection is a source-controlled contract.  The caller can select
# only an opaque run id and a bounded wait duration, never a VM, snapshot,
# endpoint, command, path, or guest credential.
$P14VmUuid = '68c47454-65cd-4211-ac24-9a3f8bc219b1'
$P14SnapshotUuid = '60813f92-d982-44ee-95a8-833596672a1b'
$P14GuestRunIdProperty = '/CTOAi/P14/RunId'
$P14GuestStatusProperty = '/CTOAi/P14/Status'
$P14GuestEnvelopeProperty = '/CTOAi/P14/EvidenceEnvelopeB64'
$P14GuestEnvelopeSha256Property = '/CTOAi/P14/EvidenceEnvelopeSha256'
$P14EndpointProfileKey = 'CTOA/P14/EndpointProfile'
$P14EndpointProfile = 'p14-offline-replay-v1'
$P14MaxEnvelopePropertyBytes = 32KB

function Stop-P14VmRunner([string]$Code) {
    throw "p14_vm_runner:$Code"
}

function Get-P14VBoxManage {
    $candidates = @(
        'C:\Program Files\Oracle\VirtualBox\VBoxManage.exe',
        'C:\Program Files (x86)\Oracle\VirtualBox\VBoxManage.exe'
    )
    $path = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } |
        Select-Object -First 1
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

function Get-P14VmState([string]$VBoxManage) {
    $machine = Invoke-P14VBoxRead $VBoxManage @('showvminfo', $P14VmUuid, '--machinereadable')
    $state = Get-P14MachineValue $machine 'VMState'
    if ($state -notin @('poweroff', 'running', 'saved', 'aborted')) {
        Stop-P14VmRunner 'vm_state_invalid'
    }
    return $state
}

function Assert-P14ApplianceIsolation([string]$VBoxManage, [switch]$RequirePowerOff) {
    $machine = Invoke-P14VBoxRead $VBoxManage @(
        'showvminfo', $P14VmUuid, '--machinereadable'
    )

    if ((Get-P14MachineValue $machine 'UUID') -ne $P14VmUuid) {
        Stop-P14VmRunner 'vm_uuid_mismatch'
    }
    if ($RequirePowerOff -and (Get-P14MachineValue $machine 'VMState') -ne 'poweroff') {
        Stop-P14VmRunner 'vm_not_powered_off'
    }
    if ((Get-P14MachineValue $machine 'CurrentSnapshotUUID') -ne $P14SnapshotUuid) {
        Stop-P14VmRunner 'snapshot_mismatch'
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
    # VirtualBox omits cableconnected1 entirely when the adapter itself is
    # disabled.  A reported cable value must still be off, but its omission is
    # the expected representation for the required `nic1=none` state.
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

    $endpoint = Invoke-P14VBoxRead $VBoxManage @(
        'getextradata', $P14VmUuid, $P14EndpointProfileKey
    )
    if ($endpoint -notcontains "Value: $P14EndpointProfile") {
        Stop-P14VmRunner 'endpoint_profile_not_approved'
    }
}

function Get-P14GuestProperty([string]$VBoxManage, [string]$Name) {
    $lines = Invoke-P14VBoxRead $VBoxManage @('guestproperty', 'get', $P14VmUuid, $Name)
    $values = @($lines | Where-Object { $_ -match '^Value:\s*(?<value>.*)$' })
    if ($values.Count -eq 0) {
        return $null
    }
    if ($values.Count -ne 1 -or $values[0] -notmatch '^Value:\s*(?<value>.*)$') {
        Stop-P14VmRunner 'guest_property_invalid'
    }
    $value = [string]$Matches['value']
    if ([string]::IsNullOrWhiteSpace($value) -or [Text.Encoding]::UTF8.GetByteCount($value) -gt $P14MaxEnvelopePropertyBytes) {
        Stop-P14VmRunner 'guest_property_invalid'
    }
    return $value
}

function Clear-P14GuestProperties([string]$VBoxManage) {
    foreach ($property in @(
            $P14GuestRunIdProperty,
            $P14GuestStatusProperty,
            $P14GuestEnvelopeProperty,
            $P14GuestEnvelopeSha256Property
        )) {
        Invoke-P14VBoxWrite $VBoxManage @('guestproperty', 'delete', $P14VmUuid, $property) | Out-Null
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

function Stop-AndRestoreP14Appliance([string]$VBoxManage) {
    $state = Get-P14VmState $VBoxManage
    if ($state -ne 'poweroff') {
        Invoke-P14VBoxWrite $VBoxManage @('controlvm', $P14VmUuid, 'poweroff') | Out-Null
        $deadline = [DateTime]::UtcNow.AddSeconds(30)
        do {
            Start-Sleep -Milliseconds 500
            $state = Get-P14VmState $VBoxManage
        } while ($state -ne 'poweroff' -and [DateTime]::UtcNow -lt $deadline)
        if ($state -ne 'poweroff') {
            Stop-P14VmRunner 'vm_shutdown_timeout'
        }
    }
    Invoke-P14VBoxWrite $VBoxManage @('snapshot', $P14VmUuid, 'restore', $P14SnapshotUuid) | Out-Null
    Assert-P14ApplianceIsolation $VBoxManage -RequirePowerOff
    Clear-P14GuestProperties $VBoxManage
}

$vbox = Get-P14VBoxManage
Assert-P14ApplianceIsolation $vbox -RequirePowerOff

if (-not $Execute) {
    [ordered]@{
        schema_version = 'ctoa.p14-vm-runner-plan.v2'
        status = 'dry_run'
        run_id = $RunId
        wait_seconds = $WaitSeconds
        endpoint_profile = $P14EndpointProfile
        would_set_guest_property = $P14GuestRunIdProperty
        would_collect_signed_envelope = $true
        would_restore_snapshot = $true
        would_start_headless = $true
        authority = [ordered]@{
            runtime_actions = $false
            live_authority = $false
            promotion_approved = $false
            operator_workstation_input_used = $false
        }
    } | ConvertTo-Json -Depth 5
    return
}

$started = $false
try {
    # A restore can reapply legacy NIC settings, so validate again before any
    # guest property is written or VM process is started.
    Invoke-P14VBoxWrite $vbox @('snapshot', $P14VmUuid, 'restore', $P14SnapshotUuid) | Out-Null
    Assert-P14ApplianceIsolation $vbox -RequirePowerOff
    Clear-P14GuestProperties $vbox
    Invoke-P14VBoxWrite $vbox @('guestproperty', 'set', $P14VmUuid, $P14GuestRunIdProperty, $RunId) | Out-Null
    Invoke-P14VBoxWrite $vbox @('startvm', $P14VmUuid, '--type', 'headless') | Out-Null
    $started = $true

    $deadline = [DateTime]::UtcNow.AddSeconds($WaitSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        $status = Get-P14GuestProperty $vbox $P14GuestStatusProperty
        if ($status -eq "completed:$RunId") {
            $envelopeB64 = Get-P14GuestProperty $vbox $P14GuestEnvelopeProperty
            $expectedEnvelopeSha256 = Get-P14GuestProperty $vbox $P14GuestEnvelopeSha256Property
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
                schema_version = 'ctoa.p14-vm-runner-plan.v2'
                status = 'completed'
                run_id = $RunId
                endpoint_profile = $P14EndpointProfile
                acceptance_envelope_b64 = $envelopeB64
                acceptance_envelope_sha256 = $expectedEnvelopeSha256
                authority = [ordered]@{
                    runtime_actions = $false
                    live_authority = $false
                    promotion_approved = $false
                    operator_workstation_input_used = $false
                }
            } | ConvertTo-Json -Depth 5
            return
        }
        if ($status -match "^blocked:${RunId}:(?<blocker>[a-z0-9_:-]{1,120})$") {
            [ordered]@{
                schema_version = 'ctoa.p14-vm-runner-plan.v2'
                status = 'blocked'
                run_id = $RunId
                endpoint_profile = $P14EndpointProfile
                blocker = [string]$Matches['blocker']
            } | ConvertTo-Json -Depth 5
            return
        }
        Start-Sleep -Milliseconds 500
    }
    Stop-P14VmRunner 'guest_evidence_timeout'
} finally {
    if ($started) {
        Stop-AndRestoreP14Appliance $vbox
    }
}
