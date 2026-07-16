# Solteria Helper Module Contract

- Status: `passed`
- Expected modules: `38`
- Passed modules: `38`
- Failed modules: `0`
- Registry lanes: `9` / `9`
- Forbidden passive hits: `0`
- Next action: Run ModuleStaticGates, then sandbox SmokeAttachModules.

## Rule

Passive helper modules may observe, format, plan, or expose UI state. They must not cast spells, use items, walk, execute snippets, or load arbitrary files. Runtime actions stay in the guarded native helper domains and still require sandbox evidence.

## Modules

| Module | File | Status | Loader | Registry | Global | Return | Missing functions | Forbidden |
|---|---|---:|---:|---:|---:|---:|---|---|
| `modules` | `ctoa_helper_modules.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `domain_contract` | `ctoa_helper_domain_contract.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `rule_engine` | `ctoa_helper_rule_engine.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `ui_primitives` | `ctoa_helper_ui_primitives.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `ui_composition` | `ctoa_helper_ui_composition.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `ui_rule_editors` | `ctoa_helper_ui_rule_editors.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `ui` | `ctoa_helper_ui.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `diagnostics` | `ctoa_helper_diagnostics.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `hotkeys` | `ctoa_helper_hotkeys.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `modal` | `ctoa_helper_modal.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `route` | `ctoa_helper_route.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `targeting` | `ctoa_helper_targeting.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `combat_runtime` | `ctoa_helper_combat_runtime.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `spell_state_registry` | `ctoa_helper_spell_state_registry.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `cavebot_runtime` | `ctoa_helper_cavebot_runtime.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `loot_runtime` | `ctoa_helper_loot_runtime.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `timer_runtime` | `ctoa_helper_timer_runtime.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `recovery_runtime` | `ctoa_helper_recovery_runtime.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `profile_schema` | `ctoa_helper_profile_schema.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `profile_persistence` | `ctoa_helper_profile_persistence.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `rule_presets` | `ctoa_helper_rule_presets.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `operator_summary` | `ctoa_helper_operator_summary.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `planner` | `ctoa_helper_planner.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `runtime_policy` | `ctoa_helper_runtime_policy.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `dispatch_guard` | `ctoa_helper_dispatch_guard.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `plan_queue` | `ctoa_helper_plan_queue.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `runtime_readiness` | `ctoa_helper_runtime_readiness.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `module_status` | `ctoa_helper_module_status.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `action_catalog` | `ctoa_helper_action_catalog.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `decision_trace` | `ctoa_helper_decision_trace.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `decision_pipeline` | `ctoa_helper_decision_pipeline.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `sandbox_handoff` | `ctoa_helper_sandbox_handoff.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `feature_flags` | `ctoa_helper_feature_flags.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `hud` | `ctoa_helper_hud.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `conditions` | `ctoa_helper_conditions.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `equipment` | `ctoa_helper_equipment.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `scripting` | `ctoa_helper_scripting.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `heal_friend` | `ctoa_helper_heal_friend.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |

## Verification

```powershell
.\.venv\Scripts\python.exe scripts\ops\otclient_helper_module_contract.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ModuleStaticGates
```
