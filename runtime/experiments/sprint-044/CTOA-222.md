# CTOA-222 Closure Memo (Sprint-044)

Date (UTC): 2026-05-15T02:16:38Z
Decision: RELEASED
Owners: devops-master (primary), security-guardian (review), strategos (approval)

## Objective

Eliminate backlog drift risk on the active VPS by enforcing Sprint-044 as the runtime backlog source across runner/report execution paths.

## Evidence

- Correct host used for remediation: 116.202.96.250.
- Unit-level backlog configuration aligned:
  - /etc/systemd/system/ctoa-runner.service -> Environment=CTOA_BACKLOG_FILE=/opt/ctoa/workflows/backlog-sprint-044.yaml
  - /etc/systemd/system/ctoa-report.service -> Environment=CTOA_BACKLOG_FILE=/opt/ctoa/workflows/backlog-sprint-044.yaml
- Environment-level backlog configuration aligned:
  - /opt/ctoa/.env contains CTOA_BACKLOG_FILE=/opt/ctoa/workflows/backlog-sprint-044.yaml
- Runtime state aligned:
  - /opt/ctoa/runtime/task-state.yaml contains backlog_id: sprint-044
- Service validation evidence:
  - runtime/ci-artifacts/sprint-044-ctoa-222-vps-evidence.log
  - validate-services run returned runner/report success status (status=0)

## Operational Notes

- During cutover, runner failures were traced to a malformed remote backlog overwrite.
- Canonical Sprint-044 backlog was redeployed in a VPS-compatible form to stabilize parser behavior on the current runner version.
- Timers remained enabled and active after remediation.

## Risk Assessment

- Residual risk: low.
- Remaining safeguard: keep unit backlog path checks in Sprint-044 regression scope (CTOA-224).
