# Pre-Launch Validation Checklist

Complete before deploying CTOA AI Toolkit to production VPS.

## Sprint-002 Track Snapshot (2026-03-12)

- [x] Track A: CI/CD domkniete
- [x] Track B: Live monitoring VPS domkniety
- [x] Track D: Agent framework domkniety
- [x] Track E: Porzadki dokumentacji domkniete

---

## Phase 1: Local Development Environment ✓

- [ ] **Python version** — `python --version` returns 3.11+
- [ ] **Virtual environment** — `.venv` activated
- [ ] **Dependencies installed** — `pip list | grep pytest` shows pytest, requests, paramiko
- [ ] **Imports work** — `python -c "import runner, agents, scoring, prompts"` succeeds
- [ ] **Tests pass locally** — `pytest tests/ -v` shows ✓ all tests
- [ ] **Code lint clean** — `pylint runner/ agents/ scoring/` shows no critical errors

---

## Phase 2: Agent Definitions ✓

- [ ] **All 10 agents defined** — `agents/definitions.py` lists CTOA-001 through CTOA-010
- [ ] **Each agent has prompt** — `agents/CTOA-001.prompt.md` ... `CTOA-010.prompt.md` exist
- [ ] **BRAVE(R) components complete** — Each prompt has B, R, A, V, E, (R) sections
- [ ] **Agents structured identically** — Check one template matches expected format
- [ ] **No duplicate agent IDs** — Each CTOA-NNN is unique
- [ ] **Approved tools listed** — Each agent specifies tools array

**Check with:**
```bash
python -c "
from agents.definitions import list_agents, get_agent
for agent in list_agents():
    ag = get_agent(agent)
    print(f'{agent}: {len(ag.approved_tools)} tools')
"
```

---

## Phase 3: Prompt Engine (BRAVE(R)) ✓

- [ ] **braver_templates.py works** — `python -c "from prompts.braver_templates import render_template"`
- [ ] **All components render** — `render_template(agent_def, task, context)` returns valid prompt
- [ ] **Examples included** — Few-shot examples in prompts/ directory
- [ ] **Output schema defined** — Result format for each agent (JSON structure)
- [ ] **Token estimation accurate** — `estimate_tokens()` function within 5% of actual

**Test with:**
```bash
python -c "
from prompts.braver_templates import render_template
from agents.definitions import get_agent
agent = get_agent('CTOA-001')
prompt = render_template(agent, 'test task', {'context': 'example'})
print(f'Prompt length: {len(prompt)} chars')
"
```

---

## Phase 4: Scoring & Governance ✓

- [ ] **Tool Advisor works** — `tool_advisor.rank_tools_for_task('task')` returns list
- [ ] **Policy Pack enforces rules** — `policy_pack.apply_rules(tools, task_type)` filters properly
- [ ] **Risk Matrix evaluated** — `risk_matrix.assess_decision(decision)` rates risk level
- [ ] **Scoring is deterministic** — Same input → same output
- [ ] **Tool costs realistic** — Scores match expected API costs
- [ ] **Rate limits configured** — policy_pack.py has RATE_LIMITS dict

**Test with:**
```bash
python -c "
from scoring.tool_advisor import rank_tools_for_task
from scoring.policy_pack import apply_rules
tools = rank_tools_for_task('code-review')
print(f'Top 3 tools: {[t[\"name\"] for t in tools[:3]]}')
filtered = apply_rules(tools, 'code-review')
print(f'After policy: {[t[\"name\"] for t in filtered]}')
"
```

---

## Phase 5: Runner & Orchestration ✓

- [ ] **runner.py tick() works** — Can fetch issues from GitHub (requires GITHUB_PAT env var)
- [ ] **runner.py report() works** — Generates sprint summary markdown
- [ ] **runner.py approve() works** — Can approve/reject tasks
- [ ] **Agent executor runs** — `agent_executor.execute_agent(issue, agent_def)` succeeds
- [ ] **Result format valid** — Output includes {decision, log, telemetry}
- [ ] **Error handling robust** — Failed agent run doesn't crash runner

**Test with:**
```bash
export GITHUB_PAT="ghp_test_token_here"
python runner/runner.py tick --dry-run
# Should list issues without executing
```

---

## Phase 6: GitHub Integration ✓

- [ ] **GitHub PAT valid** — `curl -H "Authorization: token $GITHUB_PAT" https://api.github.com/user` succeeds
- [ ] **GitHub PAT scopes correct** — `repo` (read/write) scope enabled
- [ ] **GraphQL query works** — `runner/github_client.py` can fetch issues
- [ ] **Issue label system ready** — `ctoa-execution` and `approved` labels exist in repo
- [ ] **Webhook configured** (optional) — Triggers runner on issue creation
- [ ] **CI workflows defined** — `.github/workflows/ci.yml` exists and passes

**Verify PAT:**
```bash
curl -s -H "Authorization: token $GITHUB_PAT" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/user | grep login
```

---

## Phase 7: LLM Integration ✓

- [ ] **OpenAI API key works** — `python -c "import openai; openai.api_key='...'; openai.Model.list()"`
- [ ] **Model accessible** — GPT-4 (or fallback) endpoint responds
- [ ] **Azure OpenAI key works** (if using Azure backup)
- [ ] **Token estimation accurate** — Test prompt costs match estimate
- [ ] **Temperature settings sensible** — Different agents have appropriate temps (0.1-0.8)
- [ ] **Rate limits respected** — No API throttling in tests

**Test connection:**
```bash
export OPENAI_API_KEY="sk-..."
python -c "
import openai
model = 'gpt-4'
msg = openai.ChatCompletion.create(
    model=model,
    messages=[{'role': 'user', 'content': 'hello'}],
    max_tokens=10
)
print(f'Cost: \${msg[\"usage\"][\"total_tokens\"] * 0.03 / 1000:.4f}')
"
```

---

## Phase 8: VPS Preparation ✓

- [ ] **VPS accessible via SSH** — `ssh -i ~/.ssh/ctoa_vps_ed25519 root@46.225.110.52 echo "✓"`
- [ ] **SSH key permissions** — `ls -la ~/.ssh/ctoa_vps_ed25519` shows `600`
- [ ] **VPS has Python 3.11+** — SSH in and check `python3.11 --version`
- [ ] **VPS has git** — `ssh ... git --version` works
- [ ] **VPS storage adequate** — At least 5GB free in `/opt/ctoa`
- [ ] **VPS network stable** — Ping 5 times, all return <100ms

**Full test:**
```bash
ssh -i ~/.ssh/ctoa_vps_ed25519 root@46.225.110.52 << 'EOF'
python3.11 --version
git --version
df -h | grep /opt || echo "Need /opt partition"
free -h
EOF
```

---

## Phase 9: Systemd Services ✓

- [ ] **Service files created** — `/etc/systemd/system/ctoa-*.service` exist on VPS
- [ ] **Timer files created** — `/etc/systemd/system/ctoa-*.timer` exist on VPS
- [ ] **Services enabled** — `systemctl is-enabled ctoa-runner.timer` returns `enabled`
- [ ] **Services start cleanly** — `systemctl start ctoa-runner` succeeds
- [ ] **Logs write to correct location** — `/var/log/ctoa/` directory exists
- [ ] **Log rotation configured** — `/etc/logrotate.d/ctoa` exists

**Verify on VPS:**
```bash
systemctl daemon-reload
systemctl enable ctoa-runner.timer
systemctl enable ctoa-report.timer
systemctl start ctoa-runner.timer
systemctl status ctoa-runner.timer
mkdir -p /var/log/ctoa
```

---

## Phase 10: Environment Variables ✓

- [ ] **`.env` file created on VPS** — `/opt/ctoa/.env` contains secrets
- [ ] **File permissions secure** — `stat /opt/ctoa/.env` shows `0600`
- [ ] **GITHUB_PAT set** — `ssh ... grep GITHUB_PAT /opt/ctoa/.env` shows value
- [ ] **OpenAI key set** — `ssh ... grep OPENAI_API /opt/ctoa/.env` shows value
- [ ] **No secrets in code** — `grep -r "ghp_\|sk-" runner/ agents/` returns nothing
- [ ] **Secrets in .gitignore** — `.env` is in `.gitignore`

---

## Phase 11: Database & Storage ✓

- [ ] **No database required** — CTOA uses GitHub as primary store
- [ ] **Local cache directory** — `/opt/ctoa/runtime/` exists and is writable
- [ ] **Log directory** — `/var/log/ctoa/` exists and is writable
- [ ] **Sufficient disk space** — `df -h /opt/ctoa` shows >5GB free

---

## Phase 12: Deployment Dry-Run ✓

- [ ] **Can push code to VPS** — Test `git push` or use deploy script
- [ ] **Dependency install works** — `pip install -r requirements.txt` on VPS succeeds
- [ ] **Import tests pass** — `ssh ... python -c "import runner, agents, scoring"` works
- [ ] **runner.py --help works** — `ssh ... python runner/runner.py --help` shows usage
- [ ] **Dry-run completes** — `python runner/runner.py tick --dry-run` succeeds

**Full dry-run:**
```bash
ssh -i ~/.ssh/ctoa_vps_ed25519 root@46.225.110.52 << 'EOF'
cd /opt/ctoa
source .venv/bin/activate
python runner/runner.py tick --dry-run
python runner/runner.py report --publish=false
EOF
```

---

## Phase 13: Monitoring & Alerting ✓

- [ ] **Log aggregation works** — Can view `/var/log/ctoa/*.log` files
- [ ] **Error logging works** — Errors write to `errors.log` with timestamp
- [ ] **Metrics collected** — `agent-execution.log` includes duration, tokens, cost
- [ ] **Systemd journal works** — `journalctl -u ctoa-runner` shows logs
- [ ] **Alerts configured** (optional) — Email or Slack alerts on failures

**Test logging:**
```bash
ssh -i ~/.ssh/ctoa_vps_ed25519 root@46.225.110.52 << 'EOF'
tail -20 /var/log/ctoa/agent-execution.log
journalctl -u ctoa-runner -n 10
EOF
```

---

## Phase 14: Documentation ✓

- [ ] **README.md complete** — Covers project goal, quick start, architecture
- [ ] **LOCAL_SETUP.md complete** — Dev can follow it end-to-end
- [ ] **ARCHITECTURE.md complete** — Explains all components and data flows
- [ ] **VPS SETUP.md complete** — Deployment steps clear
- [ ] **Inline comments clear** — Code explains "why", not just "what"
- [ ] **CHANGELOG.md updated** — Documents changes since last version

**Spot check:**
```bash
ls -1 docs/*.md
# LOCAL_SETUP.md, ARCHITECTURE.md, README.md should all exist
```

---

## Phase 15: Security Audit ✓

- [ ] **No hardcoded secrets** — `grep -r "ghp_\|sk-\|password" runner/ agents/ scoring/` is empty
- [ ] **SSH key not in repo** — `.ssh/ctoa_vps_ed25519` is in `.gitignore`
- [ ] **API keys rotated** — GitHub PAT and OpenAI key created with expiration date
- [ ] **Policy pack enforced** — Unapproved tools are blocked
- [ ] **Approval gate works** — High-risk decisions require human review
- [ ] **Audit trail complete** — All decisions logged in GitHub and `/var/log/ctoa/`

---

## Phase 16: Performance Testing ✓

- [ ] **Single agent execution** — Takes <10 seconds (including LLM call)
- [ ] **10 concurrent agents** — Complete in <2 minutes (parallel execution)
- [ ] **LLM call latency** — <3 seconds on average
- [ ] **Tool scoring** — <100ms to rank tools
- [ ] **GitHub API calls** — <2 seconds for issue fetch
- [ ] **Memory usage** — <500MB during execution

**Benchmark:**
```bash
export CTOA_DEBUG=true
time python runner/runner.py tick --dry-run
# Should complete in <10 seconds
```

---

## Phase 17: Go/No-Go Decision ✓

**Go conditions (ALL must be true):**
- [ ] All 16 phases above completed and checked
- [ ] No blocking issues in test runs
- [ ] VPS deployment tested successfully
- [ ] Team review approved
- [ ] Runbook documented (SETUP.md, LOCAL_SETUP.md)

**No-Go conditions (ANY is blocking):**
- [ ] Security audit failures
- [ ] LLM API unavailable
- [ ] GitHub authentication broken
- [ ] VPS unreachable or unresponsive
- [ ] Performance below targets (>15 sec for 10 agents)
- [ ] Critical bugs in runner or agent executor

**Go/No-Go Date:** _______________  
**Decision:** [ ] GO [ ] NO-GO (Hold for fixes)  
**Approved By:** _______________

---

## Rollback Procedure

If production issues occur:

1. **Stop execution:** `systemctl stop ctoa-runner`
2. **Revert code:** `git reset --hard HEAD~1`
3. **Restart:** `systemctl start ctoa-runner`
4. **Verify:** Check `/var/log/ctoa/` for error messages
5. **Post-mortem:** Document root cause and fix plan

---

## Post-Launch Monitoring (Week 1)

- [ ] Daily log review (check for errors, anomalies)
- [ ] Track agent execution metrics (time, cost, quality)
- [ ] Monitor VPS resources (CPU, memory, disk)
- [ ] Review GitHub PR approvals (are humans satisfied?)
- [ ] Update metrics dashboard with real data
- [ ] Plan optimizations based on actual usage

---

## Contact & Support

- **Issues:** https://github.com/famatyyk/CTOAi/issues
- **Runbooks:** [LOCAL_SETUP.md](../docs/LOCAL_SETUP.md), [VPS SETUP.md](../deploy/vps/SETUP.md)
- **Architecture:** [ARCHITECTURE.md](../docs/ARCHITECTURE.md)

