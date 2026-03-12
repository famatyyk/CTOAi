param(
    [Parameter(Mandatory = $true)]
    [ValidateSet(
        'Verify',
        'WhoAmI',
        'Setup24x7',
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
    $hostName = Get-RequiredEnv 'CTOA_VPS_HOST'
    $userName = [Environment]::GetEnvironmentVariable('CTOA_VPS_USER')
    if ([string]::IsNullOrWhiteSpace($userName)) {
        $userName = 'root'
    }
    return "$userName@$hostName"
}

function Get-KeyPath() {
    $keyPath = Get-RequiredEnv 'CTOA_VPS_KEY_PATH'
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
systemctl daemon-reload
systemctl enable --now ctoa-runner.timer
systemctl enable --now ctoa-report.timer
systemctl status ctoa-runner.timer --no-pager -l | head -n 12
systemctl status ctoa-report.timer --no-pager -l | head -n 12
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
        $script = @"
set -e
cat > /opt/ctoa/.env <<'EOF'
GITHUB_PAT=$pat
EOF
grep '^GITHUB_PAT=' /opt/ctoa/.env | sed 's/=.*/=***set***/'
"@
        Invoke-SshScript $script
    }
    'ReportViaServiceEnv' {
        Invoke-SshCommand 'bash -lc "systemctl restart ctoa-report.service; systemctl status ctoa-report.service --no-pager -l | head -n 20; journalctl -u ctoa-report.service -n 25 --no-pager"'
    }
    'PublishWithSourcedEnv' {
        Invoke-SshScript @'
set -e
cd /opt/ctoa
set -a
. /opt/ctoa/.env
set +a
. .venv/bin/activate
python3 runner/runner.py report --publish
sed -n '1,2p' /opt/ctoa/.env | sed 's/=.*$/=***set***/'
if [ -f /opt/ctoa/logs/runner.log ]; then
    tail -n 20 /opt/ctoa/logs/runner.log
else
    echo runner.log not present
fi
'@
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