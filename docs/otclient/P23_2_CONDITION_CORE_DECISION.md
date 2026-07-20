# P23.2 Condition Core Decision

P23.2 closes with `no_shared_runtime_core`. Helper and Safe share a small
semantic vocabulary, not a loader-visible Lua file.

## Why a shared runtime core was rejected

The two products do not have the same condition lifecycle. Helper owns a
versioned rule schema, up to eight conditions, hysteresis, cooldown, Boolean
metrics, and an injected random offset for each pure evaluation. Safe owns a
profile-v3 representation with up to four conditions and stores an
`_effective_value` until the action that owns the rule succeeds and resets it.

Moving both products onto one file would therefore do one of two harmful
things: flatten real product behavior into a misleading least-common
denominator, or make Safe's package and lifecycle depend on a Helper-owned
runtime module. Both outcomes violate the separate-product boundary.

## What remains shared

- The six numeric operators: `<`, `<=`, `=`, `!=`, `>=`, and `>`.
- AND/OR truth-table composition.
- Deterministic one-shot fixture cases that prove mapped numeric semantics.

The fixture does not prove equal randomization lifecycle, runtime readiness,
dispatch, acceptance, or promotion. Its Safe-side Lua file remains under
`tests/fixtures/lua` and is a contract probe, not a product adapter.

## Product-local owners

- Helper: `scripts/lua/otclient/ctoa_helper_rule_engine.lua`, preserving
  `ctoa-helper-profile-v1` and `ctoa-helper-rule-v1`.
- Safe: `mods/ctoa_safe/ctoa_safe_helper.lua`, preserving
  `ctoa-safe-profile-v3` and the existing seven-file release package.

No loader, profile persistence, mutable threshold state, event, action,
evidence receipt, release manifest, sandbox root, or live root is shared.

The machine-readable decision is `AI/P23_2_CONDITION_CORE_DECISION.json`.

## Validation

The focused boundary set passes 52 tests: 14 contract/roadmap tests, 24
exclusive-loader and Safe runtime tests, three release-boundary tests, and 11
Helper rule/profile tests. All 61 Helper Lua files and the fixture compile with
`luac -p`; the module audit reports `ready`.

Engine Brain refresh reports doc sync and secret guardrail `passed`, and the
control-central pack contains 10 untruncated sections. The latest Environment
Doctor result is `warn` with zero failures and three warnings; one warning is
the manually disconnected Cloudflare WARP state. This is not treated as Helper
or P23 acceptance evidence.
