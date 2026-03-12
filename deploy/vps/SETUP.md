# VPS Setup (Ubuntu)

## 1. Prepare host
1. Clone repo to `/opt/ctoa`
2. Install Python 3.10+
3. Create virtual environment

```bash
cd /opt/ctoa
python3 -m venv .venv
source .venv/bin/activate
pip install -r runner/requirements.txt
mkdir -p logs runtime
```

## 2. Configure GitHub token
Create `/opt/ctoa/.env`:

```bash
GITHUB_PAT=YOUR_GITHUB_PERSONAL_ACCESS_TOKEN
```

Token scope minimum: `repo` (private/public repo update issues).

## 3. Install systemd units
```bash
sudo cp deploy/vps/systemd/ctoa-runner.service /etc/systemd/system/
sudo cp deploy/vps/systemd/ctoa-runner.timer /etc/systemd/system/
sudo cp deploy/vps/systemd/ctoa-report.service /etc/systemd/system/
sudo cp deploy/vps/systemd/ctoa-report.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ctoa-runner.timer
sudo systemctl enable --now ctoa-report.timer
```

## 4. Verify
```bash
systemctl status ctoa-runner.timer
systemctl status ctoa-report.timer
journalctl -u ctoa-runner.service -n 50 --no-pager
journalctl -u ctoa-report.service -n 50 --no-pager
```

## 5. Manual commands
```bash
python3 runner/runner.py tick
python3 runner/runner.py report
python3 runner/runner.py report --publish
python3 runner/runner.py approve --task CTOA-001
```

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

After generating a fresh PAT manually in GitHub, set it locally:

```powershell
[Environment]::SetEnvironmentVariable("CTOA_GITHUB_PAT", "YOUR_NEW_GITHUB_PAT", "User")
$env:CTOA_GITHUB_PAT = "YOUR_NEW_GITHUB_PAT"
```
