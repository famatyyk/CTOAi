# CTOA Systems Validation Checklist

**Last Updated:** 2026-05-15T00:00:00+00:00

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


## Sprint-0 Integration Validation

### Full Local Stack
- [ ] `CTOA: Sprint-0 Compose Up (Full Stack)` completed
- [ ] `CTOA: Sprint-0 Alembic Upgrade Head` completed
- [ ] `CTOA: Sprint-0 Enqueue Worker Tick` completed
- [ ] `CTOA: Sprint-0 Validate Integration Pack` completed

### Observability
- [ ] Prometheus healthy: `http://127.0.0.1:9090/-/healthy`
- [ ] Loki ready: `http://127.0.0.1:3100/ready`
- [ ] Metrics exposed by app: `http://127.0.0.1:8787/metrics`

### Worker + Queue
- [ ] Redis queue accepts jobs (`scripts/ops/queue_enqueue_job.py`)
- [ ] Worker processes `orchestrator.tick` jobs
- [ ] Worker result list (`ctoa:jobs:results`) is populated
## Sprint-048 Release Gate OneShot (Default Pre-Push)

Use this as the default local pre-push chain for Sprint-048 governance safety.

- [x] `CTOA: Run All Tests` completed (non-e2e suite)
- [x] `CTOA: Sprint-048 Validate` completed (`runtime/ci-artifacts/sprint-048-validation.json`)
- [x] `CTOA: Launch Pack` gate completed (`launch_allowed`)
- [x] `CTOA: Core Guard Check` completed (`core integrity check PASSED`)

Reference one-shot task:
- [x] `CTOA: Release Gate OneShot`

## Sprint-049 Approval Publish Completion Path

Use this deterministic operator flow to close tasks from `WAITING_APPROVAL` to `RELEASED`.

- [x] Set backlog scope for runner session: `CTOA_BACKLOG_FILE=workflows/backlog-sprint-049.yaml`
- [x] Inspect approval queue: `python runner/runner.py report`
- [x] Confirm `## Waiting Approval` is readable and parseable in report output
- [x] If tasks are pending approval, release explicitly by task id: `python runner/runner.py approve --task CTOA-XXX`
- [x] Re-run report and verify task moved to `RELEASED` and approval queue reflects the change

Current verification snapshot (2026-05-24):

- Report generated successfully for sprint-049 backlog
- `WAITING_APPROVAL: 0` and `## Waiting Approval: none`
- No runtime crash when reading approval section
