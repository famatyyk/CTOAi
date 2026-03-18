param(
    [Parameter(Mandatory = $true)]
    [ValidateSet(
        'Verify',
        'WhoAmI',
        'Setup24x7',
        'EnableLiveHealth',
        'TailLiveHealth',
        'ValidateServices',
        'StabilizeReportService',
        'WriteGithubPat',
        'ReportViaServiceEnv',
        'PublishWithSourcedEnv',
        'InspectReportEnv',
        'ReportErrorDetails',
        'SetupDB',
        'SetupAgents',
        'TailAgents',
        'FixDbPerms',
        'RegisterServer',
        'RegisterServerList',
        'KickoffNow',
        'MythibiaBurst',
        'GlobalBurst',
        'InstallKickoffTimer',
        'ShowKickoffTimer',
        'DisableKickoffTimer',
        'ShowServerStatus',
        'ShowScoutDetails',
        'ShowReseedTimers',
        'WatchScoutingUntilSettled',
        'ApplyScoutingTimeoutPolicy',
        'InstallTieredReseedTimers',
        'HotfixOrchestratorService',
        'ShowReseedPolicy',
        'ShowSystemHealth',
        'ShowPipelineProgress',
        'ListActions',
        'ShowServiceRestarts',
        'HealService',
        # GS Reset cycle
        'InstallGsReset',
        'InstallGsResetFromBranch',
        'EnsureGsEnvKeys',
        'TriggerGsResetNow',
        'TailGsReset',
        'GsStatus',
        'GsProvisionDbContainer',
        'GsCoherence',
        'GsModuleInject',
        'GsApiValidate',
        'ValidateSyntax'
    )]
    [string]$Action,

    [Parameter(Mandatory = $false)]
    [string]$ServiceName,

    [Parameter(Mandatory = $false)]
    [string]$ServerUrls
)

$ErrorActionPreference = 'Stop'

function Get-RequiredEnv([string]$Name) {
    $value = [Environment]::GetEnvironmentVariable($Name, 'Process')
    if ([string]::IsNullOrWhiteSpace($value)) { $value = [Environment]::GetEnvironmentVariable($Name, 'User') }
    if ([string]::IsNullOrWhiteSpace($value)) { $value = [Environment]::GetEnvironmentVariable($Name, 'Machine') }
    if ([string]::IsNullOrWhiteSpace($value)) { throw "Missing env var: $Name" }
    return $value
}

function Get-OptionalEnv([string]$Name, [string]$DefaultValue) {
    $value = [Environment]::GetEnvironmentVariable($Name, 'Process')
    if ([string]::IsNullOrWhiteSpace($value)) { $value = [Environment]::GetEnvironmentVariable($Name, 'User') }
    if ([string]::IsNullOrWhiteSpace($value)) { $value = [Environment]::GetEnvironmentVariable($Name, 'Machine') }
    if ([string]::IsNullOrWhiteSpace($value)) { return $DefaultValue }
    return $value
}

function Resolve-ServerUrl([string]$Candidate, [string]$Fallback) {
    $u = $Candidate
    if (-not [string]::IsNullOrWhiteSpace($u)) {
        $u = $u.Trim().Trim('"').Trim("'")
        $parsed = $null
        if ([Uri]::TryCreate($u, [UriKind]::Absolute, [ref]$parsed) -and ($parsed.Scheme -in @('http', 'https'))) {
            return $u
        }
    }
    return $Fallback
}

function Get-RemoteTarget() {
    $h = [Environment]::GetEnvironmentVariable('CTOA_VPS_HOST')
    if ([string]::IsNullOrWhiteSpace($h)) { $h = '46.225.110.52' }
    $u = [Environment]::GetEnvironmentVariable('CTOA_VPS_USER')
    if ([string]::IsNullOrWhiteSpace($u)) { $u = 'root' }
    return "$u@$h"
}

function Get-KeyPath() {
    $k = [Environment]::GetEnvironmentVariable('CTOA_VPS_KEY_PATH')
    if ([string]::IsNullOrWhiteSpace($k)) { $k = Join-Path $env:USERPROFILE '.ssh\ctoa_vps_ed25519' }
    if (-not (Test-Path $k)) { throw "SSH key not found: $k" }
    return $k
}

function Invoke-WithSshRetry([scriptblock]$Operation, [string]$Label) {
    $attempts = [int](Get-OptionalEnv 'CTOA_SSH_RETRY_ATTEMPTS' '5')
    $delaySeconds = [int](Get-OptionalEnv 'CTOA_SSH_RETRY_DELAY_SECONDS' '3')
    if ($attempts -lt 1) { $attempts = 1 }
    if ($delaySeconds -lt 1) { $delaySeconds = 1 }

    for ($i = 1; $i -le $attempts; $i++) {
        try {
            & $Operation
            if ($LASTEXITCODE -eq 0) {
                return
            }
        } catch {
            if ($i -eq $attempts) {
                throw
            }
        }

        if ($i -lt $attempts) {
            Write-Warning ("[{0}] SSH attempt {1}/{2} failed, retry in {3}s" -f $Label, $i, $attempts, $delaySeconds)
            Start-Sleep -Seconds $delaySeconds
            $delaySeconds = [Math]::Min($delaySeconds * 2, 20)
        }
    }

    throw ("[{0}] SSH failed after {1} attempts" -f $Label, $attempts)
}

function Invoke-SshCommand([string]$Cmd) {
    $t = Get-RemoteTarget; $k = Get-KeyPath
    Invoke-WithSshRetry -Label 'Invoke-SshCommand' -Operation {
        & ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new -i $k $t $Cmd
    }
}

function Invoke-SshScript([string]$Script) {
    $t = Get-RemoteTarget; $k = Get-KeyPath
    $normalized = (($Script -replace "`r`n","`n") -replace "`r","`n")
    Invoke-WithSshRetry -Label 'Invoke-SshScript' -Operation {
        ($normalized + "`n") | & ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new -i $k $t "tr -d '\r' | bash -s"
    }
}

function Invoke-RemoteSyntaxValidation() {
        Invoke-SshScript @'
set -euo pipefail
found=0
failed=0
for file in /opt/ctoa/scripts/ops/*.sh; do
    [ -e "$file" ] || continue
    found=1
    rel="${file#/opt/ctoa/}"
    if bash -n "$file"; then
        echo "OK: $rel"
    else
        echo "FAIL: $rel"
        failed=1
    fi
done

if [ "$found" -eq 0 ]; then
    echo 'FAIL: no shell scripts found in scripts/ops'
    exit 1
fi

if [ "$failed" -ne 0 ]; then
    exit 1
fi

exit 0
'@
}

function Invoke-RemoteVerify() {
        Invoke-SshScript @'
set -euo pipefail
echo CONNECTED
hostname
whoami
found=0
failed=0
for file in /opt/ctoa/scripts/ops/*.sh; do
    [ -e "$file" ] || continue
    found=1
    rel="${file#/opt/ctoa/}"
    if bash -n "$file"; then
        echo "OK: $rel"
    else
        echo "FAIL: $rel"
        failed=1
    fi
done

if [ "$found" -eq 0 ]; then
    echo 'FAIL: no shell scripts found in scripts/ops'
    exit 1
fi

if [ "$failed" -ne 0 ]; then
    exit 1
fi

exit 0
'@
}

function Get-SetupScript() {
    return @'
set -e
export DEBIAN_FRONTEND=noninteractive
if ! command -v git >/dev/null 2>&1; then apt-get update -y; apt-get install -y git; fi
if ! command -v python3 >/dev/null 2>&1; then apt-get update -y; apt-get install -y python3 python3-venv python3-pip; fi
if [ -d /opt/ctoa/.git ]; then
  cd /opt/ctoa; git fetch --all; git checkout main; git pull --ff-only
else
  rm -rf /opt/ctoa; git clone https://github.com/famatyyk/CTOAi.git /opt/ctoa
fi
cd /opt/ctoa
python3 -m venv .venv
. .venv/bin/activate
# Self-heal venv tooling in case pip entrypoint is broken after system updates.
python3 -m ensurepip --upgrade
python3 -m pip install --upgrade pip setuptools wheel
python3 -m pip install -r runner/requirements.txt
# Mobile console runtime deps live in top-level requirements.
python3 -m pip install 'fastapi>=0.115.0' 'uvicorn>=0.30.0'
mkdir -p logs runtime
if [ ! -f /opt/ctoa/.env ]; then printf 'GITHUB_PAT=\n' > /opt/ctoa/.env; fi
cp deploy/vps/systemd/ctoa-runner.service /etc/systemd/system/
cp deploy/vps/systemd/ctoa-runner.timer /etc/systemd/system/
cp deploy/vps/systemd/ctoa-report.service /etc/systemd/system/
cp deploy/vps/systemd/ctoa-report.timer /etc/systemd/system/
cp deploy/vps/systemd/ctoa-health-live.service /etc/systemd/system/
cp deploy/vps/systemd/ctoa-retention-cleanup.service /etc/systemd/system/
cp deploy/vps/systemd/ctoa-retention-cleanup.timer /etc/systemd/system/
cp deploy/vps/systemd/ctoa-mobile-token-rotation.service /etc/systemd/system/
cp deploy/vps/systemd/ctoa-mobile-token-rotation.timer /etc/systemd/system/
cp deploy/vps/systemd/ctoa-lab-runner.service /etc/systemd/system/
cp deploy/vps/systemd/ctoa-lab-runner.timer /etc/systemd/system/
cp deploy/vps/systemd/ctoa-mythibia-news-watcher.service /etc/systemd/system/
cp deploy/vps/systemd/ctoa-mythibia-news-watcher.timer /etc/systemd/system/
cp deploy/vps/systemd/ctoa-mythibia-news-api.service /etc/systemd/system/
cp deploy/vps/logrotate/ctoa /etc/logrotate.d/ctoa
chmod +x /opt/ctoa/deploy/vps/cleanup-retention.sh
chmod +x /opt/ctoa/deploy/vps/rotate-mobile-token.sh
systemctl daemon-reload
systemctl enable --now ctoa-runner.timer
systemctl enable --now ctoa-report.timer
systemctl enable --now ctoa-health-live.service
systemctl enable --now ctoa-retention-cleanup.timer
systemctl enable --now ctoa-mobile-token-rotation.timer
# lab-runner module is currently not shipped; keep timer disabled to avoid noisy failures.
systemctl disable --now ctoa-lab-runner.timer || true
systemctl enable --now ctoa-mythibia-news-watcher.timer
systemctl enable --now ctoa-mythibia-news-api.service

if [ "${CTOA_SETUP_SMOKE:-0}" = "1" ]; then
    echo "[Setup24x7] running optional smoke checks"
    systemctl start ctoa-runner.service || true
    systemctl start ctoa-agents-orchestrator.service || true
    systemctl start ctoa-auto-trainer.service || true
    sudo -u postgres psql -d ctoa -At -c "SELECT 'db-ok'" || true
    systemctl show ctoa-runner.service -p Result -p ExecMainStatus || true
    systemctl show ctoa-agents-orchestrator.service -p Result -p ExecMainStatus || true
    systemctl show ctoa-auto-trainer.service -p Result -p ExecMainStatus || true
fi
'@
}

switch ($Action) {
    'Verify'              {
        Invoke-RemoteVerify
    }
    'WhoAmI'              { Invoke-SshCommand 'whoami' }
    'Setup24x7'           { $sc = Get-SetupScript; Invoke-SshScript $sc }
    'TailLiveHealth'      { Invoke-SshCommand 'tail -n 80 -f /opt/ctoa/logs/health-live.log' }
    'ReportErrorDetails'  { Invoke-SshCommand 'tail -n 60 /opt/ctoa/logs/runner.log' }
    'TailAgents'          { Invoke-SshCommand 'tail -n 100 -f /opt/ctoa/logs/agents-orchestrator.log' }
    'ShowServerStatus' {
        Invoke-SshScript @'
set -e
echo "=== Server status counts ==="
sudo -u postgres psql -d ctoa -c "SELECT status, COUNT(*) AS n FROM servers GROUP BY status ORDER BY status;"
echo
echo "=== Recent servers ==="
sudo -u postgres psql -d ctoa -c "SELECT id, url, status, COALESCE(game_type,'') AS game_type, LEFT(COALESCE(scout_error,''), 120) AS scout_error, to_char(updated_at, 'YYYY-MM-DD HH24:MI:SS') AS updated_at FROM servers ORDER BY updated_at DESC LIMIT 20;"
'@
    }
    'ShowScoutDetails' {
        $filterUrl = Get-OptionalEnv 'CTOA_FILTER_URL' ''
        $filterStatus = Get-OptionalEnv 'CTOA_FILTER_STATUS' ''
        $filterClause = ''
        $whereParts = @()

        if (-not [string]::IsNullOrWhiteSpace($filterUrl)) {
            $safeFilterUrl = $filterUrl -replace "'", "''"
            $whereParts += "s.url = '$safeFilterUrl'"
        }

        if (-not [string]::IsNullOrWhiteSpace($filterStatus)) {
            $safeFilterStatus = $filterStatus.ToUpperInvariant() -replace "'", "''"
            $whereParts += "s.status = '$safeFilterStatus'"
        }

        if ($whereParts.Count -gt 0) {
            $filterClause = "WHERE " + ($whereParts -join " AND ")
        }

        Invoke-SshScript @"
set -e
echo "=== Recent scout endpoint detections ==="
sudo -u postgres psql -d ctoa -c "SELECT s.id AS server_id, s.url, e.path, e.last_status, COALESCE(e.response_schema->>'_probe_source','unknown') AS probe_source, to_char(e.last_checked, 'YYYY-MM-DD HH24:MI:SS') AS last_checked FROM api_endpoints e JOIN servers s ON s.id=e.server_id $filterClause ORDER BY e.last_checked DESC NULLS LAST LIMIT 80;"
echo
echo "=== Scout source summary per server ==="
sudo -u postgres psql -d ctoa -c "SELECT s.id AS server_id, s.url, COALESCE(e.response_schema->>'_probe_source','unknown') AS probe_source, COUNT(*) AS endpoints FROM api_endpoints e JOIN servers s ON s.id=e.server_id $filterClause GROUP BY s.id, s.url, probe_source ORDER BY s.id DESC, endpoints DESC;"
"@
    }
    'ShowReseedTimers' {
        Invoke-SshScript @'
set -e
echo "=== reseed timers ==="
systemctl list-timers 'ctoa-reseed-tier-*' --no-pager || true
echo
echo "=== ctoa-reseed-tier-ab.timer ==="
systemctl status ctoa-reseed-tier-ab.timer --no-pager -l | sed -n '1,40p' || true
echo
echo "=== ctoa-reseed-tier-c.timer ==="
systemctl status ctoa-reseed-tier-c.timer --no-pager -l | sed -n '1,40p' || true
echo
echo "=== reseed logs (tail 60) ==="
tail -n 60 /opt/ctoa/logs/reseed-tier.log 2>/dev/null || echo 'reseed-tier.log-not-found'
'@
    }
    'ShowReseedPolicy' {
        Invoke-SshScript @'
set -e
. /opt/ctoa/.env 2>/dev/null || true
DEFAULT_MIN_AGE="${CTOA_RESEED_ERROR_MIN_AGE_HOURS:-6}"
AB_MIN_AGE="${CTOA_RESEED_ERROR_MIN_AGE_HOURS_AB:-$DEFAULT_MIN_AGE}"
C_MIN_AGE="${CTOA_RESEED_ERROR_MIN_AGE_HOURS_C:-24}"
AB_URLS="${CTOA_RESEED_TIER_AB_URLS:-}"
C_URLS="${CTOA_RESEED_TIER_C_URLS:-}"
echo "=== reseed policy ==="
echo "  Tier A/B  stale-ERROR threshold : ${AB_MIN_AGE}h"
echo "  Tier C    stale-ERROR threshold : ${C_MIN_AGE}h"
echo "  Tier A/B  URLs                 : ${AB_URLS:-<none>}"
echo "  Tier C    URLs                 : ${C_URLS:-<none>}"
echo
echo "=== server status per tier ==="
sudo -u postgres psql -d ctoa -At -c "
SELECT
  url,
  status,
  ROUND(EXTRACT(EPOCH FROM (NOW()-updated_at))/3600,1) AS age_h,
  CASE
    WHEN url = ANY(string_to_array('${AB_URLS}',',')) THEN 'AB'
    WHEN url = ANY(string_to_array('${C_URLS}',',')) THEN 'C'
    ELSE '?'
  END AS tier
FROM servers
ORDER BY tier, url;
" 2>/dev/null | column -t -s '|' || true
echo
echo "=== next scheduled runs ==="
systemctl list-timers ctoa-reseed-tier-ab.timer ctoa-reseed-tier-c.timer --no-pager 2>/dev/null || true
'@
    }
        'ShowSystemHealth' {
                Invoke-SshScript @'
set -e
. /opt/ctoa/.env 2>/dev/null || true

echo "=== failed units ==="
systemctl --failed --no-pager || true
echo

echo "=== key CTOA timers ==="
systemctl list-timers \
    ctoa-agents-orchestrator.timer \
    ctoa-auto-trainer.timer \
    ctoa-runner.timer \
    ctoa-report.timer \
    ctoa-reseed-tier-ab.timer \
    ctoa-reseed-tier-c.timer \
    --no-pager 2>/dev/null || true
echo

echo "=== key CTOA unit-file states ==="
systemctl list-unit-files \
    ctoa-auto-trainer.service \
    ctoa-auto-trainer.timer \
    ctoa-agents-orchestrator.service \
    ctoa-agents-orchestrator.timer \
    ctoa-lab-runner.service \
    ctoa-lab-runner.timer \
    ctoa-runner.service \
    ctoa-runner.timer \
    ctoa-report.service \
    ctoa-report.timer \
    ctoa-reseed-tier-ab.timer \
    ctoa-reseed-tier-c.timer \
    --no-pager 2>/dev/null || true
echo

echo "=== key CTOA runtime states ==="
systemctl list-units \
    ctoa-auto-trainer.service \
    ctoa-health-live.service \
    ctoa-mobile-console.service \
    ctoa-mythibia-news-api.service \
    ctoa-agents-orchestrator.service \
    ctoa-runner.service \
    ctoa-report.service \
    ctoa-reseed-tier-ab.service \
    ctoa-reseed-tier-c.service \
    ctoa-lab-runner.timer \
    --all --no-pager 2>/dev/null || true
echo

echo "=== orchestrator status ==="
systemctl show ctoa-agents-orchestrator.service -p TimeoutStartUSec -p TimeoutStopUSec -p ActiveState -p SubState -p Result -p ExecMainStatus || true
echo

echo "=== server status counts ==="
sudo -u postgres psql -d ctoa -c "SELECT status, COUNT(*) AS n FROM servers GROUP BY status ORDER BY status;" 2>/dev/null || true
echo

DEFAULT_MIN_AGE="${CTOA_RESEED_ERROR_MIN_AGE_HOURS:-6}"
AB_MIN_AGE="${CTOA_RESEED_ERROR_MIN_AGE_HOURS_AB:-$DEFAULT_MIN_AGE}"
C_MIN_AGE="${CTOA_RESEED_ERROR_MIN_AGE_HOURS_C:-24}"
AB_URLS="${CTOA_RESEED_TIER_AB_URLS:-}"
C_URLS="${CTOA_RESEED_TIER_C_URLS:-}"

echo "=== reseed summary ==="
echo "  Tier A/B threshold : ${AB_MIN_AGE}h"
echo "  Tier C   threshold : ${C_MIN_AGE}h"
echo "  Tier A/B URLs      : ${AB_URLS:-<none>}"
echo "  Tier C   URLs      : ${C_URLS:-<none>}"
echo

echo "=== server status per tier ==="
sudo -u postgres psql -d ctoa -At -c "
SELECT
    url,
    status,
    ROUND(EXTRACT(EPOCH FROM (NOW()-updated_at))/3600,1) AS age_h,
    CASE
        WHEN url = ANY(string_to_array('${AB_URLS}',',')) THEN 'AB'
        WHEN url = ANY(string_to_array('${C_URLS}',',')) THEN 'C'
        ELSE '?'
    END AS tier
FROM servers
ORDER BY tier, url;
" 2>/dev/null | column -t -s '|' || true
echo

echo "=== recent reseed log ==="
tail -n 20 /opt/ctoa/logs/reseed-tier.log 2>/dev/null || echo 'reseed-tier.log-not-found'
echo

# ── SSH quality monitor ──────────────────────────────────────────────────────
echo "=== SSH quality monitor (last 60 s) ==="
SSH_FAIL_THRESHOLD=${CTOA_SSH_FAIL_THRESHOLD:-5}          # fails/min to trigger auto-heal
WINDOW_SEC=60

# Count disconnect/banner-exchange/kex failures in the last WINDOW_SEC seconds
SSH_FAILS=$(journalctl -u sshd --since "-${WINDOW_SEC}s" --no-pager -q 2>/dev/null \
  | grep -cEi 'Did not receive identification|Connection reset|banner exchange|kex|Invalid user|authentication failure' || true)
SSH_FAILS=${SSH_FAILS:-0}

FAIL_RATE_INT=$(( SSH_FAILS * 60 / WINDOW_SEC ))
echo "  SSH fail events (last ${WINDOW_SEC}s) : ${SSH_FAILS}"
echo "  SSH fail rate (per min)              : ${FAIL_RATE_INT}"
echo "  Auto-heal threshold (per min)        : ${SSH_FAIL_THRESHOLD}"

if [ "${FAIL_RATE_INT}" -ge "${SSH_FAIL_THRESHOLD}" ]; then
  echo "  STATUS : DEGRADED – threshold exceeded, triggering auto-heal"

  # reset-failed for ctoa services that depend heavily on outbound SSH / sshd
  SSH_HEAVY_SERVICES=(
    ctoa-agents-orchestrator.service
    ctoa-runner.service
    ctoa-report.service
    ctoa-reseed-tier-ab.service
    ctoa-reseed-tier-c.service
    ctoa-lab-runner.service
  )
  for svc in "${SSH_HEAVY_SERVICES[@]}"; do
    current_result=$(systemctl show "$svc" -p Result --value 2>/dev/null || echo 'unknown')
    if [ "$current_result" = "failed" ] || [ "$current_result" = "exit-code" ] || [ "$current_result" = "signal" ]; then
      echo "    reset-failed $svc  (was: $current_result)"
      systemctl reset-failed "$svc" 2>/dev/null || true
    fi
  done
  echo "  Auto-heal complete."
else
  echo "  STATUS : OK"
fi
echo
# ────────────────────────────────────────────────────────────────────────────
'@
        }
        'ShowPipelineProgress' {
                Invoke-SshScript @'
set -e

echo "=== pipeline progress ==="

server_line=$(sudo -u postgres psql -d ctoa -At -c "SELECT COUNT(*)::int AS total, SUM((status='READY')::int)::int AS ready, SUM((status='SCOUTING')::int)::int AS scouting, SUM((status='NEW')::int)::int AS newc, SUM((status='ERROR')::int)::int AS err FROM servers;" 2>/dev/null || echo "0|0|0|0|0")
IFS='|' read -r s_total s_ready s_scout s_new s_err <<< "$server_line"
s_total=${s_total:-0}; s_ready=${s_ready:-0}; s_scout=${s_scout:-0}; s_new=${s_new:-0}; s_err=${s_err:-0}

module_line=$(sudo -u postgres psql -d ctoa -At -c "SELECT COUNT(*)::int AS total, SUM((status='QUEUED')::int)::int AS queued, SUM((status='GENERATED')::int)::int AS generated, SUM((status='VALIDATED')::int)::int AS validated, SUM((status='FAILED')::int)::int AS failed FROM modules;" 2>/dev/null || echo "0|0|0|0|0")
IFS='|' read -r m_total m_queued m_generated m_validated m_failed <<< "$module_line"
m_total=${m_total:-0}; m_queued=${m_queued:-0}; m_generated=${m_generated:-0}; m_validated=${m_validated:-0}; m_failed=${m_failed:-0}

if [ "$s_total" -gt 0 ]; then
    p_ready=$(awk -v r="$s_ready" -v t="$s_total" 'BEGIN { printf "%.0f", (100*r)/t }')
else
    p_ready=0
fi

if [ "$m_total" -gt 0 ]; then
    p_validated=$(awk -v v="$m_validated" -v t="$m_total" 'BEGIN { printf "%.0f", (100*v)/t }')
else
    p_validated=0
fi

bar() {
    p=$1
    if [ "$p" -lt 0 ]; then p=0; fi
    if [ "$p" -gt 100 ]; then p=100; fi
    filled=$((p / 5))
    empty=$((20 - filled))
    printf '['
    i=0; while [ $i -lt $filled ]; do printf '#'; i=$((i+1)); done
    i=0; while [ $i -lt $empty ]; do printf '.'; i=$((i+1)); done
    printf '] %3s%%' "$p"
}

printf "servers READY share     : "; bar "$p_ready"; printf "  (total=%s ready=%s scouting=%s new=%s error=%s)\n" "$s_total" "$s_ready" "$s_scout" "$s_new" "$s_err"
printf "modules VALIDATED share : "; bar "$p_validated"; printf "  (total=%s queued=%s generated=%s validated=%s failed=%s)\n" "$m_total" "$m_queued" "$m_generated" "$m_validated" "$m_failed"

echo
echo "=== per-agent last status ==="
sudo -u postgres psql -d ctoa -c "SELECT DISTINCT ON (agent) agent, status, to_char(finished_at,'YYYY-MM-DD HH24:MI:SS') AS finished_at FROM agent_runs ORDER BY agent, id DESC;" 2>/dev/null || true

echo
echo "=== why little output now ==="
sudo -u postgres psql -d ctoa -c "SELECT s.id, s.url, s.status, COUNT(m.id) AS modules_total, SUM((m.status='VALIDATED')::int) AS modules_validated FROM servers s LEFT JOIN modules m ON m.server_id=s.id GROUP BY s.id, s.url, s.status ORDER BY s.id;" 2>/dev/null || true
'@
        }
        'ListActions' {
                $actions = @(
                        'Verify','WhoAmI','Setup24x7','EnableLiveHealth','TailLiveHealth','ValidateServices',
                        'StabilizeReportService','WriteGithubPat','ReportViaServiceEnv','PublishWithSourcedEnv',
                        'InspectReportEnv','ReportErrorDetails','SetupDB','SetupAgents','TailAgents','FixDbPerms',
                    'RegisterServer','RegisterServerList','KickoffNow','MythibiaBurst','GlobalBurst','InstallKickoffTimer','ShowKickoffTimer',
                        'DisableKickoffTimer','ShowServerStatus','ShowScoutDetails','ShowReseedTimers',
                        'WatchScoutingUntilSettled','ApplyScoutingTimeoutPolicy','InstallTieredReseedTimers',
                        'HotfixOrchestratorService','ShowReseedPolicy','ShowSystemHealth','ShowPipelineProgress',
                        'ListActions','ShowServiceRestarts','HealService','InstallGsReset','InstallGsResetFromBranch',
                        'EnsureGsEnvKeys','TriggerGsResetNow','TailGsReset','GsStatus','GsProvisionDbContainer',
                        'GsCoherence','GsModuleInject','GsApiValidate','ValidateSyntax'
                )

                Write-Host '=== Available Actions ==='
                foreach ($a in $actions) {
                        Write-Host ("- {0}" -f $a)
                }
                Write-Host ''
                Write-Host '=== Common commands ==='
                Write-Host 'powershell -ExecutionPolicy Bypass -File ctoa-vps.ps1 -Action ShowSystemHealth'
                Write-Host 'powershell -ExecutionPolicy Bypass -File ctoa-vps.ps1 -Action ShowPipelineProgress'
                Write-Host 'powershell -ExecutionPolicy Bypass -File ctoa-vps.ps1 -Action KickoffNow'
                Write-Host 'powershell -ExecutionPolicy Bypass -File ctoa-vps.ps1 -Action GlobalBurst'
                Write-Host 'powershell -ExecutionPolicy Bypass -File ctoa-vps.ps1 -Action RegisterServerList -ServerUrls "https://url1,https://url2"'
                Write-Host 'powershell -ExecutionPolicy Bypass -File ctoa-vps.ps1 -Action HealService -ServiceName ctoa-mobile-console'
        }
    'ShowServiceRestarts' {
        Invoke-SshScript @'
set -e
services="ctoa-mobile-console.service ctoa-health-live.service ctoa-mythibia-news-api.service ctoa-agents-orchestrator.service ctoa-auto-trainer.service"
echo "=== service restart counters ==="
for s in $services; do
  printf "\n--- %s ---\n" "$s"
  systemctl show "$s" -p ActiveState -p SubState -p Result -p NRestarts -p ExecMainStatus || true
  journalctl -u "$s" -n 12 --no-pager || true
done
'@
    }
    'HealService' {
        if ([string]::IsNullOrWhiteSpace($ServiceName)) {
            $ServiceName = Get-OptionalEnv 'CTOA_HEAL_SERVICE_NAME' ''
        }
        if ([string]::IsNullOrWhiteSpace($ServiceName)) {
            throw 'HealService requires -ServiceName (or env CTOA_HEAL_SERVICE_NAME)'
        }

        $svc = $ServiceName.Trim()
        if (-not $svc.EndsWith('.service')) {
            $svc = "$svc.service"
        }
        $svc = $svc -replace "'", "''"

        Invoke-SshScript @"
set -e
SVC='$svc'
    echo "=== heal service: `$SVC ==="
    systemctl reset-failed "`$SVC" || true
    systemctl restart "`$SVC"
sleep 2
    systemctl show "`$SVC" -p ActiveState -p SubState -p Result -p NRestarts -p ExecMainStatus
    systemctl status "`$SVC" --no-pager -l | sed -n '1,40p' || true
    journalctl -u "`$SVC" -n 30 --no-pager || true
"@
    }
        'WatchScoutingUntilSettled' {
                $watchUrl = Get-RequiredEnv 'CTOA_WATCH_URL'
                $intervalSeconds = [int](Get-OptionalEnv 'CTOA_WATCH_INTERVAL_SECONDS' '180')
                $maxChecks = [int](Get-OptionalEnv 'CTOA_WATCH_MAX_CHECKS' '12')

                if ($intervalSeconds -lt 15) {
                        throw 'CTOA_WATCH_INTERVAL_SECONDS must be >= 15'
                }
                if ($maxChecks -lt 1) {
                        throw 'CTOA_WATCH_MAX_CHECKS must be >= 1'
                }

                $safeUrl = $watchUrl -replace "'", "''"
                Write-Host "[WatchScoutingUntilSettled] url=$watchUrl interval=${intervalSeconds}s max_checks=$maxChecks"

                for ($i = 1; $i -le $maxChecks; $i++) {
                        Write-Host "[WatchScoutingUntilSettled] pass $i/$maxChecks -> ValidateServices"
                        Invoke-SshScript @'
set -e
systemctl start ctoa-runner.service
systemctl start ctoa-report.service || true
'@

                        Write-Host "[WatchScoutingUntilSettled] checking status for $watchUrl"
                        $status = Invoke-SshScript @"
set -e
sudo -u postgres psql -d ctoa -At -c "SELECT status FROM servers WHERE url='$safeUrl' ORDER BY updated_at DESC LIMIT 1;"
"@

                        $status = ($status | Out-String).Trim().ToUpperInvariant()
                        if ([string]::IsNullOrWhiteSpace($status)) {
                                throw "Watch URL not found in servers: $watchUrl"
                        }

                        Write-Host "[WatchScoutingUntilSettled] status=$status"
                        if ($status -ne 'SCOUTING') {
                                Write-Host "[WatchScoutingUntilSettled] settled with status=$status"
                                Invoke-SshScript @"
set -e
sudo -u postgres psql -d ctoa -c "SELECT id, url, status, COALESCE(game_type,'') AS game_type, LEFT(COALESCE(scout_error,''), 160) AS scout_error, to_char(updated_at, 'YYYY-MM-DD HH24:MI:SS') AS updated_at FROM servers WHERE url='$safeUrl' ORDER BY updated_at DESC LIMIT 1;"
"@
                                return
                        }

                        if ($i -lt $maxChecks) {
                                Start-Sleep -Seconds $intervalSeconds
                        }
                }

                Write-Host "[WatchScoutingUntilSettled] timeout reached, still SCOUTING after $maxChecks checks"
                Invoke-SshScript @"
set -e
sudo -u postgres psql -d ctoa -c "SELECT id, url, status, COALESCE(game_type,'') AS game_type, LEFT(COALESCE(scout_error,''), 160) AS scout_error, to_char(updated_at, 'YYYY-MM-DD HH24:MI:SS') AS updated_at FROM servers WHERE url='$safeUrl' ORDER BY updated_at DESC LIMIT 1;"
"@
        }
        'ApplyScoutingTimeoutPolicy' {
                $timeoutMinutes = [int](Get-OptionalEnv 'CTOA_SCOUT_TIMEOUT_MINUTES' '30')
                $maxRetries = [int](Get-OptionalEnv 'CTOA_SCOUT_MAX_RETRIES' '2')

                if ($timeoutMinutes -lt 5) {
                        throw 'CTOA_SCOUT_TIMEOUT_MINUTES must be >= 5'
                }
                if ($maxRetries -lt 0) {
                        throw 'CTOA_SCOUT_MAX_RETRIES must be >= 0'
                }

                Write-Host "[ApplyScoutingTimeoutPolicy] timeout=${timeoutMinutes}m max_retries=$maxRetries"

                Invoke-SshScript @"
set -e
echo "=== stale SCOUTING candidates ==="
sudo -u postgres psql -d ctoa -c "SELECT id, url, status, to_char(updated_at, 'YYYY-MM-DD HH24:MI:SS') AS updated_at FROM servers WHERE status='SCOUTING' AND updated_at < now() - interval '$timeoutMinutes minutes' ORDER BY updated_at ASC;"

echo
echo "=== policy updates (retry->NEW or finalize->ERROR) ==="
sudo -u postgres psql -d ctoa -c "WITH stale AS ( SELECT id, url, COALESCE(scout_error,'') AS scout_error, COALESCE((regexp_match(COALESCE(scout_error,''), '\\[auto-retry ([0-9]+)\\/([0-9]+)\\]'))[1]::int, 0) AS retries FROM servers WHERE status='SCOUTING' AND updated_at < now() - interval '$timeoutMinutes minutes' ), upd AS ( UPDATE servers s SET status = CASE WHEN stale.retries < $maxRetries THEN 'NEW' ELSE 'ERROR' END, scout_error = CASE WHEN stale.retries < $maxRetries THEN trim(both ' ' from concat_ws(' | ', nullif(stale.scout_error,''), format('[auto-retry %s/%s] stale SCOUTING > %s min at %s', stale.retries + 1, $maxRetries, $timeoutMinutes, to_char(now(), 'YYYY-MM-DD HH24:MI:SS')))) ELSE trim(both ' ' from concat_ws(' | ', nullif(stale.scout_error,''), format('[timeout-final %s/%s] stale SCOUTING > %s min at %s', stale.retries, $maxRetries, $timeoutMinutes, to_char(now(), 'YYYY-MM-DD HH24:MI:SS')))) END, updated_at = now() FROM stale WHERE s.id = stale.id RETURNING s.id, s.url, s.status, LEFT(COALESCE(s.scout_error,''), 180) AS scout_error ) SELECT * FROM upd ORDER BY id;"

echo
echo "=== status counts after policy ==="
sudo -u postgres psql -d ctoa -c "SELECT status, COUNT(*) AS n FROM servers GROUP BY status ORDER BY status;"

# Trigger orchestrator only if retries moved anything back to NEW.
if sudo -u postgres psql -d ctoa -At -c "SELECT COUNT(*) FROM servers WHERE status='NEW';" | grep -Eq '^[1-9][0-9]*$'; then
        systemctl start ctoa-agents-orchestrator.service || true
fi
"@
        }
        'InstallTieredReseedTimers' {
                $tierAbUrls = Get-OptionalEnv 'CTOA_RESEED_TIER_AB_URLS' 'https://tibiantis.online,https://tibia.com'
                $tierCUrls = Get-OptionalEnv 'CTOA_RESEED_TIER_C_URLS' 'https://mythibia.online,https://otland.net'
                $abIntervalMinutes = [int](Get-OptionalEnv 'CTOA_RESEED_AB_INTERVAL_MINUTES' '120')
                $cDailyTimeUtc = Get-OptionalEnv 'CTOA_RESEED_C_DAILY_UTC' '03:15'

                if ($abIntervalMinutes -lt 10) {
                        throw 'CTOA_RESEED_AB_INTERVAL_MINUTES must be >= 10'
                }

                Write-Host "[InstallTieredReseedTimers] TierAB=$tierAbUrls"
                Write-Host "[InstallTieredReseedTimers] TierC=$tierCUrls"
                Write-Host "[InstallTieredReseedTimers] AB interval=${abIntervalMinutes}m, C daily UTC=$cDailyTimeUtc"

                $remoteScript = @'
set -e
mkdir -p /opt/ctoa/scripts/ops /opt/ctoa/logs
touch /opt/ctoa/.env

cat > /opt/ctoa/scripts/ops/reseed-tier.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail

TIER="${1:-${CTOA_RESEED_TIER:-}}"
if [ -z "$TIER" ]; then
  echo "Usage: reseed-tier.sh <AB|C>"
  exit 1
fi

DEFAULT_ERROR_MIN_AGE_HOURS="${CTOA_RESEED_ERROR_MIN_AGE_HOURS:-6}"

if [ -f /opt/ctoa/.env ]; then
  # shellcheck disable=SC1091
  set -a; . /opt/ctoa/.env; set +a
fi

case "${TIER^^}" in
  AB)
    URLS="${CTOA_RESEED_TIER_AB_URLS:-https://tibiantis.online,https://tibia.com}"
        ERROR_MIN_AGE_HOURS="${CTOA_RESEED_ERROR_MIN_AGE_HOURS_AB:-$DEFAULT_ERROR_MIN_AGE_HOURS}"
    ;;
  C)
    URLS="${CTOA_RESEED_TIER_C_URLS:-https://mythibia.online,https://otland.net}"
        ERROR_MIN_AGE_HOURS="${CTOA_RESEED_ERROR_MIN_AGE_HOURS_C:-24}"
    ;;
  *)
    echo "Unknown tier: $TIER"
    exit 1
    ;;
esac

IFS=',' read -r -a arr <<< "$URLS"
for raw in "${arr[@]}"; do
  url="$(echo "$raw" | xargs)"
  [ -n "$url" ] || continue

    row="$(sudo -u postgres psql -d ctoa -At -F '|' -c "SELECT status, EXTRACT(EPOCH FROM (now() - updated_at))/3600.0 AS age_hours FROM servers WHERE url='$url' ORDER BY updated_at DESC LIMIT 1;")"

    if [ -z "$row" ]; then
        echo "[reseed-tier][$TIER] skip (not-found): $url"
        continue
    fi

    status="${row%%|*}"
    age_hours="${row#*|}"

    if [ "$status" != "ERROR" ]; then
        echo "[reseed-tier][$TIER] skip (status=$status): $url"
        continue
    fi

    should_queue="$(sudo -u postgres psql -d ctoa -At -c "SELECT CASE WHEN $age_hours >= $ERROR_MIN_AGE_HOURS THEN '1' ELSE '0' END;")"
    if [ "$should_queue" != "1" ]; then
        echo "[reseed-tier][$TIER] skip (ERROR too fresh: ${age_hours}h < ${ERROR_MIN_AGE_HOURS}h): $url"
        continue
    fi

    sudo -u postgres psql -d ctoa -c "UPDATE servers SET status='NEW', updated_at=now(), scout_error=trim(both ' ' from concat_ws(' | ', nullif(COALESCE(scout_error,''),''), '[tier-reseed ${TIER}] auto retry after stale ERROR (${ERROR_MIN_AGE_HOURS}h+)')) WHERE url='$url';" >/dev/null
    echo "[reseed-tier][$TIER] queued stale ERROR: $url (age=${age_hours}h)"
done

systemctl start ctoa-agents-orchestrator.service || true
SH

chmod +x /opt/ctoa/scripts/ops/reseed-tier.sh

grep -v '^CTOA_RESEED_TIER_AB_URLS=' /opt/ctoa/.env > /opt/ctoa/.env.tmp || true
mv /opt/ctoa/.env.tmp /opt/ctoa/.env
echo "CTOA_RESEED_TIER_AB_URLS=__TIER_AB_URLS__" >> /opt/ctoa/.env

grep -v '^CTOA_RESEED_TIER_C_URLS=' /opt/ctoa/.env > /opt/ctoa/.env.tmp || true
mv /opt/ctoa/.env.tmp /opt/ctoa/.env
echo "CTOA_RESEED_TIER_C_URLS=__TIER_C_URLS__" >> /opt/ctoa/.env

grep -v '^CTOA_RESEED_ERROR_MIN_AGE_HOURS_AB=' /opt/ctoa/.env > /opt/ctoa/.env.tmp || true
mv /opt/ctoa/.env.tmp /opt/ctoa/.env
echo "CTOA_RESEED_ERROR_MIN_AGE_HOURS_AB=__ERROR_MIN_AGE_HOURS_AB__" >> /opt/ctoa/.env

grep -v '^CTOA_RESEED_ERROR_MIN_AGE_HOURS_C=' /opt/ctoa/.env > /opt/ctoa/.env.tmp || true
mv /opt/ctoa/.env.tmp /opt/ctoa/.env
echo "CTOA_RESEED_ERROR_MIN_AGE_HOURS_C=__ERROR_MIN_AGE_HOURS_C__" >> /opt/ctoa/.env

grep -v '^CTOA_RESEED_ERROR_MIN_AGE_HOURS=' /opt/ctoa/.env > /opt/ctoa/.env.tmp || true
mv /opt/ctoa/.env.tmp /opt/ctoa/.env
echo "CTOA_RESEED_ERROR_MIN_AGE_HOURS=__ERROR_MIN_AGE_HOURS__" >> /opt/ctoa/.env

cat > /etc/systemd/system/ctoa-reseed-tier-ab.service <<'UNIT'
[Unit]
Description=CTOA reseed Tier A/B URLs
After=network-online.target

[Service]
Type=oneshot
WorkingDirectory=/opt/ctoa
ExecStart=/opt/ctoa/scripts/ops/reseed-tier.sh AB
StandardOutput=append:/opt/ctoa/logs/reseed-tier.log
StandardError=append:/opt/ctoa/logs/reseed-tier.log
UNIT

cat > /etc/systemd/system/ctoa-reseed-tier-ab.timer <<UNIT
[Unit]
Description=CTOA reseed Tier A/B timer

[Timer]
OnBootSec=5min
OnUnitActiveSec=__AB_INTERVAL_MINUTES__min
Persistent=true
Unit=ctoa-reseed-tier-ab.service

[Install]
WantedBy=timers.target
UNIT

cat > /etc/systemd/system/ctoa-reseed-tier-c.service <<'UNIT'
[Unit]
Description=CTOA reseed Tier C URLs
After=network-online.target

[Service]
Type=oneshot
WorkingDirectory=/opt/ctoa
ExecStart=/opt/ctoa/scripts/ops/reseed-tier.sh C
StandardOutput=append:/opt/ctoa/logs/reseed-tier.log
StandardError=append:/opt/ctoa/logs/reseed-tier.log
UNIT

cat > /etc/systemd/system/ctoa-reseed-tier-c.timer <<UNIT
[Unit]
Description=CTOA reseed Tier C timer (daily)

[Timer]
OnCalendar=*-*-* __C_DAILY_UTC__
Persistent=true
Unit=ctoa-reseed-tier-c.service

[Install]
WantedBy=timers.target
UNIT

systemctl daemon-reload
systemctl enable --now ctoa-reseed-tier-ab.timer
systemctl enable --now ctoa-reseed-tier-c.timer

echo "=== reseed timer status ==="
systemctl list-timers 'ctoa-reseed-tier-*' --no-pager
echo
echo "=== reseed env summary ==="
grep -E '^CTOA_RESEED_(TIER_(AB|C)_URLS|ERROR_MIN_AGE_HOURS(_(AB|C))?)=' /opt/ctoa/.env
'@

                $remoteScript = $remoteScript.Replace('__TIER_AB_URLS__', $tierAbUrls)
                $remoteScript = $remoteScript.Replace('__TIER_C_URLS__', $tierCUrls)
                $remoteScript = $remoteScript.Replace('__ERROR_MIN_AGE_HOURS_AB__', (Get-OptionalEnv 'CTOA_RESEED_ERROR_MIN_AGE_HOURS_AB' '6'))
                $remoteScript = $remoteScript.Replace('__ERROR_MIN_AGE_HOURS_C__', (Get-OptionalEnv 'CTOA_RESEED_ERROR_MIN_AGE_HOURS_C' '24'))
                $remoteScript = $remoteScript.Replace('__ERROR_MIN_AGE_HOURS__', (Get-OptionalEnv 'CTOA_RESEED_ERROR_MIN_AGE_HOURS' '6'))
                $remoteScript = $remoteScript.Replace('__AB_INTERVAL_MINUTES__', [string]$abIntervalMinutes)
                $remoteScript = $remoteScript.Replace('__C_DAILY_UTC__', $cDailyTimeUtc)
                Invoke-SshScript $remoteScript
        }
        'HotfixOrchestratorService' {
                Invoke-SshScript @'
set -e
cat > /etc/systemd/system/ctoa-agents-orchestrator.service <<'UNIT'
[Unit]
Description=CTOA Agents Orchestrator (one-shot pipeline run)
After=network.target postgresql.service

[Service]
Type=oneshot
User=root
WorkingDirectory=/opt/ctoa
EnvironmentFile=/opt/ctoa/.env
Environment=PYTHONUNBUFFERED=1
ExecStart=/opt/ctoa/.venv/bin/python3 -m runner.agents.orchestrator
StandardOutput=append:/opt/ctoa/logs/agents-orchestrator.log
StandardError=append:/opt/ctoa/logs/agents-orchestrator.log
TimeoutStartSec=900
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl reset-failed ctoa-agents-orchestrator.service || true

# Avoid overlapping stuck process before applying hotfix.
if systemctl is-active --quiet ctoa-agents-orchestrator.service; then
    systemctl stop ctoa-agents-orchestrator.service || true
fi

systemctl start ctoa-agents-orchestrator.service || true

echo "=== orchestrator unit timeout settings ==="
systemctl show ctoa-agents-orchestrator.service -p TimeoutStartUSec -p TimeoutStopUSec -p ExecMainStartTimestamp -p ActiveState -p SubState
echo
echo "=== orchestrator service status ==="
systemctl status ctoa-agents-orchestrator.service --no-pager -l | sed -n '1,60p'
echo
echo "=== orchestrator journal tail ==="
journalctl -u ctoa-agents-orchestrator.service -n 80 --no-pager
'@
        }
        'RegisterServer' {
                $serverUrl = Get-RequiredEnv 'CTOA_SERVER_URL'
                $serverName = Get-OptionalEnv 'CTOA_SERVER_NAME' 'External-Server'
                $safeUrl = $serverUrl -replace "'", "''"
                $safeName = $serverName -replace "'", "''"

                Invoke-SshScript @"
set -e
sudo -u postgres psql -d ctoa -c "INSERT INTO servers(url,name,status) VALUES ('$safeUrl','$safeName','NEW') ON CONFLICT (url) DO UPDATE SET name=EXCLUDED.name, status='NEW', updated_at=now();"
systemctl start ctoa-agents-orchestrator.service
echo "[RegisterServer] submitted: $serverUrl"
"@
        }
    'RegisterServerList' {
        $serverUrlsRaw = $ServerUrls
        if ([string]::IsNullOrWhiteSpace($serverUrlsRaw)) {
            $serverUrlsRaw = Get-OptionalEnv 'CTOA_SERVER_URLS' ''
        }
        if ([string]::IsNullOrWhiteSpace($serverUrlsRaw)) {
            throw 'RegisterServerList requires -ServerUrls "url1,url2" (or env CTOA_SERVER_URLS)'
        }

        $urls = @($serverUrlsRaw -split ',' | ForEach-Object { $_.Trim() } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
        if ($urls.Count -eq 0) {
            throw 'RegisterServerList did not receive any valid URLs'
        }

        foreach ($url in $urls) {
            $safeUrl = $url -replace "'", "''"
            Invoke-SshScript @"
set -e
cd /opt/ctoa
sudo -u postgres psql -d ctoa -c "INSERT INTO servers(url,name,status) VALUES ('$safeUrl','External-Server','NEW') ON CONFLICT (url) DO UPDATE SET name=EXCLUDED.name, status='NEW', updated_at=now();"
echo "[RegisterServerList] submitted: $url"
"@
        }

        Invoke-SshScript @'
set -e
cd /opt/ctoa
systemctl start ctoa-runner.service || true
systemctl start ctoa-agents-orchestrator.service || true
sudo -u postgres psql -d ctoa -c "SELECT status, COUNT(*) AS n FROM servers GROUP BY status ORDER BY status;"
'@
    }
    'KickoffNow' {
        Invoke-SshScript @'
set -e
cd /opt/ctoa
echo "=== KickoffNow: ERROR -> NEW ==="
sudo -u postgres psql -d ctoa -c "UPDATE servers SET status='NEW', scout_error=NULL, updated_at=NOW() WHERE status='ERROR';"
echo
echo "=== KickoffNow: start processing ==="
systemctl start ctoa-runner.service || true
systemctl start ctoa-agents-orchestrator.service || true
systemctl start ctoa-report.service || true
echo
echo "=== KickoffNow: server counts ==="
sudo -u postgres psql -d ctoa -c "SELECT status, COUNT(*) AS n FROM servers GROUP BY status ORDER BY status;"
echo
echo "=== KickoffNow: latest runs ==="
sudo -u postgres psql -d ctoa -c "SELECT id, agent, status, to_char(started_at,'YYYY-MM-DD HH24:MI:SS') AS started_at FROM agent_runs ORDER BY id DESC LIMIT 12;"
'@
    }
        'MythibiaBurst' {
            $targetUrl = Get-OptionalEnv 'CTOA_MYTHIBIA_URL' 'https://mythibia.online'
            if ([string]::IsNullOrWhiteSpace($targetUrl)) {
                $targetUrl = Get-OptionalEnv 'CTOA_PRIMARY_SERVER_URL' 'https://mythibia.online'
            }
            if (-not [string]::IsNullOrWhiteSpace($ServerUrls)) {
                $targetUrl = ($ServerUrls -split ',')[0].Trim()
            }
            $targetUrl = Resolve-ServerUrl $targetUrl 'https://mythibia.online'
                $safeUrl = $targetUrl -replace "'", "''"

                Invoke-SshScript @"
set -e
cd /opt/ctoa
URL='$safeUrl'

echo "=== MythibiaBurst target: `$URL ==="

sudo -u postgres psql -d ctoa -c "INSERT INTO servers(url,name,status) VALUES ('`$URL','Mythibia-Primary','READY') ON CONFLICT (url) DO UPDATE SET status='READY', updated_at=now();"

sudo -u postgres psql -d ctoa -c "
WITH s AS (
    SELECT id FROM servers WHERE url='`$URL' LIMIT 1
), base_templates AS (
    SELECT DISTINCT ON (m.template)
            m.template,
            COALESCE(NULLIF(m.output_file,''), m.template || '.lua') AS output_file
    FROM modules m
    JOIN servers sx ON sx.id = m.server_id
    WHERE sx.url='`$URL'
    ORDER BY m.template, m.id DESC
), seeded AS (
    INSERT INTO modules (server_id, task_id, template, output_file, status)
    SELECT
        s.id,
        'SRV' || lpad(s.id::text, 3, '0') || '-' || upper(left(replace(bt.template,'_',''), 14)) || '-R' || substring(md5(random()::text || clock_timestamp()::text),1,6),
        bt.template,
        regexp_replace(bt.output_file, '\\.[Ll][Uu][Aa]$', '', 'g') || '_r' || to_char(now(),'HH24MISS') || '.lua',
        'QUEUED'
    FROM s
    JOIN base_templates bt ON true
    RETURNING id
)
SELECT COUNT(*) AS queued_now FROM seeded;
"

systemctl start ctoa-agents-orchestrator.service || true
sleep 4

echo
echo "=== MythibiaBurst module status (target server) ==="
sudo -u postgres psql -d ctoa -c "SELECT m.status, COUNT(*) AS n FROM modules m JOIN servers s ON s.id=m.server_id WHERE s.url='`$URL' GROUP BY m.status ORDER BY m.status;"
echo
echo "=== MythibiaBurst latest modules ==="
sudo -u postgres psql -d ctoa -c "SELECT m.id, m.task_id, m.template, m.status, COALESCE(m.output_file,'') AS output_file, COALESCE(m.output_path,'') AS output_path FROM modules m JOIN servers s ON s.id=m.server_id WHERE s.url='`$URL' ORDER BY m.id DESC LIMIT 20;"
"@
        }
    'GlobalBurst' {
        $burstPerServer = [int](Get-OptionalEnv 'CTOA_BURST_PER_SERVER' '12')
        if ($burstPerServer -lt 1) {
            throw 'CTOA_BURST_PER_SERVER must be >= 1'
        }
        if ($burstPerServer -gt 50) {
            $burstPerServer = 50
        }

        Invoke-SshScript @"
    set -u
cd /opt/ctoa

echo "=== GlobalBurst: quarantine invalid URLs ==="
    sudo -u postgres psql -d ctoa -c "UPDATE servers SET status='ERROR', scout_error='invalid url quarantined by GlobalBurst', updated_at=now() WHERE url !~* '^https?://';" || true

echo
echo "=== GlobalBurst: mark valid servers READY ==="
    sudo -u postgres psql -d ctoa -c "UPDATE servers SET status='READY', scout_error=NULL, updated_at=now() WHERE url ~* '^https?://';" || true

echo
echo "=== GlobalBurst: seed modules for all valid servers (per-server burst=$burstPerServer) ==="
    if ! sudo -u postgres psql -d ctoa -c "
WITH valid_servers AS (
    SELECT id, url
    FROM servers
    WHERE url ~* '^https?://'
), catalog AS (
    SELECT DISTINCT ON (m.template)
        m.template,
        COALESCE(NULLIF(m.output_file,''), m.template || '.lua') AS output_file
    FROM modules m
    WHERE COALESCE(m.template,'') <> ''
    ORDER BY m.template, m.id DESC
), server_templates AS (
    SELECT DISTINCT ON (m.server_id, m.template)
        m.server_id,
        m.template,
        COALESCE(NULLIF(m.output_file,''), m.template || '.lua') AS output_file
    FROM modules m
    JOIN valid_servers vs ON vs.id = m.server_id
    WHERE COALESCE(m.template,'') <> ''
    ORDER BY m.server_id, m.template, m.id DESC
), servers_without_templates AS (
    SELECT vs.id
    FROM valid_servers vs
    LEFT JOIN server_templates st ON st.server_id = vs.id
    WHERE st.server_id IS NULL
), source_templates AS (
    SELECT st.server_id, st.template, st.output_file
    FROM server_templates st
    UNION ALL
    SELECT swt.id AS server_id, c.template, c.output_file
    FROM servers_without_templates swt
    JOIN catalog c ON true
), picked AS (
    SELECT server_id, template, output_file
    FROM (
        SELECT
            st.server_id,
            st.template,
            st.output_file,
            ROW_NUMBER() OVER (PARTITION BY st.server_id ORDER BY md5(st.template || clock_timestamp()::text || random()::text)) AS rn
        FROM source_templates st
    ) x
    WHERE rn <= $burstPerServer
), seeded AS (
    INSERT INTO modules (server_id, task_id, template, output_file, status)
    SELECT
        p.server_id,
        'SRV' || lpad(p.server_id::text, 3, '0') || '-' || upper(left(replace(p.template,'_',''), 14)) || '-R' || substring(md5(random()::text || clock_timestamp()::text),1,6),
        p.template,
        regexp_replace(p.output_file, '\\.[Ll][Uu][Aa]$', '', 'g') || '_r' || to_char(now(),'HH24MISS') || '.lua',
        'QUEUED'
    FROM picked p
    RETURNING server_id
)
SELECT COUNT(*) AS queued_now, COUNT(DISTINCT server_id) AS seeded_servers FROM seeded;
"; then
    echo "[GlobalBurst] seed query failed (continuing to keep services alive)"
fi

echo
echo "=== GlobalBurst: start pipeline services ==="
systemctl start --no-block ctoa-runner.service || true
systemctl start --no-block ctoa-agents-orchestrator.service || true
systemctl start --no-block ctoa-report.service || true

sleep 4
echo
echo "=== GlobalBurst: server status ==="
sudo -u postgres psql -d ctoa -c "SELECT status, COUNT(*) AS n FROM servers GROUP BY status ORDER BY status;" || true
echo
echo "=== GlobalBurst: module status ==="
sudo -u postgres psql -d ctoa -c "SELECT status, COUNT(*) AS n FROM modules GROUP BY status ORDER BY status;" || true
echo
echo "=== GlobalBurst: latest agent runs ==="
sudo -u postgres psql -d ctoa -c "SELECT id, agent, status, to_char(started_at,'YYYY-MM-DD HH24:MI:SS') AS started_at FROM agent_runs ORDER BY id DESC LIMIT 15;" || true
"@
    }
    'InstallKickoffTimer' {
        $kickoffEveryMinutes = [int](Get-OptionalEnv 'CTOA_KICKOFF_EVERY_MINUTES' '15')
        if ($kickoffEveryMinutes -lt 1) {
            throw 'CTOA_KICKOFF_EVERY_MINUTES must be >= 1'
        }

        Invoke-SshScript @"
set -e
mkdir -p /opt/ctoa/scripts/ops /opt/ctoa/logs

cat > /opt/ctoa/scripts/ops/kickoff-now.sh <<'SCRIPT'
#!/usr/bin/env bash
set -euo pipefail
cd /opt/ctoa
source /opt/ctoa/.env 2>/dev/null || true

BURST_PER_SERVER="`${CTOA_KICKOFF_BURST_PER_SERVER:-6}"
if ! [[ "`$BURST_PER_SERVER" =~ ^[0-9]+$ ]]; then BURST_PER_SERVER=6; fi
if [ "`$BURST_PER_SERVER" -lt 1 ]; then BURST_PER_SERVER=1; fi
if [ "`$BURST_PER_SERVER" -gt 30 ]; then BURST_PER_SERVER=30; fi

echo "[kickoff-now] `$(date -u +'%Y-%m-%dT%H:%M:%SZ') global reseed + start services (burst=`${BURST_PER_SERVER})" >> /opt/ctoa/logs/kickoff.log

sudo -u postgres psql -d ctoa -c "UPDATE servers SET status='ERROR', scout_error='invalid url quarantined by kickoff', updated_at=now() WHERE url !~* '^https?://';" >> /opt/ctoa/logs/kickoff.log 2>&1 || true
sudo -u postgres psql -d ctoa -c "UPDATE servers SET status='READY', scout_error=NULL, updated_at=now() WHERE url ~* '^https?://';" >> /opt/ctoa/logs/kickoff.log 2>&1 || true

sudo -u postgres psql -d ctoa -c "
WITH valid_servers AS (
    SELECT id, url
    FROM servers
    WHERE url ~* '^https?://'
), catalog AS (
    SELECT DISTINCT ON (m.template)
        m.template,
        COALESCE(NULLIF(m.output_file,''), m.template || '.lua') AS output_file
    FROM modules m
    WHERE COALESCE(m.template,'') <> ''
    ORDER BY m.template, m.id DESC
), server_templates AS (
    SELECT DISTINCT ON (m.server_id, m.template)
        m.server_id,
        m.template,
        COALESCE(NULLIF(m.output_file,''), m.template || '.lua') AS output_file
    FROM modules m
    JOIN valid_servers vs ON vs.id = m.server_id
    WHERE COALESCE(m.template,'') <> ''
    ORDER BY m.server_id, m.template, m.id DESC
), servers_without_templates AS (
    SELECT vs.id
    FROM valid_servers vs
    LEFT JOIN server_templates st ON st.server_id = vs.id
    WHERE st.server_id IS NULL
), source_templates AS (
    SELECT st.server_id, st.template, st.output_file
    FROM server_templates st
    UNION ALL
    SELECT swt.id AS server_id, c.template, c.output_file
    FROM servers_without_templates swt
    JOIN catalog c ON true
), picked AS (
    SELECT server_id, template, output_file
    FROM (
        SELECT
            st.server_id,
            st.template,
            st.output_file,
            ROW_NUMBER() OVER (PARTITION BY st.server_id ORDER BY md5(st.template || clock_timestamp()::text || random()::text)) AS rn
        FROM source_templates st
    ) x
    WHERE rn <= `${BURST_PER_SERVER}
), seeded AS (
    INSERT INTO modules (server_id, task_id, template, output_file, status)
    SELECT
        p.server_id,
        'SRV' || lpad(p.server_id::text, 3, '0') || '-' || upper(left(replace(p.template,'_',''), 14)) || '-R' || substring(md5(random()::text || clock_timestamp()::text),1,6),
        p.template,
        regexp_replace(p.output_file, '\\.[Ll][Uu][Aa]$', '', 'g') || '_r' || to_char(now(),'HH24MISS') || '.lua',
        'QUEUED'
    FROM picked p
    RETURNING server_id
)
SELECT COUNT(*) AS queued_now, COUNT(DISTINCT server_id) AS seeded_servers FROM seeded;
" >> /opt/ctoa/logs/kickoff.log 2>&1 || true

systemctl start --no-block ctoa-runner.service >> /opt/ctoa/logs/kickoff.log 2>&1 || true
systemctl start --no-block ctoa-agents-orchestrator.service >> /opt/ctoa/logs/kickoff.log 2>&1 || true
systemctl start --no-block ctoa-report.service >> /opt/ctoa/logs/kickoff.log 2>&1 || true
SCRIPT

chmod +x /opt/ctoa/scripts/ops/kickoff-now.sh

cat > /etc/systemd/system/ctoa-kickoff.service <<'UNIT'
[Unit]
Description=CTOA kickoff now (ERROR->NEW and start pipeline)
After=network-online.target postgresql.service
Wants=network-online.target

[Service]
Type=oneshot
User=root
WorkingDirectory=/opt/ctoa
ExecStart=/bin/bash /opt/ctoa/scripts/ops/kickoff-now.sh
StandardOutput=append:/opt/ctoa/logs/kickoff.log
StandardError=append:/opt/ctoa/logs/kickoff.log
UNIT

cat > /etc/systemd/system/ctoa-kickoff.timer <<'UNIT'
[Unit]
Description=CTOA kickoff timer (every ${kickoffEveryMinutes} min)

[Timer]
OnBootSec=2min
OnUnitActiveSec=${kickoffEveryMinutes}min
Persistent=true
Unit=ctoa-kickoff.service

[Install]
WantedBy=timers.target
UNIT

systemctl daemon-reload
systemctl enable --now ctoa-kickoff.timer
systemctl start ctoa-kickoff.service || true

echo "=== kickoff timer installed ==="
systemctl status ctoa-kickoff.timer --no-pager -l | sed -n '1,40p'
echo
echo "=== kickoff service last 30 lines ==="
tail -n 30 /opt/ctoa/logs/kickoff.log 2>/dev/null || true
"@
    }
    'ShowKickoffTimer' {
        Invoke-SshScript @'
set -e
echo "=== ctoa-kickoff.timer ==="
systemctl status ctoa-kickoff.timer --no-pager -l | sed -n '1,60p' || true
echo
echo "=== ctoa-kickoff.service (last run) ==="
systemctl status ctoa-kickoff.service --no-pager -l | sed -n '1,60p' || true
echo
echo "=== kickoff log tail ==="
tail -n 60 /opt/ctoa/logs/kickoff.log 2>/dev/null || echo 'kickoff.log-not-found'
'@
    }
    'DisableKickoffTimer' {
        Invoke-SshScript @'
set -e
systemctl disable --now ctoa-kickoff.timer || true
systemctl stop ctoa-kickoff.service || true
echo "=== kickoff timer disabled ==="
systemctl list-unit-files ctoa-kickoff.timer ctoa-kickoff.service --no-pager || true
'@
    }
    'FixDbPerms' {
        Invoke-SshScript @'
set -e
sudo -u postgres psql -d ctoa <<"SQL"
GRANT CONNECT ON DATABASE ctoa TO ctoa;
GRANT USAGE ON SCHEMA public TO ctoa;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO ctoa;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO ctoa;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO ctoa;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO ctoa;
SQL
echo '[FixDbPerms] grants applied'
'@
    }
    'ReportViaServiceEnv' { Invoke-SshCommand 'systemctl restart ctoa-report.service; journalctl -u ctoa-report.service -n 25 --no-pager' }
    'PublishWithSourcedEnv' { Invoke-SshCommand 'cd /opt/ctoa; set -a; . /opt/ctoa/.env; set +a; . .venv/bin/activate; python3 runner/runner.py report --publish' }
    'WriteGithubPat' {
        $pat = Get-RequiredEnv 'CTOA_GITHUB_PAT'
        Invoke-SshCommand "sed -i '/^GITHUB_PAT/d' /opt/ctoa/.env; echo GITHUB_PAT=$pat >> /opt/ctoa/.env; echo PAT-written"
    }
    'StabilizeReportService' {
        Invoke-SshScript @'
set -e
systemctl restart ctoa-report.service
systemctl status ctoa-report.service --no-pager -l | head -n 20
if [ -f /opt/ctoa/logs/runner.log ]; then tail -n 20 /opt/ctoa/logs/runner.log; fi
'@
    }
    'InspectReportEnv' {
        Invoke-SshScript @'
set -e
grep -n '^GITHUB_PAT=' /opt/ctoa/.env | sed 's/=.*/=***set***/' || echo PAT-not-set
systemctl restart ctoa-report.service
journalctl -u ctoa-report.service -n 12 --no-pager
'@
    }
    'ValidateServices' {
        Invoke-SshScript @'
set -e
systemctl start ctoa-runner.service
systemctl start ctoa-report.service || true
systemctl status ctoa-runner.service --no-pager -l | head -n 12
systemctl status ctoa-report.service --no-pager -l | head -n 20
if [ -f /opt/ctoa/logs/runner.log ]; then tail -n 40 /opt/ctoa/logs/runner.log; else echo runner.log-not-present; fi
'@
    }
    'EnableLiveHealth' {
        Invoke-SshScript @'
set -e
mkdir -p /opt/ctoa/logs
cat > /etc/systemd/system/ctoa-health-live.service << 'UNIT'
[Unit]
Description=CTOA live health monitor
After=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/ctoa
EnvironmentFile=/opt/ctoa/.env
ExecStart=/opt/ctoa/.venv/bin/python3 runner/health_live.py
Restart=always
RestartSec=30
StandardOutput=append:/opt/ctoa/logs/health-live.log
StandardError=append:/opt/ctoa/logs/health-live.log

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now ctoa-health-live.service
systemctl status ctoa-health-live.service --no-pager -l
'@
    }
    'SetupDB' {
                Invoke-SshScript @'
set -e
cd /opt/ctoa
.venv/bin/pip install -q psycopg2-binary
# generate DB password if missing
if ! grep -q '^DB_PASSWORD=' /opt/ctoa/.env 2>/dev/null; then
    DBPW=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 28)
    printf '\nDB_NAME=ctoa\nDB_USER=ctoa\nDB_HOST=127.0.0.1\nDB_PORT=5432\nDB_PASSWORD=%s\n' "$DBPW" >> /opt/ctoa/.env
    echo '[SetupDB] DB_PASSWORD generated'
fi
set -a; . /opt/ctoa/.env; set +a
# create role if not exists
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='ctoa'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE ROLE ctoa WITH LOGIN PASSWORD '${DB_PASSWORD}';"
# create database if not exists
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='ctoa'" | grep -q 1 || \
    sudo -u postgres createdb -O ctoa ctoa
# apply schema (idempotent - IF NOT EXISTS)
sudo -u postgres psql -d ctoa -f /opt/ctoa/deploy/vps/db/init.sql && echo '[SetupDB] Schema applied'
pg_isready -h 127.0.0.1 -U ctoa -d ctoa && echo '[SetupDB] DB ready'
'@
    }
    'SetupAgents' {
        Invoke-SshScript @'
    set -e
    cd /opt/ctoa
    git pull --ff-only
    .venv/bin/pip install -q psycopg2-binary
    mkdir -p /opt/ctoa/generated /opt/ctoa/releases /opt/ctoa/logs
    cp deploy/vps/systemd/ctoa-agents-orchestrator.service /etc/systemd/system/
    cp deploy/vps/systemd/ctoa-agents-orchestrator.timer   /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable --now ctoa-agents-orchestrator.timer
    grep -q 'CTOA_GENERATED_DIR' /opt/ctoa/.env 2>/dev/null || echo 'CTOA_GENERATED_DIR=/opt/ctoa/generated' >> /opt/ctoa/.env
    grep -q 'CTOA_RELEASES_DIR'  /opt/ctoa/.env 2>/dev/null || echo 'CTOA_RELEASES_DIR=/opt/ctoa/releases'   >> /opt/ctoa/.env
    grep -q 'CTOA_REPO_DIR'      /opt/ctoa/.env 2>/dev/null || echo 'CTOA_REPO_DIR=/opt/ctoa'               >> /opt/ctoa/.env
    grep -q 'CTOA_DAILY_MODULE_LIMIT' /opt/ctoa/.env 2>/dev/null || echo 'CTOA_DAILY_MODULE_LIMIT=50' >> /opt/ctoa/.env
    grep -q 'CTOA_DAILY_PROGRAM_LIMIT' /opt/ctoa/.env 2>/dev/null || echo 'CTOA_DAILY_PROGRAM_LIMIT=5' >> /opt/ctoa/.env
    grep -q 'CTOA_MIN_QUALITY' /opt/ctoa/.env 2>/dev/null || echo 'CTOA_MIN_QUALITY=90' >> /opt/ctoa/.env
    grep -q 'CTOA_SCOUT_SERVER_TIMEOUT_SECONDS' /opt/ctoa/.env 2>/dev/null || echo 'CTOA_SCOUT_SERVER_TIMEOUT_SECONDS=120' >> /opt/ctoa/.env
    systemctl restart ctoa-mobile-console.service
    systemctl status ctoa-agents-orchestrator.timer     --no-pager -l | head -n 8
    systemctl status ctoa-mobile-console.service        --no-pager -l | head -n 6
    pg_isready -h 127.0.0.1 -U ctoa -d ctoa && echo '[SetupAgents] DB OK'
    echo '[SetupAgents] Done - orchestrator fires every 10 minutes'
'@
    }

    # =========================================================================
    # GS RESET ACTIONS
    # =========================================================================

    'InstallGsReset' {
        # Install ctoa-gs-reset.service + timer and all GS scripts on VPS.
        # Auto-fallback: if main does not have GS files, try CTOA_GS_SOURCE_REF.
        $sourceRef = Get-OptionalEnv 'CTOA_GS_SOURCE_REF' ''
        $safeRef = $sourceRef -replace "'", "''"

        $remoteScript = @'
set -e
cd /opt/ctoa
git fetch --quiet
git reset --hard origin/main

required_files="
/opt/ctoa/scripts/ops/gs-reset.sh
/opt/ctoa/scripts/ops/gs-startup-sequence.sh
/opt/ctoa/scripts/ops/gs-coherence-check.sh
/opt/ctoa/scripts/ops/gs-module-inject.sh
/opt/ctoa/scripts/ops/gs-api-validator.py
/opt/ctoa/deploy/vps/systemd/ctoa-gs-reset.service
/opt/ctoa/deploy/vps/systemd/ctoa-gs-reset.timer
"

check_required_files() {
    local prefix="$1"
    local missing=0
    for f in $required_files; do
        if [ ! -f "$f" ]; then
            echo "[$prefix] MISSING: $f"
            missing=1
        fi
    done
    return "$missing"
}

if ! check_required_files 'InstallGsReset'; then
    if [ -n "__FALLBACK_REF__" ]; then
        echo "[InstallGsReset] main missing GS files, trying fallback ref: __FALLBACK_REF__"
        git fetch --quiet origin "__FALLBACK_REF__"
        git checkout -f FETCH_HEAD
        if ! check_required_files 'InstallGsReset'; then
            echo "[InstallGsReset] ERROR: GS files missing in fallback ref: __FALLBACK_REF__"
            exit 1
        fi
    else
        echo "[InstallGsReset] ERROR: GS files are not present on origin/main on VPS."
        echo "[InstallGsReset] Set CTOA_GS_SOURCE_REF to fallback branch and rerun."
        exit 1
    fi
fi

chmod +x /opt/ctoa/scripts/ops/gs-reset.sh
chmod +x /opt/ctoa/scripts/ops/gs-startup-sequence.sh
chmod +x /opt/ctoa/scripts/ops/gs-coherence-check.sh
chmod +x /opt/ctoa/scripts/ops/gs-module-inject.sh
chmod +x /opt/ctoa/scripts/ops/gs-api-validator.py
cp /opt/ctoa/deploy/vps/systemd/ctoa-gs-reset.service /etc/systemd/system/
cp /opt/ctoa/deploy/vps/systemd/ctoa-gs-reset.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable ctoa-gs-reset.timer
systemctl start ctoa-gs-reset.timer
systemctl list-timers ctoa-gs-reset.timer --no-pager
echo [InstallGsReset] GS reset timer armed and active
'@

    $remoteScript = $remoteScript.Replace('__FALLBACK_REF__', $safeRef)
    Invoke-SshScript $remoteScript
    }

    'InstallGsResetFromBranch' {
        # Emergency install from a specific remote ref/branch.
        # Use env var CTOA_GS_SOURCE_REF or provide value when prompted.
        $sourceRef = Get-OptionalEnv 'CTOA_GS_SOURCE_REF' ''
        if ([string]::IsNullOrWhiteSpace($sourceRef)) {
            $sourceRef = Read-Host 'Enter source ref (example: ci/hardening-failclosed-diff)'
        }
        if ([string]::IsNullOrWhiteSpace($sourceRef)) {
            throw 'InstallGsResetFromBranch requires source ref.'
        }

        $safeRef = $sourceRef -replace "'", "''"

        $remoteScript = @'
set -e
cd /opt/ctoa
    echo "[InstallGsResetFromBranch] source ref: __SOURCE_REF__"
    git fetch --quiet origin "__SOURCE_REF__"
git checkout -f FETCH_HEAD

required_files="
/opt/ctoa/scripts/ops/gs-reset.sh
/opt/ctoa/scripts/ops/gs-startup-sequence.sh
/opt/ctoa/scripts/ops/gs-coherence-check.sh
/opt/ctoa/scripts/ops/gs-module-inject.sh
/opt/ctoa/scripts/ops/gs-api-validator.py
/opt/ctoa/deploy/vps/systemd/ctoa-gs-reset.service
/opt/ctoa/deploy/vps/systemd/ctoa-gs-reset.timer
"

missing=0
for f in $required_files; do
    if [ ! -f "$f" ]; then
        echo "[InstallGsResetFromBranch] MISSING: $f"
        missing=1
    fi
done

if [ "$missing" -ne 0 ]; then
    echo "[InstallGsResetFromBranch] ERROR: required GS files missing in ref __SOURCE_REF__"
    exit 1
fi

chmod +x /opt/ctoa/scripts/ops/gs-reset.sh
chmod +x /opt/ctoa/scripts/ops/gs-startup-sequence.sh
chmod +x /opt/ctoa/scripts/ops/gs-coherence-check.sh
chmod +x /opt/ctoa/scripts/ops/gs-module-inject.sh
chmod +x /opt/ctoa/scripts/ops/gs-api-validator.py
cp /opt/ctoa/deploy/vps/systemd/ctoa-gs-reset.service /etc/systemd/system/
cp /opt/ctoa/deploy/vps/systemd/ctoa-gs-reset.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable ctoa-gs-reset.timer
systemctl restart ctoa-gs-reset.timer
systemctl list-timers ctoa-gs-reset.timer --no-pager
echo "[InstallGsResetFromBranch] GS reset timer armed from ref __SOURCE_REF__"
'@

    $remoteScript = $remoteScript.Replace('__SOURCE_REF__', $safeRef)
    Invoke-SshScript $remoteScript
    }

    'EnsureGsEnvKeys' {
        # Secure one-command setup of missing .env keys required by GS coherence.
        # Recommended input path:
        #   $env:CTOA_OPENAI_API_KEY = '...'
        # Optional:
        #   $env:CTOA_GITHUB_PAT = '...'

        $openAiKey = Get-OptionalEnv 'CTOA_OPENAI_API_KEY' ''
        if ([string]::IsNullOrWhiteSpace($openAiKey)) {
            throw 'Missing local env var CTOA_OPENAI_API_KEY. Set it and rerun -Action EnsureGsEnvKeys.'
        }

        $githubPat = Get-OptionalEnv 'CTOA_GITHUB_PAT' ''

        $safeOpenAi = $openAiKey -replace "'", "'\''"
        $safeGithubPat = $githubPat -replace "'", "'\''"

        $remoteScript = @'
set -e
ENV_FILE="/opt/ctoa/.env"

mkdir -p /opt/ctoa
touch "$ENV_FILE"
chmod 600 "$ENV_FILE" 2>/dev/null || true

upsert_if_missing_or_empty() {
    local key="$1"
    local value="$2"

    if grep -q "^${key}=" "$ENV_FILE"; then
        current="$(grep "^${key}=" "$ENV_FILE" | head -n 1 | cut -d'=' -f2-)"
        if [ -n "$current" ]; then
            echo "[EnsureGsEnvKeys] ${key} already set."
            return 0
        fi
        sed -i "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
        echo "[EnsureGsEnvKeys] ${key} updated from empty value."
        return 0
    fi

    echo "${key}=${value}" >> "$ENV_FILE"
    echo "[EnsureGsEnvKeys] ${key} added."
}

upsert_if_missing_or_empty OPENAI_API_KEY '__OPENAI_KEY__'

if [ -n '__GITHUB_PAT__' ]; then
    upsert_if_missing_or_empty GITHUB_PAT '__GITHUB_PAT__'
fi

echo "[EnsureGsEnvKeys] Completed key setup."
'@

        $remoteScript = $remoteScript.Replace('__OPENAI_KEY__', $safeOpenAi)
        $remoteScript = $remoteScript.Replace('__GITHUB_PAT__', $safeGithubPat)
        Invoke-SshScript $remoteScript
    }

    'TriggerGsResetNow' {
        # Manual full GS cycle now (emergency/test)
        Write-Host '[GS-RESET] This will stop and restart all CTOA services on VPS.' -ForegroundColor Yellow
        $confirm = Read-Host 'Type YES to confirm'
        if ($confirm -ne 'YES') { Write-Host 'Aborted.'; return }
        Invoke-SshCommand 'bash /opt/ctoa/scripts/ops/gs-reset.sh 2>&1 | tail -120'
    }

    'TailGsReset' {
        Invoke-SshCommand 'mkdir -p /opt/ctoa/logs; touch /opt/ctoa/logs/gs-reset.log; tail -n 100 -f /opt/ctoa/logs/gs-reset.log'
    }

    'GsStatus' {
        Invoke-SshScript @'
set -e
echo === GS Timer Status ===
systemctl list-timers ctoa-gs-reset.timer --no-pager
echo
echo === Last GS Reset Log tail 40 ===
tail -n 40 /opt/ctoa/logs/gs-reset.log 2>/dev/null || true
echo
echo === Last Inject Log tail 20 ===
tail -n 20 /opt/ctoa/logs/gs-inject.log 2>/dev/null || true
echo
echo === Active CTOA services ===
systemctl list-units ctoa-* --no-pager --no-legend --state=active
'@
    }

        'GsProvisionDbContainer' {
                # Provision ctoa-db container required by ctoa-db.service.
                Invoke-SshScript @'
set -e
cd /opt/ctoa

if command -v docker-compose >/dev/null 2>&1; then
    DC="docker-compose"
elif docker compose version >/dev/null 2>&1; then
    DC="docker compose"
else
    DC=""
fi

if [ -n "$DC" ]; then
    echo "[GsProvisionDbContainer] Using compose: $DC"
    $DC -f deploy/vps/docker-compose.yml up -d ctoa-db
else
    echo "[GsProvisionDbContainer] Compose not available, using docker run fallback"

    ENV_FILE="/opt/ctoa/.env"
    touch "$ENV_FILE"

    # shellcheck disable=SC1090
    set -a; . "$ENV_FILE"; set +a

    DB_NAME="${DB_NAME:-ctoa}"
    DB_USER="${DB_USER:-ctoa}"
    DB_PASSWORD="${DB_PASSWORD:-}"

    if [ -z "$DB_PASSWORD" ]; then
        DB_PASSWORD="$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 28)"
        if grep -q '^DB_PASSWORD=' "$ENV_FILE"; then
            sed -i "s|^DB_PASSWORD=.*|DB_PASSWORD=$DB_PASSWORD|" "$ENV_FILE"
        else
            echo "DB_PASSWORD=$DB_PASSWORD" >> "$ENV_FILE"
        fi
        echo "[GsProvisionDbContainer] DB_PASSWORD generated and saved to /opt/ctoa/.env"
    fi

    docker rm -f ctoa-db >/dev/null 2>&1 || true
    docker run -d \
        --name ctoa-db \
        --restart unless-stopped \
        -e POSTGRES_DB="$DB_NAME" \
        -e POSTGRES_USER="$DB_USER" \
        -e POSTGRES_PASSWORD="$DB_PASSWORD" \
        -p 127.0.0.1:5432:5432 \
        -v ctoa_pgdata:/var/lib/postgresql/data \
        -v /opt/ctoa/deploy/vps/db/init.sql:/docker-entrypoint-initdb.d/init.sql:ro \
        postgres:16-alpine >/dev/null
fi

echo "[GsProvisionDbContainer] Container list:"
docker ps -a --format 'table {{.Names}}\t{{.Status}}' | sed -n '1,30p'

echo "[GsProvisionDbContainer] ctoa-db.service status:"
systemctl restart ctoa-db.service || true
systemctl status ctoa-db.service --no-pager -l | sed -n '1,80p'
'@
        }

    'GsCoherence' {
        Invoke-SshCommand 'bash /opt/ctoa/scripts/ops/gs-coherence-check.sh 2>&1'
    }

    'GsModuleInject' {
        Invoke-SshCommand 'bash /opt/ctoa/scripts/ops/gs-module-inject.sh 2>&1'
    }

    'GsApiValidate' {
        Invoke-SshCommand 'cd /opt/ctoa && . .venv/bin/activate && python3 scripts/ops/gs-api-validator.py 2>&1'
    }

    'ValidateSyntax' {
        Invoke-RemoteSyntaxValidation
    }
}
