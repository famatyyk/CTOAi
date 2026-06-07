# ADR-001: Shared UTC Clock Utility for Hybrid Modules

## Status

Accepted

## Date

2026-06-05

## Context

Hybrid runtime modules in `runner/hybrid_bot` had duplicated local `_utcnow()` implementations.

This created avoidable divergence risk in time handling and made future time-related testing harder.

## Decision

Introduce one shared time helper module:

- `runner/hybrid_bot/clock.py`
- Public API: `utc_now() -> datetime`

Migrate these modules to use it:

- `runner/hybrid_bot/bot_runner.py`
- `runner/hybrid_bot/metrics.py`
- `runner/hybrid_bot/state_manager.py`

## Consequences

| Type | Result |
| --- | --- |
| Positive | One canonical UTC source in hybrid runtime |
| Positive | Lower copy-paste drift risk |
| Positive | Easier future injection/mocking of clock behavior |
| Neutral | Small import-level change across three modules |
| Risk | If utility import path changes, all consumers are affected |

## Validation

| Check | Expected |
| --- | --- |
| Static diagnostics | No new errors in changed modules |
| Hybrid tests | Existing tests continue to pass |
| Behavioral semantics | No change in orchestration state transitions |
