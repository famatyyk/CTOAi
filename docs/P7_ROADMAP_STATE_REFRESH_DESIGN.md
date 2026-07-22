# P7 Roadmap-State Refresh Registration

Status: `registered_fail_closed`.

## Scope

- Action ID: `roadmap-state-refresh`
- MCP tool: `ctoai_roadmap_state_refresh`
- Risk class: `safe_write`
- Fixed outputs: `AI/generated/ROADMAP_STATE.json`,
  `AI/generated/ROADMAP_STATE.md`, and sanitized audit records in
  `runtime/control-center/action-audit.jsonl`.

The action is registered in the P7 safe-write catalog, but registration is not
operator readiness. A missing, stale, mismatched, tampered, or unreviewed P13
source, plugin contract, Control Center preflight, or audit record blocks the
candidate. No fallback may convert those failures into a ready state.

## Fail-Closed Boundary

Dry runs use the fixed P13 generator and do not write roadmap outputs; they may
append a sanitized audit record. A confirmed output refresh requires
`dry_run=false` and the exact confirmation `refresh roadmap state`. The caller
cannot choose an arbitrary input, output, command, runtime target, or client.

This registration grants no runtime executor, runtime MCP write authority, live
promotion authority, or P8–P12/P14 evidence rebaseline. It records and projects
only the current bounded P13 contract. External P14 sandbox evidence remains
separate and must be collected and verified through its own protected flow.

## Enablement Rule

Control Center may surface the candidate only when its current source contract,
plugin capability, cockpit preflight, and audited evidence all pass. Otherwise
it remains visible only as a blocked, read-only decision with its reason.
