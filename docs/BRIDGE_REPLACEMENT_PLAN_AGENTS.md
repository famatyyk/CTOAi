# Bridge Replacement Plan for runner/agents.py

Goal: archive `runner/agents.py` safely without breaking runtime execution (`runner/runner.py`) or CI.

Status: COMPLETED (legacy file moved to `archived/runtime/agents_legacy.py`).

## Current Situation

- Runtime source of truth is frozen to:
  - `runner/runner.py`
  - `runner/agents/`
- Legacy exception list is now empty.
- `runner/agents/__init__.py` exports `execute_agent_for_task` from `runner/agents/executor.py`.

## Risks

- Removing `runner/agents.py` too early breaks bridge import in `runner/agents/__init__.py`.
- `runner/runner.py` still contains fallback import: `from agents import execute_agent_for_task`.

## Safe Migration Sequence

1. Readiness checks (no behavior changes):
- Run `python scripts/ops/bridge_replacement_readiness.py`.
- Confirm only expected legacy dependency points are present.

2. Introduce native runtime executor in package:
- Add `runner/agents/executor.py`.
- Move/copy `execute_agent_for_task` and required Track classes from `runner/agents.py`.
- Keep function signature and return shape unchanged.

3. Switch imports to package-native path:
- Update `runner/agents/__init__.py` to import from `runner/agents/executor.py` (no dynamic load).
- Update `runner/runner.py` to use only `from runner.agents import execute_agent_for_task`.

4. Validation gate:
- Run runtime freeze guard, core guard, and baseline tests.
- Run one manual `runner.py tick` smoke test.

5. Archive legacy file:
- Move `runner/agents.py` to `archived/runtime/agents_legacy.py`.
- Remove final legacy exception from `core/runtime-freeze-policy.json`.

6. Final lock:
- Add CI check that fails if `runner/agents.py` reappears in tracked files.

## Rollback Plan

- If runtime dispatch breaks, restore previous commit where dynamic bridge still points to `runner/agents.py`.
- No data migration is required; change is code-only.
