# Local Development Guide

Get CTOA AI Toolkit running on your local machine in <10 minutes.

---

## Prerequisites

- **Python 3.11+** (check: `python --version`)
- **Git** (check: `git --version`)
- **SSH key** for VPS (if testing remote operations)
- **Windows, macOS, or Linux** (guide uses PowerShell/Bash syntax)

---

## Setup Steps

### 1. Clone Repository

```bash
git clone git@github.com:famatyyk/CTOAi.git
cd CTOAi
```

### 2. Create Python Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**macOS/Linux (Bash):**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Expected packages:
- `pytest` (testing)
- `pyyaml` (config)
- `requests` (API calls)
- `paramiko` (SSH)

### 4. Configure Environment Variables

### 4a. Bootstrap Local Product Config

Before first launch, create a local product config and local state database:

```bash
python scripts/ops/ctoa_product_bootstrap.py
```

This creates ignored local files under `.ctoa-local/`:

- `user-config.json`
- `bootstrap-state.json`
- `toolkit-state.db`

### 4b. Mandatory Update Gate

Every product launch must pass the update gate before the toolkit starts:

```bash
python scripts/ops/ctoa_update_gate.py
```

If the gate fails, update the repo and re-run bootstrap.

**Windows (PowerShell):**
```powershell
# These persist across sessions
$env:CTOA_VPS_HOST = "your-vps-host"
$env:CTOA_VPS_USER = "your-vps-user"
$env:CTOA_VPS_KEY_PATH = "$env:USERPROFILE\.ssh\ctoa_vps_ed25519"

# Optional (only if testing agent execution):
$env:CTOA_GITHUB_PAT = "your_token_here"

# Persist to user profile:
[Environment]::SetEnvironmentVariable("CTOA_VPS_HOST", "your-vps-host", "User")
# ... repeat for other vars
```

**macOS/Linux (Bash):**
```bash
export CTOA_VPS_HOST="your-vps-host"
export CTOA_VPS_USER="your-vps-user"
export CTOA_VPS_KEY_PATH="$HOME/.ssh/ctoa_vps_ed25519"

# Persist to ~/.bashrc or ~/.zshrc:
echo 'export CTOA_VPS_HOST="your-vps-host"' >> ~/.bashrc
```

### 5. Verify Setup

```bash
# Check Python
python --version  # Should be 3.11+

# Check imports
python -c "import pytest; import requests; import paramiko; print('OK: imports available')"

# Run tests (should pass or show clear error messages)
pytest tests/ -v

# Check VPS connectivity (if SSH key installed)
scripts/ops/ctoa-vps.ps1 -Action Verify
```

### 6. Daily Git Preflight (before pull/rebase/push)

```bash
python scripts/ops/ctoa_env_doctor.py
```

If status is `FAIL`, fix reported issues first.

---

## Git + SSH Hardening

### Git Not In PATH (Windows)

If `git --version` fails but Git is installed, set one of:

```powershell
# Option 1: one-time current shell
$env:Path += ';C:\Program Files\Git\cmd'

# Option 2: persistent fallback for CTOA scripts
[Environment]::SetEnvironmentVariable('CTOA_GIT_BIN', 'C:\Program Files\Git\cmd\git.exe', 'User')
```

### SSH Checklist (Local Dev)

```bash
# 1) key exists
ls ~/.ssh

# 2) agent has key
ssh-add -l

# 3) GitHub auth check
ssh -T git@github.com
```

Expected success message contains `successfully authenticated`.

### Clean Tree + Sync Routine

```bash
python scripts/ops/ctoa_env_doctor.py
git fetch origin
git rebase origin/main
python scripts/ops/ctoa_env_doctor.py
```

---

## Running Tests

### Run All Tests

```bash
pytest tests/ -v
```

### Run with Coverage

```bash
pytest tests/ --cov=runner --cov=agents --cov=scoring --cov-report=html
# Open htmlcov/index.html in browser
```

### Run Specific Test Suite

```bash
# Basic core tests
pytest tests/test_suite.py -v

# Agent framework tests
pytest tests/test_agent_framework.py -v

# Specific test class
pytest tests/test_suite.py::TestRunnerBasics -v

# Specific test
pytest tests/test_suite.py::TestRunnerBasics::test_imports -v
```

---

## Common Tasks

### Test Agent Definitions

```bash
python -c "
from agents.definitions import list_agents, get_agents_for_task
print('Agents:', list_agents())
print('CTOA-001 assigned to:', get_agents_for_task('CTOA-001'))
"
```

### Test BRAVE(R) Templates

```bash
python -c "
from prompts.braver_templates import get_all_components, render_template
print('BRAVE(R) components:', get_all_components())
"
```

### Score Tools

```bash
python -c "
from scoring.tool_advisor import rank_tools_for_task
tools = rank_tools_for_task('test-task')
for tool in tools[:3]:
    print(f'{tool[\"name\"]}: {tool[\"score\"]:.3f}')
"
```

### Execute Local Tests

```bash
python tests/test_suite.py -v
python tests/test_agent_framework.py -v
```

---

## Debugging

### Enable Debug Logging

```bash
export CTOA_DEBUG=true
pytest tests/ -v -s  # -s shows print() statements
```

### Check Import Paths

```bash
python -c "import sys; print('\n'.join(sys.path))"
```

### Verify SSH Configuration

```powershell
# Test SSH key permissions
ls -la ~/.ssh/ctoa_vps_ed25519

# Test SSH connection (no execution, just auth)
scripts/ops/ctoa-vps.ps1 -Action Verify
```

### View Test Coverage

```bash
pytest tests/ --cov=runner --cov-report=term-missing
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: No module named 'pytest'` | Run: `pip install -r requirements.txt` |
| `Permission denied` (SSH key) | Run: `chmod 600 ~/.ssh/ctoa_vps_ed25519` |
| `Import errors from agents/` | Ensure `.venv` is activated: `source .venv/bin/activate` |
| Tests fail with timeouts | Some tests have 30sec timeouts; run on stable network |
| `CTOA_VPS_KEY_PATH not set` | Follow section 4 above (set env vars) |

---

## Next Steps

1. **Run Tests:** `pytest tests/ -v`
2. **Bootstrap Product State:** `python scripts/ops/ctoa_product_bootstrap.py`
3. **Pass Update Gate:** `python scripts/ops/ctoa_update_gate.py`
4. **Read Docs:** Review [SPRINT-002.md](../SPRINT-002.md)
5. **Deploy to VPS:** See [deploy/vps/SETUP.md](../deploy/vps/SETUP.md)

---

## Getting Help

- **Issues:** [GitHub Issues](https://github.com/famatyyk/CTOAi/issues)
- **Docs:** [README.md](../README.md), [CHANGELOG.md](../CHANGELOG.md), [SPRINT-002.md](../SPRINT-002.md)
- **Logs:** Check `.github/workflows/` for pipeline results

Happy coding! đźš€


## Sprint-0 Integration Pack

Use this flow to run the full local integration stack (app + db + redis + worker + observability).

### Tooling bootstrap

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
pre-commit install
```

### Full stack startup

```bash
docker compose up -d ctoa-db ctoa-redis ctoa ctoa-worker ctoa-prometheus ctoa-loki ctoa-promtail
```

Grafana is no longer part of the default local stack. If you need dashboards later, run them as a separate optional service instead of blocking Control Center on port 3000.

### Database migrations

```bash
.venv/Scripts/python.exe -m alembic upgrade head
```

### Quick validation

```bash
.venv/Scripts/python.exe scripts/ops/queue_enqueue_job.py --action orchestrator.tick
curl http://127.0.0.1:8787/metrics
curl http://127.0.0.1:9090/-/healthy
curl http://127.0.0.1:3100/ready
```

### VS Code tasks (recommended)

- `CTOA: Sprint-0 Compose Up (Full Stack)`
- `CTOA: Sprint-0 Alembic Upgrade Head`
- `CTOA: Sprint-0 Enqueue Worker Tick`
- `CTOA: Sprint-0 Validate Integration Pack`
- `CTOA: Sprint-0 Compose Down (Full Stack)`
