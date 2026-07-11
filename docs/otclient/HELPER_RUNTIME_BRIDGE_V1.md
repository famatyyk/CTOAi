# Helper Runtime Bridge v1

Status: `sandbox_accepted` on 2026-07-11. Evidence: ModuleStaticGates 33/33,
ModuleAttachSmoke 4/4, SmokeAttachAll 16/16, and
`recovery_bridge_sandbox_smoke.json` 9/9. Runtime remained disarmed and the
dry-run trace did not invoke its injected executor.

Native sandbox execution is routed through the Helper's existing guarded
`castSpell` adapter only after the bridge verifies the `SolteriaCodexTest`
work directory, a matching armed session, client readiness, PZ/cooldown guards,
and the operator's second confirmation click. The Healing panel exposes
`ARM bridge`, `Dry run`, and an immediate `KILL`; live paths fail closed.

## Outcome

Enable one bounded Healing/Recovery action in the sandbox without changing the
Helper safe-boot contract. The bridge connects passive decisions to an injected
executor; it does not call OTClient globals directly and does not authorize live
promotion.

## Scope

- Action: `plan_heal` / `cast_heal` only.
- Environment: sandbox only.
- Boot state: disarmed and dry-run.
- Arm gate: explicit operator confirmation, runtime enablement, and a non-empty
  session identifier.
- Runtime guards: online client, living player, client readiness, protection
  zone exclusion, cooldown, armed-session match, and active kill switch.
- Failure policy: bounded consecutive failures activate the kill switch.
- Trace: `decision -> guard -> action -> result` using
  `ctoa.recovery-bridge-trace.v1`.

## Acceptance Evidence

1. Real-Lua tests prove dry-run never invokes the executor.
2. Execution requires an explicitly armed matching sandbox session.
3. Cooldown and PZ guards fail closed.
4. Retry-budget exhaustion disarms the bridge and activates its kill switch.
5. The packaged boot graph includes the bridge after policy and dispatch guard.
6. No direct `g_game`, cast, item-use, movement, or live-promotion call exists.
7. Sandbox attach and in-world evidence are required before adding a native
   executor adapter or expanding beyond Healing/Recovery.

## Deliberate Boundary

This phase supplies the execution boundary and injected-executor contract. The
native OTClient executor adapter, operator UI arming control, live promotion,
Combat, CaveBot, Equipment, Conditions, and Heal Friend remain outside v1 until
the sandbox acceptance evidence is complete.
