# Solteria Helper Sandbox Smoke Queue

## Decision

- Status: `ready_for_operator`
- Helper version: `v2.4.1`
- Runtime status: `not_running`
- Release gate: `blocked`
- Next action: Launch sandbox client and enter test character
- Live safety: read-only plan; live promotion still requires `-ApproveLiveDeploy`.

## Queue

| Order | Step | Status | Command | Evidence | Reason |
|---:|---|---:|---|---|---|
| 1 | `local_ready` / Refresh local package and static gates | `passed` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action LocalReady` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\local_ready.json` | Local package, SmokePreflight, ModuleStaticGates, and GoalStatus should be current before attach. |
| 2 | `launch_sandbox` / Launch sandbox client and enter test character | `required` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action Launch` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\smoke_status.json` | Launch the sandbox client, enter test character, then run SmokeAttachModules. |
| 3 | `ready_check` / Confirm helper is attached in-world | `required` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ReadyCheck` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\ready_check.json` | Run after the sandbox character is in-world; character-select screens are not enough. |
| 4 | `module_attach_group` / Capture grouped prototype module tab evidence | `required` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttachModules` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\module_attach_smoke.json` | ModuleAttachSmoke manifest SHA256 does not match the current dev manifest; rerun SmokeAttachModules after sandbox character is in-world. |
| 5 | `attach_conditions` / Attach module tab: conditions | `queued` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab conditions` | `runtime\solteria_helper_dev\module_attach_smoke.json` | Static gate is passed; in-world tab evidence is still required. |
| 6 | `attach_equipment` / Attach module tab: equipment | `queued` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab equipment` | `runtime\solteria_helper_dev\module_attach_smoke.json` | Static gate is passed; in-world tab evidence is still required. |
| 7 | `attach_heal_friend` / Attach module tab: heal_friend | `queued` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab heal_friend` | `runtime\solteria_helper_dev\module_attach_smoke.json` | Static gate is passed; in-world tab evidence is still required. |
| 8 | `attach_scripting` / Attach module tab: scripting | `queued` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab scripting` | `runtime\solteria_helper_dev\module_attach_smoke.json` | Static gate is passed; in-world tab evidence is still required. |
| 9 | `attach_hud` / Attach module tab: hud | `queued` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab tools_hud` | `runtime\solteria_helper_dev\module_attach_smoke.json` | Static gate is passed; in-world tab evidence is still required. |
| 10 | `attach_route` / Attach module tab: route | `queued` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab cavebot` | `runtime\solteria_helper_dev\module_attach_smoke.json` | Static gate is passed; in-world tab evidence is still required. |
| 11 | `attach_targeting` / Attach module tab: targeting | `queued` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab hunting` | `runtime\solteria_helper_dev\module_attach_smoke.json` | Static gate is passed; in-world tab evidence is still required. |
| 12 | `attach_combat_runtime` / Attach module tab: combat_runtime | `queued` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab hunting_magic` | `runtime\solteria_helper_dev\module_attach_smoke.json` | Static gate is passed; in-world tab evidence is still required. |
| 13 | `attach_cavebot_runtime` / Attach module tab: cavebot_runtime | `queued` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab cavebot` | `runtime\solteria_helper_dev\module_attach_smoke.json` | Static gate is passed; in-world tab evidence is still required. |
| 14 | `attach_loot_runtime` / Attach module tab: loot_runtime | `queued` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab tools_diag` | `runtime\solteria_helper_dev\module_attach_smoke.json` | Static gate is passed; in-world tab evidence is still required. |
| 15 | `attach_timer_runtime` / Attach module tab: timer_runtime | `queued` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab tools_timer` | `runtime\solteria_helper_dev\module_attach_smoke.json` | Static gate is passed; in-world tab evidence is still required. |
| 16 | `smoke_attach_all` / Capture full in-world helper acceptance | `required` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttachAll` | `C:\Users\zycie\CTOAi\runtime\otclient_ui_preview\solteria-helper-smokeall-inworld-20260715-1859.json` | SmokeAttachAll manifest SHA256 does not match the current dev manifest; rerun SmokeAttachAll after sandbox character is in-world. |
| 17 | `promote_live_approval` / Promote only after explicit live approval | `required` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action PromoteLiveCtoa -ApproveLiveDeploy -SmokeReport <fresh-smokeattachall-json>` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\live_promotion.json` | Live promotion report is older than the current dev manifest; rerun promotion after the current gates pass. |

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
