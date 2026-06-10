# Phase-5 Nightly Dry-Check Checklist

generated_utc: 20260609T051016Z
overall_status: ATTENTION
target_runs: 3
selected_nightly_runs: 3
pending_runs: 0
nightly_schedule_utc: 02:20 (+/- 45 min)

## Checklist

- [x] Run 1: phase5-drycheck-20260516T022001Z at 20260516T022001Z (OK)
- [ ] Run 2: phase5-drycheck-20260517T022001Z at 20260517T022001Z (ALERT)
- [ ] Run 3: phase5-drycheck-20260518T022001Z at 20260518T022001Z (ALERT)

## Nightly Runs

| Run | Snapshot | Timestamp UTC | Result | Status | Branch | Porcelain Empty | Mirror Policy | Alert |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | phase5-drycheck-20260516T022001Z | 20260516T022001Z | PASS | CLEAN | main | True | SATISFIED | NONE |
| 2 | phase5-drycheck-20260517T022001Z | 20260517T022001Z | FAIL | DIRTY | main | False | REQUIRED_WITHIN_ONE_SPRINT | result_not_pass,status_not_clean,mirror_policy_not_satisfied,porcelain_not_empty |
| 3 | phase5-drycheck-20260518T022001Z | 20260518T022001Z | FAIL | DIRTY | main | False | REQUIRED_WITHIN_ONE_SPRINT | result_not_pass,status_not_clean,mirror_policy_not_satisfied,porcelain_not_empty |

## Observed Non-Nightly Runs

| Snapshot | Timestamp UTC | Result | Status | Delta To Nightly (min) |
| --- | --- | --- | --- | --- |
| phase5-drycheck-20260515T185948Z | 20260515T185948Z | PASS | CLEAN | 999 |

## Alert Rule

Alert when any nightly run has non-empty status-porcelain or summary result/status differs from PASS/CLEAN.
