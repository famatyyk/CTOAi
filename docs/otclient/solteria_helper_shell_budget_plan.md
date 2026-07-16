# Solteria Helper Shell Budget Plan

- Status: `within_budget`
- Helper lines: `3576` / `4500`
- Helper functions: `102` / `130`
- Over line budget by: `0`
- Over function budget by: `0`
- Under hard ceiling: `true`
- Next action: Keep budgets guarded before adding new modules.

## Rule

Use this plan to choose the next extraction from measured shell pressure. Runtime execution remains in guarded shell paths until sandbox `SmokeAttachModules`, fresh `SmokeAttachAll`, and explicit live approval exist.

## Top Domains

| Domain | Functions | Lines | Next action |
|---|---:|---:|---|
| `shell_misc` | `40` | `742` | Keep this shell-only unless a named module owns the contract. |
| `runtime_combat` | `18` | `359` | Keep execution guarded; move remaining decision text and readiness summaries into combat/runtime adapters. |
| `runtime_cavebot` | `9` | `318` | Keep autoWalk guarded; move remaining cavebot editor text and waypoint button state into route/cavebot adapters. |
| `diagnostics_smoke` | `7` | `230` | Keep smoke commands in the shell, but move static evidence formatting into diagnostics helpers. |
| `runtime_recovery` | `8` | `163` | Mirror remaining recovery decision labels in passive healing metadata before changing potion/spell runtime. |
| `profile_persistence` | `5` | `159` | Move profile dirty-reason metadata and save/export field grouping into profile schema helpers. |
| `ui_builder` | `10` | `137` | Move repeated section/row builder metadata into passive UI descriptor tables before adding new tabs. |
| `observer_modules` | `2` | `47` | Keep observers read-only; move any tab-only status text into their module summaries. |
| `input_contracts` | `2` | `29` | Expand fixture coverage before accepting new shortcuts or destructive commands. |
| `operator_summary` | `1` | `7` | Move remaining operator-facing prose into ctoa_helper_operator_summary.lua. |

## Largest Functions

| Domain | Function | Lines | Span |
|---|---|---:|---|
| `shell_misc` | `init` | `70` | `3334-3403` |
| `shell_misc` | `updateOverviewStats` | `57` | `1296-1352` |
| `shell_misc` | `maybeUseTools` | `54` | `2076-2129` |
| `shell_misc` | `maybeRunTimer` | `41` | `2034-2074` |
| `shell_misc` | `onThink` | `39` | `2131-2169` |
| `runtime_combat` | `retargetSafeMonster` | `54` | `1166-1219` |
| `runtime_combat` | `scanCombatArea` | `44` | `978-1021` |
| `runtime_combat` | `executeOffensiveAction` | `32` | `1423-1454` |
| `runtime_combat` | `applyRotationPreset` | `32` | `2647-2678` |
| `runtime_combat` | `isMonsterCreature` | `27` | `927-953` |
| `runtime_cavebot` | `maybeRunCavebot` | `98` | `1849-1946` |
| `runtime_cavebot` | `autoWalkTo` | `62` | `1732-1793` |
| `runtime_cavebot` | `testCavebotAutoWalk` | `53` | `1795-1847` |
| `runtime_cavebot` | `runMovementApiProbe` | `50` | `1582-1631` |
| `runtime_cavebot` | `deleteCurrentCavebotWaypoint` | `15` | `1716-1730` |
| `diagnostics_smoke` | `applySmokeCommand` | `112` | `490-601` |
| `diagnostics_smoke` | `runMagicApiProbe` | `44` | `1633-1676` |
| `diagnostics_smoke` | `appendLog` | `18` | `159-176` |
| `diagnostics_smoke` | `status` | `17` | `178-194` |
| `diagnostics_smoke` | `processSmokeCommand` | `17` | `603-619` |
| `runtime_recovery` | `maybeHeal` | `46` | `1495-1540` |
| `runtime_recovery` | `maybeManaPotion` | `36` | `1948-1983` |
| `runtime_recovery` | `maybeObserveHealFriend` | `33` | `1075-1107` |
| `runtime_recovery` | `ensureCTOAManager` | `19` | `3545-3563` |
| `runtime_recovery` | `readPlayerVitals` | `12` | `1482-1493` |
| `profile_persistence` | `loadProfile` | `57` | `233-289` |
| `profile_persistence` | `loadUiPrefs` | `45` | `338-382` |
| `profile_persistence` | `applyHudPrefs` | `29` | `2847-2875` |
| `profile_persistence` | `markProfileDirty` | `23` | `665-687` |
| `profile_persistence` | `applyUiPrefs` | `5` | `417-421` |

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
