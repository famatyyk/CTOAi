# Loot, Target, and Supply Spec

## Scope
Lua helpers for combat-adjacent decisions.

## Contracts
- `supply_manager.lua` decides when to refill and returns shortage details.
- `target_priority.lua` normalizes targets and picks a best candidate.
- `loot_filter.lua` allows blacklist-first filtering and stack detection.

## Acceptance
- Helpers must tolerate missing or partial tables.
- Invalid candidates must fail closed.
- Whitelist-free loot mode should still work when only a blacklist is configured.
