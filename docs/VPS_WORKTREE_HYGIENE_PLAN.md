# VPS Dirty Worktree Hygiene Plan (Non-Destructive)

Date: 2026-05-15
Scope: /opt/ctoa on production VPS
Goal: Restore predictable update flow without destructive git operations.

## Principles

- Do not run git reset --hard.
- Do not delete unknown files without backup.
- Capture audit trail before each mutation.

## Phase 1 - Inventory and Evidence

1. Snapshot current repository state:
   - git -C /opt/ctoa status --short
   - git -C /opt/ctoa branch --show-current
   - git -C /opt/ctoa rev-parse HEAD
2. Export full diff and untracked list to timestamped artifacts in /opt/ctoa/runtime/evidence/worktree-hygiene/.
3. Tag every local change as one of:
   - keep-and-commit
   - keep-but-stash
   - archive-and-remove

## Phase 2 - Safe Preservation

1. Create immutable backup bundle before any cleanup:
   - tar czf /opt/ctoa/runtime/evidence/worktree-hygiene/pre-clean-<ts>.tar.gz <changed paths>
2. For changes not ready to commit, create named stashes (including untracked):
   - git -C /opt/ctoa stash push -u -m "hygiene:<category>:<ts>"
3. For operational scripts edited directly on VPS, copy to /opt/ctoa/runtime/evidence/worktree-hygiene/manual-edits/<ts>/.

## Phase 3 - Reconcile with Main (Fast-Forward Only)

1. Enforce safe.directory for root and service users.
2. Use only:
   - git -C /opt/ctoa fetch origin main
   - git -C /opt/ctoa pull --ff-only origin main
3. If pull is blocked, stop and classify blockers; never force overwrite.

## Phase 4 - Controlled Re-apply

1. Re-apply stashed changes one group at a time:
   - git -C /opt/ctoa stash apply <stash>
2. After each apply:
   - run targeted validation task(s)
   - commit immediately if valid
3. Keep unrelated local edits isolated in separate commits.

## Phase 5 - Guardrails to Prevent Regression

1. Add a nightly dry-check job:
   - git -C /opt/ctoa status --porcelain should be empty.
2. Add a pre-update gate in VPS scripts that aborts update when worktree is dirty and writes actionable report. (DONE in Sprint-046)
3. Require any emergency VPS edit to be mirrored to main within one sprint cycle.

## Immediate Next Actions

1. [x] Run Phase 1 inventory and publish evidence bundle. (DONE)
2. [x] Classify current dirty files with owners. (DONE)
3. [x] Implement and verify pre-update dirty-worktree gate. (DONE)
4. [x] Execute Phase 2 backups and stashes before next sprint pull attempt. (DONE: 20260515T140911Z)
5. [x] Proceed to Phase 3 fast-forward reconcile only. (DONE: 20260515T141636Z)
6. [x] Prepare controlled re-apply map, checkpoints, and rollback plan for Phase 4. (DONE: 20260515T141731Z)

7. [x] Execute Phase 4 controlled re-apply on VPS (group-by-group with validation). (DONE: 20260515T143659Z)



8. [x] Proceed to Phase 5 guardrails hardening and nightly cleanliness enforcement. (DONE: 20260515T185948Z)
9. [ ] Monitor first 3 nightly dry-check runs and alert on any non-empty porcelain status. (ACTIVE NEXT STEP; one-command runner: scripts/ops/phase5_nightly_sync.py)

