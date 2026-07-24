[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# This script is packaged only as \P14Payload\copy.ps1 on the standalone
# answer medium.  specialize invokes it as LOCAL SYSTEM through a bounded
# optical-drive scan.  Its sole setup-time action is to copy and hash-verify
# the four fixed setup files below; it never installs Guest Additions, creates
# a scheduled task, starts staging, connects to a network, or restarts Windows.
$P14PayloadDirectoryName = 'P14Payload'
$P14PayloadScriptName = 'copy.ps1'
$P14SourceScanLetters = @('D', 'E', 'F', 'G', 'H')
$P14DestinationDirectory = 'C:\Windows\Setup\Scripts'
$P14ReceiptDirectory = 'C:\ProgramData\CTOAi\P14'
$P14SuccessReceiptPath = 'C:\ProgramData\CTOAi\P14\specialize-static-copy-receipt.json'
$P14BlockedReceiptPath = 'C:\ProgramData\CTOAi\P14\specialize-static-copy-blocked.json'
$P14ReceiptSchema = 'ctoa.p14-specialize-static-copy.v1'
$P14CopyBufferBytes = 1MB

# Hashes are intentionally literal commitments to the source-controlled
# answer-medium payloads.  They are refreshed only with the matching payload
# review; a changed, missing, or extra source is rejected before any target is
# made visible to SetupComplete.
$P14PayloadHashes = [ordered]@{
    'ctoa_p14_stage_bootstrap.ps1' = '87a1959503fe9efb0f092d70dc96cf611fdfebe0cde3f0e6b5fd653881c5c257'
    'ctoa_p14_guest_additions_setup.cmd' = '0730373df956921060b7bfe960901381454f79cef0e907e7ea360da2940e4c63'
    'ctoa_p14_post_oobe_bootstrap.ps1' = '25e2ee257c0bd1b619984971096351195218b54d1edc0b04aac8418a5d5d48d1'
    'SetupComplete.cmd' = 'ebc189eb5384432c210d02eb3312c0907d9c17b23a842816b7cbe20ff1810cdc'
}

function Stop-P14SpecializeStaticCopy([string]$Code) {
    throw "p14_specialize_static_copy:$Code"
}

function Test-P14ReparsePoint([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        return $false
    }
    return (((Get-Item -LiteralPath $Path -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)
}

function Assert-P14RegularFile([string]$Path, [string]$Code) {
    if (
        -not (Test-Path -LiteralPath $Path -PathType Leaf) -or
        (Test-P14ReparsePoint $Path)
    ) {
        Stop-P14SpecializeStaticCopy $Code
    }
}

function Assert-P14Directory([string]$Path, [string]$Code, [bool]$Create) {
    if (-not (Test-Path -LiteralPath $Path)) {
        if (-not $Create) {
            Stop-P14SpecializeStaticCopy $Code
        }
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
    if (
        -not (Test-Path -LiteralPath $Path -PathType Container) -or
        (Test-P14ReparsePoint $Path)
    ) {
        Stop-P14SpecializeStaticCopy $Code
    }
}

function Assert-P14SystemIdentity {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    if ($null -eq $identity.User -or $identity.User.Value -ne 'S-1-5-18') {
        Stop-P14SpecializeStaticCopy 'system_identity_required'
    }
}

function Get-P14Sha256([string]$Path) {
    Assert-P14RegularFile $Path 'regular_file_required'
    $before = Get-Item -LiteralPath $Path -Force
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
        Stop-P14SpecializeStaticCopy 'file_changed_during_hash'
    }
    return $digest
}

function Get-P14PayloadCandidates {
    $candidates = [System.Collections.Generic.List[string]]::new()
    foreach ($letter in $P14SourceScanLetters) {
        $candidate = "$letter`:\$P14PayloadDirectoryName\$P14PayloadScriptName"
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            $candidates.Add([IO.Path]::GetFullPath($candidate)) | Out-Null
        }
    }
    return $candidates.ToArray()
}

function Get-P14PayloadRoot {
    if ([string]::IsNullOrWhiteSpace($PSCommandPath)) {
        Stop-P14SpecializeStaticCopy 'script_path_missing'
    }
    $scriptPath = [IO.Path]::GetFullPath($PSCommandPath)
    $candidates = @(Get-P14PayloadCandidates)
    if ($candidates.Count -ne 1) {
        Stop-P14SpecializeStaticCopy 'payload_media_ambiguous'
    }
    if (-not $scriptPath.Equals($candidates[0], [StringComparison]::OrdinalIgnoreCase)) {
        Stop-P14SpecializeStaticCopy 'script_path_not_candidate'
    }
    $sourceRoot = [IO.Path]::GetDirectoryName($scriptPath)
    $driveRoot = [IO.Path]::GetPathRoot($scriptPath)
    if (
        [string]::IsNullOrWhiteSpace($sourceRoot) -or
        [string]::IsNullOrWhiteSpace($driveRoot) -or
        $driveRoot -notmatch '^[D-H]:\\$'
    ) {
        Stop-P14SpecializeStaticCopy 'payload_root_invalid'
    }
    $expectedRoot = Join-Path $driveRoot $P14PayloadDirectoryName
    if (-not $sourceRoot.Equals($expectedRoot, [StringComparison]::OrdinalIgnoreCase)) {
        Stop-P14SpecializeStaticCopy 'payload_root_invalid'
    }
    Assert-P14Directory $sourceRoot 'payload_root_invalid' $false
    return $sourceRoot
}

function Test-P14AnyReceiptExists {
    return (Test-Path -LiteralPath $P14SuccessReceiptPath) -or
        (Test-Path -LiteralPath $P14BlockedReceiptPath)
}

function Get-P14ReceiptPath([string]$Status) {
    if ($Status -eq 'copied') {
        return $P14SuccessReceiptPath
    }
    if ($Status -eq 'blocked') {
        return $P14BlockedReceiptPath
    }
    Stop-P14SpecializeStaticCopy 'receipt_status_invalid'
}

function Write-P14Receipt(
    [string]$Status,
    [string]$Code,
    [string]$SourceRoot,
    [System.Collections.IDictionary]$Payloads
) {
    Assert-P14Directory 'C:\ProgramData\CTOAi' 'receipt_directory_invalid' $true
    Assert-P14Directory $P14ReceiptDirectory 'receipt_directory_invalid' $true
    if (Test-P14AnyReceiptExists) {
        Stop-P14SpecializeStaticCopy 'receipt_already_exists'
    }
    $receiptPath = Get-P14ReceiptPath $Status
    $receipt = [ordered]@{
        schema_version = $P14ReceiptSchema
        status = $Status
        code = $Code
        source_root = $SourceRoot
        payloads = $Payloads
        recorded_at = (Get-Date -AsUTC -Format 'o')
    }
    $raw = [Text.UTF8Encoding]::new($false).GetBytes(($receipt | ConvertTo-Json -Depth 6) + [Environment]::NewLine)
    $stream = $null
    try {
        $stream = [IO.File]::Open(
            $receiptPath,
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

function Copy-P14VerifiedPayload(
    [string]$SourceRoot,
    [string]$Name,
    [string]$ExpectedSha256
) {
    $source = Join-Path $SourceRoot $Name
    Assert-P14RegularFile $source 'payload_source_missing_or_reparse'
    $sourceSha256 = Get-P14Sha256 $source
    if ($sourceSha256 -ne $ExpectedSha256) {
        Stop-P14SpecializeStaticCopy 'payload_source_hash_mismatch'
    }

    $destination = Join-Path $P14DestinationDirectory $Name
    if (Test-Path -LiteralPath $destination) {
        Assert-P14RegularFile $destination 'payload_destination_invalid'
        if ((Get-P14Sha256 $destination) -ne $ExpectedSha256) {
            Stop-P14SpecializeStaticCopy 'payload_destination_existing_mismatch'
        }
        return $sourceSha256
    }

    $temporary = Join-Path $P14DestinationDirectory ('.' + $Name + '.p14-copy-tmp')
    if (Test-Path -LiteralPath $temporary) {
        Stop-P14SpecializeStaticCopy 'payload_temporary_exists'
    }
    $input = $null
    $output = $null
    try {
        $input = [IO.File]::Open($source, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
        $output = [IO.File]::Open($temporary, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
        $input.CopyTo($output, $P14CopyBufferBytes)
        $output.Flush($true)
    } finally {
        if ($null -ne $output) {
            $output.Dispose()
        }
        if ($null -ne $input) {
            $input.Dispose()
        }
    }
    try {
        if ((Get-P14Sha256 $temporary) -ne $ExpectedSha256) {
            Stop-P14SpecializeStaticCopy 'payload_temporary_hash_mismatch'
        }
        [IO.File]::Move($temporary, $destination)
        if ((Get-P14Sha256 $destination) -ne $ExpectedSha256) {
            Stop-P14SpecializeStaticCopy 'payload_destination_hash_mismatch'
        }
    } finally {
        if (Test-Path -LiteralPath $temporary) {
            [IO.File]::Delete($temporary)
        }
    }
    return $sourceSha256
}

$sourceRoot = $null
try {
    Assert-P14SystemIdentity
    $sourceRoot = Get-P14PayloadRoot
    Assert-P14Directory $P14DestinationDirectory 'destination_directory_invalid' $true
    if (Test-P14AnyReceiptExists) {
        Stop-P14SpecializeStaticCopy 'receipt_already_exists'
    }

    $copiedPayloads = [ordered]@{}
    foreach ($entry in $P14PayloadHashes.GetEnumerator()) {
        $copiedPayloads[$entry.Key] = Copy-P14VerifiedPayload $sourceRoot $entry.Key $entry.Value
    }
    Write-P14Receipt 'copied' 'ok' $sourceRoot $copiedPayloads
} catch {
    $message = [string]$_.Exception.Message
    $code = if ($message -match '^p14_specialize_static_copy:(?<code>[a-z0-9._:-]+)$') {
        $Matches['code']
    } else {
        'unexpected_failure'
    }
    try {
        if (-not (Test-P14AnyReceiptExists)) {
            Write-P14Receipt 'blocked' $code $sourceRoot ([ordered]@{})
        }
    } catch {
    }
    throw
}
