# Pathing Spec

## Scope
Lua pathing helpers for waypoint traversal and blocked-tile recovery.

## Contract
- Accept a route as a list of waypoints.
- Normalize waypoint shapes before use.
- Return a fallback waypoint if the route is empty or invalid.
- Stop retrying after the configured retry budget is exhausted.

## Acceptance
- `scripts/lua/pathing_helper.lua` exposes `normalizeRoute`, `nextWaypoint`, and `retryBlocked`.
- Blocked routes fail closed instead of looping forever.
