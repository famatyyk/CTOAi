# B4 Runtime State Refactor Execution

Tracker: #137
Date: 2026-05-31
Branch: feat/b4-runtime-state-path-refactor
Status: IN_PROGRESS

## Scope

Refactor mutable ML runtime state out of `data/`:
- qtable_a.json
- qtable_b.json
- dql_steps.json

## Code Changes

- bot/decision/ml_model.py
  - primary state path: `runtime/state/` (env override: `BOT_RUNTIME_STATE_DIR`)
  - legacy read fallback: parent of `BOT_DB_PATH`
  - writes always target runtime state path

## Core Data Policy Alignment

Kept in `data/` as static product inputs:
- data/game/monsters.json
- data/game/hunt_routes.json
- data/game/items.json

Removed from tracked Core (runtime-generated):
- data/qtable_a.json
- data/qtable_b.json
- data/dql_steps.json
