# Helper Runtime Module Safety Gates v1

Status: `static_contract_accepted`; runtime dispatch remains unavailable.

## Outcome

Move beyond the accepted Recovery Bridge without treating general Helper static
or attach evidence as permission to execute a different action class. Every new
domain has its own default-closed, sandbox dry-run gate and an explicit place in
the sequence.

## Required Sequence

Canonical order: `Conditions -> Equipment -> Heal Friend`.

1. `conditions_runtime_gate` follows accepted Recovery evidence. Version 1
   allowlists only `plan_paralyze_recovery` and requires a current condition
   observation, the exact allowlisted `exura` recovery spell, a bound Recovery
   dry-run trace, PZ/offline/dead/client guards, operator confirmation, elapsed
   cooldown, bounded non-negative retry, and disabled Combat/CaveBot.
2. `equipment_runtime_gate` follows an accepted Conditions gate. Version 1
   allowlists only `plan_ring_swap`, requires exact current/candidate item IDs,
   a matching ring-slot/container/revision rollback snapshot, an unambiguous
   inventory, a confirmed free slot, elapsed cooldown, and zero automatic
   retries. The accepted Conditions trace is carried into this decision.
3. `heal_friend_runtime_gate` follows accepted Conditions and Equipment gates.
   Version 1 allowlists only `plan_sio` and requires a persisted exact whitelist,
   stable observed/current creature ID and name, a current persisted-whitelist
   revision, real party membership by creature ID, visibility, same-floor and
   range checks, fresh timestamp-derived HP evidence, PZ/offline/dead/client
   guards, elapsed cooldown, and explicit operator confirmation. Both accepted
   predecessor traces are carried into this decision.

The shared `ctoa_helper_runtime_policy.lua` requires the matching action-specific
gate in addition to the existing manifest/static/attach/full-smoke/live-approval
policy. Gate acceptance is a structured trace bound to `gate_id` and
`next_action`; a caller-provided boolean or `runtime_action=false` cannot bypass
classification. Poison/burn/energy/bleed recovery and amulet swaps are
`deferred_module_scope` in v1. `plan_attack`, offensive spell/rune plans, and
`plan_walk` always return `high_risk_deferred`, even if every generic gate is
green.

## Evidence Contract

- `ConditionsRuntimeGateStaticSmoke` ->
  `conditions_runtime_gate_static_smoke.json`
- `EquipmentRuntimeGateStaticSmoke` ->
  `equipment_runtime_gate_static_smoke.json`
- `HealFriendRuntimeGateStaticSmoke` ->
  `heal_friend_runtime_gate_static_smoke.json`
- real-Lua guard matrices prove accepted and blocked cases;
- `RuntimeModuleGatesSandboxSmoke` proves synthetic action-bound acceptance,
  explicit outside-PZ fail-closed behavior, current in-world gate behavior, and
  high-risk/out-of-scope deferral; it is a mandatory release-gate artifact;
- all reports declare `dispatch_allowed=false`, `runtime_actions=false`, and
  `live_promotion=false`.

Static acceptance proves the policy boundary only. A domain may gain an
execute-once bridge only after fresh package, module static gates, in-world tab
evidence, a domain-specific dry-run against real observations, and a separate
operator-reviewed action smoke. No gate in this document promotes or changes
the live Solteria client.

`RuntimeModuleGatesSandboxSmoke=passed` is not action acceptance. Its current
lane result may remain `blocked_fail_closed` when PZ is unknown/in-zone or real
domain evidence and operator confirmation are absent. That is the intended
safe result; a later domain-specific acceptance must be reviewed separately.

## Deliberate Boundary

- Conditions execution is not enabled by this gate.
- Equipment movement/use and rollback execution are not enabled by this gate.
- Heal Friend casting and whitelist mutation are not enabled by this gate.
- Combat and CaveBot remain later, high-risk phases.
