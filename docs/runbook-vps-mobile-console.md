# VPS Mobile Console Ops Runbook

## 1. Login Path

From Windows PowerShell:

```powershell
& C:\Windows\System32\OpenSSH\ssh.exe -i C:\Users\zycie\.ssh\ctoa_vps_auto_ed25519 ctoa-admin@116.202.96.250
```

Privilege escalation (when required):

```bash
sudo -n /bin/bash
```

## 2. Health-Check Flow

Run one-shot validation from repository root:

```powershell
$env:CTOA_VPS_HOST='116.202.96.250'
$env:CTOA_VPS_USER='ctoa-admin'
$env:CTOA_VPS_KEY_PATH='C:\Users\zycie\.ssh\ctoa_vps_auto_ed25519'
& .\scripts\ops\ctoa-vps.ps1 -Action HealthCheckOneShot
```

Direct service checks on VPS:

```bash
sudo -n systemctl status ctoa-mobile-console --no-pager
sudo -n systemctl status ctoa-runner.timer --no-pager
sudo -n systemctl status ctoa-report.timer --no-pager
sudo -n fail2ban-client status sshd
```

## 3. Restart Flow

```bash
sudo -n systemctl restart ctoa-mobile-console
sudo -n systemctl restart ctoa-runner.timer ctoa-report.timer
sudo -n systemctl status ctoa-mobile-console --no-pager
```

## 4. Rollback Flow

List available backups:

```bash
sudo -n find /opt/ctoa/backups -type f -maxdepth 2 | sort
```

Restore config bundle:

```bash
sudo -n tar -xzf /opt/ctoa/backups/config/ctoa-config-YYYYmmddTHHMMSSZ.tar.gz -C /
sudo -n systemctl daemon-reload
sudo -n systemctl restart ctoa-mobile-console ctoa-runner.timer ctoa-report.timer
```

Restore PostgreSQL dump:

```bash
gunzip -c /opt/ctoa/backups/db/ctoa-db-YYYYmmddTHHMMSSZ.sql.gz | sudo -n psql -h 127.0.0.1 -U ctoa_mobile -d ctoa_mobile
```

## 5. Backup Verification

```bash
sudo -n systemctl status ctoa-backup.timer --no-pager
sudo -n systemctl start ctoa-backup.service
sudo -n tail -n 80 /opt/ctoa/logs/backup-nightly.log
```
