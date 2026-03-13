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
        'ShowScoutDetails'
    )]
    [string]$Action
)

$ErrorActionPreference = 'Stop'

function Get-RequiredEnv([string]$Name) {
    $value = [Environment]::GetEnvironmentVariable($Name)
    if ([string]::IsNullOrWhiteSpace($value)) { throw "Missing env var: $Name" }
    return $value
}

function Get-OptionalEnv([string]$Name, [string]$DefaultValue) {
    $value = [Environment]::GetEnvironmentVariable($Name)
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
        $filterClause = ''
        if (-not [string]::IsNullOrWhiteSpace($filterUrl)) {
            $safeFilterUrl = $filterUrl -replace "'", "''"
            $filterClause = "WHERE s.url = '$safeFilterUrl'"
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
}
