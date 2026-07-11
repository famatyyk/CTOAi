[CmdletBinding()]
param(
    [string]$SourceRoot = (Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) ".vscode\extensions"),
    [string]$ExtensionsRoot = (Join-Path $HOME ".vscode\extensions")
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Assert-ChildPath {
    param(
        [Parameter(Mandatory = $true)][string]$Root,
        [Parameter(Mandatory = $true)][string]$Candidate
    )

    $resolvedRoot = [System.IO.Path]::GetFullPath($Root)
    $resolvedCandidate = [System.IO.Path]::GetFullPath($Candidate)
    $trimChars = [char[]]@([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
    $rootPrefix = $resolvedRoot.TrimEnd($trimChars) + [System.IO.Path]::DirectorySeparatorChar
    if (-not $resolvedCandidate.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to write outside ExtensionsRoot"
    }
    return $resolvedCandidate
}

if (-not (Test-Path -LiteralPath $SourceRoot -PathType Container)) {
    throw "Extension source directory does not exist: $SourceRoot"
}

New-Item -ItemType Directory -Path $ExtensionsRoot -Force | Out-Null
$resolvedExtensionsRoot = [System.IO.Path]::GetFullPath($ExtensionsRoot)

foreach ($extension in Get-ChildItem -LiteralPath $SourceRoot -Directory) {
    $source = $extension.FullName
    if (-not (Test-Path -LiteralPath $source -PathType Container)) {
        continue
    }
    $resolvedTarget = Assert-ChildPath -Root $resolvedExtensionsRoot -Candidate (Join-Path $resolvedExtensionsRoot $extension.Name)
    if (Test-Path -LiteralPath $resolvedTarget) {
        Remove-Item -LiteralPath $resolvedTarget -Recurse -Force
    }
    Copy-Item -LiteralPath $source -Destination $resolvedTarget -Recurse -Force
    Write-Output "Installed extension mirror: $($extension.Name)"
}
