param(
    [string]$ComposeFile = "docker-compose.yml"
)

$ErrorActionPreference = "Stop"

Write-Host "=== CTOA Sprint-0 integration validation ==="
Write-Host "[1/5] docker compose ps"
docker compose -f $ComposeFile ps

Write-Host "[2/5] alembic current"
$alembicExe = ".\\.venv\\Scripts\\alembic.exe"
& $alembicExe current
if ($LASTEXITCODE -ne 0) {
    throw "Alembic current failed with exit code $LASTEXITCODE"
}

Write-Host "[3/5] metrics endpoint"
$metrics = Invoke-WebRequest -Uri "http://127.0.0.1:8787/metrics" -UseBasicParsing -TimeoutSec 10
if ($metrics.StatusCode -ne 200) {
    throw "Metrics endpoint returned status $($metrics.StatusCode)"
}

Write-Host "[4/5] observability endpoints"
$prom = Invoke-WebRequest -Uri "http://127.0.0.1:9090/-/healthy" -UseBasicParsing -TimeoutSec 10
$loki = Invoke-WebRequest -Uri "http://127.0.0.1:3100/ready" -UseBasicParsing -TimeoutSec 10
if ($prom.StatusCode -ne 200 -or $loki.StatusCode -ne 200) {
    throw "Prometheus/Loki readiness check failed"
}

Write-Host "[5/5] enqueue worker tick job"
& .\.venv\Scripts\python.exe scripts/ops/queue_enqueue_job.py --action orchestrator.tick
if ($LASTEXITCODE -ne 0) {
    throw "Queue enqueue check failed with exit code $LASTEXITCODE"
}

Write-Host "Sprint-0 validation PASS"