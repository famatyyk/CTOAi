param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('sample-dry-run', 'file-source', 'listener', 'poll')]
    [string]$Action,
    [string]$EnvFile = '.ctoa-local/azure-alerts.env',
    [int]$PollSeconds = 60,
    [string]$SourceFile = 'runtime/ingest/azure-activity-log.json',
    [string]$ListenerHost = '127.0.0.1'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Import-DotEnvFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }

    $lines = Get-Content -LiteralPath $Path -Encoding UTF8
    foreach ($line in $lines) {
        $trimmed = $line.Trim()
        if ([string]::IsNullOrWhiteSpace($trimmed)) { continue }
        if ($trimmed.StartsWith('#')) { continue }

        $idx = $trimmed.IndexOf('=')
        if ($idx -lt 1) { continue }

        $name = $trimmed.Substring(0, $idx).Trim()
        $value = $trimmed.Substring($idx + 1).Trim()
        if ([string]::IsNullOrWhiteSpace($name)) { continue }

        [Environment]::SetEnvironmentVariable($name, $value, 'Process')
    }
}

function Resolve-PythonExecutable {
    $venvPython = '.\\.venv\\Scripts\\python.exe'
    if (Test-Path -LiteralPath $venvPython) {
        return $venvPython
    }

    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($null -ne $cmd -and -not [string]::IsNullOrWhiteSpace($cmd.Source)) {
        return $cmd.Source
    }

    throw 'Python executable not found. Install Python or create .venv/Scripts/python.exe'
}

function Test-LoopbackHost {
    param(
        [Parameter(Mandatory = $true)]
        [string]$HostName
    )

    $normalized = $HostName.Trim().ToLowerInvariant()
    return ($normalized -in @('localhost', '127.0.0.1', '::1', '[::1]'))
}

function Assert-AzureListenerExposure {
    param(
        [Parameter(Mandatory = $true)]
        [string]$HostName
    )

    if ([string]::IsNullOrWhiteSpace($HostName)) {
        throw 'ListenerHost is required.'
    }

    $ingestSecret = [Environment]::GetEnvironmentVariable('CTOA_AZURE_INGEST_SECRET', 'Process')
    if (-not (Test-LoopbackHost -HostName $HostName) -and [string]::IsNullOrWhiteSpace($ingestSecret)) {
        throw 'Refusing to expose Azure alert listener on a non-loopback host without CTOA_AZURE_INGEST_SECRET.'
    }
}

function Invoke-AzureAlertsPipeline {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$ExtraArgs
    )

    $python = Resolve-PythonExecutable
    & $python 'scripts/ops/azure_activity_alerts.py' @ExtraArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Push-Location (Resolve-Path '.')
try {
    Import-DotEnvFile -Path $EnvFile

    switch ($Action) {
        'sample-dry-run' {
            Invoke-AzureAlertsPipeline -ExtraArgs @(
                '--source-file','docs/examples/azure-activity-log-samples.json',
                '--source-format','json',
                '--routes','console,jsonl,discord_webhook',
                '--output-jsonl','runtime/alerts/azure-activity-alerts.jsonl',
                '--min-severity','warning',
                '--dry-run'
            )
        }
        'file-source' {
            Invoke-AzureAlertsPipeline -ExtraArgs @(
                '--source-file',$SourceFile,
                '--source-format','auto',
                '--routes','console,jsonl,discord_webhook',
                '--output-jsonl','runtime/alerts/azure-activity-alerts.jsonl',
                '--min-severity','warning'
            )
        }
        'listener' {
            Assert-AzureListenerExposure -HostName $ListenerHost
            $python = Resolve-PythonExecutable
            & $python 'scripts/ops/azure_activity_webhook_listener.py' `
                '--host' $ListenerHost `
                '--port' '8791' `
                '--path' '/azure/activity' `
                '--routes' 'console,jsonl,discord_webhook' `
                '--output-jsonl' 'runtime/alerts/azure-activity-alerts.jsonl' `
                '--min-severity' 'warning'
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        }
        'poll' {
            Write-Host 'Azure alert poller started (60s).'
            while ($true) {
                if (Test-Path -LiteralPath $SourceFile) {
                    Invoke-AzureAlertsPipeline -ExtraArgs @(
                        '--source-file',$SourceFile,
                        '--source-format','auto',
                        '--routes','console,jsonl,discord_webhook',
                        '--output-jsonl','runtime/alerts/azure-activity-alerts.jsonl',
                        '--min-severity','warning'
                    )
                }
                Start-Sleep -Seconds $PollSeconds
            }
        }
    }
}
finally {
    Pop-Location
}
