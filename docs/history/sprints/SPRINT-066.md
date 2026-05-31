# Sprint-066 Plan - 3 Day Execution Window

Status: IN_PROGRESS
Theme: Sprint-066 packaging + release hardening
Window: 2026-06-13 -> 2026-06-15
Backlog: workflows/backlog-sprint-066.yaml
Flow: workflows/sprint-066-delivery-flow.yaml

## Sprint Mission

Sprint-066 closes the last mile of productization:
- signed release/update manifests,
- simpler bootstrap UX,
- cleaner public/private boundaries and refreshed product docs.

## Task Matrix

| Task ID | Title | Owner | Support | Exit Signal |
| --- | --- | --- | --- | --- |
| CTOA-329 | Release/update manifest signing and launch gate hardening | strategos | devops-master, qa-terminator | unsigned or stale launches stay blocked |
| CTOA-330 | Bootstrap UX simplification | core-architect | code-smith | first-launch state creation stays reproducible |
| CTOA-331 | Public/private surface cleanup and doc refresh | documentation-sage | core-architect | docs and manifests reflect current product boundaries |

## KPI Contract

- Process KPI: update gate blocks invalid launches and accepts signed release metadata.
- Product KPI #1: bootstrap flow completes with minimal manual intervention.
- Product KPI #2: public/private docs and package manifests stay aligned with the public toolkit boundary.

## Definition of Done

- `ctoa_update_gate` passes for the new release flow.
- Bootstrap creates local state without manual workarounds.
- Public/private boundaries are explicit in docs and package manifests.
- README and product map do not reference stale active stages.
- Sprint has validator, progress doc, and evidence chain like prior sprints.