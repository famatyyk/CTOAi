# Solteria Helper Sandbox Smoke Queue

## Decision

- Status: `passed`
- Helper version: `v2.0.0`
- Runtime status: `ready_for_readycheck`
- Release gate: `passed`
- Next action: Refresh local package and static gates
- Live safety: read-only plan; live promotion still requires `-ApproveLiveDeploy`.

## Queue

| Order | Step | Status | Command | Evidence | Reason |
|---:|---|---:|---|---|---|
| 1 | `local_ready` / Refresh local package and static gates | `required` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action LocalReady` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\local_ready.json` | Local package, SmokePreflight, ModuleStaticGates, and GoalStatus should be current before attach. |
| 2 | `launch_sandbox` / Launch sandbox client and enter test character | `required` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action Launch` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\smoke_status.json` | Run ReadyCheck, then SmokeAttachModules when the test character is in-world. |
| 3 | `ready_check` / Confirm helper is attached in-world | `required` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ReadyCheck` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\ready_check.json` | Run after the sandbox character is in-world; character-select screens are not enough. |
| 4 | `module_attach_group` / Capture grouped prototype module tab evidence | `passed` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttachModules` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\module_attach_smoke.json` | Prototype module tabs need grouped in-world evidence. |
| 5 | `attach_heal_friend` / Attach module tab: heal_friend | `passed` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab heal_friend` | `runtime\solteria_helper_dev\module_attach_smoke.json` | Static gate is passed; in-world tab evidence is still required. |
| 6 | `attach_conditions` / Attach module tab: conditions | `passed` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab conditions` | `runtime\solteria_helper_dev\module_attach_smoke.json` | Static gate is passed; in-world tab evidence is still required. |
| 7 | `attach_equipment` / Attach module tab: equipment | `passed` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab equipment` | `runtime\solteria_helper_dev\module_attach_smoke.json` | Static gate is passed; in-world tab evidence is still required. |
| 8 | `attach_scripting` / Attach module tab: scripting | `passed` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab scripting` | `runtime\solteria_helper_dev\module_attach_smoke.json` | Static gate is passed; in-world tab evidence is still required. |
| 9 | `attach_hud` / Attach module tab: hud | `passed` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab tools_hud` | `runtime\solteria_helper_dev\module_attach_smoke.json` | Static gate is passed; in-world tab evidence is still required. |
| 10 | `attach_route` / Attach module tab: route | `passed` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab cavebot` | `runtime\solteria_helper_dev\module_attach_smoke.json` | Static gate is passed; in-world tab evidence is still required. |
| 11 | `attach_targeting` / Attach module tab: targeting | `passed` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab hunting` | `runtime\solteria_helper_dev\module_attach_smoke.json` | Static gate is passed; in-world tab evidence is still required. |
| 12 | `attach_combat_runtime` / Attach module tab: combat_runtime | `passed` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab hunting_magic` | `runtime\solteria_helper_dev\module_attach_smoke.json` | Static gate is passed; in-world tab evidence is still required. |
| 13 | `attach_cavebot_runtime` / Attach module tab: cavebot_runtime | `passed` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab cavebot` | `runtime\solteria_helper_dev\module_attach_smoke.json` | Static gate is passed; in-world tab evidence is still required. |
| 14 | `attach_loot_runtime` / Attach module tab: loot_runtime | `passed` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab tools_diag` | `runtime\solteria_helper_dev\module_attach_smoke.json` | Static gate is passed; in-world tab evidence is still required. |
| 15 | `attach_timer_runtime` / Attach module tab: timer_runtime | `passed` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab tools_timer` | `runtime\solteria_helper_dev\module_attach_smoke.json` | Static gate is passed; in-world tab evidence is still required. |
| 16 | `smoke_attach_all` / Capture full in-world helper acceptance | `passed` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttachAll` | `C:\Users\zycie\CTOAi\runtime\otclient_ui_preview\solteria-helper-smokeall-inworld-20260711-0131.json` | Fresh full attach report is required for the current manifest. |
| 17 | `promote_live_approval` / Promote only after explicit live approval | `passed` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action PromoteLiveCtoa -ApproveLiveDeploy -SmokeReport <fresh-smokeattachall-json>` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\live_promotion.json` | Live promotion remains gated by explicit approval. |

## Static-Only Modules

| Module | Status | Evidence | Reason |
|---|---:|---|---|
| `planner` | `passed` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\planner_static_smoke.json` | No dedicated UI tab; covered by static gate report and grouped module attach context. |
| `runtime_policy` | `passed` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\runtime_policy_static_smoke.json` | No dedicated UI tab; covered by static gate report and grouped module attach context. |
| `dispatch_guard` | `passed` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\dispatch_guard_static_smoke.json` | No dedicated UI tab; covered by static gate report and grouped module attach context. |
| `plan_queue` | `passed` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\plan_queue_static_smoke.json` | No dedicated UI tab; covered by static gate report and grouped module attach context. |
| `runtime_readiness` | `passed` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\runtime_readiness_static_smoke.json` | No dedicated UI tab; covered by static gate report and grouped module attach context. |
| `module_status` | `passed` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\module_status_static_smoke.json` | No dedicated UI tab; covered by static gate report and grouped module attach context. |
| `action_catalog` | `passed` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\action_catalog_static_smoke.json` | No dedicated UI tab; covered by static gate report and grouped module attach context. |
| `decision_trace` | `passed` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\decision_trace_static_smoke.json` | No dedicated UI tab; covered by static gate report and grouped module attach context. |
| `sandbox_handoff` | `passed` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\sandbox_handoff_static_smoke.json` | No dedicated UI tab; covered by static gate report and grouped module attach context. |
| `feature_flags` | `passed` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\feature_flags_static_smoke.json` | No dedicated UI tab; covered by static gate report and grouped module attach context. |
| `hotkeys` | `passed` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\hotkeys_static_smoke.json` | No dedicated UI tab; covered by static gate report and grouped module attach context. |
| `modal` | `passed` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\modal_static_smoke.json` | No dedicated UI tab; covered by static gate report and grouped module attach context. |
| `input_contracts` | `passed` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\input_contract_fixtures.json` | No dedicated UI tab; covered by static gate report and grouped module attach context. |
| `profile_schema` | `passed` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\profile_schema_static_smoke.json` | No dedicated UI tab; covered by static gate report and grouped module attach context. |
| `operator_summary` | `passed` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\operator_summary_static_smoke.json` | No dedicated UI tab; covered by static gate report and grouped module attach context. |
| `external_bot_import_gate` | `passed` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\external_bot_import_gate_static_smoke.json` | No dedicated UI tab; covered by static gate report and grouped module attach context. |
| `helper_shell_budget` | `passed` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\helper_shell_budget_static_smoke.json` | No dedicated UI tab; covered by static gate report and grouped module attach context. |
| `helper_shell_budget_plan` | `passed` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\helper_shell_budget_plan.json` | No dedicated UI tab; covered by static gate report and grouped module attach context. |

## Operator Rule

Run this queue from top to bottom. If any attach step reports character-select, offline helper, stale manifest, or failed screenshot evidence, stop and refresh `LocalReady` before continuing.
