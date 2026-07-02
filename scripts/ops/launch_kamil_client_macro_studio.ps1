param(
    [string]$ClientPath = 'C:\Users\zycie\Downloads\kamil-client\bin\klient.exe',
    [switch]$NoMacroStudio,
    [string]$ProfileOverride = '',
    [switch]$SmokeTest
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

function Get-PythonExe {
    $python = Join-Path $root '.venv\Scripts\python.exe'
    if (Test-Path -LiteralPath $python) {
        return $python
    }
    throw "Missing repo-local Python at $python. Create the virtual environment with: python -m venv .venv"
}

function Resolve-ClientProfile {
    param([string]$Path, [string]$Override)

    if ($Override) {
        return $Override
    }

    $router = Join-Path $root 'scripts\ops\client_profile_router.py'
    $python = Get-PythonExe
    $profile = & $python $router --path $Path
    if (-not $profile) {
        return 'default'
    }
    return $profile.Trim()
}

function Start-KamilClient {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Client executable not found: $Path"
    }

    Start-Process -FilePath $Path -WorkingDirectory (Split-Path -Parent $Path)
}

function Start-MacroStudio {
    $python = Get-PythonExe
    Start-Process -FilePath $python -ArgumentList @('-m', 'bot.overlay.macro_overlay') -WorkingDirectory $root -WindowStyle Hidden
}

if ($SmokeTest) {
    $python = Get-PythonExe
    $router = Join-Path $root 'scripts\ops\client_profile_router.py'
    $macroConfig = Join-Path $root 'config\bot_macro_pad.json'

    $resolvedProfile = if ($ProfileOverride) {
        $ProfileOverride
    } else {
        (& $python $router --path $ClientPath).Trim()
    }

    if ([string]::IsNullOrWhiteSpace($resolvedProfile)) {
        throw "Smoke test failed: profile resolution returned empty output."
    }

    & $python -c "import json, pathlib, bot.overlay.macro_overlay, bot.overlay.status_overlay; print('launcher-smoke-ok')" | Out-Host
    & $python -c "import json; from pathlib import Path; json.loads(Path(r'$macroConfig').read_text(encoding='utf-8')); print('macro-config-ok')" | Out-Host
    Write-Host "Smoke profile: $resolvedProfile"
    Write-Host "Smoke python: $python"
    exit 0
}

$profile = Resolve-ClientProfile -Path $ClientPath -Override $ProfileOverride
$env:BOT_CLIENT_PROFILE = $profile

Start-KamilClient -Path $ClientPath

if (-not $NoMacroStudio) {
    Start-Sleep -Seconds 2
    Start-MacroStudio
}

Write-Host "Started client: $ClientPath"
Write-Host "Loaded profile: $profile"
if (-not $NoMacroStudio) {
    Write-Host "Started Macro Studio overlay"
}
