# CTOA AI Toolkit

10-agent AI operating system for autonomous sprint delivery,
BRAVE(R)-driven prompting, tool-advisor scoring,
and auditable two-wave approvals.

## Command Center

| Signal | Current State |
| --- | --- |
| Baseline | v1.14.0 APPROVED |
| Release Train | Sprint-059 RELEASED (Wave-1 evidence finalized) |
| Delivery Mode | STRATEGOS (guarded autonomy) |
| Validation | `pytest` + sprint validators + CI gate chain |
| Next Action | Sprint-061 kickoff package active: 1 process KPI + 2 product KPIs |

Primary governance sources:

- [Post-GA Candidate](docs/POST_GA_DELIVERY_TRAIN_CANDIDATE.yaml)
- [Post-GA Baseline](docs/POST_GA_DELIVERY_TRAIN_BASELINE.md)
- [Roadmap v0.2.0 -> v1.0.0](docs/ROADMAP_V0.2.0_TO_V1.0.0.md)
- [Sprint-057 Release Pack](docs/history/sprints/SPRINT-057.md)
- [Sprint-057 Progress](docs/history/sprints/SPRINT-057-PROGRESS.md)
- [Track C Productization](docs/PRODUCTIZATION_TRACK_C.md)
- [Sprint-058 Plan](docs/history/sprints/SPRINT-058.md)
- [Sprint-059 Plan](docs/history/sprints/SPRINT-059.md)
- [Sprint-060 Plan](docs/history/sprints/SPRINT-060.md)
- [Sprint-060 Progress](docs/history/sprints/SPRINT-060-PROGRESS.md)
- [Sprint-061 Plan](docs/history/sprints/SPRINT-061.md)
- [Sprint-061 Progress](docs/history/sprints/SPRINT-061-PROGRESS.md)

## Azure Activity Training Status

- Active eval prompt: `azure-activity-fact-first` (confirmed by run-001, run-002, and run-003 3-variant comparisons)
- Prompt variants: [evals/prompt-variants](evals/prompt-variants)
- Run artifacts: [evals/runs/run-001](evals/runs/run-001), [evals/runs/run-002](evals/runs/run-002), [evals/runs/run-003](evals/runs/run-003)
- Editable AI Toolkit registry: [agents/toolkit/editable_agents.json](agents/toolkit/editable_agents.json)
- Aggregator: `python scripts/ops/aggregate_agent_eval.py evals/runs/run-003/results.<variant>.<model>.jsonl`
- Comparator: `python scripts/ops/compare_eval_summaries.py evals/runs/run-003/*.summary.json`

## What This Repo Does

- Orchestrates 10 specialized agents across analysis, generation,
  validation, and release governance.
- Applies BRAVE(R) prompt templates for deterministic, policy-aware execution.
- Scores tool choices using relevance/cost/risk signals before action.
- Enforces release progression with explicit evidence and wave gates.
- Produces auditable artifacts for every sprint-level decision.

## Active Product Portfolio

- CTOAi Control Center:
  [web/src/app/control-center](web/src/app/control-center) +
  [docs/REPO_SCHEMA.md](docs/REPO_SCHEMA.md)
- CTOA Control Plane:
  [mobile_console](mobile_console) +
  [scripts/ops/ctoa-vps.ps1](scripts/ops/ctoa-vps.ps1)
- CTOA Agent Execution Engine:
  [runner](runner) + [agents](agents) + [prompts](prompts)
- CTOA Release Governance:
  [workflows](workflows) + [policies](policies) +
  [runtime/experiments](runtime/experiments)
- Solteria/OTClient Helper:
  [scripts/lua/otclient](scripts/lua/otclient) +
  [P8-P16 execution roadmap](AI/P8_P16_EXECUTION_ROADMAP.md). Routine evidence
  collection uses `.\ctoa.ps1 otbg` in `BackgroundNoScreen` mode, requires an
  official promotion-bound manifest pin, and never takes over the user's game
  window. `.\ctoa.ps1 otp9` reuses that bounded lane and then runs the P9
  Conditions data-only shadow replay; it never dispatches or promotes live.
  `.\ctoa.ps1 otp10refresh` refreshes the fixed P10 doctor-to-consumer-parity
  evidence chain without IDs, confirmation, acceptance, replay, client control,
  or local-profile writes.

Product map and ownership list:

- [docs/PRODUCT_PORTFOLIO.md](docs/PRODUCT_PORTFOLIO.md)
- [docs/REPO_SCHEMA.md](docs/REPO_SCHEMA.md)
- [docs/CTOAI_FOUNDATION_CLEANUP.md](docs/CTOAI_FOUNDATION_CLEANUP.md)

Repository hygiene and private-first publication policy:

- [docs/REPO_HYGIENE_POLICY.md](docs/REPO_HYGIENE_POLICY.md)
- [Public/Private Architecture](docs/PRODUCT_PUBLIC_PRIVATE_ARCHITECTURE.md)

## Architecture At A Glance

| Area | Path | Responsibility |
| --- | --- | --- |
| Agent definitions | `agents/definitions.py` | Role model and capabilities |
| Prompt engine | `prompts/braver_templates.py` | BRAVE(R) templates |
| Tool scoring | `scoring/` | Advisor logic and scoring rules |
| Runtime execution | `runner/` | Execution, checks, orchestration |
| Governance policy | `policies/` | CI gate and release contracts |
| Workflow specs | `workflows/` | Sprint backlog and flow manifests |

## Operations

Common local commands:

```bash
python scripts/ops/ctoa_product_bootstrap.py
python scripts/ops/ctoa_update_gate.py
python -m pytest -q
python scripts/ops/sprint056_validate.py
```

VS Code task shortcuts available in this workspace:

- `CTOA: Bootstrap Product Config`
- `CTOA: Check Update Gate`
- `CTOA: Run All Tests`
- `CTOA: Sprint-042 Validate`
- `CTOA: Validate Pack`
- `CTOA: Launch Pack`

Active runbook policy:

- Active Wave-1 execution range: Sprint-027 and newer.
- Legacy range: Sprint-012 to Sprint-026 (kept for historical traceability, not part of active runbook).
- Legacy tasks can still be run manually for forensic/backfill work.

## Sprint Cadence (Post-GA)

Every sprint follows a two-wave approval model:

1. Wave-1: automated checks, validator pass, launch/test evidence.
2. Wave-2: manual sign-off recorded in the sprint release pack.
3. Baseline promotion: version moves only after Wave-2 record.

Recent approved milestones:

- v1.14.0 (Sprint-056)
- v1.13.0 (Sprint-040)
- v1.2.0 (Sprint-029)
- v1.1.1 (Sprint-028)
- v1.1.0 (Sprint-027)
- v1.0.4 (Sprint-021)
- v1.0.5 (Sprint-022)
- v1.0.6 (Sprint-023)
- v1.0.7 (Sprint-024)

## Documentation Index

- [Enhanced Agent/Prompt Definitive](docs/AGENT_PROMPT_DEFINITIVE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Core Guardrails](docs/CORE_GUARDRAILS.md)
- [Local Setup](docs/LOCAL_SETUP.md)
- [Mobile Console](docs/MOBILE_CONSOLE.md)
- [Validation Checklist](docs/VALIDATION_CHECKLIST.md)
- [Discord Agent](docs/DISCORD_AGENT.md)
- [Product Portfolio](docs/PRODUCT_PORTFOLIO.md)
- [Repo Hygiene Policy](docs/REPO_HYGIENE_POLICY.md)
- [Enhanced Top-3 Sprint Plan](docs/ENHANCED_TOP3_SPRINT_PLAN.md)
- [Azure Alerts Automation Setup](docs/azure-alerts-automation-setup.md)
- [Azure Activity Log Interpretation Runbook](docs/runbook-azure-activity-log-interpretation.md)
- [Azure Agent Eval Dataset](evals/README-azure-agent-eval-dataset.md)

## License

Private and proprietary. No permission is granted to redistribute current or
future source revisions without a separate written agreement. Historical
revisions that were previously published remain subject to the terms that
applied when those revisions were released.
