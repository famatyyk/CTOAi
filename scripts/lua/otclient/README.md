# CTOA OTClient Native Modules

Advanced Tibia automation modules designed specifically for **OTClient** using native API calls.

The v2.4.0 package no longer autoloads the Helper directly. The only startup
entrypoint is `mods/ctoa_chooser`: after login it requires an explicit per-session
choice between the full Helper and the separate CTOA Safe project. Both project
modules use `autoload: false`, reject unauthorized initialization, terminate on
logout, and cannot run together. The Helper still starts with safe boot active;
selection loads its UI but does not arm gameplay automation.

## 📋 Features

### ✅ Native OTClient Integration
- **Real Event Handling**: Uses `connect()` for true event-driven automation
- **Performance Optimized**: Direct API calls instead of polling/monitoring
- **Memory Efficient**: Leverages OTClient's built-in systems

### 🎯 Available Modules

| Module | Purpose | OTClient API Used |
|----|----|----|
| **ctoa_native_heal.lua** | Local-only legacy recovery reference; not shipped or loaded | standalone source review only |
| **ctoa_native_combat.lua** | Local-only legacy targeting reference; not shipped or loaded | standalone source review only |
| **ctoa_native_loot.lua** | Local-only legacy loot reference; not shipped or loaded | standalone source review only |
| **ctoa_helper_modules.lua** | Passive module lane registry | `_G.CTOA_HELPER_MODULES`, `getModuleLanes()`, `getShortLabels()` |
| **ctoa_helper_ui_primitives.lua** | Passive shared widget/form primitives | `_G.CTOA_HELPER_UI_PRIMITIVES`, guarded widget basics, form geometry, bounded rule navigation; no gameplay callbacks |
| **ctoa_helper_ui_composition.lua** | Passive declarative UI composition | `_G.CTOA_HELPER_UI_COMPOSITION`, sidebar/subtab/table/action metadata; no profile mutation or gameplay callbacks |
| **ctoa_helper_ui_rule_editors.lua** | Passive rule-editor presentation | `_G.CTOA_HELPER_UI_RULE_EDITORS`, shared chrome plus Target/Spell/Combat Action editors with injected callbacks; no gameplay APIs |
| **ctoa_helper_rule_engine.lua** | Pure typed action/condition validation and passive evaluation | `_G.CTOA_HELPER_RULE_ENGINE`, HP/MP/monster/distance/PZ/condition metrics, AND/OR, cooldown, hysteresis, bounded randomization; no dispatch |
| **ctoa_helper_runtime_core.lua** | Passive runtime registry, event bus, and budgeted scheduler | `_G.CTOA_HELPER_RUNTIME_CORE`, disabled-by-default tasks, bounded ticks, failure backoff |
| **ctoa_helper_combat_observer.lua** | Passive normalized combat/targeting observations | `_G.CTOA_HELPER_COMBAT_OBSERVER`, `ctoa.combat-observation.v1`, `combat.observed` |
| **ctoa_helper_recovery_observer.lua** | Passive normalized HP/MP/recovery observations | `_G.CTOA_HELPER_RECOVERY_OBSERVER`, `ctoa.recovery-observation.v1`, `recovery.observed` |
| **ctoa_helper_cavebot_observer.lua** | Passive position/path capability observations | `_G.CTOA_HELPER_CAVEBOT_OBSERVER`, `ctoa.cavebot-observation.v1`, `cavebot.observed` |
| **ctoa_helper_loot_observer.lua** | Passive container/capacity observations | `_G.CTOA_HELPER_LOOT_OBSERVER`, `ctoa.loot-observation.v1`, `loot.observed` |
| **ctoa_helper_equipment_observer.lua** | Passive equipment-slot observations | `_G.CTOA_HELPER_EQUIPMENT_OBSERVER`, `ctoa.equipment-observation.v1`, `equipment.observed` |
| **ctoa_helper_otclient_observation_adapter.lua** | Guarded read-only OTClient snapshot provider | `_G.CTOA_HELPER_OTCLIENT_OBSERVATION_ADAPTER`, target/spectator/PZ/cooldown/latency reads, sanitized Conditions, bounded Equipment ring/container observations, and bounded P11 party-candidate scans |
| **ctoa_helper_diagnostics.lua** | Passive log and diagnostics export helpers | `_G.CTOA_HELPER_DIAGNOSTICS`, `ctoa_local.log`, `ctoa_diag_export.lua` |
| **ctoa_helper_client_reporter.lua** | Passive BackgroundNoScreen heartbeat | `_G.CTOA_HELPER_CLIENT_REPORTER`, deterministic work-dir JSON, optional P9 Conditions, P10 Equipment, and P11 Heal Friend scan evidence, zero runtime actions |
| **ctoa_helper_hotkeys.lua** | Passive hotkey parser, formatter, and binding-decision helpers | `_G.CTOA_HELPER_HOTKEYS`, normalize/display/bindingDecision helpers |
| **ctoa_helper_modal.lua** | Passive confirmation lifecycle and decision-text helpers | `_G.CTOA_HELPER_MODAL`, request/status/decisionText helpers |
| **ctoa_helper_route.lua** | Passive cavebot route engine and probe metadata helpers | `_G.CTOA_HELPER_ROUTE`, waypoint labels, mutations, stats, non-mutating `ctoa.route-probe-metadata.v1`, contract |
| **ctoa_helper_targeting.lua** | Passive target scoring helpers | `_G.CTOA_HELPER_TARGETING`, ignored names, score rules, decision, contract |
| **ctoa_helper_combat_runtime.lua** | Passive combat runtime adapter plan and operator decision text | `_G.CTOA_HELPER_COMBAT_RUNTIME`, plan/summary/actionStatusText/waitReason/decisionState/contract |
| **ctoa_helper_cavebot_runtime.lua** | Passive cavebot runtime adapter plan, probe metadata/report, movement status, and trace formatting | `_G.CTOA_HELPER_CAVEBOT_RUNTIME`, `ctoa.cavebot-probe-metadata.v1`, `ctoa.cavebot-probe-report.v1`, plan/probeReport/statusText/traceText/contract |
| **ctoa_helper_loot_runtime.lua** | Passive loot runtime adapter plan | `_G.CTOA_HELPER_LOOT_RUNTIME`, plan/summary/contract |
| **ctoa_helper_timer_runtime.lua** | Passive timer runtime adapter plan | `_G.CTOA_HELPER_TIMER_RUNTIME`, plan/summary/contract |
| **ctoa_helper_profile_schema.lua** | Passive profile schema metadata | `_G.CTOA_HELPER_PROFILE_SCHEMA`, required sections, safe false keys, migration plan |
| **ctoa_helper_profile_persistence.lua** | Passive profile persistence policy | `_G.CTOA_HELPER_PROFILE_PERSISTENCE`, load candidates, save headers, autosave metadata |
| **ctoa_helper_rule_presets.lua** | Strict portable rule preset boundary | `_G.CTOA_HELPER_RULE_PRESETS`, versioned Target/Spell/Combat Action import/export; rule-list mutation only, never runtime arming |
| **ctoa_helper_planner.lua** | Passive planner coordinator | `_G.CTOA_HELPER_PLANNER`, collect/best/summary/contract |
| **ctoa_helper_runtime_policy.lua** | Passive runtime gate policy | `_G.CTOA_HELPER_RUNTIME_POLICY`, manifest/smoke/live approval gates |
| **ctoa_helper_dispatch_guard.lua** | Passive dispatch allow/deny guard | `_G.CTOA_HELPER_DISPATCH_GUARD`, classify/decision/summary/contract |
| **ctoa_helper_plan_queue.lua** | Passive guarded decision queue | `_G.CTOA_HELPER_PLAN_QUEUE`, normalize/enqueue/trim/summary/contract |
| **ctoa_helper_runtime_readiness.lua** | Passive runtime bridge readiness | `_G.CTOA_HELPER_RUNTIME_READINESS`, components/gates/snapshot/decision |
| **ctoa_helper_recovery_bridge.lua** | Sandbox-only Healing/Recovery bridge v1 | `_G.CTOA_HELPER_RECOVERY_BRIDGE`, dry-run/session arm/kill switch/dispatch trace |
| **ctoa_helper_runtime_module_gate.lua** | Shared passive action-specific gate evaluator | `_G.CTOA_HELPER_RUNTIME_MODULE_GATE`, default-closed dry-run traces |
| **ctoa_helper_conditions_runtime_gate.lua** | Conditions safety gate | `_G.CTOA_HELPER_CONDITIONS_RUNTIME_GATE`, paralyze-only gate after Recovery |
| **ctoa_helper_equipment_runtime_gate.lua** | Equipment safety gate | `_G.CTOA_HELPER_EQUIPMENT_RUNTIME_GATE`, ring-only rollback-ready gate after Conditions |
| **ctoa_helper_heal_friend_runtime_gate.lua** | Heal Friend safety gate | `_G.CTOA_HELPER_HEAL_FRIEND_RUNTIME_GATE`, exact-whitelist gate after Equipment/Conditions |
| **ctoa_helper_module_status.lua** | Passive module status board | `_G.CTOA_HELPER_MODULE_STATUS`, order/normalize/snapshot/summary/contract |
| **ctoa_helper_action_catalog.lua** | Passive action/risk catalog | `_G.CTOA_HELPER_ACTION_CATALOG`, action domains, risk classes, gates |
| **ctoa_helper_decision_trace.lua** | Passive decision trace formatter | `_G.CTOA_HELPER_DECISION_TRACE`, policy/guard reasons, missing gates |
| **ctoa_helper_sandbox_handoff.lua** | Passive sandbox smoke handoff | `_G.CTOA_HELPER_SANDBOX_HANDOFF`, launch/ready/attach/smoke/promote sequence |
| **ctoa_helper_feature_flags.lua** | Passive feature flag matrix | `_G.CTOA_HELPER_FEATURE_FLAGS`, safe defaults, domains, required gates |
| **ctoa_helper_hud.lua** | Passive HUD text and position helpers | `_G.CTOA_HELPER_HUD`, start/disarmed/runtime text |
| **ctoa_helper_conditions.lua** | Read-only condition state observer | `_G.CTOA_HELPER_CONDITIONS`, state snapshots, API probe text |
| **ctoa_helper_equipment.lua** | Read-only equipment slot observer | `_G.CTOA_HELPER_EQUIPMENT`, inventory slot snapshots, API probe text |
| **ctoa_helper_scripting.lua** | Policy-only scripting shell | `_G.CTOA_HELPER_SCRIPTING`, deny-all status, passive policy plan, summary text |
| **ctoa_helper_heal_friend.lua** | Read-only Heal Friend observer/planner | `_G.CTOA_HELPER_HEAL_FRIEND`, whitelist scan, summary text |
| **ctoa_native_helper.lua** | In-client operator panel | `g_ui`, `cycleEvent`, `g_game.talk()`, `g_keyboard.pressKey()` |
| **ctoa_otclient_loader.lua** | Module management | Core loading system |

## 🔧 Installation

Build the complete three-directory package through the official wrapper:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action PrepareDev
```

Do not add `ctoa_otclient_loader.lua`, `ctoa_native_helper.lua`, or the Safe
loader directly to `init.lua`. Direct loading bypasses the exclusive project
selection contract. The generated package installs `ctoa_project_loader.lua` as
the only root entrypoint and keeps both project `.otmod` files non-autoloading.

## 🧩 Compatibility Matrix

| Component | Supported | Notes |
|----|----|----|
| OTClient-based clients | Yes | Requires Lua `dofile` support and `connect()` events |
| Windows | Yes | Preferred path: `%APPDATA%\\OTClient\\user_dir\\ctoa_otclient\\` |
| Linux | Yes | Preferred path: `~/.otclient/user_dir/ctoa_otclient/` |
| macOS | Yes | Preferred path: `~/Library/Application Support/otclient/user_dir/ctoa_otclient/` |

If your client uses a custom `user_dir`, place files there and keep the same folder name.

## 🚀 Usage

After login, choose exactly one project in the neutral loader. The Helper panel
uses its configured hotkey only after Helper was selected; Safe remains unloaded.

## Runtime Logic

The loader starts in **helper-ui-only** mode and does not auto-load combat, heal, or loot modules. This keeps boot safe while still letting an operator arm runtime modules from the helper UI.

Current helper logic includes:
- module registry: `ctoa_helper_modules.lua` exports every implemented/prototype
  lane, profile key, operating mode, and gate so UI, audits, and docs stay
  aligned; `ctoa_helper_runtime_core.lua` separately owns runtime instances,
  passive event delivery, and fair round-robin cooperative task scheduling
  with a fixed tick budget. A task deferred by the budget is considered first
  on the next tick, while new runtime-core tasks remain disabled by default and
  cannot execute game actions. `ctoa_native_helper.lua` keeps a fallback
  registry for manual loads;
- diagnostics domain: `ctoa_helper_diagnostics.lua` owns log append, diagnostics
  export paths, sample buffers, and export file writing while API probes and UI
  rendering stay in the helper shell;
- Hotkeys domain: `ctoa_helper_hotkeys.lua` owns passive hotkey normalization,
  allowed-choice checks, binding-decision fixtures, and display text while key
  binding stays in the helper shell;
- Modal domain: `ctoa_helper_modal.lua` owns passive confirmation request,
  expiry, status, decision-text, and button text helpers while widget creation
  and command execution stay in the helper shell;
- Route domain: `ctoa_helper_route.lua` owns passive cavebot waypoint labels,
  index selection, add/delete/reorder mutations, active target advancement,
  route stats, retry status text, plus non-mutating selected-target/position
  probe metadata and its static contract. Native path sampling, editor command
  dispatch, and `LocalPlayer:autoWalk` stay in the guarded helper shell;
- Targeting domain: `ctoa_helper_targeting.lua` owns passive ignored-name,
  priority-rank, target-score rules, target decision summaries, and its static
  contract while creature scanning and `g_game.attack` stay in the helper
  shell;
- Combat runtime adapter: `ctoa_helper_combat_runtime.lua` owns passive combat
  plan summaries, wait-reason text, decision-state text, cooldown text, action
  status text, and static contract metadata; it never scans, attacks, casts,
  uses items, or touches OTClient globals, and guarded execution stays in the
  helper shell until sandbox `SmokeAttachAll` evidence exists;
- Cavebot runtime adapter: `ctoa_helper_cavebot_runtime.lua` owns passive
  movement plan summaries, canonical movement API probe metadata/report and
  formatting, movement blocked-reason text, movement status text, movement
  trace text, retry-budget guard metadata, and static contract metadata; it
  never walks, pathfinds, mutates routes, arms runtime, or touches OTClient
  globals. Native capability/path sampling and guarded
  `LocalPlayer:autoWalk` execution stays in the helper shell until sandbox
  `SmokeAttachAll` evidence exists;
- Loot runtime adapter: `ctoa_helper_loot_runtime.lua` owns passive container
  plan summaries, capacity guard metadata, and static contract metadata; it
  never scans containers, opens containers, moves items, uses items, or touches
  OTClient globals, and guarded loot execution stays behind `experimental_loot`
  plus sandbox evidence;
- Timer runtime adapter: `ctoa_helper_timer_runtime.lua` owns passive timer
  plan summaries, interval guard metadata, and static contract metadata; it
  never talks, casts, evaluates snippets, or loads files, and timer execution
  stays in the helper shell until sandbox evidence exists;
- Profile schema adapter: `ctoa_helper_profile_schema.lua` owns passive schema
  metadata, required section order, safe-false keys, and migration plan text; it
  never loads, saves, or migrates files, and profile writes remain behind the
  helper profile audit and sandbox evidence;
- Profile persistence policy: `ctoa_helper_profile_persistence.lua` owns
  passive load candidate lists, save path fallback policy, generated file
  headers, save status text, and autosave metadata; the helper shell still owns
  every `dofile`, `io.open`, and profile write operation;
- Planner coordinator: `ctoa_helper_planner.lua` owns passive plan collection,
    ranking, best-plan selection, summary text, and a static contract; it never
    executes plans, casts, talks, uses items, walks, or touches OTClient globals;
- Runtime policy guard: `ctoa_helper_runtime_policy.lua` owns passive gate
    evaluation for manifest freshness, ModuleStaticGates, ModuleAttachSmoke,
    SmokeAttachAll, and explicit live approval; it never executes plans and is
    the contract future dispatchers must pass before any runtime action path;
- Dispatch guard: `ctoa_helper_dispatch_guard.lua` owns passive ranked-plan
    classification, runtime policy handoff, sandbox attach requirements, and
    allow/deny reason text; it never executes, casts, talks, attacks, walks, or
    uses items, and its `dispatch_allowed` contract remains false until a
    future bridge has sandbox and live approval evidence;
- Plan queue: `ctoa_helper_plan_queue.lua` owns passive normalization,
    bounded retention, trimming, and summaries for guarded decisions; it stores
    review state only, never dispatches queued plans, and requires planner plus
    dispatch guard evidence before any future bridge can consume entries;
- Runtime readiness: `ctoa_helper_runtime_readiness.lua` owns passive
    component/gate coverage, queued-plan review status, and no-execution bridge
    summaries; it requires planner, runtime policy, dispatch guard, plan queue,
    ModuleAttachSmoke, SmokeAttachAll, and live approval before reporting a
    future runtime bridge as review-ready;
- Module status board: `ctoa_helper_module_status.lua` owns passive module
    ordering, readiness-row normalization, blocker counts, and summary text for
    evidence/UI review; it requires module contract plus ModuleStaticGates and
    never executes, dispatches, casts, talks, uses items, walks, or attacks;
- Action catalog: `ctoa_helper_action_catalog.lua` owns passive runtime action
    names, domain mapping, risk classes, and required gate metadata for future
    dispatchers; it models `plan_attack`, `plan_walk`, `plan_sio`, condition
    recovery, equipment swaps, passive scripting reviews, and hold actions
    without executing any of them;
- Decision trace: `ctoa_helper_decision_trace.lua` owns passive formatting of
    plan, runtime policy, dispatch guard, action catalog, and queue review
    records; it exposes reasons and missing gates for operator evidence without
    writing logs or executing queued plans;
- Sandbox handoff: `ctoa_helper_sandbox_handoff.lua` owns the passive operator
    sequence for sandbox runtime smoke: Launch, ReadyCheck, SmokeAttachModules,
    SmokeAttachAll, and explicit PromoteLiveCtoa approval; it never launches,
    attaches, promotes, or executes actions itself;
- Feature flags: `ctoa_helper_feature_flags.lua` owns the passive safe-default
    matrix for runtime and experimental flags, including auto haste, exeta,
    runes, cavebot movement, experimental loot, Heal Friend, Conditions,
    Equipment, and Scripting eval/snippet gates; it audits flag metadata without
    toggling profile values;
- HUD domain: `ctoa_helper_hud.lua` owns passive HUD text and position
  formatting while widget creation and visibility stay in the helper shell;
- UI domain: `ctoa_helper_ui.lua` owns passive CaveBot action metadata,
  CaveBot delay/reach choice metadata, and panel renderers while callback
  execution stays in the helper shell;
- Conditions domain: `ctoa_helper_conditions.lua` owns read-only condition state
  snapshots, API probe status text, observer sampling, passive recovery
  planning, tab summary text, and a static contract; it never triggers recovery
  actions and remains gated by `ModuleAttachSmoke`;
- Equipment domain: `ctoa_helper_equipment.lua` owns read-only inventory slot
  snapshots, equipment API probe status text, observer sampling, passive
  ring/amulet swap planning, tab summary text, and a static contract; it never
  swaps, moves, or uses items and remains gated by `ModuleAttachSmoke`;
- Scripting domain: `ctoa_helper_scripting.lua` owns deny-all policy status,
  passive policy planning, summary text, and a static contract; it never
  evaluates snippets, loads files, talks, or casts and remains gated by security
  review plus `ModuleAttachSmoke`;
- Heal Friend domain: `ctoa_helper_heal_friend.lua` owns whitelist matching,
  visible-player scan, observer status, and summary text; it never casts or
  sends chat and remains gated by `ModuleAttachSmoke`;
- Overview readiness matrix: implemented lanes show `ARMED`, `IDLE`, or
  `FLAG`, while prototype lanes show `OBSERVE` or `GATED` from the same
  registry without enabling new runtime actions;
- safe boot guard: runtime, healing, targeting, haste, exeta, runes, timer, and cavebot movement are disabled after profile load unless the operator arms them;
- BackgroundNoScreen reporter: writes only the bounded capability heartbeat at
  `mods/ctoa_otclient/ctoa_client_capabilities.json` under the client work
  directory. The external `ctoa.ps1 otbg` reader never sends input, focuses or
  captures a window, starts/stops the client, or authorizes runtime/promotion;
- P9 Conditions producer: reuses that 5-second heartbeat and emits only the
  optional, tri-state `ctoa.conditions-observation.v1` object. It exposes no
  names, IDs, coordinates, raw state masks, log lines, or paths, and all action,
  dispatch, execution, and promotion flags stay false;
- recovery engine: HP spell rotation, HP actionbar potion, MP actionbar potion, shared recovery gap, and real local-player vitals before percent fallback;
- combat engine: monster-only targeting, ignored NPC names, NPC icon blocking, priority target scoring, chase mode, PZ guard, action locks, exeta/rune/rotation planning, and debug decision text;
- cavebot route loop: waypoint editor, guarded `LocalPlayer:autoWalk`, PZ guard, path probe, retry budget, and automatic movement disable on repeated failure;
- timer action: bounded say/cast loop driven by `timer_interval_ms` and `timer_message`;
- loot scanner: passive valuable-item scoring, corpse/open-container scans, capacity guard, bounded item moves, and `experimental_loot` feature flag gating;
- prototype lanes: Conditions state observer, Equipment slot observer, Heal Friend party/whitelist observer, and Scripting policy shell persist profile settings and show read-only runtime evidence. Conditions, Equipment, and Heal Friend now have separate ordered dry-run safety gates, but no new executor is enabled.

Standalone legacy modules (`ctoa_native_heal.lua`, `ctoa_native_combat.lua`,
`ctoa_native_loot.lua`) are retained only as local source references. The
official Helper package, sandbox sync, loader manifest, P14 signed manifest,
and live promotion surface exclude them. Their maintained replacements are the
`ctoa_helper_*_runtime.lua`, observer, policy, and guarded bridge modules.

## ✅ Smoke Test (3 minutes)

1. Start OTClient and verify loader was called from `init.lua`.
2. Open in-game console and confirm at least one `[CTOA-OTC]` message appears.
3. Check `ctoa_local.log` (or `user_dir/ctoa_local.log`) and confirm fresh module entries.

Expected result: modules load without errors and log lines are appended on startup.

## ⚙️ Configuration

### Healing Module
```lua
-- Preferred: edit ctoa_ek_profile.lua or use the helper UI.
healing = {
    spell_enabled = false,
    potion_enabled = false,
    mana_potion_enabled = true,
    spell_threshold = 80,
    potion_threshold = 62,
    mana_potion_threshold = 45,
    spell = "exura ico",
    critical_spell = "exura med ico",
    potion_actionbar_slot = "F1",
    mana_potion_actionbar_slot = "F2",
}
```

### Combat Module
```lua
-- Edit profile priority targets, not runtime code.
tools = {
    auto_attack = false,
    chase = true,
    pause_in_pz = true,
    attack_range = 7,
    priority_names = {"demon", "dragon lord", "dragon"},
    ignored_names = {"hireling", "postman", "npc"},
}
```

### Prototype Module Lanes
```lua
-- These profiles are intentionally read-only until sandbox evidence exists.
heal_friend = { enabled = false, runtime_enabled = false }
conditions = { enabled = false, observe_states = true, api_probe_enabled = true, runtime_enabled = false }
equipment = {
    enabled = false,
    observe_slots = true,
    family_enabled = {ring_primary = false, ring_secondary = false},
    runtime_enabled = false,
}
scripting = { enabled = false, policy_mode = "deny_all", allow_user_snippets = false, allow_runtime_eval = false }
```

The module workplan in `docs/otclient/solteria_helper_module_workplan.md`
tracks the exact gate for each lane. `heal_friend` may read visible player
names/HP and match the whitelist, but it must not cast `exura sio` until
whitelist persistence and no-target sandbox smoke pass. `conditions` may read
`hasState`, `getStates`, and condition constants, and may produce passive
recovery plans, but it must not trigger recovery actions until sandbox state
evidence exists. `equipment` may read ring, amulet, and hand slots plus API
availability (`getInventoryItem` and slot constants), and may produce passive
ring/amulet swap plans, but it must not swap, move, or use inventory items until
the inventory API probe output and non-combat sandbox smoke pass.
`ctoa_helper_equipment_family_registry.lua` treats backpack, equipped, and
returned IDs as states of a named equipment family. The Equipment UI exposes
disabled-by-default family checkboxes and hides raw IDs. Unknown transitions
remain passive proposals requiring operator approval; amulet execution remains
deferred even though the schema is slot-generic.
`scripting` is a policy surface only: it can record intended settings and
produce passive `audit_only` / `policy_review` plans, but it must not call
`loadstring`, `dofile`, runtime eval, or user-provided snippets until a
security review, denylist tests, audit logging, and sandbox smoke exist.
New helper behavior must add or update a `MODULE_LANES` entry before UI or
runtime code is promoted.

### Loot Module
```lua
-- Loot stays gated behind runtime + experimental_loot.
tools = {
    auto_open_corpses = false,
    auto_loot_containers = false,
    loot_range = 2,
    loot_capacity_threshold = 50,
    loot_max_items_per_scan = 8,
    feature_flags = {
        experimental_loot = false,
    },
}
```

## Repo Validation

Use the repo-local checks before promoting helper files into a live client:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_otclient_helper_zerobot_shell.py tests\test_otclient_helper_profile_audit.py tests\test_ctoa_helper_smoke_report.py -q
.\.venv\Scripts\python.exe scripts\ops\otclient_helper_module_contract.py
```

For sandbox packaging and live-client safety checks:

```powershell
.\scripts\windows\solteria_helper_test_env.ps1 -Action SmokePreflight
```

## 🔍 Monitoring & Logs

All modules write detailed logs to:
- `ctoa_local.log` (primary)
- `user_dir/ctoa_local.log` (fallback)

**Log Format:**
```
2026-03-21 15:30:45 [CTOA-OTC-HEAL] Auto heal: exura (HP: 45%)
2026-03-21 15:30:47 [CTOA-OTC-COMBAT] New target: Dragon (priority: 3)
2026-03-21 15:30:50 [CTOA-OTC-LOOT] Looted: Gold Coin x25
```

## 🔗 OTClient API Reference

### Key APIs Used
- **g_game.talk()** - Cast spells/say text
- **g_game.attack()** - Attack creature  
- **g_game.move()** - Move items
- **g_map.getCreaturesInRange()** - Find creatures
- **connect()** - Event handling system
- **LocalPlayer events** - Health/mana changes
- **Container events** - Loot detection

## ⚠️ Safety Notes

1. **Legitimate Use Only**: OTClient is open-source, these modules use official APIs
2. **Server Rules**: Always comply with your server's automation policies
3. **Testing**: Test in safe areas before using in dangerous zones
4. **Monitoring**: Check logs regularly for issues

## 🔄 Integration with CTOA Generator

These modules are automatically generated by the CTOA AI system:
- **Generator Agent** creates server-specific versions
- **Validator Agent** checks syntax before deployment
- **Brain v2** schedules generation based on server data

## 📚 Advanced Usage

### Custom Module Integration
```lua
-- Register with CTOA Manager
CTOA_Manager:registerModule("my_module", {
    enabled = true,
    onThink = function() --[[ your logic ]] end
})
```

### Multi-Server Support
The CTOA system automatically adapts modules based on:
- Server monster data
- Available items/loot
- Player statistics
- Server-specific features

---

**🤖 Generated by CTOA AI Toolkit v1.0**  
*For support: Check logs, review OTClient documentation, verify API usage*
