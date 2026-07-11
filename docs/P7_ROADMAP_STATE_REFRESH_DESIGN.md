# P7 Roadmap State Refresh Design

Status: `design_only`; the action and MCP tool are not enabled.

## Selection

- Action ID: `roadmap-state-refresh`
- Proposed MCP tool: `ctoai_roadmap_state_refresh`
- Risk class: `safe_write`
- Purpose: derive one machine-readable roadmap state from existing generated
  manifests and evidence, reducing drift between `Current State`, `Now`, and
  `Next` without editing hand-authored roadmap policy.

Exactly this one action is selected for the next P7 design lane. Deploy, live
client, promotion, arbitrary command, and arbitrary path actions remain outside
the plugin surface.

## Bounded Write Contract

The future implementation may write only:

- `AI/generated/ROADMAP_STATE.json`
- `AI/generated/ROADMAP_STATE.md`
- sanitized audit records in `runtime/control-center/action-audit.jsonl`

Inputs are fixed to `AI/FEATURE_ROADMAP.md`, `AI/generated/manifest.json`,
`AI/generated/P7_OPERATOR_BRIEF.json`, and bounded Helper/Control Center
evidence summaries. It must not read `.env`, auth stores, logs, databases,
arbitrary runtime files, or paths supplied by a caller.

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

## Control Center Gate

Control Center remains read-only for this candidate until all contract tests
pass and at least one current dry-run audit record is reviewed. Before
enablement it may display only `design_only`, missing gates, proposed outputs,
and the dry-run command. The action button and MCP write tool count must remain
unchanged.

## Required Tests Before Enablement

- schema and fixed-input parsing;
- output path confinement and symlink rejection;
- dry-run produces zero artifact writes;
- exact confirmation rejection/acceptance;
- cockpit preflight failure is fail-closed;
- atomic JSON/Markdown output parity;
- sanitized audit record on dry-run, confirmed success, and failure;
- MCP schema rejects arbitrary command/path fields;
- Control Center evidence and detail views show `design_only` without an action
  button;
- regression proof that active safe-write tool count remains five until a
  separate reviewed enablement change.

## Enablement Boundary

Implementation, dry-run evidence, Control Center UI exposure, and MCP
enablement are separate future changes. This design alone does not authorize or
enable `ctoai_roadmap_state_refresh`.
