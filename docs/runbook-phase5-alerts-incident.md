# Phase-5 Alerts Incident Runbook

Purpose: provide a single, fast response procedure when Phase-5 morning monitoring reports alerts.

## Trigger

Run this runbook immediately when at least one condition is true:
- morning brief verdict is ATTENTION and reason is alerts_detected
- phase5-nightly-checklist.md shows alerts_count > 0
- phase5-step9-close reports ready=True but ok=False

## Fast Start (First 10 Minutes)

1. Capture current state:
- docs/evidence/vps-worktree-hygiene/phase5-morning-brief.md
- docs/evidence/vps-worktree-hygiene/phase5-nightly-checklist.md
- runtime/ci-artifacts/phase5-nightly-checklist.json

2. Re-run strict monitor locally:
- .venv/Scripts/python.exe scripts/ops/phase5_nightly_sync.py --require-complete --auto-close-step9 --checklist-json-out runtime/ci-artifacts/phase5-nightly-checklist.json

3. Identify alert source from the Nightly Runs table and latest snapshot folder under:
- docs/evidence/vps-worktree-hygiene/phase5-drycheck-<timestamp>/

## Diagnosis Checklist

1. If porcelain_not_empty appears:
- inspect status-porcelain.txt in the failing snapshot
- on VPS run: sudo -n /opt/ctoa/scripts/ops/ctoa-root-action.sh worktree-drycheck
- verify no emergency edits were left unmirrored

2. If result_not_pass or status_not_clean appears:
- inspect summary.md and report.txt in the failing snapshot
- check VPS logs: /opt/ctoa/logs/worktree-drycheck.log

3. If branch_not_main or mirror_policy_not_satisfied appears:
- verify branch and HEAD in snapshot summary.md
- verify deploy process did not leave branch drift on VPS

4. If nightly run is missing:
- verify cron entry: sudo -n crontab -l | grep worktree-nightly-drycheck
- verify cron service active and timezone UTC on VPS

## Corrective Actions

1. Dirty worktree:
- classify changed files
- mirror emergency edits to main branch in same sprint
- re-run worktree dry-check and confirm CLEAN

2. Scheduler issues:
- reinstall cron via root action
- confirm next execution window and log append behavior

3. Data mismatch:
- re-sync snapshots with phase5_nightly_sync.py
- regenerate checklist and morning brief

## Exit Criteria

Incident is resolved only when all are true:
- checklist shows alerts_count = 0
- strict run returns no new ATTENTION alerts for root cause
- evidence updated with corrected snapshot and brief

## Escalation

Escalate to God Mode when:
- same alert repeats for 2 consecutive mornings
- unresolved alert persists beyond one sprint day
- automatic step-9 closure fails with ok=False
