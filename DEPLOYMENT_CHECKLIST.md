# CTOAi Local AI Integration - Deployment Checklist

## Pre-Deployment (Local)

- [ ] Model pulled: `docker model pull hf.co/bartowski/Qwen2.5-Coder-1.5B-Instruct-GGUF`
- [ ] Model cached: `docker model ls | grep qwen`
- [ ] Dependencies installed: `pip install httpx openai -q`
- [ ] `.env.local-ai` exists in repo root
- [ ] `runner/llm_providers/` directory created with 3 files:
  - [ ] `__init__.py` (provider factory)
  - [ ] `local_model.py` (Docker Model Runner client)
  - [ ] `azure_foundry.py` (Azure fallback)
- [ ] `runner/agents/executor.py` updated with `invoke_llm_for_task()`
- [ ] `scripts/test_local_model.py` exists
- [ ] `scripts/example_strategos_local_ai.py` exists
- [ ] `scripts/setup_local_ai.sh` exists
- [ ] Documentation created:
  - [ ] `docs/LOCAL_AI_MODEL_SETUP.md`
  - [ ] `LOCAL_AI_INTEGRATION_SUMMARY.md`
  - [ ] `SETUP_LOCAL_AI_README.md`

## Local Testing

Run before VPS deployment:

```bash
# Test 1: Health check (should pass in 2 seconds)
python3 scripts/test_local_model.py --health-only
# Expected: "[test] ✓ Provider health check PASSED"

# Test 2: Full completion test (should complete in 30 seconds)
python3 scripts/test_local_model.py
# Expected: Model response received + output displayed

# Test 3: Custom prompt
python3 scripts/test_local_model.py --invoke "Write a Python hello world"
# Expected: Model response printed

# Test 4: Agent examples
python3 scripts/example_strategos_local_ai.py
# Expected: STRATEGOS decisions, Agent 7 suggestions
```

Deployment tasks:
- [ ] All local tests pass
- [ ] No errors in logs
- [ ] Model response quality acceptable

## VPS Deployment

**Prerequisites:**
- SSH access to VPS (46.225.110.52)
- Docker installed on VPS
- Docker Model Runner available on VPS
- `/opt/ctoa` directory exists

**Deployment Steps:**

### Step 1: Connect to VPS
```bash
ssh ctoa@46.225.110.52
cd /opt/ctoa
```

- [ ] SSH connection successful
- [ ] Working directory: `/opt/ctoa`

### Step 2: Pull Model on VPS
```bash
docker model pull hf.co/bartowski/Qwen2.5-Coder-1.5B-Instruct-GGUF
docker model ls | grep qwen
```

- [ ] Model pulled successfully
- [ ] Model listed in `docker model ls`
- [ ] Size ~986 MB confirmed

### Step 3: Push Local Code to VPS

From your local machine:
```bash
cd C:\Users\zycie\CTOAi

# Copy integration files
scp runner/llm_providers/*.py ctoa@46.225.110.52:/opt/ctoa/runner/llm_providers/
scp scripts/test_local_model.py ctoa@46.225.110.52:/opt/ctoa/scripts/
scp scripts/example_strategos_local_ai.py ctoa@46.225.110.52:/opt/ctoa/scripts/
scp .env.local-ai ctoa@46.225.110.52:/opt/ctoa/.env.local-ai
```

- [ ] All files copied to VPS
- [ ] Permissions correct (readable by ctoa user)

### Step 4: Update VPS Environment

On VPS:
```bash
# Add local AI config to .env
echo "" >> /opt/ctoa/.env
echo "# Local AI Model Configuration" >> /opt/ctoa/.env
echo "CTOA_LLM_PROVIDER=auto" >> /opt/ctoa/.env
echo "CTOA_LOCAL_MODEL_URL=http://localhost:11434/v1" >> /opt/ctoa/.env
echo "CTOA_LOCAL_MODEL_NAME=hf.co/bartowski/Qwen2.5-Coder-1.5B-Instruct-GGUF" >> /opt/ctoa/.env

# Verify
grep CTOA_LLM_PROVIDER /opt/ctoa/.env
```

- [ ] `.env` updated with local AI config
- [ ] No duplicate entries
- [ ] Variables correctly formatted

### Step 5: Test VPS Integration

On VPS:
```bash
cd /opt/ctoa
python3 scripts/test_local_model.py --health-only
```

- [ ] Health check passes
- [ ] Local model accessible
- [ ] Model endpoint responding

### Step 6: Restart VPS Services

On VPS:
```bash
# Restart runner and report timers
sudo systemctl restart ctoa-runner.timer
sudo systemctl restart ctoa-report.timer

# Check status
sudo systemctl status ctoa-runner.timer
sudo systemctl status ctoa-report.timer
```

- [ ] Both services restarted successfully
- [ ] No error messages
- [ ] Services in "active" state

### Step 7: Verify First Agent Execution

On VPS:
```bash
# Run one tick with agents
cd /opt/ctoa
python3 runner/runner.py tick --agents

# Monitor for 10 seconds
tail -f logs/runner.log | grep -i llm
```

- [ ] Tick completes without error
- [ ] Agent execution initiated
- [ ] LLM integration working (check logs for "LLM" or "provider")

### Step 8: Check Live Status

On VPS:
```bash
# Generate live report
python3 runner/runner.py report

# Should show current task states
```

- [ ] Report generates successfully
- [ ] Task states updated
- [ ] No "ERROR" lines in output

### Step 9: Monitor Logs (Optional)

On VPS:
```bash
# Check for any errors or warnings
sudo journalctl -u ctoa-runner.timer -n 50
sudo journalctl -u ctoa-report.timer -n 50
```

- [ ] No critical errors
- [ ] Services running as expected
- [ ] LLM queries succeeding (check for completion responses)

## Post-Deployment Validation

### Local Verification
```bash
# From your local machine, verify system is running
curl -s http://46.225.110.52:8787/api/health | jq .
```

- [ ] Health endpoint responds
- [ ] VPS system operational

### Long-term Monitoring

Set up daily checks:
```bash
# On VPS (can add to crontab)
cd /opt/ctoa && python3 runner/runner.py report > /tmp/ctoa_status.txt
echo "Last tick: $(grep 'last_tick_at' /tmp/ctoa_status.txt)"
echo "Tasks released: $(grep 'RELEASED' /tmp/ctoa_status.txt | wc -l)"
```

- [ ] Daily status checks configured
- [ ] Task completion tracking active
- [ ] Agent execution monitoring enabled

## Rollback Plan (If Needed)

If local model causes issues:

```bash
# On VPS
ssh ctoa@46.225.110.52

# Restore to Azure-only (existing behavior)
# Option 1: Revert .env
cp /opt/ctoa/.env.backup /opt/ctoa/.env
export CTOA_LLM_PROVIDER=azure

# Option 2: Pull code from git
cd /opt/ctoa && git checkout runner/llm_providers/

# Restart
sudo systemctl restart ctoa-runner.timer
```

- [ ] Rollback procedure documented
- [ ] Backup of pre-deployment .env stored
- [ ] Git history preserved for recovery

## Success Criteria

After deployment, all should be true:

✅ Model pulled on VPS and cached
✅ Integration files deployed
✅ Environment configured with `CTOA_LLM_PROVIDER=auto`
✅ Health check passes: `python3 scripts/test_local_model.py --health-only`
✅ First agent tick completes: `python3 runner/runner.py tick --agents`
✅ Logs show LLM provider in use
✅ Live status reports task progress
✅ Systemd timers running automatically

## Support

**If health check fails:**
1. Verify model is cached: `docker model ls`
2. Verify endpoint accessible: `curl http://localhost:11434/health`
3. Check Docker Model Runner running
4. Increase timeout: `export CTOA_LOCAL_MODEL_TIMEOUT_SECS=300`

**If agent execution fails:**
1. Check logs: `tail -50 logs/runner.log | grep ERROR`
2. Verify FOUNDRY credentials fallback (if Azure needed)
3. Check model response quality in logs
4. Increase timeout for slow machines

**Questions?**
- See `docs/LOCAL_AI_MODEL_SETUP.md` for detailed troubleshooting
- Review `scripts/example_strategos_local_ai.py` for integration patterns
- Check `SETUP_LOCAL_AI_README.md` for architecture overview

---

**Deployment Date:** _______________
**Deployed By:** _______________
**Sign-off:** _______________
