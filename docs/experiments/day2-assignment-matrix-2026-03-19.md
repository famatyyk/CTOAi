# Day 2 Assignment Matrix - 2026-03-19

## Scope
Active experiments for Day 2:
1. `EXP-001` Prompt Quality Lift
2. `EXP-002` Tool Routing Efficiency

Hold experiment:
1. `EXP-003` Landing Telemetry and UX Signal

## Timeboxes (CET)
- Kickoff sync: 09:00-09:20
- Build baseline: 09:20-11:00
- Build challenger: 11:00-13:00
- Validation and scoring: 14:00-16:30
- Decision checkpoint: 16:30-17:00

## Assignment Matrix
| Agent | EXP | Responsibility | Deliverable | Deadline |
|------|-----|----------------|-------------|----------|
| `queen-ctoa` | 001, 002 | Scope enforcement and final go/no-go on Day 2 outcomes | Day 2 decision note | 17:00 |
| `pm-roadmap` | 001, 002 | Work breakdown, owner tracking, blocker triage | Updated matrix + blocker log | 10:00, 15:30 |
| `prompt-forge` | 001 | Baseline and challenger prompt sets | Prompt pack A (baseline), Prompt pack B (challenger) | 11:30 |
| `tool-advisor` | 002 | Prepare routing/scoring challenger variants | Ranking variant set with rationale | 11:30 |
| `mmo-intel` | 001, 002 | Domain relevance and risk context for task samples | Domain risk and relevance brief | 12:00 |
| `lua-scripter` | 001 | Define code-centric quality checks for prompt outputs | Lua quality checklist + sample outputs review | 14:30 |
| `bot-architect` | 002 | Evaluate architecture impact of routing variants | Routing complexity and coupling review | 14:30 |
| `builder-engine` | 001, 002 | Execute controlled trial runs for baseline/challenger | Run log and comparison table | 15:30 |
| `qa-safety` | 001, 002 | Validate failure thresholds and safety regressions | QA pass/fail matrix | 16:00 |
| `ci-publisher` | 001, 002 | Pre-check promotion readiness criteria | Promotion readiness checklist | 16:15 |

## Checkpoint Criteria at 16:30
- `EXP-001` can continue only if quality or operator-load metric improves with no safety regression.
- `EXP-002` can continue only if routing reduces retries or cycle-time with no risk regression.
- Any inconclusive result remains `hold` unless an explicit Day 3 re-scope is approved.

## Day 2 Expected Outputs
1. Baseline vs challenger evidence package for `EXP-001`.
2. Baseline vs challenger evidence package for `EXP-002`.
3. Updated `go/hold/kill` recommendation for both experiments.
