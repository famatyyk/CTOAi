# Sprint-044 Plan - 3 Day Execution Window

Sprint Period: 2026-05-18 to 2026-05-20
Status: PLANNED (kickoff baseline prepared 2026-05-15)
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
