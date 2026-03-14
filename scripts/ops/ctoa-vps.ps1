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
        'ShowServerStatus',
        'ShowScoutDetails',
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
        'GsApiValidate'
    )]
    [string]$Action
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

function Invoke-SshCommand([string]$Cmd) {
    $t = Get-RemoteTarget; $k = Get-KeyPath
    & ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -i $k $t $Cmd
}

function Invoke-SshScript([string]$Script) {
    $t = Get-RemoteTarget; $k = Get-KeyPath
    ($Script -replace "`r`n","`n") | & ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -i $k $t 'bash -s'
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
pip install -r runner/requirements.txt
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
systemctl enable --now ctoa-lab-runner.timer
systemctl enable --now ctoa-mythibia-news-watcher.timer
systemctl enable --now ctoa-mythibia-news-api.service
'@
}

switch ($Action) {
    'Verify'              { Invoke-SshCommand 'echo CONNECTED; hostname; whoami' }
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
}
