# CTOA AI Toolkit

**Status:** Sprint-003 Active (2026-03-12 to 2026-03-26)  
**Security:** 🟢 SSH & PAT rotated | 🟢 Git hardened | 🟢 Tests automated  
**Agents:** 10 active | BRAVE(R) templates | Tool advisor system  

**Coordinated Task Orchestration Architecture** — A 10-agent AI system for autonomous sprint execution with human oversight.

---

## What Is CTOA?

CTOA AI Toolkit orchestrates 10+ AI agents (CTOA-001 through CTOA-010) to autonomously execute coding tasks from a GitHub issue queue, using the BRAVE(R) prompt engine and intelligent tool selection, while maintaining full auditability and human control.

**Key Features:**
- 🤖 **10 specialized agents** — Each with targeted expertise  
- 🧠 **BRAVE(R) Prompt Engine** — Structured prompts for consistent decisions
- 🎯 **Tool Advisor** — Intelligent ranking by relevance, cost, risk
- 🔐 **Policy & Governance** — Enforcement of org rules and approval gates
- 📊 **Full Audit Trail** — Every decision logged and reviewable
- ☁️ **Cloud-Ready** — Deploy to any VPS with Python 3.11+

---

## Quick Links

- **🚀 Getting Started:** [Local Development Guide](docs/LOCAL_SETUP.md) (5 minutes)
- **📚 Deep Dive:** [Architecture Guide](docs/ARCHITECTURE.md) (10 minutes)
- **☁️ Deploy to VPS:** [VPS Setup Guide](deploy/vps/SETUP.md) (15 minutes)
- **✅ Pre-Launch:** [Validation Checklist](docs/VALIDATION_CHECKLIST.md) (review before production)

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  GitHub (Control Plane)                                  │
│  - Issue #1: Live Status (hourly)                        │
│  - Issue #2: Health Dashboard (hourly)                   │
│  - Actions: CI/CD Pipeline (on every commit)             │
│  - CTOA-NNN: Agent Tasks (backlog)                       │
└──────────────┬───────────────────────────────────────────┘
               │
     ┌─────────┴──────────┐
     │                    │
     ▼                    ▼
┌──────────────────┐  ┌─────────────────────────┐
│  Local Dev       │  │  VPS (46.225.110.52)    │
│  - Python Tests  │  │  - 24/7 Runner Service  │
│  - Git Workflow  │  │  - Reporter Service     │
│  - BRAVE(R) Dev  │  │  - Health Monitor       │
│  - SSH Key       │  │  - Systemd Timers       │
└──────────────────┘  └─────────────────────────┘
```

## Components

| Component | Purpose | Status |
|-----------|---------|--------|
| **runner/runner.py** | Main execution loop, task ticking | ✅ Active |
| **runner/agent_executor.py** | Execute agents with LLM | ✅ Active |
| **runner/health_metrics.py** | VPS system metrics collection | ✅ Active |
| **runner/status_sync.py** | GitHub Issue automation | ✅ Active |
| **.github/workflows/** | CI/CD: tests, lint, secret scan | ✅ Hardened |
| **agents/definitions.py** | 10-agent framework + metadata | ✅ Sprint-002 |
| **agents/CTOA-NNN.prompt.md** | BRAVE(R) templates (10 files) | ✅ Sprint-002 |
| **prompts/braver_templates.py** | Prompt composition engine | ✅ Sprint-002 |
| **scoring/tool_advisor.py** | Intelligent tool selection | ✅ Sprint-002 |
| **scoring/policy_pack.py** | Org governance enforcement | ✅ Sprint-002 |
| **deploy/systemd/** | Service definitions | ✅ Sprint-002 |
| **tests/** | Unit & integration tests (pytest) | ✅ Sprint-002 |

## Quick Start

### Option 1: Local Development (5 minutes)

Read **[Local Development Guide](docs/LOCAL_SETUP.md)** for step-by-step instructions:

```bash
# Quick version:
git clone https://github.com/famatyyk/CTOAi.git
cd CTOAi
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest tests/ -v
```

### Option 2: Deploy to VPS (15 minutes)

Read **[VPS Setup Guide](deploy/vps/SETUP.md)** for deployment steps:

```bash
# Bootstrap or refresh VPS environment
scripts/ops/ctoa-vps.ps1 -Action Setup24x7

# Enable persistent live health stream service
scripts/ops/ctoa-vps.ps1 -Action EnableLiveHealth

# Follow live health stream logs
scripts/ops/ctoa-vps.ps1 -Action TailLiveHealth
```

### Option 3: Understand the Architecture (10 minutes)

Read **[Architecture Guide](docs/ARCHITECTURE.md)** to learn:
- How the 10 agents execute tasks
- Tool scoring and policy enforcement
- BRAVE(R) prompt composition
- Data flows end-to-end

## CI/CD Pipeline

Primary workflows:
- `.github/workflows/ctoa-pipeline.yml` (tests + lint + checks on push)
- `.github/workflows/ctoa-status-sync.yml` (hourly status/labels sync)
- `.github/workflows/ctoa-daily-insights.yml` (daily operational insights)
- `.github/workflows/ctoa-weekly-report.yml` (weekly summary)

View results in GitHub Actions for this repository.

## Sprint-002 Roadmap

| Track | Status | Items |
|-------|--------|-------|
| **A: CI/CD** | ✅ DONE | pytest framework, GitHub Actions, coverage |
| **B: Monitoring** | ✅ DONE | Health metrics, Issue #2 dashboard, alerting |
| **C: Backlog** | ✅ DONE | CTOA-001..010 migrated to GitHub Issues #13-#22 |
| **D: Agents** | ✅ DONE | 10 agents, BRAVE(R), tool advisor |
| **E: Documentation** | ✅ DONE | README, guides, architecture |

## Logs & Status

- **Live Status:** [Issue #1](https://github.com/famatyyk/CTOAi/issues/1)
- **Health Dashboard:** [Issue #2](https://github.com/famatyyk/CTOAi/issues/2) (hourly)
- **Backlog & Tasks:** [Issues](https://github.com/famatyyk/CTOAi/issues) (CTOA-001..010)
- **VPS Logs:** `/opt/ctoa/logs/` (runner.log, reporter.log, alerts.log)
- **Local Logs:** `./.venv/` (pytest, coverage)

## Security

- ✅ SSH Key: ed25519, rotated on 2026-03-12
- ✅ GitHub PAT: Rotated on 2026-03-12, revoked old token
- ✅ Repo: No hardcoded secrets (GitHub push protection active)
- ✅ Pipeline: Scans for PAT, AWS keys, SSH keys
- ✅ Audit Trail: PAT usage logged, health metrics timestamped

See [CHANGELOG.md](CHANGELOG.md) for rotation details.

## License
MIT
