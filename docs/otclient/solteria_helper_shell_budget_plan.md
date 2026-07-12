# Solteria Helper Shell Budget Plan

- Status: `needs_extraction`
- Helper lines: `4373` / `4500`
- Helper functions: `158` / `130`
- Over line budget by: `0`
- Over function budget by: `28`
- Under hard ceiling: `true`
- Next action: Extract the highest-line non-runtime text/metadata domain first, keep execution in guarded shell, then rerun ModuleStaticGates.

## Rule

Use this plan to choose the next extraction from measured shell pressure. Runtime execution remains in guarded shell paths until sandbox `SmokeAttachModules`, fresh `SmokeAttachAll`, and explicit live approval exist.

## Top Domains

| Domain | Functions | Lines | Next action |
|---|---:|---:|---|
| `shell_misc` | `55` | `893` | Keep this shell-only unless a named module owns the contract. |
| `runtime_combat` | `26` | `436` | Keep execution guarded; move remaining decision text and readiness summaries into combat/runtime adapters. |
| `diagnostics_smoke` | `16` | `417` | Keep smoke commands in the shell, but move static evidence formatting into diagnostics helpers. |
| `runtime_cavebot` | `19` | `406` | Keep autoWalk guarded; move remaining cavebot editor text and waypoint button state into route/cavebot adapters. |
| `runtime_recovery` | `11` | `189` | Mirror remaining recovery decision labels in passive healing metadata before changing potion/spell runtime. |
| `profile_persistence` | `10` | `187` | Move profile dirty-reason metadata and save/export field grouping into profile schema helpers. |
| `ui_builder` | `14` | `170` | Move repeated section/row builder metadata into passive UI descriptor tables before adding new tabs. |
| `input_contracts` | `5` | `68` | Expand fixture coverage before accepting new shortcuts or destructive commands. |
| `observer_modules` | `2` | `47` | Keep observers read-only; move any tab-only status text into their module summaries. |

## Largest Functions

| Domain | Function | Lines | Span |
|---|---|---:|---|
| `shell_misc` | `init` | `65` | `4166-4230` |
| `shell_misc` | `maybeUseTools` | `49` | `3041-3089` |
| `shell_misc` | `reportClientCapabilities` | `47` | `641-687` |
| `shell_misc` | `updateOverviewStats` | `43` | `1924-1966` |
| `shell_misc` | `maybeRunTimer` | `41` | `2999-3039` |
| `runtime_combat` | `executeOffensiveAction` | `60` | `2058-2117` |
| `runtime_combat` | `scanCombatArea` | `44` | `1606-1649` |
| `runtime_combat` | `retargetSafeMonster` | `43` | `1823-1865` |
| `runtime_combat` | `findBestAttackTarget` | `34` | `1773-1806` |
| `runtime_combat` | `rotationWaitReason` | `24` | `1985-2008` |
| `diagnostics_smoke` | `runApiProbe` | `97` | `2330-2426` |
| `diagnostics_smoke` | `applySmokeCommand` | `86` | `995-1080` |
| `diagnostics_smoke` | `runMagicApiProbe` | `44` | `2487-2530` |
| `diagnostics_smoke` | `refreshApiSnapshotUi` | `31` | `2255-2285` |
| `diagnostics_smoke` | `recordDiagnosticsSnapshot` | `22` | `2287-2308` |
| `runtime_cavebot` | `maybeRunCavebot` | `92` | `2820-2911` |
| `runtime_cavebot` | `autoWalkTo` | `57` | `2709-2765` |
| `runtime_cavebot` | `testCavebotAutoWalk` | `52` | `2767-2818` |
| `runtime_cavebot` | `runMovementApiProbe` | `45` | `2441-2485` |
| `runtime_cavebot` | `cavebotRuntimeMovementCapability` | `22` | `2620-2641` |
| `runtime_recovery` | `maybeHeal` | `46` | `2167-2212` |
| `runtime_recovery` | `maybeManaPotion` | `36` | `2913-2948` |
| `runtime_recovery` | `maybeObserveHealFriend` | `30` | `1719-1748` |
| `runtime_recovery` | `ensureCTOAManager` | `19` | `4342-4360` |
| `runtime_recovery` | `readPlayerVitals` | `12` | `2145-2156` |
| `profile_persistence` | `loadProfile` | `43` | `689-731` |
| `profile_persistence` | `loadUiPrefs` | `41` | `780-820` |
| `profile_persistence` | `applyHudPrefs` | `29` | `3743-3771` |
| `profile_persistence` | `markProfileDirty` | `23` | `1131-1153` |
| `profile_persistence` | `exportProfile` | `12` | `883-894` |

## Next Extraction Domains

1. `runtime_combat`
2. `diagnostics_smoke`
3. `runtime_cavebot`
4. `runtime_recovery`
5. `profile_persistence`

## Verification

```powershell
.\.venv\Scripts\python.exe scripts\ops\otclient_helper_shell_budget_plan.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action HelperShellBudgetPlanStaticSmoke
```
