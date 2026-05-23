# CTOA CI Executive Report

- Repository: `famatyyk/CTOAi`
- Generated at (UTC): `2026-05-22T08:18:38+00:00`

## CI Health Score

- `7d`: **37.5 / 100**

## Workflow Metrics (7d)

| Workflow | Completed | Success | Failed | Skipped | Success % (all completed) | Success % (pass/fail only) |
|---|---:|---:|---:|---:|---:|---:|
| CTOA Close On Gate | 37 | 0 | 0 | 37 | 0.0% | n/a |
| CTOA Daily Insights | 7 | 7 | 0 | 0 | 100.0% | 100.0% |
| CTOA Issue Sync | 7 | 7 | 0 | 0 | 100.0% | 100.0% |
| CTOA Pipeline | 37 | 0 | 37 | 0 | 0.0% | 0.0% |
| CTOA Status Sync | 124 | 124 | 0 | 0 | 100.0% | 100.0% |
| CTOA Weekly Report | 1 | 1 | 0 | 0 | 100.0% | 100.0% |
| site-pages | 0 | 0 | 0 | 0 | n/a | n/a |

## Top 3 Risks

1. CTOA Pipeline pass/fail success remains low at 0.0%, reducing overall delivery confidence.
2. site-pages reliability is at 0.0% pass/fail success; publication lane has low resilience.
3. Approval-gated runs can remain in waiting state and delay release throughput if review SLA is not enforced.

## Top 3 Remediation Actions

1. Pipeline hardening sprint: Run daily failure triage on `CTOA Pipeline` and target pass/fail success >= 40% in 7 days (current: 0.0%).
2. Approval SLA enforcement: Set explicit `Approval Publish` response SLA (for example 60 minutes), plus waiting-run watch and escalation.
3. Pages preflight and stability: Keep preflight checks in `site-pages` and target >= 95% pass/fail success over the next 5 runs (current: 0.0%).

## Notes

- Scores are weighted by workflow criticality.
- Pass/fail-only rate excludes skipped runs to reduce false pessimism on gate workflows.
- This report is intended for executive trend tracking and weekly remediation planning.
