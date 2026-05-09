# Real-Time Module Creation Flow

This runbook explains near-real-time module generation
and how training/skilling evidence is produced during execution.

Canonical policy source:

- [Enhanced Agent/Prompt Definitive](./AGENT_PROMPT_DEFINITIVE.md)

## Pipeline At A Glance

1. Scout intake: new server/task signal appears.
2. Ingest: source data is fetched and normalized.
3. Brain planning: module tasks are queued.
4. Generator: module files are rendered.
5. Validator: quality gates pass/fail artifacts.
6. Publisher: eligible artifacts are promoted by release criteria.

Reference:

- `runner/agents/orchestrator.py`
- `runner/agents/generator_agent.py`

## Generated Output Locations

- Local default: `generated/` (or `CTOA_GENERATED_DIR`)
- VPS default: `/opt/ctoa/generated`

## Local Real-Time Run (Developer Loop)

```bash
# 1) Start one orchestrator pass
python -m runner.agents.orchestrator

# 2) Inspect newest generated artifacts
find generated -type f -printf "%TY-%Tm-%Td %TH:%TM %p\n" | sort -r | head -40

# 3) Validate
python -m pytest tests/e2e/test_browser_smoke.py -m e2e -v
python -m pytest -q
```

## VPS Real-Time Run (Ops Loop)

```bash
# Trigger one orchestrator run
systemctl start --no-block ctoa-agents-orchestrator.service

# Follow orchestrator output
tail -n 120 /opt/ctoa/logs/agents-orchestrator.log

# Check newest generated artifacts
find /opt/ctoa/generated -type f -printf "%TY-%Tm-%Td %TH:%TM %p\n" \
   | sort -r \
   | head -40
```

## Real-Time Training/Skilling Hooks

Each pass should produce data for:

- **Training Event:** telemetry + failures + validator outcome + decision.
- **Skill Update Candidate:** prompt/tool/routing change proposal.
- **Promotion Criteria Check:** baseline comparison + gate outcome.

Cycle:

- `telemetry -> failure analysis -> prompt update`
- `A/B -> validation -> rollout`

## Minimum Validation Gates

1. Browser E2E smoke pass:
   - owner flow: login + settings + ideas
   - operator flow: owner-only settings denied
   - operator split: ideas allowed, settings denied
2. Full pytest pass (or documented non-blocking known issue)
3. No CI guardrail regression
4. Evidence set complete for GO/NO-GO

## Minimal Evidence Set per Run

1. Generated artifact sample and manifest/listing
2. Validator and test outputs
3. Delta summary vs previous stable run (quality/cost/latency)
4. Risk note and fallback/rollback path
5. Decision log pointer for Wave-1/Wave-2

## Troubleshooting Quick Map

1. No generated files:
   - Check orchestrator service/timer status.
   - Check generator/validator logs.
2. Files generated but not promotable:
   - Check failed validations and missing evidence fields.
3. UI/API mismatch:
   - Re-run browser smoke and inspect role-based responses.

Related runbooks:

- [VPS Agent Outputs](./runbook-vps-agent-outputs.md)
- [Sprint Governance](./SPRINT_GOVERNANCE.md)
