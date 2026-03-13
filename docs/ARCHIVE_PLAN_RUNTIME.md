# Runtime Archive Plan (Safe, No-Delete)

This plan freezes one runtime path as source of truth and prepares legacy files for controlled archival.

## Source Of Truth (Frozen)

- Runtime entrypoint: `runner/runner.py`
- Agent runtime package: `runner/agents/`

## Legacy Files (Temporary Exceptions)

These are still tracked but are marked as legacy in `core/runtime-freeze-policy.json`:

- `runner/agents.py`
- `runner/lab_runner.py`
- `sprint_007_execute.py`
- `monitor_agents.py`

## Archival Target

Move legacy files to:

- `archived/runtime/`

No deletion in this phase. Keep git history intact.

## Migration Order

1. Stop references to each legacy file in scripts/docs/automation.
2. Move one legacy file at a time to `archived/runtime/`.
3. Add a short shim or note if needed.
4. Remove that file from `legacy_exceptions` in `core/runtime-freeze-policy.json`.
5. Verify CI passes.

## Hard CI Gate

Pipeline now runs `scripts/ops/runtime_path_guard.py`.
It fails on any *new* runtime/agent path outside frozen source-of-truth, unless explicitly added as legacy exception.

This prevents silent repo sprawl from returning.
