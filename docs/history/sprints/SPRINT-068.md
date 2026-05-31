# SPRINT-068

## Mission
Harden the delivery/governance closure path by locking validator CLI contracts, wave-summary artifact behavior, and sprint evidence documentation.

## Scope
- Validator CLI and fail-path contract hardening (`CTOA-335`)
- Wave summary UTF-8 artifact contract hardening (`CTOA-336`)
- Governance-loop docs and evidence alignment (`CTOA-337`)

## Definition Of Done
- Sprint-068 validator passes with all required contract checks.
- Local tasks and CI wiring are present for Sprint-068 delivery gate and evidence upload.
- Progress artifact is generated from `workflows/backlog-sprint-068.yaml`.
- Wave summary artifact contract is covered by tests and CI-consumable.

## Deliverables
- `workflows/backlog-sprint-068.yaml`
- `workflows/sprint-068-delivery-flow.yaml`
- `docs/history/sprints/SPRINT-068-PROGRESS.md`
- `scripts/ops/sprint068_validate.py`
- `.vscode/tasks.json` Sprint-068 task wiring
- `.github/workflows/ctoa-pipeline.yml` Sprint-068 gate and evidence upload wiring

## Risks
- CLI contract drift between validator scripts and CI consumers.
- Artifact schema mismatch between runtime generators and governance gates.
- Incomplete doc/evidence linkage causing weak Wave-1 traceability.

## Gate Policy
- Wave-1: automated validator + summary + docs/evidence checks pass.
- Wave-2: manual STRATEGOS sign-off.
