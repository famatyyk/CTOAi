Set-StrictMode -Version Latest

function Assert-CtoaTaskName {
    param([Parameter(Mandatory = $true)][string]$TaskName)

    if ([string]::IsNullOrWhiteSpace($TaskName)) {
        throw 'TaskName must not be empty.'
    }
    if ($TaskName.Length -gt 80 -or $TaskName -notmatch '^CTOA-[A-Za-z0-9][A-Za-z0-9_.-]{0,75}$') {
        throw "TaskName must be a CTOA-* name with only letters, numbers, dot, underscore, or dash: $TaskName"
    }

    return $TaskName
}

function Assert-CtoaRunKeyName {
    param([Parameter(Mandatory = $true)][string]$RunKeyName)

    if ([string]::IsNullOrWhiteSpace($RunKeyName)) {
        throw 'RunKeyName must not be empty.'
    }
    if ($RunKeyName.Length -gt 80 -or $RunKeyName -notmatch '^CTOA-[A-Za-z0-9][A-Za-z0-9_.-]{0,75}$') {
        throw "RunKeyName must be a CTOA-* name with only letters, numbers, dot, underscore, or dash: $RunKeyName"
    }

    return $RunKeyName
}

function Assert-CtoaStartTime {
    param([Parameter(Mandatory = $true)][string]$StartTime)

    if ($StartTime -notmatch '^\d{2}:\d{2}$') {
        throw 'StartTime must be HH:mm format, e.g. 07:10'
    }

    $parts = $StartTime.Split(':')
    $hour = [int]$parts[0]
    $minute = [int]$parts[1]
    if ($hour -gt 23 -or $minute -gt 59) {
        throw 'StartTime must be a valid 24-hour time.'
    }

    return $StartTime
}

function Resolve-RepoChildPath {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$ChildPath,
        [Parameter(Mandatory = $true)][string]$Label,
        [switch]$RequireExists
    )

    $resolvedBase = [System.IO.Path]::GetFullPath((Resolve-Path -LiteralPath $RepoRoot).Path).TrimEnd([char[]]@('\', '/'))
    $resolvedChild = [System.IO.Path]::GetFullPath($ChildPath)
    $baseWithSeparator = $resolvedBase + [System.IO.Path]::DirectorySeparatorChar

    if (
        -not $resolvedChild.Equals($resolvedBase, [System.StringComparison]::OrdinalIgnoreCase) -and
        -not $resolvedChild.StartsWith($baseWithSeparator, [System.StringComparison]::OrdinalIgnoreCase)
    ) {
        throw "$Label must stay under $resolvedBase; got $resolvedChild"
    }

    if ($RequireExists -and -not (Test-Path -LiteralPath $resolvedChild)) {
        throw "$Label not found: $resolvedChild"
    }

    return $resolvedChild
}

function Resolve-CtoaLogPath {
    param([Parameter(Mandatory = $true)][string]$LogPath)

    if ([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
        throw 'LOCALAPPDATA is required to resolve CTOA watcher logs.'
    }

    $logRoot = Join-Path $env:LOCALAPPDATA 'CTOA\logs'
    New-Item -ItemType Directory -Path $logRoot -Force | Out-Null

    $resolvedBase = [System.IO.Path]::GetFullPath((Resolve-Path -LiteralPath $logRoot).Path).TrimEnd([char[]]@('\', '/'))
    $resolvedLog = [System.IO.Path]::GetFullPath($LogPath)
    $baseWithSeparator = $resolvedBase + [System.IO.Path]::DirectorySeparatorChar

    if (
        -not $resolvedLog.Equals($resolvedBase, [System.StringComparison]::OrdinalIgnoreCase) -and
        -not $resolvedLog.StartsWith($baseWithSeparator, [System.StringComparison]::OrdinalIgnoreCase)
    ) {
        throw "LogPath must stay under $resolvedBase; got $resolvedLog"
    }

    if ([System.IO.Path]::GetExtension($resolvedLog) -ne '.log') {
        throw "LogPath must end with .log: $resolvedLog"
    }

    return $resolvedLog
}

function Format-CtoaCommandArgument {
    param([Parameter(Mandatory = $true)][string]$Value)

    if ($Value.Contains('"')) {
        throw "Command argument must not contain quotes: $Value"
    }

    return '"' + $Value + '"'
}
