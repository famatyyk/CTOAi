[CmdletBinding()]
param(
    [string]$Action,
    [string]$ServiceName,
    [string]$ServerUrls
)

$target = Join-Path $PSScriptRoot 'scripts/ops/ctoa-vps.ps1'
if (-not (Test-Path $target)) {
    throw "Missing target script: $target"
}

$forward = @{}
if ($PSBoundParameters.ContainsKey('Action')) { $forward.Action = $Action }
if ($PSBoundParameters.ContainsKey('ServiceName')) { $forward.ServiceName = $ServiceName }
if ($PSBoundParameters.ContainsKey('ServerUrls')) { $forward.ServerUrls = $ServerUrls }

& $target @forward
exit $LASTEXITCODE
