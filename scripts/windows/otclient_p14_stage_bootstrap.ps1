[CmdletBinding()]
param(
    [switch]$Install,

    [switch]$Run
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# This bootstrap is copied into the answer ISO at the exact path below.  The
# answer ISO invokes -Install as LOCAL SYSTEM; the resulting startup task runs
# -Run as LOCAL SYSTEM and copies only a verified, read-only VirtualBox share.
# It never starts a staged executable, Python, Git, client, capture, baseline,
# provisioner, broker, or runner.
$P14BootstrapScript = 'C:\Windows\Setup\Scripts\ctoa_p14_stage_bootstrap.ps1'
$P14BootstrapTaskName = 'CTOAi-P14-Stage-Bootstrap'
$P14PowerShell = 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
$P14ShareRoot = '\\VBOXSVR\CTOA_P14_STAGE'
$P14ManifestName = 'p14-stage-manifest.json'
$P14ManifestPath = '\\VBOXSVR\CTOA_P14_STAGE\p14-stage-manifest.json'
$P14RunnerRoot = 'C:\P14Runner'
$P14ReceiptDirectory = 'C:\ProgramData\CTOAi\P14'
$P14ReceiptPath = 'C:\ProgramData\CTOAi\P14\stage-bootstrap-receipt.json'
$P14GuestStatusProperty = '/CTOAi/P14/StageBootstrap'
$P14AllowedRoots = @('repo', 'client', 'toolchain')
$P14ManifestSchema = 'ctoa.p14-stage-input.v1'
$P14ReceiptSchema = 'ctoa.p14-stage-bootstrap-receipt.v1'
$P14MaximumManifestBytes = 8MB
$P14MaximumFileCount = 20000
$P14MaximumFileBytes = 1GB
$P14MaximumTotalBytes = 16GB
$P14CopyBufferBytes = 1MB
$P14ShareWaitAttempts = 120
$P14ShareWaitSeconds = 5
$script:P14VBoxControl = $null

function Stop-P14StageBootstrap([string]$Code) {
    throw "p14_stage_bootstrap:$Code"
}

function Test-P14ReparsePoint([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        return $false
    }
    return (((Get-Item -LiteralPath $Path -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)
}

function Assert-P14Directory([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
    if (-not (Test-Path -LiteralPath $Path -PathType Container) -or (Test-P14ReparsePoint $Path)) {
        Stop-P14StageBootstrap 'directory_invalid'
    }
}

function Test-P14PathWithin([string]$Path, [string]$Root) {
    $candidate = [IO.Path]::GetFullPath($Path).TrimEnd('\')
    $allowed = [IO.Path]::GetFullPath($Root).TrimEnd('\')
    return $candidate.Equals($allowed, [StringComparison]::OrdinalIgnoreCase) -or
        $candidate.StartsWith($allowed + '\', [StringComparison]::OrdinalIgnoreCase)
}

function Get-P14RawSha256([byte[]]$Bytes) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        return ([BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace('-', '').ToLowerInvariant()
    } finally {
        $sha.Dispose()
    }
}

function Get-P14FileDigest(
    [string]$Path,
    [int64]$MaximumBytes = $P14MaximumFileBytes
) {
    if (
        -not (Test-Path -LiteralPath $Path -PathType Leaf) -or
        (Test-P14ReparsePoint $Path)
    ) {
        Stop-P14StageBootstrap 'regular_file_required'
    }
    $before = Get-Item -LiteralPath $Path -Force
    if ($before.Length -lt 0 -or $before.Length -gt $MaximumBytes) {
        Stop-P14StageBootstrap 'file_size_invalid'
    }
    $stream = [IO.File]::Open(
        $Path,
        [IO.FileMode]::Open,
        [IO.FileAccess]::Read,
        [IO.FileShare]::Read
    )
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        $digest = ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-', '').ToLowerInvariant()
    } finally {
        $sha.Dispose()
        $stream.Dispose()
    }
    $after = Get-Item -LiteralPath $Path -Force
    if (
        $after.Length -ne $before.Length -or
        $after.LastWriteTimeUtc.Ticks -ne $before.LastWriteTimeUtc.Ticks -or
        (Test-P14ReparsePoint $Path)
    ) {
        Stop-P14StageBootstrap 'file_changed_during_hash'
    }
    return [ordered]@{
        bytes = [int64]$before.Length
        sha256 = $digest
    }
}

function ConvertTo-P14Hashtable(
    [object]$Value,
    [int]$CurrentDepth = 0,
    [int]$MaximumDepth = 20
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

function Skip-P14JsonWhitespace([string]$Text, [ref]$Index) {
    while ($Index.Value -lt $Text.Length -and [char]::IsWhiteSpace($Text[$Index.Value])) {
        $Index.Value++
    }
}

function Read-P14JsonStringToken([string]$Text, [ref]$Index) {
    if ($Index.Value -ge $Text.Length -or $Text[$Index.Value] -ne '"') {
        Stop-P14StageBootstrap 'json_invalid'
    }
    $start = $Index.Value
    $Index.Value++
    while ($Index.Value -lt $Text.Length) {
        $character = $Text[$Index.Value]
        if ([int][char]$character -lt 0x20) {
            Stop-P14StageBootstrap 'json_invalid'
        }
        if ($character -eq '"') {
            $Index.Value++
            return $Text.Substring($start, $Index.Value - $start)
        }
        if ($character -eq '\') {
            $Index.Value++
            if ($Index.Value -ge $Text.Length) {
                Stop-P14StageBootstrap 'json_invalid'
            }
            $escape = $Text[$Index.Value]
            if ($escape -eq 'u') {
                if ($Index.Value + 4 -ge $Text.Length) {
                    Stop-P14StageBootstrap 'json_invalid'
                }
                $hex = $Text.Substring($Index.Value + 1, 4)
                if ($hex -notmatch '^[0-9A-Fa-f]{4}$') {
                    Stop-P14StageBootstrap 'json_invalid'
                }
                $Index.Value += 5
                continue
            }
            if ($escape -notin @('"', '\', '/', 'b', 'f', 'n', 'r', 't')) {
                Stop-P14StageBootstrap 'json_invalid'
            }
        }
        $Index.Value++
    }
    Stop-P14StageBootstrap 'json_invalid'
}

function Assert-P14JsonValue([string]$Text, [ref]$Index, [int]$Depth = 0) {
    if ($Depth -gt 20) {
        Stop-P14StageBootstrap 'json_depth_exceeded'
    }
    Skip-P14JsonWhitespace $Text $Index
    if ($Index.Value -ge $Text.Length) {
        Stop-P14StageBootstrap 'json_invalid'
    }
    $character = $Text[$Index.Value]
    if ($character -eq '{') {
        $Index.Value++
        Skip-P14JsonWhitespace $Text $Index
        $seen = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
        if ($Index.Value -lt $Text.Length -and $Text[$Index.Value] -eq '}') {
            $Index.Value++
            return
        }
        while ($true) {
            Skip-P14JsonWhitespace $Text $Index
            $token = Read-P14JsonStringToken $Text $Index
            try {
                $key = ConvertFrom-Json -InputObject $token -ErrorAction Stop
            } catch {
                Stop-P14StageBootstrap 'json_invalid'
            }
            if ($key -isnot [string] -or -not $seen.Add($key)) {
                Stop-P14StageBootstrap 'duplicate_json_key'
            }
            Skip-P14JsonWhitespace $Text $Index
            if ($Index.Value -ge $Text.Length -or $Text[$Index.Value] -ne ':') {
                Stop-P14StageBootstrap 'json_invalid'
            }
            $Index.Value++
            Assert-P14JsonValue $Text $Index ($Depth + 1)
            Skip-P14JsonWhitespace $Text $Index
            if ($Index.Value -ge $Text.Length) {
                Stop-P14StageBootstrap 'json_invalid'
            }
            if ($Text[$Index.Value] -eq '}') {
                $Index.Value++
                return
            }
            if ($Text[$Index.Value] -ne ',') {
                Stop-P14StageBootstrap 'json_invalid'
            }
            $Index.Value++
        }
    }
    if ($character -eq '[') {
        $Index.Value++
        Skip-P14JsonWhitespace $Text $Index
        if ($Index.Value -lt $Text.Length -and $Text[$Index.Value] -eq ']') {
            $Index.Value++
            return
        }
        while ($true) {
            Assert-P14JsonValue $Text $Index ($Depth + 1)
            Skip-P14JsonWhitespace $Text $Index
            if ($Index.Value -ge $Text.Length) {
                Stop-P14StageBootstrap 'json_invalid'
            }
            if ($Text[$Index.Value] -eq ']') {
                $Index.Value++
                return
            }
            if ($Text[$Index.Value] -ne ',') {
                Stop-P14StageBootstrap 'json_invalid'
            }
            $Index.Value++
        }
    }
    if ($character -eq '"') {
        Read-P14JsonStringToken $Text $Index | Out-Null
        return
    }
    $start = $Index.Value
    while (
        $Index.Value -lt $Text.Length -and
        -not [char]::IsWhiteSpace($Text[$Index.Value]) -and
        $Text[$Index.Value] -notin @(',', ']', '}')
    ) {
        $Index.Value++
    }
    if ($Index.Value -eq $start) {
        Stop-P14StageBootstrap 'json_invalid'
    }
}

function Assert-P14NoDuplicateJsonKeys([string]$Text) {
    $index = 0
    Assert-P14JsonValue $Text ([ref]$index)
    Skip-P14JsonWhitespace $Text ([ref]$index)
    if ($index -ne $Text.Length) {
        Stop-P14StageBootstrap 'json_invalid'
    }
}

function Get-P14Json([string]$Path) {
    $digest = Get-P14FileDigest $Path $P14MaximumManifestBytes
    $raw = [IO.File]::ReadAllBytes($Path)
    $after = Get-P14FileDigest $Path $P14MaximumManifestBytes
    if ($raw.Length -ne $digest['bytes'] -or $after['sha256'] -ne $digest['sha256']) {
        Stop-P14StageBootstrap 'manifest_changed_during_read'
    }
    try {
        $text = [Text.UTF8Encoding]::new($false, $true).GetString($raw).TrimStart([char]0xFEFF)
        Assert-P14NoDuplicateJsonKeys $text
        $value = ConvertTo-P14Hashtable -Value ($text | ConvertFrom-Json -ErrorAction Stop)
    } catch {
        if ($_.Exception.Message -match '^p14_stage_bootstrap:') {
            throw
        }
        Stop-P14StageBootstrap 'json_invalid'
    }
    if ($value -isnot [hashtable]) {
        Stop-P14StageBootstrap 'manifest_invalid'
    }
    return [ordered]@{
        value = $value
        sha256 = $digest['sha256']
    }
}

function Assert-P14ExactKeys([hashtable]$Value, [string[]]$Expected, [string]$Code) {
    if ($null -eq $Value) {
        Stop-P14StageBootstrap $Code
    }
    $actual = @($Value.Keys | ForEach-Object { [string]$_ })
    if (@(Compare-Object -ReferenceObject $Expected -DifferenceObject $actual -CaseSensitive).Count -ne 0) {
        Stop-P14StageBootstrap $Code
    }
}

function Assert-P14SafeRelativePath([object]$Value) {
    if (
        $Value -isnot [string] -or
        [string]::IsNullOrWhiteSpace($Value) -or
        $Value.Length -gt 240 -or
        $Value.Contains('\') -or
        $Value.StartsWith('/') -or
        $Value.Contains(':') -or
        $Value -match '[\x00-\x1f]'
    ) {
        Stop-P14StageBootstrap 'manifest_path_invalid'
    }
    foreach ($segment in $Value.Split('/')) {
        if (
            [string]::IsNullOrWhiteSpace($segment) -or
            $segment -in @('.', '..') -or
            $segment.EndsWith('.') -or
            $segment.EndsWith(' ')
        ) {
            Stop-P14StageBootstrap 'manifest_path_invalid'
        }
    }
}

function Get-P14StageManifest {
    $parsed = Get-P14Json $P14ManifestPath
    $value = $parsed['value']
    Assert-P14ExactKeys $value @('schema_version', 'source_revision', 'file_count', 'files') 'manifest_invalid'
    if (
        $value['schema_version'] -ne $P14ManifestSchema -or
        $value['source_revision'] -isnot [string] -or
        $value['source_revision'] -notmatch '^[a-f0-9]{40}$' -or
        ($value['file_count'] -isnot [int] -and $value['file_count'] -isnot [long]) -or
        $value['file_count'] -lt 1 -or
        $value['file_count'] -gt $P14MaximumFileCount -or
        $value['files'] -isnot [array] -or
        $value['file_count'] -ne $value['files'].Count
    ) {
        Stop-P14StageBootstrap 'manifest_invalid'
    }
    $files = [System.Collections.Generic.List[object]]::new()
    $seen = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    $rootCounts = [ordered]@{}
    foreach ($root in $P14AllowedRoots) {
        $rootCounts[$root] = 0
    }
    $previous = $null
    $totalBytes = [int64]0
    foreach ($entry in $value['files']) {
        if ($entry -isnot [hashtable]) {
            Stop-P14StageBootstrap 'manifest_entry_invalid'
        }
        Assert-P14ExactKeys $entry @('root', 'path', 'bytes', 'sha256') 'manifest_entry_invalid'
        if (
            $entry['root'] -isnot [string] -or
            $entry['root'] -notin $P14AllowedRoots -or
            ($entry['bytes'] -isnot [int] -and $entry['bytes'] -isnot [long]) -or
            $entry['bytes'] -lt 0 -or
            $entry['bytes'] -gt $P14MaximumFileBytes -or
            $entry['sha256'] -isnot [string] -or
            $entry['sha256'] -notmatch '^[a-f0-9]{64}$'
        ) {
            Stop-P14StageBootstrap 'manifest_entry_invalid'
        }
        Assert-P14SafeRelativePath $entry['path']
        $key = "$($entry['root'])/$($entry['path'])"
        if (-not $seen.Add($key)) {
            Stop-P14StageBootstrap 'manifest_path_duplicate_or_case_collision'
        }
        if ($null -ne $previous -and [StringComparer]::OrdinalIgnoreCase.Compare($previous, $key) -ge 0) {
            Stop-P14StageBootstrap 'manifest_order_invalid'
        }
        $previous = $key
        $totalBytes += [int64]$entry['bytes']
        if ($totalBytes -gt $P14MaximumTotalBytes) {
            Stop-P14StageBootstrap 'manifest_total_size_invalid'
        }
        $rootCounts[$entry['root']]++
        $files.Add([ordered]@{
                root = $entry['root']
                path = $entry['path']
                bytes = [int64]$entry['bytes']
                sha256 = $entry['sha256']
            }) | Out-Null
    }
    foreach ($root in $P14AllowedRoots) {
        if ($rootCounts[$root] -lt 1) {
            Stop-P14StageBootstrap 'manifest_root_missing'
        }
    }
    return [ordered]@{
        source_revision = $value['source_revision']
        file_count = $files.Count
        files = ,$files.ToArray()
        manifest_sha256 = $parsed['sha256']
    }
}

function Join-P14FixedRoot([string]$Root, [string]$Relative) {
    $path = $Root
    foreach ($segment in $Relative.Split('/')) {
        $path = Join-Path $path $segment
    }
    if (-not (Test-P14PathWithin $path $Root)) {
        Stop-P14StageBootstrap 'path_outside_allowed_root'
    }
    return $path
}

function Assert-P14ShareTopLevel {
    if (-not (Test-Path -LiteralPath $P14ShareRoot -PathType Container) -or (Test-P14ReparsePoint $P14ShareRoot)) {
        Stop-P14StageBootstrap 'fixed_share_unavailable'
    }
    $expected = @($P14ManifestName) + $P14AllowedRoots
    $entries = @(Get-ChildItem -LiteralPath $P14ShareRoot -Force)
    $actual = @($entries | ForEach-Object { [string]$_.Name })
    if (@(Compare-Object -ReferenceObject $expected -DifferenceObject $actual -CaseSensitive).Count -ne 0) {
        Stop-P14StageBootstrap 'share_top_level_invalid'
    }
    foreach ($entry in $entries) {
        if (Test-P14ReparsePoint $entry.FullName) {
            Stop-P14StageBootstrap 'share_reparse_point_rejected'
        }
        if ($entry.Name -eq $P14ManifestName) {
            if (-not (Test-Path -LiteralPath $entry.FullName -PathType Leaf)) {
                Stop-P14StageBootstrap 'share_manifest_invalid'
            }
        } elseif (-not (Test-Path -LiteralPath $entry.FullName -PathType Container)) {
            Stop-P14StageBootstrap 'share_root_invalid'
        }
    }
}

function Get-P14TreeFiles([string]$RootName, [string]$RootPath) {
    if (-not (Test-Path -LiteralPath $RootPath -PathType Container) -or (Test-P14ReparsePoint $RootPath)) {
        Stop-P14StageBootstrap 'share_root_invalid'
    }
    $result = @{}
    $rootFull = [IO.Path]::GetFullPath($RootPath).TrimEnd('\')
    $pending = [System.Collections.Generic.List[string]]::new()
    $pending.Add($rootFull) | Out-Null
    while ($pending.Count -gt 0) {
        $directory = $pending[$pending.Count - 1]
        $pending.RemoveAt($pending.Count - 1)
        if (Test-P14ReparsePoint $directory) {
            Stop-P14StageBootstrap 'share_reparse_point_rejected'
        }
        foreach ($entry in @(Get-ChildItem -LiteralPath $directory -Force)) {
            if (Test-P14ReparsePoint $entry.FullName) {
                Stop-P14StageBootstrap 'share_reparse_point_rejected'
            }
            if ($entry.PSIsContainer) {
                $pending.Add($entry.FullName) | Out-Null
                continue
            }
            if (-not (Test-Path -LiteralPath $entry.FullName -PathType Leaf)) {
                Stop-P14StageBootstrap 'share_special_file_rejected'
            }
            $relative = $entry.FullName.Substring($rootFull.Length).TrimStart([char[]]@('\')).Replace('\', '/')
            Assert-P14SafeRelativePath $relative
            $key = "$RootName/$relative"
            if ($result.ContainsKey($key)) {
                Stop-P14StageBootstrap 'share_path_case_collision'
            }
            $result[$key] = $entry.FullName
        }
    }
    return $result
}

function Assert-P14ShareMatchesManifest([System.Collections.IDictionary]$Manifest) {
    Assert-P14ShareTopLevel
    $actual = @{}
    foreach ($root in $P14AllowedRoots) {
        $rootFiles = Get-P14TreeFiles $root (Join-Path $P14ShareRoot $root)
        foreach ($key in $rootFiles.Keys) {
            if ($actual.ContainsKey($key)) {
                Stop-P14StageBootstrap 'share_path_case_collision'
            }
            $actual[$key] = $rootFiles[$key]
        }
    }
    if ($actual.Count -ne $Manifest['file_count']) {
        Stop-P14StageBootstrap 'share_manifest_path_set_invalid'
    }
    foreach ($entry in $Manifest['files']) {
        $key = "$($entry['root'])/$($entry['path'])"
        if (-not $actual.ContainsKey($key)) {
            Stop-P14StageBootstrap 'share_manifest_path_set_invalid'
        }
    }
    return $actual
}

function Initialize-P14DestinationRoot {
    if (Test-Path -LiteralPath $P14RunnerRoot) {
        if (
            -not (Test-Path -LiteralPath $P14RunnerRoot -PathType Container) -or
            (Test-P14ReparsePoint $P14RunnerRoot) -or
            (Get-ChildItem -LiteralPath $P14RunnerRoot -Force | Select-Object -First 1)
        ) {
            Stop-P14StageBootstrap 'destination_root_not_empty'
        }
        return
    }
    Assert-P14Directory $P14RunnerRoot
}

function Ensure-P14DestinationParent([string]$RootName, [string]$Relative) {
    $current = Join-Path $P14RunnerRoot $RootName
    Assert-P14Directory $current
    $segments = $Relative.Split('/')
    for ($index = 0; $index -lt $segments.Count - 1; $index++) {
        $current = Join-Path $current $segments[$index]
        Assert-P14Directory $current
    }
    return $current
}

function Copy-P14VerifiedFile(
    [string]$Source,
    [string]$Destination,
    [System.Collections.IDictionary]$Entry
) {
    $sourceBefore = Get-P14FileDigest $Source
    if (
        $sourceBefore['bytes'] -ne $Entry['bytes'] -or
        $sourceBefore['sha256'] -ne $Entry['sha256']
    ) {
        Stop-P14StageBootstrap 'source_manifest_hash_mismatch'
    }
    if (Test-Path -LiteralPath $Destination) {
        Stop-P14StageBootstrap 'destination_file_exists'
    }
    $input = [IO.File]::Open(
        $Source,
        [IO.FileMode]::Open,
        [IO.FileAccess]::Read,
        [IO.FileShare]::Read
    )
    $output = $null
    try {
        $output = [IO.File]::Open(
            $Destination,
            [IO.FileMode]::CreateNew,
            [IO.FileAccess]::Write,
            [IO.FileShare]::None
        )
        $buffer = [byte[]]::new($P14CopyBufferBytes)
        while ($true) {
            $read = $input.Read($buffer, 0, $buffer.Length)
            if ($read -eq 0) {
                break
            }
            $output.Write($buffer, 0, $read)
        }
        $output.Flush($true)
    } finally {
        if ($null -ne $output) {
            $output.Dispose()
        }
        $input.Dispose()
    }
    $sourceAfter = Get-P14FileDigest $Source
    $destinationAfter = Get-P14FileDigest $Destination
    if (
        $sourceAfter['bytes'] -ne $sourceBefore['bytes'] -or
        $sourceAfter['sha256'] -ne $sourceBefore['sha256'] -or
        $destinationAfter['bytes'] -ne $Entry['bytes'] -or
        $destinationAfter['sha256'] -ne $Entry['sha256']
    ) {
        Stop-P14StageBootstrap 'copy_hash_or_size_mismatch'
    }
}

function Write-P14StageReceipt([System.Collections.IDictionary]$Manifest) {
    Assert-P14Directory $P14ReceiptDirectory
    if (Test-Path -LiteralPath $P14ReceiptPath) {
        Stop-P14StageBootstrap 'receipt_already_exists'
    }
    $rootCounts = [ordered]@{}
    foreach ($root in $P14AllowedRoots) {
        $rootCounts[$root] = @($Manifest['files'] | Where-Object { $_['root'] -eq $root }).Count
    }
    $receipt = [ordered]@{
        schema_version = $P14ReceiptSchema
        status = 'staged'
        source_revision = $Manifest['source_revision']
        manifest_sha256 = $Manifest['manifest_sha256']
        file_count = $Manifest['file_count']
        roots = $rootCounts
        authority = [ordered]@{
            stage_only = $true
            staged_content_executed = $false
            baseline_created = $false
            provisioned = $false
            runtime_actions = $false
            live_authority = $false
            promotion_approved = $false
        }
    }
    $raw = [Text.UTF8Encoding]::new($false).GetBytes(($receipt | ConvertTo-Json -Depth 8) + [Environment]::NewLine)
    $stream = $null
    try {
        $stream = [IO.File]::Open(
            $P14ReceiptPath,
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
    return Get-P14RawSha256 $raw
}

function Get-P14VBoxControl {
    $candidates = @(
        'C:\Program Files\Oracle\VirtualBox Guest Additions\VBoxControl.exe',
        'C:\Windows\System32\VBoxControl.exe'
    )
    $path = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
    if (-not $path -or (Test-P14ReparsePoint $path)) {
        Stop-P14StageBootstrap 'vboxcontrol_missing'
    }
    return $path
}

function Set-P14StageStatus([string]$Status, [string]$Value) {
    if ($Value -notmatch '^[a-z0-9._:-]{1,80}$') {
        Stop-P14StageBootstrap 'status_value_invalid'
    }
    if ($null -eq $script:P14VBoxControl) {
        return
    }
    $payload = "ctoa.p14-stage-bootstrap.v1|$Status|$Value"
    & $script:P14VBoxControl guestproperty set $P14GuestStatusProperty $payload 2>$null
    if ($LASTEXITCODE -ne 0) {
        Stop-P14StageBootstrap 'guest_status_publish_failed'
    }
}

function Assert-P14SystemBootstrap {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    if ($null -eq $identity.User -or $identity.User.Value -ne 'S-1-5-18') {
        Stop-P14StageBootstrap 'local_system_required'
    }
    if (
        [string]::IsNullOrWhiteSpace($PSCommandPath) -or
        -not ([IO.Path]::GetFullPath($PSCommandPath).Equals($P14BootstrapScript, [StringComparison]::OrdinalIgnoreCase))
    ) {
        Stop-P14StageBootstrap 'bootstrap_path_invalid'
    }
}

function Assert-P14OfflineGuest {
    $activeAdapters = @(Get-NetAdapter -ErrorAction Stop | Where-Object { $_.Status -eq 'Up' })
    if ($activeAdapters.Count -ne 0) {
        Stop-P14StageBootstrap 'network_adapter_not_isolated'
    }
}

function Wait-P14FixedShare {
    for ($attempt = 0; $attempt -lt $P14ShareWaitAttempts; $attempt++) {
        if (Test-Path -LiteralPath $P14ShareRoot -PathType Container) {
            return
        }
        Set-P14StageStatus 'waiting' 'fixed_share'
        Start-Sleep -Seconds $P14ShareWaitSeconds
    }
    Stop-P14StageBootstrap 'fixed_share_unavailable'
}

function Install-P14StageBootstrapTask {
    Assert-P14SystemBootstrap
    if (-not (Test-Path -LiteralPath $P14PowerShell -PathType Leaf)) {
        Stop-P14StageBootstrap 'powershell_missing'
    }
    if (Get-ScheduledTask -TaskName $P14BootstrapTaskName -ErrorAction SilentlyContinue) {
        Stop-P14StageBootstrap 'bootstrap_task_already_exists'
    }
    $arguments = '-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $P14BootstrapScript + '" -Run'
    $action = New-ScheduledTaskAction -Execute $P14PowerShell -Argument $arguments
    $trigger = New-ScheduledTaskTrigger -AtStartup
    $principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 20)
    Register-ScheduledTask -TaskName $P14BootstrapTaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings | Out-Null
}

function Run-P14StageBootstrap {
    Assert-P14SystemBootstrap
    Assert-P14OfflineGuest
    $script:P14VBoxControl = Get-P14VBoxControl
    Wait-P14FixedShare
    Assert-P14ShareTopLevel
    $manifest = Get-P14StageManifest
    $shareFiles = Assert-P14ShareMatchesManifest $manifest
    Initialize-P14DestinationRoot
    foreach ($entry in $manifest['files']) {
        $key = "$($entry['root'])/$($entry['path'])"
        $source = $shareFiles[$key]
        $parent = Ensure-P14DestinationParent $entry['root'] $entry['path']
        $destination = Join-Path $parent ($entry['path'].Split('/')[-1])
        if (-not (Test-P14PathWithin $destination $P14RunnerRoot)) {
            Stop-P14StageBootstrap 'destination_outside_allowed_root'
        }
        Copy-P14VerifiedFile $source $destination $entry
    }
    $receiptSha256 = Write-P14StageReceipt $manifest
    Unregister-ScheduledTask -TaskName $P14BootstrapTaskName -Confirm:$false
    Set-P14StageStatus 'staged' $receiptSha256
}

if (($Install -and $Run) -or (-not $Install -and -not $Run)) {
    Stop-P14StageBootstrap 'mode_invalid'
}

try {
    if ($Install) {
        Install-P14StageBootstrapTask
    } else {
        Run-P14StageBootstrap
    }
} catch {
    $message = [string]$_.Exception.Message
    $code = if ($message -match '^p14_stage_bootstrap:(?<code>[a-z0-9._:-]+)$') {
        $Matches['code']
    } else {
        'unexpected_failure'
    }
    if ($Run -and $null -ne $script:P14VBoxControl) {
        try {
            Set-P14StageStatus 'blocked' $code
        } catch {
        }
    }
    throw
}
