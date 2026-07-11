# Solteria Helper Shell Budget Plan

- Status: `needs_extraction`
- Helper lines: `4350` / `4500`
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
| `shell_misc` | `55` | `882` | Keep this shell-only unless a named module owns the contract. |
| `runtime_cavebot` | `19` | `406` | Keep autoWalk guarded; move remaining cavebot editor text and waypoint button state into route/cavebot adapters. |
| `diagnostics_smoke` | `16` | `404` | Keep smoke commands in the shell, but move static evidence formatting into diagnostics helpers. |
| `runtime_combat` | `26` | `403` | Keep execution guarded; move remaining decision text and readiness summaries into combat/runtime adapters. |
| `runtime_recovery` | `11` | `219` | Mirror remaining recovery decision labels in passive healing metadata before changing potion/spell runtime. |
| `profile_persistence` | `10` | `175` | Move profile dirty-reason metadata and save/export field grouping into profile schema helpers. |
| `ui_builder` | `14` | `170` | Move repeated section/row builder metadata into passive UI descriptor tables before adding new tabs. |
| `input_contracts` | `5` | `68` | Expand fixture coverage before accepting new shortcuts or destructive commands. |
| `observer_modules` | `2` | `47` | Keep observers read-only; move any tab-only status text into their module summaries. |

## Largest Functions

| Domain | Function | Lines | Span |
|---|---|---:|---|
| `shell_misc` | `init` | `65` | `4156-4220` |
| `shell_misc` | `maybeUseTools` | `49` | `3070-3118` |
| `shell_misc` | `updateOverviewStats` | `43` | `1944-1986` |
| `shell_misc` | `reportClientCapabilities` | `41` | `706-746` |
| `shell_misc` | `maybeRunTimer` | `41` | `3028-3068` |
| `runtime_cavebot` | `maybeRunCavebot` | `92` | `2849-2940` |
| `runtime_cavebot` | `autoWalkTo` | `57` | `2738-2794` |
| `runtime_cavebot` | `testCavebotAutoWalk` | `52` | `2796-2847` |
| `runtime_cavebot` | `runMovementApiProbe` | `45` | `2470-2514` |
| `runtime_cavebot` | `cavebotRuntimeMovementCapability` | `22` | `2649-2670` |
| `diagnostics_smoke` | `runApiProbe` | `97` | `2359-2455` |
| `diagnostics_smoke` | `applySmokeCommand` | `77` | `1042-1118` |
| `diagnostics_smoke` | `runMagicApiProbe` | `44` | `2516-2559` |
| `diagnostics_smoke` | `refreshApiSnapshotUi` | `27` | `2288-2314` |
| `diagnostics_smoke` | `recordDiagnosticsSnapshot` | `22` | `2316-2337` |
| `runtime_combat` | `retargetSafeMonster` | `43` | `1843-1885` |
| `runtime_combat` | `executeOffensiveAction` | `43` | `2077-2119` |
| `runtime_combat` | `scanCombatArea` | `40` | `1644-1683` |
| `runtime_combat` | `findBestAttackTarget` | `34` | `1794-1827` |
| `runtime_combat` | `rotationWaitReason` | `24` | `2005-2028` |
| `runtime_recovery` | `maybeHeal` | `45` | `2201-2245` |
| `runtime_recovery` | `readPlayerVitals` | `43` | `2148-2190` |
| `runtime_recovery` | `maybeManaPotion` | `36` | `2942-2977` |
| `runtime_recovery` | `maybeObserveHealFriend` | `30` | `1741-1770` |
| `runtime_recovery` | `ensureCTOAManager` | `19` | `4318-4336` |
| `profile_persistence` | `loadUiPrefs` | `41` | `827-867` |
| `profile_persistence` | `loadProfile` | `31` | `748-778` |
| `profile_persistence` | `applyHudPrefs` | `29` | `3735-3763` |
| `profile_persistence` | `markProfileDirty` | `23` | `1169-1191` |
| `profile_persistence` | `exportProfile` | `12` | `930-941` |

## Next Extraction Domains

1. `runtime_cavebot`
2. `diagnostics_smoke`
3. `runtime_combat`
4. `runtime_recovery`
5. `profile_persistence`

## Verification

```powershell
.\.venv\Scripts\python.exe scripts\ops\otclient_helper_shell_budget_plan.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action HelperShellBudgetPlanStaticSmoke
```
