# EXP-001 Promotion Release Run Sheet - 2026-03-20

Use this run sheet to execute publication of the `EXP-001` winning package in one controlled lane.

## Scope
Active lane only:
1. `EXP-001` Prompt Quality Lift - promotion release execution

Out of scope:
1. any new experiment work
2. any mobile/UI redesign work
3. any non-essential backend expansion

## Preconditions (must all be true)
- [x] Promotion decision is `GO` in `exp-001-promotion-prep-2026-03-20.md`
- [x] Evidence bundle links are complete
- [x] Approvals captured: `qa-safety`, `ci-publisher`, `queen-ctoa`
- [x] Rollback note is explicit and actionable

## Preflight (T-15 min)
1. Confirm clean branch and latest main:
```powershell
git status --short
git pull --ff-only origin main
```
2. Open control docs:
- `docs/experiments/exp-001-promotion-prep-2026-03-20.md`
- `docs/experiments/day3-end-of-day-decision-memo-2026-03-20.md`
- `docs/VALIDATION_CHECKLIST.md`
3. Confirm release note owner and rollback owner are online.

## Execution Steps (T0)
1. `prompt-forge`
- package only the winning `EXP-001` prompt delta
- do not include unrelated changes

2. `qa-safety`
- run final focused validation on release package
- confirm no reopened safety regression

3. `ci-publisher`
- run promotion-lane pre-check and CI gate review
- confirm no blocker before publication

4. `queen-ctoa`
- record final release confirmation
- authorize publication window

## Publish Gate (must pass all)
- [ ] package scope is minimal and reversible
- [ ] QA final check = PASS
- [ ] CI gate check = PASS
- [ ] owner confirmation = PASS

If any gate fails, stop publication and switch to `HOLD`.

## Rollback Trigger (first 24h)
Trigger rollback immediately if any of these appears:
1. quality regression on monitored sample
2. operator-load spike (extra rewrite loops)
3. reproducibility degradation
4. safety confidence drop

## Rollback Action
1. revert to Day 2 baseline prompt pack
2. mark `EXP-001` state as `HOLD`
3. record incident note with timestamp and cause
4. open remediation task before next release attempt

## Monitoring Window (T+24h)
Checkpoints:
- T+1h: quick health and quality sanity check
- T+6h: operator-load and weak-output check
- T+24h: final stability decision

Outcome labels:
- `STABLE`: keep released package
- `HOLD`: keep package paused pending fixes
- `ROLLBACK`: baseline restored

## Final Close Note Template
```text
EXP-001 promotion run result: STABLE | HOLD | ROLLBACK
Timestamp: <UTC>
QA: PASS/FAIL
CI: PASS/FAIL
Owner decision: APPROVED/REJECTED
Rollback executed: YES/NO
Notes: <1-3 lines>
```
