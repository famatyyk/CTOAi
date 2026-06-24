param(
    [string]$Provider = "local",
    [string]$Model = "qwen2.5-coder:1.5b",
    [string]$Url = "http://localhost:11434/v1",
    [double]$Temperature = 0.1,
    [int]$MaxTokens = 1024,
    [string]$SystemPrompt = "You are CTOAi local assistant. Be concise, practical, and code-first.",
    [string]$Once = "",
    [string]$Mode = "general",
    [switch]$NoRag,
    [switch]$UnsafeExec,
    [switch]$HealthOnly
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
    $env:CTOA_CHAT_TEMPERATURE = [string]$Temperature
    $env:CTOA_CHAT_MAX_TOKENS = [string]$MaxTokens
    $env:CTOA_CHAT_SYSTEM_PROMPT = $SystemPrompt
    $env:CTOA_CHAT_ONCE = $Once
    $env:CTOA_CHAT_HEALTH_ONLY = if ($HealthOnly) { "1" } else { "0" }
    if ([string]::IsNullOrWhiteSpace($env:PYTHONPATH)) {
        $env:PYTHONPATH = $repoRoot
    } else {
        $env:PYTHONPATH = "$repoRoot;$env:PYTHONPATH"
    }

    $pyArgs = @(
        "scripts/ops/ctoa_chat_cli.py",
        "--temperature", [string]$Temperature,
        "--max-tokens", [string]$MaxTokens,
        "--system-prompt", $SystemPrompt,
        "--mode", $Mode
    )
    if ($Once) {
        $pyArgs += @("--once", $Once)
    }
    if ($HealthOnly) {
        $pyArgs += "--health-only"
    }
    if ($NoRag) {
        $pyArgs += "--no-rag"
    }
    if ($UnsafeExec) {
        $pyArgs += "--unsafe-exec"
    }

    & python @pyArgs
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
