# CI Remediation Plan (7 Days)

This plan targets the three current CI risks:
1. Low pass/fail success for `CTOA Pipeline`
2. Approval waiting bottlenecks
3. Limited `site-pages` reliability margin

## Day-by-Day Plan

| Day | Owner | Focus | KPI Target | Exit Check |
|---|---|---|---|---|
| Day 1 | `pm-roadmap`, `qa-safety` | Failure triage baseline for last 20 pipeline runs | Failure causes mapped >= 95% | Triage log complete |
| Day 2 | `builder-engine`, `qa-safety` | Remove avoidable false-fail patterns in checks | Pipeline pass/fail >= 20% | 1st hardening patch merged |
| Day 3 | `ci-publisher`, `queen-ctoa` | Approval SLA and waiting-run escalation | Waiting approvals > 60 min = 0 unresolved | SLA doc + reminder loop active |
| Day 4 | `builder-engine`, `tool-advisor` | Stabilize `site-pages` preflight and publish path | Next 2 pages runs = 100% | Preflight validation stable |
| Day 5 | `qa-safety`, `pm-roadmap` | Regression audit on recent fixes, including response guardrail summaries in CI and PR runs | No critical regression introduced | QA regression report approved |
| Day 6 | `ci-publisher`, `evaluator` | Executive score recalibration and trend check | 7d CI Health Score +10 points vs Day 1 baseline | Trend report generated |
| Day 7 | `queen-ctoa`, `pm-roadmap` | Final go/hold/kill for remediation items | Pipeline pass/fail >= 40% or explicit hold decision | Weekly decision memo closed |

## Daily KPI Dashboard (Minimum)

| KPI | Owner | Measurement |
|---|---|---|
| Pipeline pass/fail success % | `qa-safety` | `CTOA Pipeline` success / (success + failed) |
| Waiting approval count | `ci-publisher` | Number of `Approval Publish` jobs in waiting > 60 min |
| Pages pass/fail success % | `builder-engine` | `site-pages` success / (success + failed) |
| CI Health Score (7d) | `evaluator` | Weighted score from executive report script |

## Decision Gates
1. If pipeline pass/fail success is below 25% by Day 4, pause new experiment rollout and prioritize CI hardening only.
2. If waiting approvals are not within SLA by Day 5, escalate to owner and reduce approval-gated merge frequency.
3. If pages success is below 80% by Day 6, lock site deployment changes until preflight failures are eliminated.
