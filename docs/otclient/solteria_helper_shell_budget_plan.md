# Solteria Helper Shell Budget Plan

- Status: `within_budget`
- Helper lines: `4404` / `4500`
- Helper functions: `130` / `130`
- Over line budget by: `0`
- Over function budget by: `0`
- Under hard ceiling: `true`
- Next action: Keep budgets guarded before adding new modules.

## Rule

Use this plan to choose the next extraction from measured shell pressure. Runtime execution remains in guarded shell paths until sandbox `SmokeAttachModules`, fresh `SmokeAttachAll`, and explicit live approval exist.

## Top Domains

| Domain | Functions | Lines | Next action |
|---|---:|---:|---|
| `shell_misc` | `48` | `946` | Keep this shell-only unless a named module owns the contract. |
| `diagnostics_smoke` | `16` | `449` | Keep smoke commands in the shell, but move static evidence formatting into diagnostics helpers. |
| `runtime_combat` | `22` | `417` | Keep execution guarded; move remaining decision text and readiness summaries into combat/runtime adapters. |
| `runtime_cavebot` | `16` | `377` | Keep autoWalk guarded; move remaining cavebot editor text and waypoint button state into route/cavebot adapters. |
| `runtime_recovery` | `9` | `174` | Mirror remaining recovery decision labels in passive healing metadata before changing potion/spell runtime. |
| `profile_persistence` | `5` | `142` | Move profile dirty-reason metadata and save/export field grouping into profile schema helpers. |
| `ui_builder` | `10` | `137` | Move repeated section/row builder metadata into passive UI descriptor tables before adding new tabs. |
| `observer_modules` | `2` | `47` | Keep observers read-only; move any tab-only status text into their module summaries. |
| `input_contracts` | `2` | `29` | Expand fixture coverage before accepting new shortcuts or destructive commands. |

## Largest Functions

| Domain | Function | Lines | Span |
|---|---|---:|---|
| `shell_misc` | `moduleValue` | `118` | `208-325` |
| `shell_misc` | `init` | `70` | `4163-4232` |
| `shell_misc` | `maybeUseTools` | `49` | `2967-3015` |
| `shell_misc` | `updateOverviewStats` | `43` | `1928-1970` |
| `shell_misc` | `maybeRunTimer` | `41` | `2925-2965` |
| `diagnostics_smoke` | `applySmokeCommand` | `112` | `988-1099` |
| `diagnostics_smoke` | `runApiProbe` | `97` | `2288-2384` |
| `diagnostics_smoke` | `runMagicApiProbe` | `44` | `2450-2493` |
| `diagnostics_smoke` | `refreshApiSnapshotUi` | `31` | `2213-2243` |
| `diagnostics_smoke` | `recordDiagnosticsSnapshot` | `22` | `2245-2266` |
| `runtime_combat` | `executeOffensiveAction` | `60` | `2036-2095` |
| `runtime_combat` | `retargetSafeMonster` | `51` | `1814-1864` |
| `runtime_combat` | `scanCombatArea` | `44` | `1594-1637` |
| `runtime_combat` | `findBestAttackTarget` | `34` | `1764-1797` |
| `runtime_combat` | `isMonsterCreature` | `27` | `1523-1549` |
| `runtime_cavebot` | `maybeRunCavebot` | `92` | `2746-2837` |
| `runtime_cavebot` | `autoWalkTo` | `58` | `2633-2690` |
| `runtime_cavebot` | `testCavebotAutoWalk` | `53` | `2692-2744` |
| `runtime_cavebot` | `runMovementApiProbe` | `50` | `2399-2448` |
| `runtime_cavebot` | `cavebotRuntimeMovementCapability` | `22` | `2575-2596` |
| `runtime_recovery` | `maybeHeal` | `46` | `2136-2181` |
| `runtime_recovery` | `maybeManaPotion` | `36` | `2839-2874` |
| `runtime_recovery` | `maybeObserveHealFriend` | `33` | `1715-1747` |
| `runtime_recovery` | `ensureCTOAManager` | `19` | `4373-4391` |
| `runtime_recovery` | `readPlayerVitals` | `12` | `2123-2134` |
| `profile_persistence` | `loadProfile` | `46` | `702-747` |
| `profile_persistence` | `loadUiPrefs` | `39` | `796-834` |
| `profile_persistence` | `applyHudPrefs` | `29` | `3752-3780` |
| `profile_persistence` | `markProfileDirty` | `23` | `1152-1174` |
| `profile_persistence` | `applyUiPrefs` | `5` | `869-873` |

## Next Extraction Domains

1. `diagnostics_smoke`
2. `runtime_combat`
3. `runtime_cavebot`
4. `runtime_recovery`

## Verification

```powershell
.\.venv\Scripts\python.exe scripts\ops\otclient_helper_shell_budget_plan.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action HelperShellBudgetPlanStaticSmoke
```
