# Phase-5 Nightly Dry-Check Checklist

generated_utc: 20260515T220051Z
overall_status: IN_PROGRESS
target_runs: 3
selected_nightly_runs: 0
pending_runs: 3
nightly_schedule_utc: 02:20 (+/- 45 min)

## Checklist

- [ ] Run 1: PENDING (no nightly snapshot in configured window)
- [ ] Run 2: PENDING (no nightly snapshot in configured window)
- [ ] Run 3: PENDING (no nightly snapshot in configured window)

## Nightly Runs

| Run | Snapshot | Timestamp UTC | Result | Status | Branch | Porcelain Empty | Mirror Policy | Alert |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | PENDING | - | - | - | - | - | - | PENDING |
| 2 | PENDING | - | - | - | - | - | - | PENDING |
| 3 | PENDING | - | - | - | - | - | - | PENDING |

## Observed Non-Nightly Runs

| Snapshot | Timestamp UTC | Result | Status | Delta To Nightly (min) |
| --- | --- | --- | --- | --- |
| phase5-drycheck-20260515T185948Z | 20260515T185948Z | PASS | CLEAN | 999 |

## Alert Rule

Alert when any nightly run has non-empty status-porcelain or summary result/status differs from PASS/CLEAN.
