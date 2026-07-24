[CmdletBinding()]
param(
    [switch]$Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# This is the one-time host coordinator for the pre-baseline transfer only.
# It creates a strict manifest from the fixed transport root, exposes that
# root through one read-only share, waits for the LOCAL SYSTEM guest bootstrap
# receipt hash, powers the isolated VM down through ACPI, and removes the
# share.  It does not invoke any staged client, repo, Python, or Git content
# in the guest and it does not create a baseline, provision, bind, or run P14.
$P14ApplianceVmName = 'CTOA-P14-Runner-Fresh-20260724'
$P14StageHostRoot = 'C:\P14Transport\ctoa-p14-stage'
$P14StageShareName = 'CTOA_P14_STAGE'
$P14StageManifestName = 'p14-stage-manifest.json'
$P14GuestStatusProperty = '/CTOAi/P14/StageBootstrap'
$P14AllowedRoots = @('repo', 'client', 'toolchain')
$P14ManifestSchema = 'ctoa.p14-stage-input.v1'
$P14MaximumFileCount = 20000
$P14MaximumFileBytes = 1GB
$P14MaximumTotalBytes = 16GB
$P14StageWaitSeconds = 900
$P14ShutdownWaitSeconds = 180

function Stop-P14StageHost([string]$Code) {
    throw "p14_stage_host:$Code"
}

function Test-P14ReparsePoint([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        return $false
    }
    return (((Get-Item -LiteralPath $Path -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)
}

function Get-P14VBoxManage {
    $candidates = @(
        'C:\Program Files\Oracle\VirtualBox\VBoxManage.exe',
        'C:\Program Files (x86)\Oracle\VirtualBox\VBoxManage.exe'
    )
    $path = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
    if (-not $path -or (Test-P14ReparsePoint $path)) {
        Stop-P14StageHost 'vboxmanage_missing'
    }
    return $path
}

function Invoke-P14VBoxRead([string]$VBoxManage, [string[]]$Arguments) {
    $result = & $VBoxManage @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        Stop-P14StageHost 'vbox_read_failed'
    }
    return @($result | ForEach-Object { [string]$_ })
}

function Invoke-P14VBoxWrite([string]$VBoxManage, [string[]]$Arguments) {
    $result = & $VBoxManage @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        Stop-P14StageHost 'vbox_write_failed'
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

function Assert-P14NoSharedFolders([string[]]$Machine) {
    foreach ($line in $Machine) {
        if ($line -match '^SharedFolderNameMachineMapping[0-9]+="') {
            Stop-P14StageHost 'shared_folder_present'
        }
    }
}

function Assert-P14StageMachine([string[]]$Machine, [string]$ExpectedState) {
    if (
        (Get-P14MachineValue $Machine 'name') -ne $P14ApplianceVmName -or
        (Get-P14MachineValue $Machine 'UUID') -notmatch '^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$' -or
        (Get-P14MachineValue $Machine 'VMState') -ne $ExpectedState
    ) {
        Stop-P14StageHost 'appliance_identity_invalid'
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
            Stop-P14StageHost "appliance_setting_invalid:$($setting.Key)"
        }
    }
    $cableConnected1 = Get-P14MachineValue $Machine 'cableconnected1'
    if ($null -ne $cableConnected1 -and $cableConnected1 -ne 'off') {
        Stop-P14StageHost 'appliance_setting_invalid:cableconnected1'
    }
    foreach ($line in $Machine) {
        if ($line -match '^nic[0-9]+="(?<mode>[^"]+)"$' -and $Matches['mode'] -ne 'none') {
            Stop-P14StageHost 'network_mode_not_isolated'
        }
    }
}

function Assert-P14SafeRelativePath([string]$Value) {
    if (
        [string]::IsNullOrWhiteSpace($Value) -or
        $Value.Length -gt 240 -or
        $Value.Contains('\') -or
        $Value.StartsWith('/') -or
        $Value.Contains(':') -or
        $Value -match '[\x00-\x1f]'
    ) {
        Stop-P14StageHost 'transport_path_invalid'
    }
    foreach ($segment in $Value.Split('/')) {
        if (
            [string]::IsNullOrWhiteSpace($segment) -or
            $segment -in @('.', '..') -or
            $segment.EndsWith('.') -or
            $segment.EndsWith(' ')
        ) {
            Stop-P14StageHost 'transport_path_invalid'
        }
    }
}

function Get-P14FileDigest([string]$Path) {
    if (
        -not (Test-Path -LiteralPath $Path -PathType Leaf) -or
        (Test-P14ReparsePoint $Path)
    ) {
        Stop-P14StageHost 'transport_regular_file_required'
    }
    $before = Get-Item -LiteralPath $Path -Force
    if ($before.Length -lt 0 -or $before.Length -gt $P14MaximumFileBytes) {
        Stop-P14StageHost 'transport_file_size_invalid'
    }
    $hash = Get-FileHash -LiteralPath $Path -Algorithm SHA256
    $after = Get-Item -LiteralPath $Path -Force
    if (
        $after.Length -ne $before.Length -or
        $after.LastWriteTimeUtc.Ticks -ne $before.LastWriteTimeUtc.Ticks -or
        (Test-P14ReparsePoint $Path)
    ) {
        Stop-P14StageHost 'transport_file_changed_during_hash'
    }
    return [ordered]@{
        bytes = [int64]$before.Length
        sha256 = $hash.Hash.ToLowerInvariant()
    }
}

function Assert-P14TransportTopLevel {
    if (
        -not (Test-Path -LiteralPath $P14StageHostRoot -PathType Container) -or
        (Test-P14ReparsePoint $P14StageHostRoot)
    ) {
        Stop-P14StageHost 'transport_root_missing'
    }
    $entries = @(Get-ChildItem -LiteralPath $P14StageHostRoot -Force)
    $actual = @($entries | ForEach-Object { [string]$_.Name })
    if (@(Compare-Object -ReferenceObject $P14AllowedRoots -DifferenceObject $actual -CaseSensitive).Count -ne 0) {
        Stop-P14StageHost 'transport_top_level_invalid'
    }
    foreach ($entry in $entries) {
        if (
            -not (Test-Path -LiteralPath $entry.FullName -PathType Container) -or
            (Test-P14ReparsePoint $entry.FullName)
        ) {
            Stop-P14StageHost 'transport_root_invalid'
        }
    }
    $gitDirectory = Join-Path (Join-Path $P14StageHostRoot 'repo') '.git'
    if (
        -not (Test-Path -LiteralPath $gitDirectory -PathType Container) -or
        (Test-P14ReparsePoint $gitDirectory)
    ) {
        Stop-P14StageHost 'transport_repository_invalid'
    }
}

function Get-P14TransportEntries([string]$RootName) {
    $rootPath = Join-Path $P14StageHostRoot $RootName
    $rootFull = [IO.Path]::GetFullPath($rootPath).TrimEnd('\')
    $pending = [System.Collections.Generic.List[string]]::new()
    $pending.Add($rootFull) | Out-Null
    $entries = [System.Collections.Generic.List[object]]::new()
    $seen = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    while ($pending.Count -gt 0) {
        $directory = $pending[$pending.Count - 1]
        $pending.RemoveAt($pending.Count - 1)
        if (Test-P14ReparsePoint $directory) {
            Stop-P14StageHost 'transport_reparse_point_rejected'
        }
        foreach ($entry in @(Get-ChildItem -LiteralPath $directory -Force)) {
            if (Test-P14ReparsePoint $entry.FullName) {
                Stop-P14StageHost 'transport_reparse_point_rejected'
            }
            if ($entry.PSIsContainer) {
                $pending.Add($entry.FullName) | Out-Null
                continue
            }
            if (-not (Test-Path -LiteralPath $entry.FullName -PathType Leaf)) {
                Stop-P14StageHost 'transport_special_file_rejected'
            }
            $relative = $entry.FullName.Substring($rootFull.Length).TrimStart([char[]]@('\')).Replace('\', '/')
            Assert-P14SafeRelativePath $relative
            if (-not $seen.Add($relative)) {
                Stop-P14StageHost 'transport_path_case_collision'
            }
            $digest = Get-P14FileDigest $entry.FullName
            $entries.Add([ordered]@{
                    root = $RootName
                    path = $relative
                    bytes = $digest['bytes']
                    sha256 = $digest['sha256']
                }) | Out-Null
        }
    }
    return ,$entries.ToArray()
}

function Get-P14HostGit {
    $git = Get-Command git.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $git) {
        Stop-P14StageHost 'host_git_missing'
    }
    return $git.Source
}

function Get-P14SourceRevision {
    $git = Get-P14HostGit
    $repo = Join-Path $P14StageHostRoot 'repo'
    $revision = (& $git -C $repo rev-parse HEAD 2>$null | Select-Object -First 1).Trim().ToLowerInvariant()
    $dirty = @(& $git -C $repo status --porcelain 2>$null)
    if ($LASTEXITCODE -ne 0 -or $revision -notmatch '^[a-f0-9]{40}$' -or $dirty.Count -ne 0) {
        Stop-P14StageHost 'transport_source_revision_invalid'
    }
    return $revision
}

function Write-P14StageManifest([System.Collections.IDictionary]$Manifest) {
    $path = Join-Path $P14StageHostRoot $P14StageManifestName
    if (Test-Path -LiteralPath $path) {
        Stop-P14StageHost 'transport_manifest_already_exists'
    }
    $raw = [Text.UTF8Encoding]::new($false).GetBytes(($Manifest | ConvertTo-Json -Depth 8) + [Environment]::NewLine)
    $stream = $null
    try {
        $stream = [IO.File]::Open(
            $path,
            [IO.FileMode]::CreateNew,
            [IO.FileAccess]::Write,
            [IO.FileShare]::None
        )
        $stream.Write($raw, 0, $raw.Length)
        $stream.Flush($true)
    } finally {
        if ($null -ne $stream) {
            $stream.Dispose()
        }
    }
}

function New-P14StageManifest {
    Assert-P14TransportTopLevel
    $entries = [System.Collections.Generic.List[object]]::new()
    foreach ($root in $P14AllowedRoots) {
        foreach ($entry in (Get-P14TransportEntries $root)) {
            $entries.Add($entry) | Out-Null
        }
    }
    if ($entries.Count -lt 1 -or $entries.Count -gt $P14MaximumFileCount) {
        Stop-P14StageHost 'transport_file_count_invalid'
    }
    $rootCounts = [ordered]@{}
    foreach ($root in $P14AllowedRoots) {
        $rootCounts[$root] = 0
    }
    $totalBytes = [int64]0
    foreach ($entry in $entries) {
        $rootCounts[$entry['root']]++
        $totalBytes += [int64]$entry['bytes']
        if ($totalBytes -gt $P14MaximumTotalBytes) {
            Stop-P14StageHost 'transport_total_size_invalid'
        }
    }
    foreach ($root in $P14AllowedRoots) {
        if ($rootCounts[$root] -lt 1) {
            Stop-P14StageHost 'transport_required_root_empty'
        }
    }
    $files = @(
        $entries |
            Sort-Object @{
                Expression = { ("$($_['root'])/$($_['path'])").ToLowerInvariant() }
            }, @{
                Expression = { "$($_['root'])/$($_['path'])" }
            }
    )
    $manifest = [ordered]@{
        schema_version = $P14ManifestSchema
        source_revision = Get-P14SourceRevision
        file_count = $files.Count
        files = $files
    }
    Write-P14StageManifest $manifest
    return $manifest
}

function Get-P14StageStatus([string]$VBoxManage) {
    $lines = Invoke-P14VBoxRead $VBoxManage @('guestproperty', 'get', $P14ApplianceVmName, $P14GuestStatusProperty)
    $valueLine = @($lines | Where-Object { $_ -match '^Value:\s*(?<value>.*)$' })
    if ($valueLine.Count -ne 1 -or $valueLine[0] -notmatch '^Value:\s*(?<value>.*)$') {
        Stop-P14StageHost 'guest_status_invalid'
    }
    $value = [string]$Matches['value']
    if ($value -eq 'No value set!') {
        return $null
    }
    if ($value -notmatch '^ctoa\.p14-stage-bootstrap\.v1\|(?<status>waiting|staged|blocked)\|(?<value>[a-z0-9._:-]{1,80})$') {
        Stop-P14StageHost 'guest_status_invalid'
    }
    return [ordered]@{
        status = $Matches['status']
        value = $Matches['value']
    }
}

function Wait-P14StageResult([string]$VBoxManage) {
    $deadline = (Get-Date).AddSeconds($P14StageWaitSeconds)
    while ((Get-Date) -lt $deadline) {
        $status = Get-P14StageStatus $VBoxManage
        if ($null -ne $status) {
            if ($status['status'] -eq 'staged' -and $status['value'] -match '^[a-f0-9]{64}$') {
                return $status
            }
            if ($status['status'] -eq 'blocked') {
                Stop-P14StageHost "guest_bootstrap_blocked:$($status['value'])"
            }
        }
        Start-Sleep -Seconds 5
    }
    Stop-P14StageHost 'guest_bootstrap_timeout'
}

function Wait-P14VmPowerOff([string]$VBoxManage) {
    $deadline = (Get-Date).AddSeconds($P14ShutdownWaitSeconds)
    while ((Get-Date) -lt $deadline) {
        if ((Get-P14MachineValue (Get-P14Machine $VBoxManage) 'VMState') -eq 'poweroff') {
            return
        }
        Start-Sleep -Seconds 5
    }
    Stop-P14StageHost 'guest_shutdown_timeout'
}

function Remove-P14StageShare([string]$VBoxManage) {
    Invoke-P14VBoxWrite $VBoxManage @(
        'sharedfolder',
        'remove',
        $P14ApplianceVmName,
        "--name=$P14StageShareName"
    ) | Out-Null
    Assert-P14NoSharedFolders (Get-P14Machine $VBoxManage)
}

if (-not $Apply) {
    [ordered]@{
        schema_version = 'ctoa.p14-stage-host-plan.v1'
        status = 'dry_run'
        vm_name = $P14ApplianceVmName
        host_transport_root = $P14StageHostRoot
        guest_share = '\\VBOXSVR\CTOA_P14_STAGE'
        share_read_only = $true
        allowed_roots = $P14AllowedRoots
        host_writes = @('p14-stage-manifest.json', 'temporary_vbox_share')
        teardown = 'acpi_shutdown_then_remove_share_and_verify_no_shared_folders'
        staged_content_executed = $false
        baseline_created = $false
        provisioned = $false
    } | ConvertTo-Json -Depth 6
    return
}

$vbox = Get-P14VBoxManage
Assert-P14StageMachine (Get-P14Machine $vbox) 'poweroff'
Assert-P14NoSharedFolders (Get-P14Machine $vbox)
$manifest = New-P14StageManifest
$existingStageStatus = Get-P14StageStatus $vbox
if ($null -ne $existingStageStatus) {
    Invoke-P14VBoxWrite $vbox @('guestproperty', 'delete', $P14ApplianceVmName, $P14GuestStatusProperty) | Out-Null
}
Invoke-P14VBoxWrite $vbox @(
    'sharedfolder',
    'add',
    $P14ApplianceVmName,
    "--name=$P14StageShareName",
    "--hostpath=$P14StageHostRoot",
    '--readonly',
    '--automount'
) | Out-Null

$result = $null
try {
    Invoke-P14VBoxWrite $vbox @('startvm', $P14ApplianceVmName, '--type', 'headless') | Out-Null
    $result = Wait-P14StageResult $vbox
} finally {
    $state = Get-P14MachineValue (Get-P14Machine $vbox) 'VMState'
    if ($state -ne 'poweroff') {
        Invoke-P14VBoxWrite $vbox @('controlvm', $P14ApplianceVmName, 'acpipowerbutton') | Out-Null
        Wait-P14VmPowerOff $vbox
    }
    Remove-P14StageShare $vbox
}

[ordered]@{
    schema_version = 'ctoa.p14-stage-host-result.v1'
    status = 'staged_and_torn_down'
    source_revision = $manifest['source_revision']
    file_count = $manifest['file_count']
    guest_receipt_sha256 = $result['value']
    share_removed = $true
    staged_content_executed = $false
    baseline_created = $false
    provisioned = $false
} | ConvertTo-Json -Depth 6
