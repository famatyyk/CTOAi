param(
    [string]$Provider = "local",
    [string]$Model = "qwen2.5-coder:1.5b",
    [string]$Url = "http://localhost:11434/v1",
    [string]$Smoke = "tests/test_suite.py -q",
    [string]$Mode = "ops",
    [switch]$Strict,
    [switch]$PrintReport
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path
Push-Location $repoRoot
try {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        throw "Python is required but not found in PATH."
    }

    $env:CTOA_LLM_PROVIDER = $Provider
    $env:CTOA_LOCAL_MODEL_URL = $Url
    $env:CTOA_LOCAL_MODEL_NAME = $Model
    if ([string]::IsNullOrWhiteSpace($env:PYTHONPATH)) {
        $env:PYTHONPATH = $repoRoot
    } else {
        $env:PYTHONPATH = "$repoRoot;$env:PYTHONPATH"
    }

    $pyArgs = @(
        "scripts/ops/ctoa_daily.py",
        "--smoke", $Smoke,
        "--mode", $Mode
    )
    if ($Strict) {
        $pyArgs += "--strict"
    }
    if ($PrintReport) {
        $pyArgs += "--print-report"
    }

    & python @pyArgs
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}

