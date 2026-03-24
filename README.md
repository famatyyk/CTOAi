# CTOA AI Toolkit

10-agent AI operating system for autonomous sprint delivery, BRAVE(R)-driven prompting, tool-advisor scoring, and auditable two-wave approvals.

## Command Center

| Signal | Current State |
|---|---|
| Baseline | v1.1.1 APPROVED |
| Release Train | Sprint-028 closed (Wave-1 PASS, Wave-2 RECORDED) |
| Delivery Mode | STRATEGOS (guarded autonomy) |
| Validation | `pytest` + sprint validators + CI gate chain |
| Next Action | Start productization track for configurable public toolkit packaging |

Primary governance sources:
- [Post-GA Candidate](docs/POST_GA_DELIVERY_TRAIN_CANDIDATE.yaml)
- [Post-GA Baseline](docs/POST_GA_DELIVERY_TRAIN_BASELINE.md)
- [Roadmap v0.2.0 -> v1.0.0](docs/ROADMAP_V0.2.0_TO_V1.0.0.md)
- [Sprint-028 Release Pack](runtime/experiments/sprint-028/CTOA-142.md)

## What This Repo Does

- Orchestrates 10 specialized agents across analysis, generation, validation, and release governance.
- Applies BRAVE(R) prompt templates for deterministic, policy-aware execution.
- Scores tool choices using relevance/cost/risk signals before action.
- Enforces release progression with explicit evidence and wave gates.
- Produces auditable artifacts for every sprint-level decision.

## Active Product Portfolio

- CTOA Control Plane: [mobile_console](mobile_console) + [scripts/ops/ctoa-vps.ps1](scripts/ops/ctoa-vps.ps1)
- CTOA Agent Execution Engine: [runner](runner) + [agents](agents) + [prompts](prompts)
- CTOA Release Governance: [workflows](workflows) + [policies](policies) + [runtime/experiments](runtime/experiments)

Product map and ownership list:
- [docs/PRODUCT_PORTFOLIO.md](docs/PRODUCT_PORTFOLIO.md)

Repository hygiene and publication policy:
- [docs/REPO_HYGIENE_POLICY.md](docs/REPO_HYGIENE_POLICY.md)

## Architecture At A Glance

| Area | Key Path | Responsibility |
|---|---|---|
| Agent definitions | [agents/definitions.py](agents/definitions.py) | Agent role model and capabilities |
| Prompt engine | [prompts/braver_templates.py](prompts/braver_templates.py) | BRAVE(R) decision templates |
| Tool scoring | [scoring](scoring) | Advisor logic and scoring rules |
| Runtime execution | [runner](runner) | Execution, checks, and orchestration |
| Governance policy | [policies](policies) | CI gate and release policy contracts |
| Workflow specs | [workflows](workflows) | Sprint backlog and flow manifests |

## Operations

Common local commands:

```bash
python -m pytest -q
python scripts/ops/sprint023_validate.py
```

VS Code task shortcuts available in this workspace:
- `CTOA: Run All Tests`
- `CTOA: Sprint-024 Validate Release Scalability`
- `CTOA: Validate Pack`
- `CTOA: Launch Pack`

## Sprint Cadence (Post-GA)

Every sprint follows a two-wave approval model:

1. Wave-1: automated checks, validator pass, launch/test evidence.
2. Wave-2: manual sign-off recorded in the sprint release pack.
3. Baseline promotion: version moves only after Wave-2 record.

Recent approved milestones:
- v1.1.1 (Sprint-028)
- v1.1.0 (Sprint-027)
- v1.0.4 (Sprint-021)
- v1.0.5 (Sprint-022)
- v1.0.6 (Sprint-023)
- v1.0.7 (Sprint-024)

## Documentation Index

- [Architecture](docs/ARCHITECTURE.md)
- [Core Guardrails](docs/CORE_GUARDRAILS.md)
- [Local Setup](docs/LOCAL_SETUP.md)
- [Mobile Console](docs/MOBILE_CONSOLE.md)
- [Validation Checklist](docs/VALIDATION_CHECKLIST.md)
- [Discord Agent](docs/DISCORD_AGENT.md)
- [Product Portfolio](docs/PRODUCT_PORTFOLIO.md)
- [Repo Hygiene Policy](docs/REPO_HYGIENE_POLICY.md)
- [Enhanced Top-3 Sprint Plan](docs/ENHANCED_TOP3_SPRINT_PLAN.md)

## License

MIT
