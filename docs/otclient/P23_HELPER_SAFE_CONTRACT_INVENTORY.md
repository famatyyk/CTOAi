# P23 Helper / Safe Contract Inventory

P23.1 classifies what the two products may share without turning Safe into a
copy of Helper or allowing one product's evidence to satisfy the other.
The machine-readable source is
`AI/P23_HELPER_SAFE_CONTRACT_INVENTORY.json`.

## Share

- Pure numeric comparison semantics for `<`, `<=`, `=`, `!=`, `>=`, `>`.
- Pure `AND` and `OR` condition composition.
These are data semantics only. They do not include actions, native client
calls, scheduling, arming, persistence, acceptance, or promotion.

## Adapt

- Metric names: Helper uses `hp_percent`, `mana_percent`, and
  `monster_count`; Safe uses `hp`, `mana`, and `monsters`.
- Helper-only hysteresis, cooldown, distance, PZ, and active-condition fields
  require an explicit Safe product decision before any adapter integration.
- Safe retains its own UI-facing condition representation and profile v3.
- Bounded randomization has the same maximum spread of 20 but a different
  lifecycle: Helper receives an offset per evaluation, while Safe caches its
  effective threshold until a successful owning action resets it.

The passive Safe fixture adapter exists under `tests/fixtures/lua` only for P23
parity validation. It is outside `mods/ctoa_safe`, is not loaded by
`ctoa_safe_loader.lua`, is not called by the Safe runtime, and grants no
dispatch authority.

## Reject

- Profile schemas, migrations, file paths, and persistence.
- Project loaders, lifecycle hooks, scheduled events, mutable cooldowns, and
  armed state.
- UI, HUD, widget state, and product-specific presentation.
- Acceptance receipts, runtime evidence, release manifests, and promotion
  authority.

Safe evidence never satisfies Helper acceptance, and Helper evidence never
satisfies Safe acceptance.

## Evidence

`tests/fixtures/ctoa_helper_safe_condition_parity_v1.json` contains ten
deterministic cases covering all six numeric operators, both combinators, all
three mapped metrics, and one-shot bounded randomization. Real Lua evaluates each case
through the Helper rule engine and the passive Safe contract. Every result
keeps runtime actions, dispatch, operational acceptance, and promotion false.

This fixture does not prove equal runtime randomization lifecycle. P23.2 records
the reviewed `no_shared_runtime_core` decision in
`AI/P23_2_CONDITION_CORE_DECISION.json`. Each product keeps its local evaluator,
schema, loader, mutable state, and release manifest.
