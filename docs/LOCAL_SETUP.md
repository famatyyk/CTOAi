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
git clone https://github.com/famatyyk/CTOAi.git
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

**Windows (PowerShell):**
```powershell
# These persist across sessions
$env:CTOA_VPS_HOST = "46.225.110.52"
$env:CTOA_VPS_USER = "root"
$env:CTOA_VPS_KEY_PATH = "$env:USERPROFILE\.ssh\ctoa_vps_ed25519"

# Optional (only if testing agent execution):
$env:CTOA_GITHUB_PAT = "ghp_xxxxxxxxxxxxxxxxxxxx"

# Persist to user profile:
[Environment]::SetEnvironmentVariable("CTOA_VPS_HOST", "46.225.110.52", "User")
# ... repeat for other vars
```

**macOS/Linux (Bash):**
```bash
export CTOA_VPS_HOST="46.225.110.52"
export CTOA_VPS_USER="root"
export CTOA_VPS_KEY_PATH="$HOME/.ssh/ctoa_vps_ed25519"

# Persist to ~/.bashrc or ~/.zshrc:
echo 'export CTOA_VPS_HOST="46.225.110.52"' >> ~/.bashrc
```

### 5. Verify Setup

```bash
# Check Python
python --version  # Should be 3.11+

# Check imports
python -c "import pytest; import requests; import paramiko; print('✓ All imports OK')"

# Run tests (should pass or show clear error messages)
pytest tests/ -v

# Check VPS connectivity (if SSH key installed)
scripts/ops/ctoa-vps.ps1 -Action Verify
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
2. **Read Docs:** Review [SPRINT-002.md](../SPRINT-002.md)
3. **Explore Agents:** Check `agents/definitions.py` and `scoring/tool_advisor.py`
4. **Deploy to VPS:** See [deploy/vps/SETUP.md](../deploy/vps/SETUP.md)

---

## Getting Help

- **Issues:** [GitHub Issues](https://github.com/famatyyk/CTOAi/issues)
- **Docs:** [README.md](../README.md), [CHANGELOG.md](../CHANGELOG.md), [SPRINT-002.md](../SPRINT-002.md)
- **Logs:** Check `.github/workflows/` for pipeline results

Happy coding! 🚀

