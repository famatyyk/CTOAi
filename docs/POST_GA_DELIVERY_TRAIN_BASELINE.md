# Post-GA Delivery Train Baseline

Canonical baseline for post-GA release governance.

## Baseline
- Baseline tag: v1.14.0
- Active sprint: Sprint-042
- Governance mode: two-wave approvals (Wave-1 automated, Wave-2 manual)
- Last promotion: v1.13.0 → v1.14.0 (2026-05-18 Sprint-041 CTOA-203..207)

## Recent Release History

### v1.14.0 (Sprint-041: Track C Productization)
- **Date**: 2026-05-18
- **Items**: CTOA-203, CTOA-204, CTOA-205, CTOA-206, CTOA-207
- **Focus**: Package tiering validation, public/private surface hygiene, operator UX release cadence
- **Wave-1**: 153 passed, 6 skipped (exceeds baseline) ✅
- **Wave-2**: STRATEGOS signed approval ✅
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

## Next Sprint (Sprint-042)

Sprint-042 backlog coming soon. Expected focus areas:
- Continued productization track
- Operator adoption workflow
- Infrastructure hardening (Phase-5+ evolution)

Monitor: `workflows/backlog-sprint-042.yaml` (TBD)
