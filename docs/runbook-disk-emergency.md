# Emergency Disk Response Runbook

**Last Updated:** 2026-03-12T20:05:12+00:00

## Overview
This runbook guides emergency disk space management for CTOA VPS.

## Severity Levels

### CRITICAL (>95% used)
1. Immediate impact on services
2. Execute cleanup steps
3. Page on-call engineer

### HIGH (85-95% used)
1. Monitor closely
2. Plan cleanup for next maintenance window
3. Alert team lead

### MEDIUM (75-85% used)
1. Log for review
2. Trending analysis
3. Capacity planning

## Triage Steps

1. **Check current disk usage:**
   ```bash
   df -h /
   du -sh /opt/ctoa/*
   ```

2. **Identify large files:**
   ```bash
   find /opt/ctoa -type f -size +100M | sort -k5 -rh
   ```

3. **Check log rotation:**
   ```bash
   ls -lh /opt/ctoa/logs/
   du -sh /opt/ctoa/logs/*
   ```

## Cleanup Actions

### Safe to Delete (non-critical)
- `/opt/ctoa/logs/` archives older than 30 days
- `/tmp/ctoa-*` temporary files
- `/var/tmp/runner-*` old state backups

### Review Before Deleting
- `/opt/ctoa/runtime/task-state-*.yaml` (keep last 3)
- GitHub artifact cache in `/opt/ctoa/.cache/`
- Old backlog files in `/opt/ctoa/workflows/`

### NEVER DELETE
- `/opt/ctoa/runner/` (code)
- `/opt/ctoa/.env` (configuration)
- `/opt/ctoa/workflows/backlog-*.yaml` (active backlogs)
- `/root/.ssh/` (SSH keys)

## Recovery Actions

### If disk fills to CRITICAL:

1. **Stop background services:**
   ```bash
   sudo systemctl stop ctoa-runner.timer
   sudo systemctl stop ctoa-report.timer
   ```

2. **Emergency cleanup:**
   ```bash
   rm -rf /opt/ctoa/logs/*.gz  # compressed logs
   rm -rf /tmp/ctoa-* 2>/dev/null
   ```

3. **Validate cleanup:**
   ```bash
   df -h /
   du -sh /opt/ctoa
   ```

4. **Resume services:**
   ```bash
   sudo systemctl start ctoa-runner.timer
   sudo systemctl start ctoa-report.timer
   ```

## Escalation

If cleanup doesn't free sufficient space:
1. Contact infrastructure team about expanding /opt partition
2. Consider archiving old backlogs to external storage
3. Review log rotation policies in systemd service

## References
- [ARCHITECTURE.md](ARCHITECTURE.md) - System overview
- [SETUP.md](../deploy/vps/SETUP.md) - VPS configuration
- [runner.py](../runner/runner.py) - Task orchestration

