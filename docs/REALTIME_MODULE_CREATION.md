# Real-Time Script/Module Creation Flow

## Purpose
This guide shows how scripts/modules are created in near real-time in CTOA, from intake to generated files and validation output.

## Pipeline At A Glance
1. Scout intake: new server/task appears.
2. Ingest: game/domain data is fetched and normalized.
3. Brain planning: module tasks are queued.
4. Generator: module files are rendered to output directory.
5. Validator: generated artifacts pass/fail quality gates.
6. Publisher: eligible artifacts are promoted according to release criteria.

Reference orchestrator order:
- `runner/agents/orchestrator.py`

## Where Generated Files Appear
- Local default output: `generated/` (or `CTOA_GENERATED_DIR`)
- VPS output: `/opt/ctoa/generated`

Generator reference:
- `runner/agents/generator_agent.py`

## Local Real-Time Run (Developer Loop)
Use this when you want to see modules generated immediately.

```bash
# 1) Activate environment
.\.venv\Scripts\Activate.ps1

# 2) Start one pipeline pass
python -m runner.agents.orchestrator

# 3) Inspect newest generated files
Get-ChildItem -Recurse .\generated | Sort-Object LastWriteTime -Descending | Select-Object -First 20 FullName, LastWriteTime

# 4) Run browser/API smoke tests
python -m pytest tests/e2e/test_browser_smoke.py -m e2e -v
python -m pytest -q
```

## VPS Real-Time Run (Ops Loop)
Use this when 24/7 services are active and you need immediate evidence.

```bash
# Trigger one orchestrator run
systemctl start --no-block ctoa-agents-orchestrator.service

# Follow orchestrator output
tail -n 120 /opt/ctoa/logs/agents-orchestrator.log

# Check newest generated artifacts
find /opt/ctoa/generated -type f -printf "%TY-%Tm-%Td %TH:%TM %p\n" | sort -r | head -40
```

## Validation Gates
Minimum checks before considering generated output usable:
1. Browser E2E smoke passes:
   - owner flow: login + settings + ideas
   - operator flow: owner-only settings denied
   - operator split: ideas allowed, settings denied
2. Full pytest suite passes.
3. No CI guardrail regression.

## Troubleshooting Quick Map
1. No generated files:
   - Check orchestrator service/timer status.
   - Check generator/validator logs.
2. Files generated but not promotable:
   - Validate quality gate outputs and failed module status.
3. UI/API mismatch:
   - Run browser E2E smoke and inspect admin status messages.

Related runbook:
- `docs/runbook-vps-agent-outputs.md`

## Suggested Next Iteration (Execution Plan)
1. Add structured artifact manifest per run (`manifest.json`) in generated output directories.
2. Expose "latest generated modules" endpoint in mobile console with role-aware filtering.
3. Add CI artifact upload for generated module sample + validator summary.
4. Add one latency KPI: queue-to-generated time per module.
