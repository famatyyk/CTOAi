# P7 Roadmap State Refresh Design

Status: `enabled_end_to_end`; the native generator is available through the
Control Center action engine and `ctoai_roadmap_state_refresh` MCP tool.

## Selection

- Action ID: `roadmap-state-refresh`
- MCP tool: `ctoai_roadmap_state_refresh` (enabled, native dry-run)
- Risk class: `safe_write`
- Purpose: derive one machine-readable roadmap state from existing generated
  manifests and evidence, reducing drift between `Current State`, `Now`, and
  `Next` without editing hand-authored roadmap policy.

Exactly this one CLI action is enabled for the bounded P13 lane. Deploy,
live client, promotion, arbitrary command, and arbitrary path actions remain
outside both the CLI and plugin surfaces.

## Bounded Write Contract

The implemented CLI may write only:

- `AI/generated/ROADMAP_STATE.json`
- `AI/generated/ROADMAP_STATE.md`
- sanitized audit records in `runtime/control-center/action-audit.jsonl`

Inputs are fixed to `AI/FEATURE_ROADMAP.md`, `AI/generated/manifest.json`,
`AI/generated/P7_OPERATOR_BRIEF.json`, and bounded Helper/Control Center
evidence summaries. It must not read `.env`, auth stores, logs, databases,
arbitrary runtime files, or paths supplied by a caller.

The versioned registry and both JSON Schema contracts are independently pinned
by raw SHA-256 in the generator. Same-version semantic mutation therefore fails
closed even before the first `ROADMAP_STATE.json` baseline exists.

## Dry Run And Confirmation

`dry_run=true` is the default. It performs the Control Center cockpit preflight,
parses the fixed inputs, and returns planned output paths, status changes, and
content hashes without writing either roadmap artifact.

Confirmed execution requires all of:

1. `ctoai_control_center_cockpit` preflight status `ready`;
2. `dry_run=false`;
3. exact confirmation text `refresh roadmap state`;
4. fixed workspace validation;
5. atomic temporary-file replacement for both outputs;
6. a sanitized `safe_write` audit record containing action ID, mode,
   authorization result, output hashes, and success/failure summary.

No deploy or live-client command may be returned as `next_command`.

### P8 terminal rebaseline recovery

Routine refresh remains fail-closed when any terminal evidence hash changes.
The CLI exposes one narrower recovery confirmation,
`zatwierdzam rebaseline P8 terminal evidence`, for a freshly regenerated P8
BackgroundNoScreen observation. It is accepted only when the sole state blocker
is `p8-background-acceptance:terminal_evidence_changed_since_previous_state`.
All P8 schema, ready status, empty source blockers, passive-interaction,
integrity, disarmed-runtime, and false-authority checks must already pass.

The recovery writes the same two fixed roadmap outputs and audit file. Its audit
record binds the previous and current P8 SHA-256 values and records that the
sole-blocker condition passed. It cannot suppress another blocker, redirect an
input or output path, authorize runtime/live work, or rebaseline P9-P12.

## Control Center Gate

Control Center consumes only the fixed JSON artifact. It validates the state
hash and authority boundary, displays the seven terminal ledger entries, and
checks confirmed audit binding separately from freshness and tamper status.
The action panel exposes one dry-run-first refresh capability. Its dry-run
executes the real generator instead of returning a simulated plan. Confirmed
execution remains actor-bound, time-limited, exact-confirmed, and limited to
the fixed JSON/Markdown outputs. The sixth MCP safe-write capability uses the
same generator and cockpit preflight.

P14 sandbox/runtime evidence is advisory to P13 state generation. A current
manifest mismatch therefore produces `readiness_status=awaiting_external` and
`runtime_module_gates_pending`; it does not turn the roadmap platform into a
false outage. Required P13 source, schema, ledger, tamper, or preflight failures
still block generation.

## Implemented Tests

- schema and fixed-input parsing;
- first-generation registry/schema hash-pin tamper rejection;
- output path confinement and symlink rejection;
- dry-run produces zero artifact writes;
- exact confirmation rejection/acceptance;
- P8 rebaseline requires its separate exact confirmation and exactly one
  eligible terminal-hash blocker;
- P8 rebaseline cannot suppress an additional evidence blocker;
- cockpit preflight failure is fail-closed;
- atomic JSON/Markdown output parity;
- sanitized audit record on dry-run, confirmed success, and failure;
- CLI rejects arbitrary command/path fields and exposes no caller-selected
  source or output path;
- native Control Center and MCP dry-runs execute the fixed generator;
- active safe-write tool count is six and all six require successful audited
  dry-run/preflight evidence.

## Enablement Boundary

Implementation, dry-run evidence, confirmed fixed-output generation, and
runtime/live authority remain separate. `ctoai_roadmap_state_refresh` is enabled
only as `safe_write`; the real dry-run writes sanitized audit evidence and the
exact confirmation `refresh roadmap state` authorizes the fixed JSON/Markdown
outputs. The state declares `roadmap_refresh_tool_enabled=true` while preserving
`runtime_mcp_write_tool_enabled=false`, runtime actions false, P12 reopening
false, and live authority false.
