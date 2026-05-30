# Post-GA Delivery Train Baseline

Canonical baseline for post-GA release governance.

## Baseline
- Baseline tag: v1.14.0
- Active sprint: Sprint-059 (planning kickoff)
- Governance mode: two-wave approvals (Wave-1 automated, Wave-2 manual)
- Last promotion: v1.13.0 -> v1.14.0 (2026-05-18 Sprint-041 CTOA-203..207)

## Recent Release History

### v1.14.0 (Sprint-041: Track C Productization)
- **Date**: 2026-05-18
- **Items**: CTOA-203, CTOA-204, CTOA-205, CTOA-206, CTOA-207
- **Focus**: Package tiering validation, public/private surface hygiene, operator UX release cadence
- **Wave-1**: 153 passed, 6 skipped (exceeds baseline) [PASS]
- **Wave-2**: STRATEGOS signed approval [PASS]
- **Risk**: GREEN (no blockers)
- **Evidence**: `runtime/experiments/sprint-041/WAVE-{1,2}-*.md`

### v1.13.0 (Sprint-040: Continuous Quality + Delivery + Governance)
- **Date**: 2026-05-10
- **Items**: CTOA-200..202
- **Focus**: Release pack v1.13.0, governance baseline stabilization

## Required Evidence
- CI run URL
- Validator output
- Release artifact contract validation
- Decision log for Wave-1 and Wave-2

## Ownership
- STRATEGOS: final Wave-2 approval + baseline promotion authority
- QA/DevOps: Wave-1 gate evidence
- God Mode: async scope/budget/timeline oversight

## Active Sprint Transition

Sprint-058 execution is complete and released; transition is now toward Sprint-059 planning kickoff.
- Last completed scope: `workflows/backlog-sprint-058.yaml`
- Last completed flow: `workflows/sprint-058-delivery-flow.yaml`
- Proposed release: `v1.15.0`
- Status: `TRANSITION_TO_SPRINT_059`

Sprint files with higher numbers should be treated as pre-planning unless they are explicitly marked ACTIVE and wired into validators/tasks.