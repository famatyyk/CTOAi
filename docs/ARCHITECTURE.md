# CTOA AI Toolkit Architecture

High-level design, component relationships, and data flows.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    CTOA AI Toolkit                           │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         GitHub (Issue/PR Orchestration)              │   │
│  │  - Task Queue (Issues labeled CTOA-*)                │   │
│  │  - Agent Assignment (via GitHub AI)                  │   │
│  │  - Approval Gate (PR review + CI checks)             │   │
│  └──────────────────────────────────────────────────────┘   │
│                          ▲                                   │
│                          │ (webhooks, REST API)               │
│                          ▼                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │      Runner Layer (VPS: 46.225.110.52)               │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │ Runner (runner.py)                             │  │   │
│  │  │  - Tick: Process CTOA-* issues                │  │   │
│  │  │  - Report: Generate sprint summary            │  │   │
│  │  │  - Approve: Accept/reject with decision log   │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  │                       ▼                               │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │ Agent Executor                                 │  │   │
│  │  │  - 10 concurrent agents (CTOA-001...CTOA-010) │  │   │
│  │  │  - BRAVE(R) prompt engine                     │  │   │
│  │  │  - Scoring engine (tool advisor)              │  │   │
│  │  │  - LLM integration (OpenAI, Azure OpenAI)     │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  │                       ▼                               │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │ Scoring & Tool Selection                       │  │   │
│  │  │  - Tool Advisor: Rank tools for task          │  │   │
│  │  │  - Policy Pack: Governance rules              │  │   │
│  │  │  - Risk Matrix: Override decisions            │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  │                       ▼                               │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │ External Tools & Services                      │  │   │
│  │  │  - LLM APIs (OpenAI, Azure)                   │  │   │
│  │  │  - GitHub GraphQL API                         │  │   │
│  │  │  - VS Code AI APIs (language features)        │  │   │
│  │  │  - Cloud providers (AWS, Azure, GCP)          │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  │                                                        │   │
│  │  Logs → /var/log/ctoa/                               │   │
│  │  Config → /opt/ctoa/.env                             │   │
│  │  Code → /opt/ctoa/ (git repo)                       │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Layers

### 1. Orchestration Layer (GitHub)

**Location:** External (github.com)  
**Responsibility:** Task creation, assignment, tracking, approval

Files:
- `.github/workflows/` — CI/CD pipeline definition
- Issues labeled `CTOA-001` through `CTOA-010` — agent tasks
- Pull requests — code review + approval gate

Flow:
```
User creates issue CTOA-001
    ↓
GitHub Actions runs on issue creation
    ↓
Runner fetches issue (GraphQL API)
    ↓
Agent CTOA-001 executes
    ↓
Agent creates PR with results
    ↓
CI checks run (tests, linting)
    ↓
Human reviews & merges
```

### 2. Runner Layer (VPS)

**Location:** `/opt/ctoa/runner/runner.py`  
**Responsibility:** Orchestrate agents, manage state, publish results

Key functions:
- `tick()` — Process one cycle of agent execution
- `report()` — Generate sprint summaries
- `approve()` — Record approval decision with log

Flow:
```
Systemd timer triggers runner.py tick
    ↓
Fetch all CTOA-* issues from GitHub
    ↓
Filter issuesready_to_execute
    ↓
For each issue:
    1. Load agent definition (agents/definitions.py)
    2. Create execution context
    3. Invoke agent executor
    4. Capture results (output, decision_log, telemetry)
    5. Create PR with results
    ↓
Log execution metrics
```

### 3. Agent Executor Layer

**Location:** `runner/agent_executor.py`  
**Responsibility:** Execute individual agents with LLM guidance

Key functions:
- `execute_agent()` — Run one agent against task
- `apply_policy_pack()` — Enforce governance
- `score_tools()` — Select optimal tools

Flow:
```
Agent executor receives: issue, agent_def, tools_available
    ↓
1. Load agent prompt template (agents/AGENT-NNN.prompt.md)
    ↓
2. Fetch BRAVE(R) components:
   - B: Background (context)
   - R: Role (agent persona)
   - A: Action (what to do)
   - V: Values (decision framework)
   - E: Examples (few-shot)
   - (R): Result format (JSON output schema)
    ↓
3. Render BRAVE(R) into full prompt
    ↓
4. Score tools (tool_advisor.rank_tools_for_task)
    ↓
5. Apply policy pack (policy_pack.apply_rules)
    ↓
6. Send to LLM with tool definitions
    ↓
7. Parse LLM response (decision + rationale)
    ↓
8. Return structured result {decision, log, telemetry}
```

### 4. Scoring & Governance Layer

**Location:** `scoring/`  
**Responsibility:** Tool selection, risk assessment, policy enforcement

Key files:
- `tool_advisor.py` — Rank tools by relevance/cost/risk
- `policy_pack.py` — Apply governance rules
- `risk_matrix.py` — Risk override decisions

Flow:
```
Tool Advisor:
  For each tool:
    - Relevance score (matching task keywords)
    - Cost score (API calls, inference time)
    - Risk score (security, privacy)
    - Final score = W_relevance * rel + W_cost * (1-cost) + W_risk * (1-risk)
  Sort by score, return top-N
    ↓
Policy Pack:
  For recommended tools:
    - Check "approved_tools" list
    - Check rate limits
    - Check data classification rules
    - Override if violates policy
    ↓
Risk Matrix:
  If high-risk tool selected:
    - Log decision rationale
    - Request human approval (labeled issue comment)
    - Escalate to DEFCON level if needed
```

### 5. Prompt Engine Layer (BRAVE(R))

**Location:** `prompts/braver_templates.py`  
**Responsibility:** Structured prompt composition

Components:
- **B - Background:** Context, recent decisions, task history
- **R - Role:** Agent persona, expertise, constraints
- **A - Action:** What to do, step-by-step instructions
- **V - Values:** Decision criteria, guardrails
- **E - Examples:** Few-shot instances of correct behavior
- **R - Result:** JSON schema for output

Example:
```markdown
## Background
You are Agent CTOA-001, specialized in code review.
Recent context: [loaded from issue comments]

## Role
You are an expert code reviewer with 10+ years experience.
You prioritize correctness, performance, and maintainability.

## Action
1. Review PR files for:
   - Logic correctness
   - Performance regressions
   - Security vulnerabilities
2. Recommend tools from the approved list
3. Output structured JSON with findings

## Values
- Prioritize user impact over stylistic issues
- Flag blocking issues (security, correctness)
- Suggest, don't demand changes

## Examples
... [example reviews with expected output]

## Result Format
{
  "decision": "approve|request_changes|comment",
  "findings": [...],
  "recommended_tools": [...],
  "confidence": 0.95
}
```

### 6. External Tools & Services

**LLM APIs:**
- OpenAI GPT-4 (primary)
- Azure OpenAI (fallback)

**GitHub APIs:**
- REST API v3 (create/update issues)
- GraphQL API (fetch issues, query workflows)

**Cloud Service APIs:**
- AWS (Lambda, S3, etc.)
- Azure (Functions, Storage, etc.)
- GCP (Cloud Functions, etc.)

**Programming Tools:**
- VS Code language server (code analysis)
- Git CLI (version control)
- Python test runners (pytest, coverage)

---

## Canonical Execution & Learning Flow

This architecture follows one canonical operating chain:

1. **Agent** receives task context and expected output contract.
2. **Prompt Engine (BRAVE(R))** renders execution prompt using current baseline template.
3. **Scoring & Tool Selection** ranks and constrains tools under cost/risk/policy signals.
4. **Governance** evaluates produced evidence through Wave-1 (automated) and Wave-2 (manual) gates.

Real-time learning loop across these layers:
`telemetry -> failure analysis -> prompt/skill update -> A/B -> validation -> rollout`

Definitions and quality expectations are standardized in:
- [Enhanced Agent/Prompt Definitive](./AGENT_PROMPT_DEFINITIVE.md)
- [Agent Training Masterplan](./AGENT_TRAINING_MASTERPLAN.md)
- [Sprint Governance](./SPRINT_GOVERNANCE.md)

---

## Data Flow: Task Execution

### End-to-End Example: CTOA-001 Code Review

```
1. GitHub Issue Created
   Title: "CTOA-001: Review PR #42"
   Label: "ctoa-execution"
   Status: "ready"

2. Systemd Timer Triggers (every 30min)
   Runner.tick() → fetch issues

3. Runner Fetches Issue Context
   - PR #42 files, diffs, comments
   - Recent agent history (if related tasks)
   - Policy pack rules for "code-review"

4. Agent Executor Loads CTOA-001 Definition
   agents/definitions.py:
   {
     "name": "Code Review Agent",
     "specialization": "code-review",
     "approved_tools": ["github-api", "vscode-language-server", ...],
     "max_tokens": 4000,
     "temperature": 0.3,
   }

5. BRAVE(R) Prompt Constructed
   - B: "You are reviewing PR #42 (add feature X)"
   - R: "Expert code reviewer, prioritize security"
   - A: "Check logic, performance, security; output JSON"
   - V: "Approve if no blocking issues; suggest otherwise"
   - E: <example reviews>
   - R: {decision, findings, tools, confidence}

6. Tool Advisor Scores Available Tools
   Tool: github-api
     - Relevance: 0.95 (fetch PR files, comments)
     - Cost: 0.2 (5 API calls expected)
     - Risk: 0.1 (read-only)
     - Score: 0.75
   
   Tool: vscode-language-server
     - Relevance: 0.90 (analyze code)
     - Cost: 0.05 (local, no charge)
     - Risk: 0.05 (memory usage)
     - Score: 0.85 ← TOP CHOICE
   
   Tool: aws-codeguru (AI review)
     - Relevance: 0.80
     - Cost: 0.8 (expensive)
     - Risk: 0.3 (external data)
     - Score: 0.30 ← SKIPPED (low score)

7. Policy Pack Applied
   Rule: "code-review tools must be approved"
   - github-api: approved ✓
   - vscode-language-server: approved ✓
   Result: OK, proceed

8. LLM Invocation
   Prompt:
   """
   [BRAVE(R) content above]
   
   Available tools:
   - github-api (tier: standard)
   - vscode-language-server (tier: standard)
   
   Proceed with review.
   """
   
   LLM response:
   {
     "decision": "approve",
     "findings": [
       {"file": "src/main.py", "issue": "Performance: O(n²) loop", "severity": "medium"}
     ],
     "recommended_tools": ["github-api", "vscode-language-server"],
     "confidence": 0.92
   }

9. Agent Executor Captures Result
   - Decision: "approve" + suggested improvements
   - Decision log: Why these tools, rationale
   - Telemetry: tokens used, tools called, time

10. Runner Creates PR with Results
    Fork branch: pr/ctoa-001-review-42
    Commit:
    - findings.json (structured results)
    - decision_log.md (human-readable rationale)
    - Files modified by agent (if any suggestions)
    
    PR title: "[CTOA-001] Code Review: PR #42"
    Description:
    """
    **Decision:** Approve
    **Confidence:** 92%
    **Findings:**
    - Performance: O(n²) loop in src/main.py (medium severity)
    
    **Tools Used:**
    - github-api
    - vscode-language-server
    
    **Full results:** See findings.json
    """

11. CI Runs
    - Lint findings.json
    - Validate decision_log.md format
    - Run tests affected by any code changes
    Status: ✓ All checks pass

12. Human Reviews & Merges
    Reviewer sees:
    - Auto-generated findings (can override)
    - Agent rationale (decision_log.md)
    - All CI checks passing
    
    Reviewer approves PR
    Reviewer merges to main

13. Runner Approves Original Task
    runner.py approve --task CTOA-001
    
    Updates issue CTOA-001:
    - Status: "completed"
    - Label: "approved"
    - Comment: "✓ Approved by humans. Results merged."

14. Sprint Report Generated
    runner.py report
    
    Creates/updates SPRINT-00X.md:
    """
    ## Execution Summary
    - CTOA-001: Code Review (APPROVED)
    - CTOA-002: ... (status)
    ...
    
    ## Decision Log
    - CTOA-001: Tool selection rationale
    - Risk overrides: none
    ...
    
    ## Metrics
    - Tasks completed: 1/10
    - Avg confidence: 92%
    - Total tokens: 12,345
    - Cost: $0.12
    """
```

---

## File Structure

```
CTOAi/
├── runner/                      # Core execution engine
│   ├── runner.py               # CLI: tick, report, approve
│   ├── agent_executor.py        # Execute individual agents
│   ├── requirements.txt         # Dependencies
│   └── __init__.py
│
├── agents/                       # Agent definitions
│   ├── definitions.py           # Agent metadata (name, tools, limits)
│   ├── CTOA-001.prompt.md      # BRAVE(R) templates (one per agent)
│   ├── CTOA-002.prompt.md
│   └── ...
│
├── prompts/                     # Template engine
│   ├── braver_templates.py     # BRAVE(R) composition
│   ├── examples/               # Few-shot examples for each specialty
│   └── __init__.py
│
├── scoring/                     # Governance layer
│   ├── tool_advisor.py         # Rank tools by score
│   ├── policy_pack.py          # Apply governance rules
│   ├── risk_matrix.py          # Risk override decisions
│   └── __init__.py
│
├── deploy/
│   └── vps/
│       ├── SETUP.md            # VPS deployment guide
│       ├── systemd/            # Service definitions
│       │   ├── ctoa-runner.service
│       │   ├── ctoa-runner.timer
│       │   ├── ctoa-report.service
│       │   └── ctoa-report.timer
│       └── vps-provision.sh    # Initial setup script
│
├── docs/                        # Documentation
│   ├── LOCAL_SETUP.md          # Local dev environment
│   ├── ARCHITECTURE.md         # This file
│   └── ...
│
├── .github/
│   └── workflows/              # GitHub Actions
│       ├── ci.yml              # Run on code push
│       ├── approval-gate.yml   # Human approval flow
│       └── ...
│
├── tests/                       # Unit & integration tests
│   ├── test_suite.py
│   ├── test_agent_framework.py
│   └── ...
│
└── .env                         # Secrets (local only)
    # GITHUB_PAT=...
    # OPENAI_API_KEY=...
```

---

## Scalability Considerations

### Throughput

**Current:** 10 concurrent agents (CTOA-001 to CTOA-010)

**To increase:**
1. Add CTOA-011, CTOA-012, etc. to `agents/definitions.py`
2. Create corresponding `.prompt.md` files
3. Configure in `runner.py` — adjust max_concurrent_tasks
4. Scale VPS if needed (more CPU/memory)

### Token Budget

**Assumption:** 4,000 tokens/agent/task, 10 agents/cycle = 40,000 tokens/cycle

**Cost Tracking:**
- `runner/agent_executor.py` logs tokens per agent
- `runner/runner.py` aggregates in sprint report
- Budget limit enforced: if next cycle exceeds budget, pause execution

**To optimize:**
- Use cheaper models for low-risk tasks
- Implement prompt compression
- Cache common decisions

### Tool Integration

**New tools follow pattern:**
1. Define in `scoring/tool_advisor.py` (name, cost, risk)
2. Add to policy_pack.py allow/deny lists
3. Create tool_xxx.py module in tools/
4. Update agent BRAVE(R) templates to reference tool
5. Add to ci.yml for validation

---

## Security & Governance

### Policy Pack Enforcement

```python
# scoring/policy_pack.py
APPROVED_TOOLS = {
    "github-api": ["read-only", "rate-limited"],
    "vscode-language-server": ["local-only"],
    "openai": ["approved-models-only"],
}

BLOCKED_ACTIONS = [
    "delete-repository",
    "modify-billing",
    "access-secrets",
]

def apply_rules(recommended_tools, task_type):
    """Filter/override tool selection based on policy."""
    for tool in recommended_tools:
        if tool not in APPROVED_TOOLS:
            log_risk(f"Unapproved tool: {tool}")
            raise PolicyViolation(f"Tool {tool} not approved for {task_type}")
```

### Risk Override

High-risk decisions require human approval:
- Escalate to DEFCON 1-2
- Add "requires-approval" label
- Block merge until human reviews

### Audit Trail

All decisions logged in:
- GitHub PR (decision_log.md)
- VPS logs (/var/log/ctoa/)
- Sprint reports (SPRINT-XXX.md)

---

## Performance Optimization

### LLM Calls

Target: <2 seconds per agent per task

**Optimization:**
- Use cheaper models (GPT-3.5) for simple tasks
- Cache embeddings for tool selection
- Batch requests when possible
- Early exit if high-confidence decision

### Tool Calls

Target: <5 API calls per agent per task

**Tracking:**
- agent_executor.py logs each tool invocation
- sprint_report aggregates API costs
- policy_pack can enforce rate limits

### Caching

Implement Redis cache for:
- GitHub issue context (30min TTL)
- Tool rankings (1hr TTL)
- BRAVE(R) components (24hr TTL)

---

## Monitoring & Alerting

### Key Metrics

- **Throughput:** Tasks completed/hour
- **Latency:** Time from issue creation to merge
- **Cost:** $ per task
- **Quality:** % of PRs merged without revision
- **Reliability:** % of successful executions

### Logs to Monitor

```bash
# VPS
tail -f /var/log/ctoa/agent-execution.log
tail -f /var/log/ctoa/errors.log

# GitHub Actions
View workflow runs in .github/workflows/

# Application
journalctl -u ctoa-runner -f
systemctl status ctoa-runner.timer
```

### Alerts

- **High error rate:** >10% failures/hour
- **Budget overrun:** Tokens >10% of budget
- **Tool failures:** Repeated API failures
- **Policy violations:** Unapproved tools detected

---

## Future Enhancements (Frozen Backlog)

Status: Frozen as backlog until repository split and package boundaries are completed.
Priority order:
1. Repository structure and package ownership boundaries
2. Migration execution by batches and CI gate hardening
3. Return to future enhancements only after split completion

Deferred items (not active sprint scope):
1. **Multi-agent collaboration:** Agents can delegate to other agents
2. **Learning:** Agent prompts improve based on human feedback
3. **Distributed execution:** Run agents across multiple VPS nodes
4. **Advanced orchestration:** Conditional task flows (pipeline)
5. **Real-time dashboards:** Web UI for monitoring
6. **Tool marketplace:** Community-contributed tools

---

## See Also

- [Enhanced Agent/Prompt Definitive](./AGENT_PROMPT_DEFINITIVE.md)
- [Runner Implementation](../runner/runner.py)
- [Agent Definitions](../agents/definitions.py)
- [BRAVE(R) Templates](../prompts/braver_templates.py)
- [Policy Pack Rules](../scoring/policy_pack.py)
- [Agent Training Masterplan](./AGENT_TRAINING_MASTERPLAN.md)
- [Real-Time Module Creation](./REALTIME_MODULE_CREATION.md)
- [Sprint Governance](./SPRINT_GOVERNANCE.md)
- [VPS Deployment](../deploy/vps/SETUP.md)
- [Local Development](./LOCAL_SETUP.md)

