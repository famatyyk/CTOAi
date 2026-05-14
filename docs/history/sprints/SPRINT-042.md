# Sprint-042 Plan - 3 Day Execution Window

Sprint Period: 2026-05-15 to 2026-05-17
Status: RELEASED (Wave-2 sign-off completed 2026-05-15)
Theme: Governance enforcement + least-privilege hardening + UI continuity
Backlog File: workflows/backlog-sprint-042.yaml
Delivery Flow: workflows/sprint-042-delivery-flow.yaml

---

## Sprint Goal

Complete a short hardening sprint that closes governance gaps, narrows privileged VPS access,
proves backup restore readiness, and protects recent login/navigation UX fixes with regression coverage.

## Day-by-Day Task List (Owners + Done)

### Day 1 - Governance and Control-Plane Foundation

| Task ID | Task | Primary Owner | Supporting Owner(s) | Done Criteria |
|---|---|---|---|---|
| CTOA-208 | Enforce PR quality gates and bypass governance policy | strategos | core-architect, qa-terminator | Governance docs updated, PR Quality Report requirement captured, bypass path documented |
| CTOA-209 | Create Sprint-042 validator and local wave task wiring | qa-terminator | core-architect | Validator script created, VS Code sprint tasks added, validation artifact generated |

### Day 2 - Security and Reliability Hardening

| Task ID | Task | Primary Owner | Supporting Owner(s) | Done Criteria |
|---|---|---|---|---|
| CTOA-210 | Least-privilege sudo phase 2 with wrappers | security-guardian | devops-master | Default generic root shell path removed, wrapper allowlist enforced, one-shot health check passes |
| CTOA-211 | Backup restore drill and retention evidence | devops-master | qa-terminator | Restore dry-run completes, retention policy verified, evidence artifact produced |

### Day 3 - UX Regression Shield + Gates

| Task ID | Task | Primary Owner | Supporting Owner(s) | Done Criteria |
|---|---|---|---|---|
| CTOA-212 | Cross-surface navigation and auth-header regression coverage | code-smith | qa-terminator | Shared navigation active on start/console/live pages, login header toggles correctly, regression test passes |
| CTOA-213 | Sprint-042 Wave-1 evidence run | qa-terminator | strategos | Focused tests PASS, sprint042 validator PASS, evidence bundle saved |
| CTOA-214 | Sprint-042 Wave-2 sign-off and release memo | strategos | core-architect, documentation-sage | Manual approval note recorded, rollback baseline confirmed, release memo published |

---

## Definition of Done for Sprint-042

1. All tasks CTOA-208..CTOA-214 reach WAITING_APPROVAL or RELEASED.
2. Wave-1 artifacts exist and show PASS for validator and focused regressions.
3. Wave-2 decision log includes owner accountability and rollback baseline.
4. Updated governance/ops/ui documents are linked from sprint report.

## Risks and Mitigations

- Risk: sudo hardening blocks operational scripts.
  - Mitigation: wrapper map and immediate rollback path in delivery flow.
- Risk: UI fixes regress under auth/session edge cases.
  - Mitigation: add dedicated regression test in Sprint-042 scope.
- Risk: backup appears healthy but restore is unverified.
  - Mitigation: mandatory restore drill artifact before Wave-1 PASS.

## Kickoff Commands

1. Set active backlog on VPS environment to workflows/backlog-sprint-042.yaml.
2. Pull latest main branch on VPS.
3. Run control tick and verify new backlog_id in runtime task state.
4. Execute Wave-1 run once Day 3 tasks are complete.

## Execution Outcome (Wave-2)

### Task Status Snapshot

| Task ID | Status | Evidence |
|---|---|---|
| CTOA-208 | RELEASED | docs/SPRINT_GOVERNANCE.md, docs/VALIDATION_CHECKLIST.md |
| CTOA-209 | RELEASED | scripts/ops/sprint042_validate.py, runtime/ci-artifacts/sprint-042-validation.json |
| CTOA-210 | RELEASED | deploy/vps/sudoers/90-ctoa-admin, deploy/vps/wrappers/ctoa-root-action.sh, deploy/vps/runbook-wrapper-map.md |
| CTOA-211 | RELEASED | runtime/ci-artifacts/sprint-042-restore-drill.json |
| CTOA-212 | RELEASED | tests/test_sprint042_auth_header_navigation.py |
| CTOA-213 | RELEASED | runtime/ci-artifacts/sprint-042-wave1-run.log, runtime/ci-artifacts/sprint-042-validation.json |
| CTOA-214 | RELEASED | runtime/experiments/sprint-042/CTOA-214.md |

### Wave-1 Gate Result

- Focused regression tests: PASS (18 passed).
- Sprint validator: PASS (11/11 checks passed).
- Evidence bundle generated under runtime/ci-artifacts.

### Wave-2 Decision Summary

- Decision: Sprint-042 released after Wave-2 sign-off.
- Rollback baseline: v1.13.0.
- Owner accountability: Strategos (primary), Core Architect and Documentation Sage (review).
- Residual risks: no critical blockers observed; standard post-release monitoring retained.
