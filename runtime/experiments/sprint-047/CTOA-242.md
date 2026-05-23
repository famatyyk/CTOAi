# CTOA-242 - Controlled Re-Apply Plan for Stashed VPS Changes (Phase-4 Readiness)

Date: 2026-05-15
Result: PASS (readiness plan prepared)

## Inputs

- stash_top: stash@{0}: On main: hygiene:phase2:20260515T140911Z
- phase2_changed_entries: 24
- phase4_readiness_top_path_count: 6 (tracked subset from stash show)

## Stash Group Map and Safe Re-Apply Order

1. Group A - governance docs and workflows
- paths: docs/CONSISTENCY_REPORT.md, docs/history/sprints/SPRINT-043.md, docs/history/sprints/SPRINT-044.md, workflows/backlog-sprint-042.yaml, workflows/backlog-sprint-043.yaml, workflows/backlog-sprint-044.yaml, workflows/backlog-sprint-045.yaml, workflows/sprint-042-delivery-flow.yaml, workflows/sprint-043-delivery-flow.yaml, workflows/sprint-044-delivery-flow.yaml, workflows/sprint-045-delivery-flow.yaml
- reason: lowest runtime risk, fastest reconciliation signal.

2. Group B - operational scripts
- paths: deploy/vps/rotate-mobile-token.sh, deploy/vps/backup-nightly.sh, scripts/ops/ctoa-root-action.sh
- reason: medium risk, affects automation and maintenance flows.

3. Group C - dashboard and mobile console UI
- paths: docs/site/live-dashboard.html, mobile_console/static/app.js, mobile_console/static/index.html
- reason: runtime-facing behavior and observability UX.

4. Group D - runbooks and validation checklists
- paths: docs/VALIDATION_CHECKLIST.md, docs/runbook-disk-emergency.md
- reason: procedural alignment after code/script updates.

5. Group E - backup artifacts and archives
- paths: backups/config/ctoa-config-20260514T202059Z.tar.gz, backups/config/ctoa-config-20260514T222256Z.tar.gz, backups/config/ctoa-config-20260515T025151Z.tar.gz, backups/db/ctoa-db-20260514T202059Z.sql.gz, backups/db/ctoa-db-20260514T222256Z.sql.gz
- reason: keep archival assets isolated from functional rollout.

## Validation Checkpoints Per Group

1. Before each group re-apply
- checkpoint: record git status --short and git rev-parse --short HEAD to evidence file.
- method: use git stash apply (not pop) for trial; drop stash only after group commit is verified.

2. Group A validation
- run: .venv/Scripts/python.exe scripts/ops/sprint047_validate.py --json-out runtime/ci-artifacts/sprint-047-validation.json
- pass criteria: validator PASS and no schema/task wiring regressions.

3. Group B validation
- run: bash -n deploy/vps/rotate-mobile-token.sh deploy/vps/backup-nightly.sh scripts/ops/ctoa-root-action.sh
- pass criteria: shell syntax clean and no permission/ownership regressions in script metadata.

4. Group C validation
- run: CTOA: VPS Dashboard Snapshot and CTOA: Start Mobile Console (local baseline)
- pass criteria: dashboard snapshot succeeds and static assets load without runtime errors.

5. Group D validation
- run: docs link/consistency check via Sprint validator.
- pass criteria: references resolve and governance instructions remain coherent.

6. Group E validation
- run: integrity check with file existence and archive listing metadata only.
- pass criteria: backup artifacts preserved, no accidental overwrite.

## Rollback Points

1. Create pre-group rollback tag or note
- format: phase4-pre-group-<A..E>-<timestamp>

2. If a group fails validation
- rollback: git restore --source=HEAD -- <group paths>
- keep stash intact for reattempt and update blocker note.

3. Commit isolation
- one commit per successful group with explicit scope in commit message.

4. Final stash cleanup
- only after all groups are committed and verified: git stash drop stash@{0}

## Evidence

- docs/evidence/vps-worktree-hygiene/phase2-20260515T140911Z/changed-paths.txt
- docs/evidence/vps-worktree-hygiene/phase4-readiness-20260515T141731Z/summary.md
- docs/evidence/vps-worktree-hygiene/phase4-readiness-20260515T141731Z/grouped-paths.json
- docs/evidence/vps-worktree-hygiene/phase4-readiness-20260515T141731Z/stash-top-name-status.txt
