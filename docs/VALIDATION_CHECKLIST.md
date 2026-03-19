# CTOA Systems Validation Checklist

**Last Updated:** 2026-03-12T20:05:12+00:00

## Mobile QA Validation (2026-03-19)

- [x] Menu and mobile layout readability/tap flow validated (Samsung Note 10+ class viewport)
- [x] Owner login via modal with API base validated
- [x] Owner settings save + persist-after-refresh validated
- [x] Parking Pomyslow add/remove and counter transitions validated
- [x] Operator restrictions validated (`showPrices` and `reset localStorage` controls disabled)
- [x] Overall mobile QA status: PASS

## Pre-Deployment Checks

### Code Quality
- [ ] `runner.py` syntax validated (mypy/pylint)
- [ ] `runner.py` all functions have docstrings
- [ ] No hardcoded secrets in any files
- [ ] Git secrets scan passes
- [ ] All imports resolved, no circular dependencies

### Configuration Validation
- [ ] Active backlog file is valid YAML
- [ ] All task IDs in backlog are unique
- [ ] Deliverables paths are correct (relative to repo root)
- [ ] VPS systemd service files are syntactically valid
- [ ] Environment variables documented in `.env.example`

### Functionality Tests
- [ ] `runner.py tick` completes without error
- [ ] Task state transitions work correctly
- [ ] Agent invocation completes (--agents flag)
- [ ] Report generation successful
- [ ] GitHub API connectivity via PAT token

## Post-Deployment Checks  

### Service Health (after VPS deployment)

**ctoa-runner.service/timer:**
- [ ] Timer is enabled: `sudo systemctl is-enabled ctoa-runner.timer`
- [ ] Timer last executed: `sudo systemctl status ctoa-runner.timer`
- [ ] No failed runs: `sudo journalctl -u ctoa-runner -n 20`
- [ ] State file updated: `ls -la /opt/ctoa/runtime/task-state.yaml`
- [ ] Last tick timestamp recent (within 1 hour)

**ctoa-report.service/timer:**
- [ ] Timer is enabled and active
- [ ] Report publishes to GitHub Issue #1
- [ ] No authentication errors in logs
- [ ] Rate limit not exceeded (check GitHub API headers)

**ctoa-health-live.service:**
- [ ] Service is running: `sudo systemctl is-active ctoa-health-live`
- [ ] Health endpoint responds: `curl http://localhost:9999/health`
- [ ] No restart loops in journal

**ctoa-retention-cleanup.timer:**
- [ ] Timer is enabled
- [ ] Cleanup script executes successfully
- [ ] No permission errors
- [ ] Disk space trending downward (if cleanup needed)

### Disk Space
- [ ] Root partition < 80% utilization
- [ ] `/opt/ctoa` directory < 500MB total
- [ ] Logs directory < 100MB
- [ ] No orphaned files > 100MB

### Network Connectivity
- [ ] SSH connectivity from local machine to VPS
- [ ] GitHub API reachable over HTTPS
- [ ] DNS resolution working (nslookup github.com)
- [ ] No firewall blocks on port 443 (HTTPS)

### Monitoring & Alerting
- [ ] Live status issue #1 updating hourly
- [ ] No "Failed to update issue" errors
- [ ] Health trend data accumulating
- [ ] Alert thresholds configured and active

## Runtime Validation (daily)

Run these checks daily to ensure system health:

```bash
# SSH to VPS
ssh -i ~/.ssh/ctoa_vps_ed25519 ctoa@46.225.110.52

# Check services status
sudo systemctl status ctoa-runner.timer ctoa-report.timer

# View latest activity
cd /opt/ctoa && tail -20 logs/runner.log

# Validate state file
python3 runner/runner.py report | head -20

# Check disk
df -h / && du -sh /opt/ctoa

# View live status
curl http://localhost:9999/health 2>/dev/null | jq .
```

## Failure Response

### If ctoa-runner.timer stops:
1. Check journal: `sudo journalctl -u ctoa-runner -n 50`
2. Verify backlog file exists and is valid YAML
3. Check disk space: `df -h /`
4. Restart: `sudo systemctl restart ctoa-runner.timer`

### If GitHub API fails:
1. Verify PAT token not expired
2. Check GITHUB_PAT is set: `env | grep GITHUB`
3. Test connectivity: `python3 runner/runner.py report`
4. If rate-limited, wait 1 hour and retry

### If report not updating:
1. Check issue number in CTOA_LIVE_ISSUE_TITLE
2. Verify issue exists and is not locked
3. Check GitHub API rate limits
4. View error: `sudo journalctl -u ctoa-report -n 20`

## References
- [ARCHITECTURE.md](ARCHITECTURE.md) - Overall system design
- [SETUP.md](../deploy/vps/SETUP.md) - VPS environment setup
- [runner.py](../runner/runner.py) - Main orchestration logic

