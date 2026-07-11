# Solteria Helper Module Workplan

## Current Decision

- Status: `ready`
- Helper lines: `4350`
- Helper functions: `159`
- Helper line budget: `4500`
- Helper function budget: `130`
- Helper budget status: `over_budget`
- Helper shell target: UI composition, profile persistence, and guarded dispatch only; registry/domain logic belongs in helper modules/adapters.
- Modularization pressure: `medium`
- Placeholder modules: `0`
- Implemented modules: `31`
- Prototype modules: `0`
- Registry coverage: `9` / `9`
- Next extraction: `none`
- Next supplemental split: `none`
- Next phase: P6-module-lane: keep the main helper as UI composition shell; move runtime adapters behind static contracts and sandbox gates.
- Next module action: `` - Keep module gates current before adding new runtime actions.

## Operating Rule

New behavior must enter through a named module lane with profile keys, safe boot defaults, static tests, sandbox smoke evidence, and release-gate evidence. Do not add broad runtime logic directly to the main helper without updating this workplan and the module audit.

The helper Overview must expose module readiness from `ctoa_helper_modules.lua` so operators can see implemented, prototype, armed, gated, and experimental lanes without enabling runtime actions.

## Module Lanes

| Module | Status | Target | Next step | Gate |
|---|---:|---|---|---|
| `healing` / Healing and recovery | `static_gated` | `ctoa_native_heal.lua` | Keep runtime logic mirrored in standalone passive recovery module and add sandbox HP/MP log smoke. | ValidateDev plus in-world HP/MP sandbox log evidence. |
| `combat` / Targeting and magic shooter | `static_gated` | `ctoa_native_combat.lua` | Extract shared target scoring/guards into a reusable helper runtime domain before adding more attacks. | PZ/NPC regression log plus SmokeAttachAll hunting and hunting_magic views. |
| `cavebot` / CaveBot route and movement | `static_gated` | `ctoa_native_helper.lua` | Split route editing from movement execution into separate domain blocks before adding waypoint actions. | Route editor static tests plus sandbox autoWalk retry-budget evidence. |
| `loot` / Loot scanner | `static_gated` | `ctoa_native_loot.lua` | Promote loot from experimental flag only after in-world container scan evidence exists. | ValidateDev plus bounded ctoa_local.log loot scan evidence in sandbox. |
| `timer` / Timer action | `static_gated` | `ctoa_native_helper.lua` | Keep timer as a small bounded action; do not add arbitrary scripting through timer message. | Static contract and sandbox log evidence for one timer tick. |
| `heal_friend` / Heal Friend | `static_gated` | `ctoa_helper_heal_friend.lua` | Run HealFriendNoTargetSmoke, then capture grouped in-world SmokeAttachModules evidence before any sio cast path. | No runtime sio cast until whitelist UI, profile persistence, HealFriendNoTargetSmoke, ModuleStaticGates, and ModuleAttachSmoke evidence exist. |
| `conditions` / Conditions | `static_gated` | `ctoa_helper_conditions.lua` | Run ConditionsObserverSmoke, then capture grouped in-world SmokeAttachModules state evidence before any recovery action. | No condition recovery action until API probe evidence, passive plan contract, ConditionsObserverSmoke, ModuleStaticGates, and ModuleAttachSmoke pass. |
| `equipment` / Equipment | `static_gated` | `ctoa_helper_equipment.lua` | Run EquipmentObserverSmoke, then capture grouped in-world SmokeAttachModules inventory evidence before any swap path. | No runtime swap before inventory API probe output, passive plan contract, profile persistence, EquipmentObserverSmoke, ModuleStaticGates, and ModuleAttachSmoke. |
| `scripting` / Scripting | `static_gated` | `ctoa_helper_scripting.lua` | Run ScriptingPolicySmoke, then capture grouped in-world SmokeAttachModules policy shell evidence; keep eval and user snippets blocked. | No user snippet execution until passive plan contract, security review, denylist tests, audit logging, ScriptingPolicySmoke, ModuleStaticGates, and ModuleAttachSmoke pass. |

## Extraction Map

| Order | Domain | Target | Status | Gate |
|---:|---|---|---:|---|
| 1 | `module_registry` / MODULE_LANES, module lane lookup, readiness text | `ctoa_helper_modules.lua` | `extracted` | Registry parity test plus Overview readiness smoke. |
| 2 | `diagnostics` / log helpers, API probes, status snapshots, module evidence formatting | `ctoa_helper_diagnostics.lua` | `extracted` | ValidateDev, UI preview, and no secret/runtime path leakage in generated evidence. |
| 3 | `heal_friend` / heal friend profile defaults, whitelist matching, observer sampling, UI summary | `ctoa_helper_heal_friend.lua` | `extracted` | HealFriendNoTargetSmoke, ModuleStaticGates, and ModuleAttachSmoke before any sio runtime arm. |
| 4 | `conditions` / condition state API probes, read-only observer rows, passive recovery planner, profile defaults | `ctoa_helper_conditions.lua` | `extracted` | ConditionsObserverSmoke, passive plan contract, ModuleStaticGates, and ModuleAttachSmoke before any recovery action. |
| 5 | `equipment` / inventory slot probes, passive ring/amulet swap planner, read-only UI summary | `ctoa_helper_equipment.lua` | `extracted` | EquipmentObserverSmoke, passive plan contract, ModuleStaticGates, and ModuleAttachSmoke before any use/move action. |
| 6 | `scripting` / policy shell, deny-all snippet planner, audit metadata | `ctoa_helper_scripting.lua` | `extracted` | ScriptingPolicySmoke, passive plan contract, ModuleStaticGates, and ModuleAttachSmoke; eval remains blocked. |

## Supplemental Refactor Plan

This is the next wave after the passive helper modules are contracted. It exists because the main helper is still over budget and should become a composition shell instead of absorbing more runtime logic.

| Order | Split | Target | Status | Gate |
|---:|---|---|---:|---|
| 1 | `combat_runtime_adapter` / combat arming, monster scan adapter, attack/cast execution guards | `ctoa_helper_combat_runtime.lua` | `extracted` | Combat runtime static contract, target scorer contract, monster-only regressions, PZ/NPC smoke, SmokeAttachAll hunting tabs. |
| 2 | `cavebot_runtime_adapter` / movement execution, path probe, retry budget, PZ/offline movement guards | `ctoa_helper_cavebot_runtime.lua` | `extracted` | Route contract, cavebot static tests, in-world retry-budget evidence, SmokeAttachAll cavebot tab. |
| 3 | `loot_runtime_adapter` / corpse/container scan orchestration, item move bounds, capacity guard | `ctoa_helper_loot_runtime.lua` | `extracted` | Container API probe, experimental_loot remains false by default, bounded sandbox loot log evidence. |
| 4 | `timer_runtime_adapter` / bounded timer message/cast action, interval guard, action lock | `ctoa_helper_timer_runtime.lua` | `extracted` | Static no-eval contract, one-tick sandbox log evidence, no scripting bridge. |
| 5 | `profile_schema_adapter` / profile defaults, migration keys, rotation preset metadata, profile dirty reasons, profile UI persistence | `ctoa_helper_profile_schema.lua` | `extracted` | Profile audit, schema snapshot, safe migration and rotation-summary tests, no key-order churn. |
| 6 | `operator_summary_bridge` / operator title, domain summary text, profile/UI summary bridge, and no-widget text composition | `ctoa_helper_operator_summary.lua` | `extracted` | OperatorSummary static contract, profile schema and domain summary parity, ModuleStaticGates, UI preview, and sandbox SmokeAttachModules before any runtime bridge can consume summaries. |
| 7 | `planner_coordinator` / passive plan collection, ranking, summary, and no-execution contract | `ctoa_helper_planner.lua` | `extracted` | Planner static contract, module planner regressions, ModuleStaticGates, and sandbox SmokeAttachModules before any runtime dispatcher wiring. |
| 8 | `runtime_policy_guard` / shared runtime gate evaluation, manifest freshness, sandbox smoke, and live approval policy | `ctoa_helper_runtime_policy.lua` | `extracted` | RuntimePolicy static contract, ModuleStaticGates, current manifest, ModuleAttachSmoke, SmokeAttachAll, and explicit live approval before any dispatcher executes a plan. |
| 9 | `dispatch_guard_coordinator` / ranked plan classification, runtime policy handoff, and dispatch allow/deny reasons | `ctoa_helper_dispatch_guard.lua` | `extracted` | DispatchGuard static contract, RuntimePolicy ready decision, sandbox attach evidence, and explicit live approval before any dispatcher bridge is wired. |
| 10 | `plan_queue_coordinator` / bounded guarded-decision queue, review summaries, and no-execution handoff state | `ctoa_helper_plan_queue.lua` | `extracted` | PlanQueue static contract, DispatchGuard decision evidence, bounded queue tests, sandbox attach evidence, and explicit live approval before queued plans can feed any dispatcher bridge. |
| 11 | `runtime_readiness_status` / component readiness, gate readiness, queued-plan review status, and no-execution runtime bridge summary | `ctoa_helper_runtime_readiness.lua` | `extracted` | RuntimeReadiness static contract, required component/gate coverage, current manifest, sandbox attach evidence, SmokeAttachAll, and explicit live approval before any runtime bridge is considered ready. |
| 12 | `module_status_board` / module readiness rows, status counts, blocker summary, and no-execution evidence board | `ctoa_helper_module_status.lua` | `extracted` | ModuleStatus static contract, module contract coverage, ModuleStaticGates, sandbox attach evidence, and explicit live approval before status can support runtime enablement. |
| 13 | `action_catalog_policy` / runtime action capability names, domain mapping, risk class, required gates, and no-execution dispatch metadata | `ctoa_helper_action_catalog.lua` | `extracted` | ActionCatalog static contract, action risk coverage, RuntimePolicy gate parity, ModuleStaticGates, sandbox attach evidence, and explicit live approval before any action can be dispatched. |
| 14 | `decision_trace_review` / plan/policy/guard/queue decision traces, missing gate summaries, and no-write review metadata | `ctoa_helper_decision_trace.lua` | `extracted` | DecisionTrace static contract, policy/guard reason coverage, bounded queue trace, ModuleStaticGates, sandbox attach evidence, and explicit live approval before any trace informs runtime dispatch. |
| 15 | `sandbox_handoff_checklist` / operator sandbox smoke checklist, required runtime gates, next-step summary, and no-launch/no-promote handoff metadata | `ctoa_helper_sandbox_handoff.lua` | `extracted` | SandboxHandoff static contract, Launch/ReadyCheck/SmokeAttachModules/SmokeAttachAll/ApproveLiveDeploy sequence coverage, ModuleStaticGates, and explicit live approval before live promotion. |
| 16 | `feature_flag_matrix` / safe false runtime flags, feature domains, required gates, and no-toggle profile audit metadata | `ctoa_helper_feature_flags.lua` | `extracted` | FeatureFlags static contract, safe-default coverage, profile audit parity, ModuleStaticGates, SmokeAttachAll, and explicit live approval before runtime flags can be enabled. |

## P6 Module Lane

1. Freeze the current helper UI contract with `ValidateDev`, `ctoa_helper_ui_preview.py`, and `SmokePreflight`.
2. Extract domains in the `Extraction Map` order and keep the main helper as the UI composition shell.
3. Execute the `Supplemental Refactor Plan` one adapter at a time; adapter files may plan or dispatch guarded actions only after static contracts exist.
4. Convert prototype modules in order: Heal Friend observation, Conditions diagnostics, Equipment safe swaps, Scripting policy shell.
5. For each module, add profile schema keys, safe boot defaults, tests, README/docs, `ModuleStaticGates`, and `SmokeAttachModules` before runtime enablement.
6. Keep live promotion separate and require `PromoteLiveCtoa -ApproveLiveDeploy` after in-world `SmokeAttachAll` evidence.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe scripts\ops\otclient_helper_module_audit.py --json-out runtime\solteria_helper_dev\module_audit.json
.\.venv\Scripts\python.exe -m pytest tests\test_otclient_helper_module_audit.py tests\test_otclient_helper_zerobot_shell.py tests\test_otclient_helper_profile_audit.py tests\test_ctoa_helper_smoke_report.py -q
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ValidateDev
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokePreflight
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ModuleStaticGates
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttachModules
```
