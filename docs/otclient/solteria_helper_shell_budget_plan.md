# Solteria Helper Shell Budget Plan

- Status: `needs_extraction`
- Helper lines: `4349` / `4500`
- Helper functions: `159` / `130`
- Over line budget by: `0`
- Over function budget by: `29`
- Under hard ceiling: `true`
- Next action: Extract the highest-line non-runtime text/metadata domain first, keep execution in guarded shell, then rerun ModuleStaticGates.

## Rule

Use this plan to choose the next extraction from measured shell pressure. Runtime execution remains in guarded shell paths until sandbox `SmokeAttachModules`, fresh `SmokeAttachAll`, and explicit live approval exist.

## Top Domains

| Domain | Functions | Lines | Next action |
|---|---:|---:|---|
| `shell_misc` | `55` | `889` | Keep this shell-only unless a named module owns the contract. |
| `runtime_combat` | `27` | `436` | Keep execution guarded; move remaining decision text and readiness summaries into combat/runtime adapters. |
| `runtime_cavebot` | `19` | `406` | Keep autoWalk guarded; move remaining cavebot editor text and waypoint button state into route/cavebot adapters. |
| `diagnostics_smoke` | `16` | `404` | Keep smoke commands in the shell, but move static evidence formatting into diagnostics helpers. |
| `runtime_recovery` | `11` | `219` | Mirror remaining recovery decision labels in passive healing metadata before changing potion/spell runtime. |
| `profile_persistence` | `10` | `187` | Move profile dirty-reason metadata and save/export field grouping into profile schema helpers. |
| `ui_builder` | `14` | `170` | Move repeated section/row builder metadata into passive UI descriptor tables before adding new tabs. |
| `input_contracts` | `5` | `68` | Expand fixture coverage before accepting new shortcuts or destructive commands. |
| `observer_modules` | `2` | `47` | Keep observers read-only; move any tab-only status text into their module summaries. |

## Largest Functions

| Domain | Function | Lines | Span |
|---|---|---:|---|
| `shell_misc` | `init` | `65` | `4142-4206` |
| `shell_misc` | `maybeUseTools` | `49` | `3051-3099` |
| `shell_misc` | `reportClientCapabilities` | `43` | `639-681` |
| `shell_misc` | `updateOverviewStats` | `43` | `1905-1947` |
| `shell_misc` | `maybeRunTimer` | `41` | `3009-3049` |
| `runtime_combat` | `executeOffensiveAction` | `61` | `2040-2100` |
| `runtime_combat` | `retargetSafeMonster` | `43` | `1804-1846` |
| `runtime_combat` | `scanCombatArea` | `40` | `1591-1630` |
| `runtime_combat` | `findBestAttackTarget` | `34` | `1755-1788` |
| `runtime_combat` | `rotationWaitReason` | `24` | `1966-1989` |
| `runtime_cavebot` | `maybeRunCavebot` | `92` | `2830-2921` |
| `runtime_cavebot` | `autoWalkTo` | `57` | `2719-2775` |
| `runtime_cavebot` | `testCavebotAutoWalk` | `52` | `2777-2828` |
| `runtime_cavebot` | `runMovementApiProbe` | `45` | `2451-2495` |
| `runtime_cavebot` | `cavebotRuntimeMovementCapability` | `22` | `2630-2651` |
| `diagnostics_smoke` | `runApiProbe` | `97` | `2340-2436` |
| `diagnostics_smoke` | `applySmokeCommand` | `77` | `989-1065` |
| `diagnostics_smoke` | `runMagicApiProbe` | `44` | `2497-2540` |
| `diagnostics_smoke` | `refreshApiSnapshotUi` | `27` | `2269-2295` |
| `diagnostics_smoke` | `recordDiagnosticsSnapshot` | `22` | `2297-2318` |
| `runtime_recovery` | `maybeHeal` | `45` | `2182-2226` |
| `runtime_recovery` | `readPlayerVitals` | `43` | `2129-2171` |
| `runtime_recovery` | `maybeManaPotion` | `36` | `2923-2958` |
| `runtime_recovery` | `maybeObserveHealFriend` | `30` | `1701-1730` |
| `runtime_recovery` | `ensureCTOAManager` | `19` | `4318-4336` |
| `profile_persistence` | `loadProfile` | `43` | `683-725` |
| `profile_persistence` | `loadUiPrefs` | `41` | `774-814` |
| `profile_persistence` | `applyHudPrefs` | `29` | `3721-3749` |
| `profile_persistence` | `markProfileDirty` | `23` | `1116-1138` |
| `profile_persistence` | `exportProfile` | `12` | `877-888` |

## Next Extraction Domains

1. `runtime_combat`
2. `runtime_cavebot`
3. `diagnostics_smoke`
4. `runtime_recovery`
5. `profile_persistence`

## Verification

```powershell
.\.venv\Scripts\python.exe scripts\ops\otclient_helper_shell_budget_plan.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action HelperShellBudgetPlanStaticSmoke
```
