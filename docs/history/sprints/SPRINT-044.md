# Sprint-044 Plan - 3 Day Execution Window

Sprint Period: 2026-05-18 to 2026-05-20
Status: IN_PROGRESS (CTOA-221..225 RELEASED on 2026-05-15; CTOA-226 WAITING_APPROVAL)
Theme: Operational drift prevention + control-plane regression coverage + governance-ready closure
Backlog File: workflows/backlog-sprint-044.yaml
Delivery Flow: workflows/sprint-044-delivery-flow.yaml

---

## Sprint Goal

Open Sprint-044 with a stable kickoff baseline that prevents backlog drift recurrence,
adds targeted regression coverage for control tick behavior, and prepares the standard
Wave-1 and Wave-2 governance path.

## Day-by-Day Task List (Owners + Done)

### Day 1 - Kickoff Baseline and Drift Guard Setup

| Task ID | Task | Primary Owner | Supporting Owner(s) | Done Criteria |
|---|---|---|---|---|
| CTOA-221 | Open Sprint-044 kickoff baseline and carry-over risk ledger | strategos | core-architect | Backlog + flow + sprint baseline published and aligned |
| CTOA-222 | Harden VPS service backlog selection against drift | devops-master | security-guardian | Runner/report service paths verified with no hardcoded sprint override |

### Day 2 - Quality Wiring and Regression Shield

| Task ID | Task | Primary Owner | Supporting Owner(s) | Done Criteria |
|---|---|---|---|---|
| CTOA-223 | Create Sprint-044 validator and local wave task wiring | qa-terminator | core-architect | Validator artifact generated, wave task chain ready |
| CTOA-224 | Add targeted regression coverage for control tick and backlog parsing | code-smith | qa-terminator | Regression tests pass and evidence artifact produced |

### Day 3 - Governance Gates and Closure

| Task ID | Task | Primary Owner | Supporting Owner(s) | Done Criteria |
|---|---|---|---|---|
| CTOA-225 | Sprint-044 Wave-1 evidence run | qa-terminator | strategos | Focused tests PASS, validator PASS, evidence bundle complete |
| CTOA-226 | Sprint-044 Wave-2 sign-off and release memo | strategos | core-architect, documentation-sage | Manual sign-off memo recorded with rollback baseline |

---

## Definition of Done for Sprint-044

1. All tasks CTOA-221..CTOA-226 reach WAITING_APPROVAL or RELEASED.
2. Runner/report backlog selection is validated without hardcoded sprint drift.
3. Wave-1 evidence includes PASS for focused tests, sprint044 validator, and targeted regressions.
4. Wave-2 sign-off records owner accountability, residual risks, and rollback baseline.

## Risks and Mitigations

- Risk: backlog drift reappears through unit-level environment overrides.
  - Mitigation: explicit drift guard task with service-level verification and runbook update.
- Risk: control tick behavior regresses under malformed or missing backlog files.
  - Mitigation: dedicated regression scope in Sprint-044 with evidence artifact.
- Risk: validator/wave wiring lands late and compresses governance window.
  - Mitigation: complete validator work on Day 2 and run dry checks before Wave-1.

## Kickoff Baseline Commands

1. Set active backlog on VPS to workflows/backlog-sprint-044.yaml.
2. Pull latest main branch on VPS.
3. Run control tick and verify backlog_id is sprint-044 in runtime task state.
4. Verify runner/report services read backlog path from approved environment source.
5. Execute Wave-1 run after CTOA-221..224 completion.


## Execution Outcome (CTOA-222/223 Formal Closure)

### Task Status Snapshot

| Task ID | Status | Evidence |
|---|---|---|
| CTOA-221 | RELEASED | runtime/ci-artifacts/sprint-044-ctoa-222-vps-evidence.log, runtime/experiments/sprint-044/CTOA-222.md |
| CTOA-222 | RELEASED | runtime/ci-artifacts/sprint-044-ctoa-222-vps-evidence.log, runtime/experiments/sprint-044/CTOA-222.md |
| CTOA-223 | RELEASED | scripts/ops/sprint044_validate.py, .vscode/tasks.json, runtime/ci-artifacts/sprint-044-validation.json, runtime/ci-artifacts/sprint-044-wave1-run.log, runtime/experiments/sprint-044/CTOA-223.md |

### CTOA-222 Evidence Summary

- Correct VPS host verified: 116.202.96.250.
- Runner/report unit overrides point to backlog-sprint-044 in systemd unit definitions.
- /opt/ctoa/.env and runtime/task-state confirm backlog sprint-044.
- validate-services run completed with runner/report status=0 and live status backlog=sprint-044.

### CTOA-223 Evidence Summary

- Sprint-044 validator PASS (11/11 checks passed).
- Wave run evidence PASS: full local tests 129 passed, 6 skipped; launch dry-run PASS.
- Sprint-044 task and CI wiring validated in .vscode/tasks.json and .github/workflows/ctoa-pipeline.yml.

### Governance Decision

- Manual approvals executed for CTOA-221, CTOA-222, and CTOA-223 at 2026-05-15T02:16:38Z.
- Sprint remained IN_PROGRESS while CTOA-224..226 proceeded through Wave-1 and Wave-2 gates.


## Execution Outcome (CTOA-224/225 Wave-1 Sign-Off)

### Task Status Snapshot

| Task ID | Status | Evidence |
|---|---|---|
| CTOA-224 | RELEASED | tests/test_runner_backlog_selection.py, tests/test_sprint044_control_tick.py, runtime/ci-artifacts/sprint-044-regression.json, runtime/experiments/sprint-044/CTOA-224.md |
| CTOA-225 | RELEASED | runtime/ci-artifacts/sprint-044-wave1-run.log, runtime/ci-artifacts/sprint-044-validation.json, runtime/ci-artifacts/sprint-044-regression.json, runtime/experiments/sprint-044/CTOA-225.md |

### Wave-1 Gate Result

- Full local tests: PASS (129 passed, 6 skipped).
- Sprint-044 validator: PASS (11/11 checks passed).
- Targeted regressions: PASS (7 passed).
- Launch pack dry-run: PASS (launch_allowed).

### Governance Decision

- Manual approvals executed for CTOA-224 and CTOA-225 after WAITING_APPROVAL on VPS.
- Runtime status now shows RELEASED=5 and WAITING_APPROVAL=1 (CTOA-226 only).
