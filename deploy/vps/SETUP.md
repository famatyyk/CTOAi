# VPS Setup & Deployment Guide

Deploy CTOA AI Toolkit to the production VPS server (46.225.110.52).

---

## VPS Specs

- **Host:** 46.225.110.52
- **OS:** Ubuntu 22.04 LTS
- **User:** root
- **SSH Key:** `ctoa_vps_ed25519` (Ed25519 format)
- **Python:** 3.10+ required
- **Storage:** 20 GB SSD
- **Network:** Public IP, port 22 (SSH) open

---

## Quick Start (First Deploy)

### 1. SSH Access

**From local machine:**
```bash
# Test connection
ssh -i ~/.ssh/ctoa_vps_ed25519 root@46.225.110.52 -o ConnectTimeout=5

# Key should have 600 permissions
chmod 600 ~/.ssh/ctoa_vps_ed25519
```

### 2. Provision VPS (First Time)

**Upload provisioning script:**
```bash
scp -i ~/.ssh/ctoa_vps_ed25519 scripts/ops/vps-provision.sh root@46.225.110.52:/tmp/
ssh -i ~/.ssh/ctoa_vps_ed25519 root@46.225.110.52 "bash /tmp/vps-provision.sh"
```

Or via PowerShell:
```powershell
scripts/ops/ctoa-vps.ps1 -Action Setup24x7
```

**What provisioning does:**
- Updates system packages
- Installs Python 3.11, pip, virtualenv
- Installs git, curl, nano
- Creates `/opt/ctoa` directory
- Sets up systemd services
- Configures log rotation

### 3. Clone & Setup

```bash
ssh -i ~/.ssh/ctoa_vps_ed25519 root@46.225.110.52 << 'EOF'
cd /opt/ctoa
git clone https://github.com/famatyyk/CTOAi.git .
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
mkdir -p logs runtime
EOF
```

### 4. Configure Environment

Create `.env` file on VPS:
```bash
ssh -i ~/.ssh/ctoa_vps_ed25519 root@46.225.110.52 << 'EOF'
cat > /opt/ctoa/.env << 'ENVFILE'
# GitHub
GITHUB_PAT=your_token_here

# AI Services
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
AZURE_OPENAI_KEY=xxxxxxxxxxxxxxxxxxxx

# Agent Configuration
CTOA_MAX_CONCURRENT_AGENTS=10
CTOA_LOG_LEVEL=INFO
ENVFILE

chmod 600 /opt/ctoa/.env
EOF
```

### 5. Setup Systemd Services

```bash
ssh -i ~/.ssh/ctoa_vps_ed25519 root@46.225.110.52 << 'EOF'
sudo cp deploy/vps/systemd/ctoa-runner.service /etc/systemd/system/
sudo cp deploy/vps/systemd/ctoa-runner.timer /etc/systemd/system/
sudo cp deploy/vps/systemd/ctoa-report.service /etc/systemd/system/
sudo cp deploy/vps/systemd/ctoa-report.timer /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable --now ctoa-runner.timer
sudo systemctl enable --now ctoa-report.timer

# Verify
systemctl status ctoa-runner.timer
systemctl status ctoa-report.timer
EOF
```

---

## Deployment Workflow

### Option A: Automated Deployment (Recommended)

```powershell
# Windows (bootstrap + sync + systemd timers)
scripts/ops/ctoa-vps.ps1 -Action Setup24x7
```

**What happens:**
1. Validates local environment
2. Syncs repository on VPS to `main`
3. Recreates venv and installs `runner/requirements.txt`
4. Installs/refreshes systemd units
5. Enables timers/services and verifies their status

### Option B: Manual Deployment

**Pull latest code:**
```bash
ssh -i ~/.ssh/ctoa_vps_ed25519 root@46.225.110.52 << 'EOF'
cd /opt/ctoa
git pull origin main
source .venv/bin/activate
pip install --upgrade -r requirements.txt
EOF
```

**Restart services:**
```bash
ssh -i ~/.ssh/ctoa_vps_ed25519 root@46.225.110.52 << 'EOF'
systemctl restart ctoa-runner
systemctl restart ctoa-report
systemctl status ctoa-runner
EOF
```

---

## Monitoring

### Check Service Status

```bash
ssh -i ~/.ssh/ctoa_vps_ed25519 root@46.225.110.52 << 'EOF'
systemctl status ctoa-runner.timer
systemctl status ctoa-report.timer

# View recent logs
journalctl -u ctoa-runner.service -n 50 --no-pager
journalctl -u ctoa-report.service -n 50 --no-pager
EOF
```

### View Application Logs

```bash
ssh -i ~/.ssh/ctoa_vps_ed25519 root@46.225.110.52 << 'EOF'
tail -100f /var/log/ctoa/agent-execution.log
tail -100f /var/log/ctoa/errors.log
ls -lh /var/log/ctoa/
EOF
```

### Monitor Resources

```bash
ssh -i ~/.ssh/ctoa_vps_ed25519 root@46.225.110.52 << 'EOF'
free -h  # Memory
df -h    # Disk space
top -b -n 1 | head -20  # Processes
EOF
```

---

## Manual Commands

Run directly on VPS:

```bash
ssh -i ~/.ssh/ctoa_vps_ed25519 root@46.225.110.52 << 'EOF'
cd /opt/ctoa
source .venv/bin/activate

# Execute agent tick
python3 runner/runner.py tick

# Generate report
python3 runner/runner.py report
python3 runner/runner.py report --publish

# Approve task
python3 runner/runner.py approve --task CTOA-001
EOF
```

---

## Troubleshooting

### Connection Issues

```bash
# Test SSH with verbose output
ssh -i ~/.ssh/ctoa_vps_ed25519 -v root@46.225.110.52
```

### Service Won't Start

```bash
ssh -i ~/.ssh/ctoa_vps_ed25519 root@46.225.110.52 << 'EOF'
systemctl restart ctoa-runner
journalctl -u ctoa-runner -n 100  # Show last 100 lines
EOF
```

### Missing Dependencies

```bash
ssh -i ~/.ssh/ctoa_vps_ed25519 root@46.225.110.52 << 'EOF'
cd /opt/ctoa
source .venv/bin/activate
pip list --format=freeze
pip install --upgrade -r requirements.txt
EOF
```

### Disk Space

```bash
ssh -i ~/.ssh/ctoa_vps_ed25519 root@46.225.110.52 << 'EOF'
du -sh /opt/ctoa/*
du -sh /var/log/ctoa/

# Clean old logs (>30 days)
find /var/log/ctoa/ -type f -mtime +30 -delete
EOF
```

---

## Rollback

If deployment causes issues:

```bash
ssh -i ~/.ssh/ctoa_vps_ed25519 root@46.225.110.52 << 'EOF'
cd /opt/ctoa
git log --oneline -10

# Revert to previous commit
git reset --hard HEAD~1
source .venv/bin/activate
pip install --upgrade -r requirements.txt

systemctl restart ctoa-runner
EOF
```

Or via script:
```powershell
# No dedicated rollback action in ctoa-vps.ps1.
# Use manual rollback section above on VPS.
```

---

## Backup

### Code & Configuration

```bash
ssh -i ~/.ssh/ctoa_vps_ed25519 root@46.225.110.52 << 'EOF'
tar -czf /tmp/ctoa-backup-$(date +%Y%m%d).tar.gz \
  /opt/ctoa/.env \
  /opt/ctoa/scoring/ \
  /opt/ctoa/agents/ \
  /opt/ctoa/runner/
EOF

# Copy to local (from your machine)
scp -i ~/.ssh/ctoa_vps_ed25519 root@46.225.110.52:/tmp/ctoa-backup-*.tar.gz ~/backups/
```

### Logs

```bash
ssh -i ~/.ssh/ctoa_vps_ed25519 root@46.225.110.52 << 'EOF'
tar -czf /tmp/ctoa-logs-$(date +%Y%m%d).tar.gz /var/log/ctoa/
EOF
```

---

## Performance Tuning

### Increase Concurrent Agents

Edit `/etc/systemd/system/ctoa-runner.service`:
```ini
[Service]
Environment="CTOA_MAX_CONCURRENT_AGENTS=20"
```

Then:
```bash
systemctl daemon-reload
systemctl restart ctoa-runner
```

### Adjust Log Rotation

Edit `/etc/logrotate.d/ctoa`:
```
/var/log/ctoa/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0644 root root
}
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Setup/Sync VPS | `scripts/ops/ctoa-vps.ps1 -Action Setup24x7` |
| Status | `ssh -i ... systemctl status ctoa-runner.timer` |
| Logs | `ssh -i ... tail -f /var/log/ctoa/agent-execution.log` |
| Restart | `ssh -i ... systemctl restart ctoa-runner` |
| Enable live health stream | `scripts/ops/ctoa-vps.ps1 -Action EnableLiveHealth` |
| Tail live health stream | `scripts/ops/ctoa-vps.ps1 -Action TailLiveHealth` |
| SSH | `ssh -i ~/.ssh/ctoa_vps_ed25519 root@46.225.110.52` |

---

## See Also

- [Local Development](../../docs/LOCAL_SETUP.md)
- [GitHub Actions CI](../../.github/workflows/)
- [Architecture](../../docs/ARCHITECTURE.md)
- [README](../../README.md)

## 6. VS Code task env vars
Before using the local VS Code VPS tasks, set these environment variables on your workstation:

```powershell
$env:CTOA_VPS_HOST="46.225.110.52"
$env:CTOA_VPS_USER="root"
$env:CTOA_VPS_KEY_PATH="C:\Users\zycie\ctoa_vps_key"
# Optional, only for the task that writes /opt/ctoa/.env on the VPS:
$env:CTOA_GITHUB_PAT="YOUR_GITHUB_PERSONAL_ACCESS_TOKEN"
```

The repository should never contain embedded SSH keys or PAT values in `.vscode/tasks.json`.

If a PAT was exposed, remove the local variable before creating a replacement:

```powershell
[Environment]::SetEnvironmentVariable("CTOA_GITHUB_PAT", $null, "User")
Remove-Item Env:CTOA_GITHUB_PAT -ErrorAction SilentlyContinue
```

## 7. PAT Usage Audit Trail

To enable audit logging on the VPS when PAT is used:

```bash
# On VPS (46.225.110.52):
mkdir -p /opt/ctoa/logs
chmod 700 /opt/ctoa/logs
touch /opt/ctoa/logs/pat-audit.log
chmod 600 /opt/ctoa/logs/pat-audit.log

# Add audit hook to /opt/ctoa/.env:
cat >> /opt/ctoa/.env << 'EOF'

# Audit logging
export CTOA_AUDIT_LOG=/opt/ctoa/logs/pat-audit.log
_log_pat_usage() {
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] PAT sourced by PID=$PPID User=$USER Host=$(hostname)" >> $CTOA_AUDIT_LOG
}
_log_pat_usage
EOF
```

Each use of `GITHUB_PAT` via wrapper or runner will be audited in `/opt/ctoa/logs/pat-audit.log`.

After generating a fresh PAT manually in GitHub, set it locally:

```powershell
[Environment]::SetEnvironmentVariable("CTOA_GITHUB_PAT", "YOUR_NEW_GITHUB_PAT", "User")
$env:CTOA_GITHUB_PAT = "YOUR_NEW_GITHUB_PAT"
```

## 8. VPS Health Monitoring

Two monitoring modes are available:

1. **Hourly dashboard updates** (Issue #2 comments):

```bash
ssh -i ~/.ssh/ctoa_vps_ed25519 root@46.225.110.52 \
  "cd /opt/ctoa && . .venv/bin/activate && python3 runner/health_metrics.py --publish"
```

2. **Continuous live stream** (systemd service, every 10s):

```powershell
scripts/ops/ctoa-vps.ps1 -Action EnableLiveHealth
scripts/ops/ctoa-vps.ps1 -Action TailLiveHealth
```

Live stream writes to: `/opt/ctoa/logs/health-live.log`

Metrics include CPU, memory, disk and process checks; alerts are emitted when thresholds are exceeded.
