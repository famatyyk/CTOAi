# Refactor S1 Baseline (2026-06-05)

## Scope

Hybrid runtime baseline for first refactor increment.

Measured area:

- `runner/hybrid_bot`
- `tests/test_hybrid_bot.py`

## Baseline Metrics

| Metric | Value | Source |
| --- | --- | --- |
| Hybrid Python files | 14 | PowerShell repo scan |
| Hybrid Python lines | 3859 | PowerShell line aggregation |
| `_utcnow()` duplicates (before migration) | 3 | text search in hybrid modules |
| `TODO` markers in hybrid modules | 3 | text search in hybrid modules |
| Primary hybrid test file lines | 394 | `tests/test_hybrid_bot.py` |

## S1 Change Delta (implemented)

| Item | Before | After |
| --- | --- | --- |
| UTC time helper strategy | 3 local helpers | 1 shared helper (`clock.py`) |
| Hybrid time helper definitions | 3 | 0 |
| Shared clock entry point | none | `utc_now()` |

## Notes

This baseline is intentionally narrow and auditable.
It is intended as a stable comparison point for S2/S3 modularization work.
