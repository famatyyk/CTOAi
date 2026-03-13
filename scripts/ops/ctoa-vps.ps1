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
        'ReportErrorDetails'
    )]
    [string]$Action
)

$ErrorActionPreference = 'Stop'

function Get-RequiredEnv([string]$Name) {
    $value = [Environment]::GetEnvironmentVariable($Name)
    if ([string]::IsNullOrWhiteSpace($value)) {
        throw "Missing required environment variable: $Name"
    }
    return $value
}

function Get-RemoteTarget() {
    $hostName = [Environment]::GetEnvironmentVariable('CTOA_VPS_HOST')
    if ([string]::IsNullOrWhiteSpace($hostName)) {
        $hostName = '46.225.110.52'
    }
    $userName = [Environment]::GetEnvironmentVariable('CTOA_VPS_USER')
    if ([string]::IsNullOrWhiteSpace($userName)) {
        $userName = 'root'
    }
    return "$userName@$hostName"
}

function Get-KeyPath() {
    $keyPath = [Environment]::GetEnvironmentVariable('CTOA_VPS_KEY_PATH')
    if ([string]::IsNullOrWhiteSpace($keyPath)) {
        $keyPath = Join-Path $env:USERPROFILE '.ssh\ctoa_vps_ed25519'
    }
    if (-not (Test-Path $keyPath)) {
        throw "SSH key not found: $keyPath"
    }
    return $keyPath
}

function Invoke-SshCommand([string]$RemoteCommand) {
    $target = Get-RemoteTarget
    $keyPath = Get-KeyPath
    & ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -i $keyPath $target $RemoteCommand
}

function Invoke-SshScript([string]$ScriptText) {
    $target = Get-RemoteTarget
    $keyPath = Get-KeyPath
    $normalized = $ScriptText -replace "`r`n", "`n"
    $normalized | & ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -i $keyPath $target "bash -s"
}

function Get-SetupScript() {
    return @'
set -e
export DEBIAN_FRONTEND=noninteractive
if ! command -v git >/dev/null 2>&1; then apt-get update -y; apt-get install -y git; fi
if ! command -v python3 >/dev/null 2>&1; then apt-get update -y; apt-get install -y python3 python3-venv python3-pip; fi
if [ -d /opt/ctoa/.git ]; then
  cd /opt/ctoa
  git fetch --all
  git checkout main
  git pull --ff-only
else
  rm -rf /opt/ctoa
  git clone https://github.com/famatyyk/CTOAi.git /opt/ctoa
fi
cd /opt/ctoa
python3 -m venv .venv
. .venv/bin/activate
pip install -r runner/requirements.txt
mkdir -p logs runtime
if [ ! -f /opt/ctoa/.env ]; then
  printf 'GITHUB_PAT=\n' > /opt/ctoa/.env
fi
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
systemctl status ctoa-runner.timer --no-pager -l | head -n 12
systemctl status ctoa-report.timer --no-pager -l | head -n 12
systemctl status ctoa-health-live.service --no-pager -l | head -n 20
systemctl status ctoa-retention-cleanup.timer --no-pager -l | head -n 12
systemctl status ctoa-mobile-token-rotation.timer --no-pager -l | head -n 12
systemctl status ctoa-lab-runner.timer --no-pager -l | head -n 12
systemctl status ctoa-mythibia-news-watcher.timer --no-pager -l | head -n 12
systemctl status ctoa-mythibia-news-api.service --no-pager -l | head -n 20
'@
}

switch ($Action) {
    'Verify' {
        Invoke-SshCommand 'echo CONNECTED; hostname; whoami'
    }
    'WhoAmI' {
        Invoke-SshCommand 'whoami'
    }
    'Setup24x7' {
        $script = Get-SetupScript
        Invoke-SshScript $script
    }
    'EnableLiveHealth' {
        Invoke-SshScript @'
set -e
mkdir -p /opt/ctoa/logs
cat > /etc/systemd/system/ctoa-health-live.service << 'UNIT'
[Unit]
Description=CTOA live health monitor stream
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/ctoa
Environment="PYTHONUNBUFFERED=1"
EnvironmentFile=-/opt/ctoa/.env
ExecStart=/opt/ctoa/.venv/bin/python3 /opt/ctoa/runner/health_metrics.py --watch --interval 10 --no-publish --disk-auto-cleanup --disk-cleanup-threshold 92 --disk-cleanup-cooldown 3600
Restart=always
RestartSec=2
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
    'TailLiveHealth' {
        Invoke-SshCommand 'tail -n 80 -f /opt/ctoa/logs/health-live.log'
    }
    'ValidateServices' {
                Invoke-SshScript @'
set -e
systemctl start ctoa-runner.service
systemctl start ctoa-report.service || true
systemctl status ctoa-runner.service --no-pager -l | head -n 12
systemctl status ctoa-report.service --no-pager -l | head -n 20
if [ -f /opt/ctoa/logs/runner.log ]; then
    tail -n 40 /opt/ctoa/logs/runner.log
else
    echo runner.log not present
fi
'@
    }
    'StabilizeReportService' {
        Invoke-SshCommand "printf 'GITHUB_PAT=\\n' > /opt/ctoa/.env; systemctl restart ctoa-report.service; systemctl status ctoa-report.service --no-pager -l | head -n 20; if [ -f /opt/ctoa/logs/runner.log ]; then tail -n 20 /opt/ctoa/logs/runner.log; else echo runner.log not present; fi"
    }
    'WriteGithubPat' {
        $pat = Get-RequiredEnv 'CTOA_GITHUB_PAT'
        Invoke-SshCommand "printf 'GITHUB_PAT=%s\n' '$pat' > /opt/ctoa/.env; echo GITHUB_PAT=***set***"
    }
    'ReportViaServiceEnv' {
        Invoke-SshCommand "systemctl restart ctoa-report.service; systemctl status ctoa-report.service --no-pager -l | head -n 20; journalctl -u ctoa-report.service -n 25 --no-pager"
    }
    'PublishWithSourcedEnv' {
        Invoke-SshCommand "cd /opt/ctoa; set -a; . /opt/ctoa/.env; set +a; . .venv/bin/activate; python3 runner/runner.py report --publish"
    }
    'InspectReportEnv' {
        Invoke-SshScript @'
set -e
grep -n '^GITHUB_PAT=' /opt/ctoa/.env | sed 's/=.*/=***set***/'
systemctl restart ctoa-report.service
journalctl -u ctoa-report.service -n 12 --no-pager
'@
    }
    'ReportErrorDetails' {
        Invoke-SshCommand 'tail -n 60 /opt/ctoa/logs/runner.log'
    }
}