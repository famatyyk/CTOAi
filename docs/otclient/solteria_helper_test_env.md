# Solteria Helper Test Environment

This sandbox runs a separate Solteria client from:

```text
C:\Users\zycie\AppData\Local\SolteriaCodexTest\client
```

It keeps mutable CTOA files, logs, and UI preferences separate from the normal play client:

```text
C:\Users\zycie\AppData\Local\Solteria\client
```

Large data folders/packages are linked to avoid duplicating the full client. The executable files are copied, not hardlinked, so the sandbox can run next to the normal client.

## Commands

Prepare a development package and manifest without launching, stopping, or
overwriting the live play client:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action PrepareDev
```

Run static validation for the current development package without touching the
live play client:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ValidateDev
```

Prepare sandbox files:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action Setup -Tab healing
```

Verify sandbox files match the staged dev package without launching a client:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokePreflight
```

`SmokePreflight` uses the latest staged package and only creates a fresh one
when the staged package is missing, so it does not reset a freshly passed
`ValidateDev` report.

Inspect current sandbox smoke readiness without launching or stopping a client:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeStatus
```

`SmokeStatus` writes `next_action` and `next_command` into
`runtime\solteria_helper_dev\smoke_status.json` so the next safe operator step
is explicit. The report is written atomically and uses simple process summaries
so a blocked or closed sandbox does not leave a partial JSON file.

Refresh the full development goal status without launching or stopping a
client:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action GoalStatus
```

`GoalStatus` refreshes `release_gate.json` and `goal_audit.json`, writes
`runtime\solteria_helper_dev\goal_status.json`, and prints P0-P5 status,
current blockers, and the next safe command when a next gate still exists. It
does not launch, stop, or overwrite any client.

Collect passive live evidence while the user keeps the only game screen:

```powershell
.\ctoa.ps1 otbg
```

Equivalent explicit wrapper command:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action BackgroundStatus -OperatorMode BackgroundNoScreen
```

`BackgroundNoScreen` has a positive allowlist containing only
`BackgroundStatus`. The mode is inherited by child processes and cannot be
downgraded. It rejects live approval, launch, helper-toggle, and dialog-control
parameters before dispatch. The action performs bounded passive reads, checks
immutable live parity against the manifest cryptographically bound to the
official promotion report, and writes only
`runtime\solteria_helper_dev\background_status.json`. It does not move the
mouse, send keys, focus or capture a window, start/stop a client, write a smoke
command, copy into live, or approve promotion. Use `-NoReport` for stdout-only
JSON with no evidence-file write. It requires the canonical
`%LOCALAPPDATA%\Solteria\client` root and the trusted repo-local interpreter.

Missing, stale, offline, cross-client, incomplete, or pre-process capability
heartbeat is reported as waiting/blocked rather than ready. A missing or
untrusted official live-manifest pin also blocks; the observer never creates
that pin. Only `PromoteLiveCtoa -ApproveLiveDeploy` writes it and binds its
SHA256 into `live_promotion.json`. Mutable vocation-profile drift is counted
separately from other package-code mismatch, but still blocks because those
profiles are executable Lua. The wrapper only publishes the sample after client
process identity and screenshot count are checked.

Run the P9 Conditions data-only replay through the same bounded entry path:

```powershell
.\ctoa.ps1 otp9
```

`otp9` first invokes the allowlisted `BackgroundStatus` action, requires a fresh
repo-local `background_status.json`, and then runs the trusted repo interpreter
against `scripts\ops\otclient_conditions_shadow_replay.py`. It refreshes only
the two repo-local evidence artifacts `background_status.json` and
`conditions_shadow_replay.json`. A green fixture
pack is reported separately from operational acceptance; missing or unaccepted
P8, Conditions, or Recovery evidence remains blocked. The command never adds a
wrapper action, interacts with the client window, dispatches, executes once, or
promotes live.

Emergency-disable CTOA modules in the normal live Solteria client when login is
unstable:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action DisableLiveCtoa
```

Re-enable them after testing:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action EnableLiveCtoa
```

Launch the sandbox manually:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action Launch -Tab healing
```

Capture the current sandbox window without restarting or changing helper tabs:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action Snapshot
```

Check whether the sandbox is ready for in-world attach smoke:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ReadyCheck
```

`ReadyCheck` writes `runtime\solteria_helper_dev\ready_check.json` for both
success and blocker states. If the sandbox window is missing, or if the Select
Character modal/helper-offline state blocks tab switching, the JSON records the
status, latest smoke marker, screenshot path when available, and next safe
command.

Verify real HP/MP observation while the sandbox runtime is disarmed:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action HealingVitalsSmoke
```

This writes `runtime\solteria_helper_dev\healing_vitals_smoke.json`. It reads
only the sandbox `ctoa_local.log`, requires a real bounded HP/mana API sample,
and fails closed unless the latest runtime state is disarmed. It never casts,
uses potions, arms runtime, launches a client, or touches the live client. After
it passes, capture newer visual evidence with `SmokeAttach -Tab healing`.

Verify the passive Combat/PZ/NPC safety lane with a fresh manual API probe:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action CombatSafetySmoke
```

This writes `runtime\solteria_helper_dev\combat_safety_smoke.json`. It combines
the targeting and combat-runtime static reports with a fresh read-only sandbox
probe, requires no active target, and requires runtime to be disarmed before and
throughout the probe. It does not attack, follow, cast, use runes/items, or touch
the live client. After it passes, refresh Hunting and Hunting/Magic evidence
with `SmokeAttachAll`.

Verify the CaveBot planner without walking or pathfinding:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action CavebotSafetySmoke
```

Verify one passive Timer planning tick while Timer and runtime remain disabled:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action TimerSafetySmoke
```

Verify read-only container capabilities while experimental Loot remains off:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action LootSafetySmoke
```

These reports require current static gates and disarmed runtime. CaveBot records
capabilities and route guards only, Timer must return `hold_timer_disabled`,
and Loot must return `hold_feature_flag_disabled` with zero planned items.
Refresh their evidence with `SmokeAttach -Tab cavebot`,
`SmokeAttach -Tab tools_timer`, and `SmokeAttach -Tab tools_diag`.

Run the static Heal Friend no-target contract before enabling any sio path:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action HealFriendNoTargetSmoke
```

This writes `runtime\solteria_helper_dev\heal_friend_no_target_smoke.json` and
checks the read-only observer, safe boot profile defaults, whitelist guard, and
absence of `castSpell`, actionbar sends, and `g_game.talk` in the Heal Friend
observer slice. It does not launch, stop, or overwrite any client.

Run the static Conditions observer contract before enabling any condition
recovery action:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ConditionsObserverSmoke
```

This writes `runtime\solteria_helper_dev\conditions_observer_smoke.json` and
checks the read-only state/API observer, safe boot profile defaults, and absence
of `castSpell`, actionbar sends, and `g_game.talk` in the Conditions observer
slice. It does not launch, stop, or overwrite any client.

Run the static Equipment observer contract before enabling any ring, amulet, or
weapon swap path:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action EquipmentObserverSmoke
```

This writes `runtime\solteria_helper_dev\equipment_observer_smoke.json` and
checks the read-only inventory slot/API observer, safe boot profile defaults,
and absence of `castSpell`, actionbar sends, `g_game.talk`, `g_game.move`,
`moveTo`, item use, or inventory-use calls in the Equipment observer slice. It
does not launch, stop, move gear, use items, or overwrite any client.

Run the static Scripting policy contract before enabling any command model,
snippet, or runtime eval path:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ScriptingPolicySmoke
```

This writes `runtime\solteria_helper_dev\scripting_policy_smoke.json` and
checks the deny-all profile defaults, forced-off runtime flags, blocked unsafe
status text, and absence of `loadstring`, `dofile`, `require`, runtime calls,
talk, casts, or actionbar sends in the Scripting policy slice. It does not
launch, stop, evaluate snippets, run files, talk, cast, or overwrite any client.

Run every static prototype-module gate with one command:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ModuleStaticGates
```

This writes `runtime\solteria_helper_dev\module_static_gates.json` after running
`HealFriendNoTargetSmoke`, `ConditionsObserverSmoke`,
`EquipmentObserverSmoke`, and `ScriptingPolicySmoke`. It is repo-only evidence:
it does not launch, stop, attach to, promote, or overwrite any client.

Run the complete local readiness pipeline before opening the sandbox client:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action LocalReady
```

This runs `ValidateDev`, `SmokePreflight`, `ModuleStaticGates`, `GoalStatus`,
and `SmokeQueue` in order, then writes
`runtime\solteria_helper_dev\local_ready.json`. A
`ready_for_sandbox` result means local packaging, static validation, staged
sandbox files, and prototype-module static gates are current; it still does not
launch, stop, attach to, promote, or overwrite any live client.

Run a UI smoke and capture a screenshot from the sandbox window:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action Smoke -Tab healing
```

Run all ZeroBot-like helper tabs/subtabs:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAll -DismissDialogs
```

Covered views:

```text
overview, healing, heal_friend, conditions, hunting, hunting_magic,
cavebot, equipment, tools, tools_pvp, tools_hud, tools_timer,
tools_diag, scripting, profile, ui
```

Build a machine-readable coverage report from the screenshots:

```powershell
python scripts\ops\ctoa_helper_smoke_report.py --run-id 20260705-035
```

Expected result:

```text
Coverage: 16/16
```

The report includes a `ZeroBot Mapping` section that maps every captured view
to the expected ZeroBot-like module surface. If the report says
`blocked_by_character_modal`, it is only a routing/screenshot proof, not final
in-world visual acceptance.

The reporter also writes an HTML visual review gallery next to the JSON/MD
artifacts. Open `solteria-helper-smokeall-coverage-<run-id>.html` for a compact
contact sheet of every ZeroBot-like view.

## Post-login Attach Smoke

Use this when the sandbox client is already running and a character is inside
the game world. This avoids restarting the client and avoids the Select
Character modal covering the helper.

1. Launch the sandbox:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action Launch
```

2. Log in with a test character.
3. Optionally confirm the sandbox is in-world:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ReadyCheck
```

4. Switch a helper tab without restarting the client:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab hunting_magic
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab tools_pvp
```

Run every view in the already-logged-in client:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttachModules
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttachAll
```

`SmokeAttachModules` is the focused in-world gate for the prototype module tabs:
`conditions`, `equipment`, `heal_friend`, and `scripting`. The required runtime
predecessor sequence is `conditions -> equipment -> heal_friend`. It writes
`runtime/solteria_helper_dev/module_attach_smoke.json` and routes to
`SmokeAttachAll` only when all four module tabs capture successfully.
The report also records the current dev manifest path, creation time, and
SHA-256. The release gate accepts a passing 4/4 report only when that hash
matches the current `manifest.json`; legacy reports without this binding stay
blocked even when their module counts are 4/4.

After both attach commands, run `RuntimeModuleGatesSandboxSmoke`. Its passing
state proves action-bound dry-run and fail-closed behavior only; it does not
accept a domain action and does not promote the live client.

Use a stable run id when you want repeatable artifact names:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttachAll -RunId 20260705-0430
```

`SmokeAttachAll` automatically builds an in-world coverage report with:

```powershell
python scripts\ops\ctoa_helper_smoke_report.py --run-id <run-id> --prefix solteria-helper-attach --in-world
```

Attach smoke writes `ctoa_smoke_command.lua`; the helper consumes it during
runtime, switches tabs, logs `Smoke tab visible: <tab>/<subtab>`, captures a
screenshot, and then generates the coverage report.

Attach smoke requires a fresh `Smoke tab visible: ...` marker written after the
command file is created. If the client is still on `Select Character`, attach
smoke fails with an instruction to enter the character first instead of
accepting an old log marker.

If the client is stopped at the character list, the `Select Character` modal can cover the helper. This is expected and means the screenshot is only a partial runtime proof. You can attempt to dismiss startup dialogs:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action Smoke -Tab overview -DismissDialogs
```

Stop only the sandbox client:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action Stop
```

## Tab Persistence

The smoke writes `ctoa_ui_prefs.lua` with:

```lua
active_tab = "healing"
```

The helper loads it through `ctoa_native_helper.lua`, switches to that tab on `buildUi()`, and exposes:

```lua
CTOA_Helper.showTab("healing")
```

Use this for targeted screenshots:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action Smoke -Tab ui
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action Smoke -Tab hunting
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action Smoke -Tab hunting_magic
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action Smoke -Tab tools_pvp
```

## Logs And Screenshots

Sandbox logs:

```text
C:\Users\zycie\AppData\Local\SolteriaCodexTest\client\otclient.log
C:\Users\zycie\AppData\Local\SolteriaCodexTest\client\ctoa_local.log
```

Screenshots:

```text
runtime\otclient_ui_preview\solteria-helper-testenv-<tab>-<timestamp>.png
```

Development package artifacts:

```text
runtime\solteria_helper_dev\manifest.json
runtime\solteria_helper_dev\CHANGELOG.md
runtime\solteria_helper_dev\validation.json
runtime\solteria_helper_dev\release_readiness.json
runtime\solteria_helper_dev\release_gate.json
runtime\solteria_helper_dev\goal_audit.json
runtime\solteria_helper_dev\goal_status.json
runtime\solteria_helper_dev\smoke_preflight.json
runtime\solteria_helper_dev\smoke_status.json
runtime\solteria_helper_dev\ready_check.json
runtime\solteria_helper_dev\live_promotion.json
runtime\solteria_helper_dev\background_status.json
runtime\solteria_helper_dev\live_backup_<timestamp>\backup_manifest.json
runtime\solteria_helper_dev\latest\
runtime\solteria_helper_dev\ctoa_otclient_<version>.zip
```

`manifest.json` contains the staged file list with SHA256 hashes and a snapshot
of any running Solteria process. The release gate verifies those staged file
hashes against `latest` before promotion. `validation.json` is `pending` after
`PrepareDev` and becomes `passed` only after `ValidateDev` completes all gates.
`release_readiness.json` keeps the promotion gates explicit: static validation
can pass while sandbox launch, `SmokeAttachModules`, `SmokeAttachAll`, and live approval remain
pending.
`release_gate.json` is the strict audit result. It remains `blocked` until
`smoke_preflight.json` is `passed`, fresh `SmokeAttachModules` evidence exists,
a complete in-world SmokeAttachAll report is present, and explicit live approval
or durable `live_promotion.json` evidence is present. It also writes
`next_action` and `next_command` for the next safe gate step. The preflight
report includes the current manifest fingerprint, so the gate blocks stale
preflight evidence after a new package is generated. The gate also verifies the
versioned ZIP SHA256 against `release_readiness.json` before allowing
promotion. After promotion, `live_promotion.json` must be newer than the current
manifest and the live client files must match the current manifest hashes before
`live_approval` remains `passed`.
When `ModuleAttachSmoke` or `SmokeAttachAll` is the active blocker, the gate reads
`smoke_status.json` and `ready_check.json` to choose the next safe command:
`Launch` when the sandbox is not running, `ReadyCheck` when the sandbox needs an
in-world readiness check, `SmokeAttachModules` first after `ReadyCheck` reports
`ready`, and `SmokeAttachAll` only after module attach evidence has passed. A
fresh `SmokeStatus` blocker such as `not_running`,
`character_modal`, or `helper_log_missing` takes precedence over older
`ready_check.json` evidence.
`goal_audit.json` summarizes the full development plan state and repeats the
current blockers plus the next command from the release gate when one exists.
It also lists the P0-P5 roadmap phases so the remaining incomplete phase is
visible. `goal_audit.html` is generated from that same audit as a local,
read-only dashboard with the release state, next command, roadmap, blockers,
and evidence inventory; its path is included in `goal_status.json`.
`goal_status.json` is the operator-facing read-only summary generated by
`GoalStatus`: it repeats the audit/gate state, P0-P5 roadmap statuses, live
process snapshot, blockers, and next safe command when one exists. It refreshes
`SmokeStatus` first, so the next command reflects the current sandbox process,
window, helper log, and character-modal state before release-gate routing runs.
`GOAL_HANDOFF.md` is generated from the same status payload as a one-screen
operator checklist with current state, P0-P5 roadmap, blockers, next safe
command, module workplan summary, and the live-promotion completion rule. When
`runtime\solteria_helper_dev\module_audit.json` exists, `GoalStatus` also adds
module status, modularization pressure, registry coverage, and each lane's next
step to both `goal_status.json` and `GOAL_HANDOFF.md`. The module audit also
selects `next_module_id` and `next_module_action`, so the handoff separates the
next safe smoke command from the next helper-module development move. When
`heal_friend_no_target_smoke.json` is `passed`, `GoalStatus` advances the
module recommendation to grouped in-world `SmokeAttachModules` evidence and
adds `next_module_command`: `HealFriendNoTargetSmoke` before static evidence,
`Launch` or `ReadyCheck` while the sandbox is not ready, and
`SmokeAttachModules` once `ReadyCheck` reports `ready`.
The same prototype-gate pattern is now available for `conditions` through
`ConditionsObserverSmoke`, with in-world visual acceptance captured later by
`SmokeAttach -Tab conditions`.
`EquipmentObserverSmoke` applies the same rule to `equipment`; it only accepts
read-only inventory observation and leaves ring/amulet/weapon swaps blocked
until sandbox evidence exists.
`ScriptingPolicySmoke` applies the same rule to `scripting`; it only accepts a
deny-all policy shell and leaves snippets, eval, and command execution blocked.
`GoalStatus` aggregates these prototype gates as `static_gate_summary` in
`goal_status.json` and as a `Static gates: passed/total` block in
`GOAL_HANDOFF.md`, so the operator can see which local module gates are ready
before starting sandbox attach smoke. `ModuleStaticGates` refreshes all four
prototype gate reports and writes `module_static_gates.json`; run `GoalStatus`
after it to route the next release step. The release gate also requires a fresh
passed `module_static_gates.json` and a fresh passed
`module_attach_smoke.json` before it routes to final in-world `SmokeAttachAll`,
so new prototype-module risk cannot be skipped during packaging.
`LocalReady` wraps the local half of this flow and should be the first command
when the operator wants one current handoff before opening the sandbox client.
`release_gate.json`, `goal_audit.json`, `goal_status.json`, and
`GOAL_HANDOFF.md` are written atomically, so readers do not observe partial
outputs while `GoalStatus` refreshes the audit.
Neither action copies files into the live play client.

Generate the read-only sandbox smoke queue after `LocalReady` when the release
gate is waiting on attach evidence:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeQueue
.\.venv\Scripts\python.exe scripts\ops\solteria_helper_sandbox_smoke_queue.py
```

This writes `runtime\solteria_helper_dev\sandbox_smoke_queue.json` and
`docs\otclient\solteria_helper_sandbox_smoke_queue.md` from the current
manifest, release gate, smoke status, and goal status. It only plans the
operator sequence; it does not launch, attach to, promote, stop, or overwrite
any client.

You can run the gate audit directly:

```powershell
python scripts\ops\solteria_helper_release_gate.py --dev-dir runtime\solteria_helper_dev --allow-blocked
```

If `--smoke-report` is not provided, the gate looks for the latest
`runtime\otclient_ui_preview\solteria-helper-smokeall-inworld-*.json` report.
It intentionally ignores modal-limited `solteria-helper-smokeall-coverage-*.json`
reports. An in-world report must include every expected helper view and each
listed screenshot file must exist on disk.

Live promotion is intentionally separate:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action BackupLiveCtoa
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action PromoteLiveCtoa -ApproveLiveDeploy
```

`PromoteLiveCtoa` refuses to run without `-ApproveLiveDeploy`, then checks the
existing strict release gate for the current staged package with approval. It
does not run `ValidateDev`, run `SmokePreflight`, regenerate the manifest, or
change the staged package after in-world `SmokeAttachAll` has passed. It will
still refuse to copy files until `SmokePreflight` and in-world `SmokeAttachAll`
are passed. After the gate passes, it writes a fresh
`live_backup_<timestamp>\backup_manifest.json`, copies staged files into the
live client without stopping, restarting, or launching it by default, and
records `live_promotion.json` as durable post-promotion evidence.

If the operator wants the live client opened immediately after a successful
promotion, make that explicit:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action PromoteLiveCtoa -ApproveLiveDeploy -LaunchAfterPromote
```

`-LaunchAfterPromote` starts `SourceClient\solteria-client.exe` only when that
exact live client is not already running. It records `launched`,
`already_running`, or `failed` in `live_promotion.json`; it never stops or
restarts the live client.

If needed, pass a specific in-world smoke report:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action PromoteLiveCtoa -ApproveLiveDeploy -SmokeReport runtime\otclient_ui_preview\solteria-helper-smokeall-inworld-<run-id>.json
```

The Helper can also export its bounded runtime diagnostics buffer from the
sandbox/live module directory as:

```text
ctoa_diag_export.lua
```

Use the smoke command action `diag_export` or the in-client
`CTOA_Helper.exportDiagnostics()` entrypoint after the sandbox Helper has
collected samples. The export contains only bounded passive snapshots for
HP/MP, movement, combat, magic, and container APIs.

## Test Account

Interactive in-game UI/runtime checks are no longer routine background work.
Use a separate runner/VM, or an explicitly scheduled user-visible session with a
low-risk sandbox character. Keep the main play client untouched. That separate
interactive lane is used only for:

- helper UI screenshots,
- tab persistence checks,
- combat/healing log validation,
- PZ/NPC/targeting regression tests,
- actionbar potion/rune behavior checks.

Full visual acceptance for all tabs requires the sandbox to enter the game world with a separate test character. Before login, the character selection modal is above helper widgets and can obscure screenshots even when `CTOA_Helper.showTab("<tab>")` succeeds.

Static geometry/layout acceptance is covered by:

```powershell
python scripts\ops\ctoa_helper_ui_preview.py
```

Expected result:

```text
issues: none
```

Regression tests for the ZeroBot-like shell contract:

```powershell
python -m pytest tests\test_otclient_helper_zerobot_shell.py -q
```

Expected result:

```text
4 passed
```

## PZ / NPC Targeting Regression

The helper combat runtime must not attack NPCs or run offensive actions in PZ.
Use this after changing targeting, magic shooter, rune shooter, or auto exeta.

Live/sandbox steps:

1. Enter the game world with a test character.
2. Stand in PZ or near an NPC such as `Taskmaster Liora`.
3. Keep `Targeting` enabled for 30-60 seconds.
4. Inspect `ctoa_local.log`.

Passing log pattern:

```text
[CTOA-OTC-COMBAT] Combat paused: no valid monster target
```

Failing log pattern:

```text
[CTOA-OTC-COMBAT] Auto target: Taskmaster Liora
```

If a bad target still appears, inspect the probe line. It logs the client-side
creature methods used by the guard:

```text
[CTOA-OTC-COMBAT] Target probe: <name> id=<id> reason=<reason> isNpc=<...> isMonster=<...> isPlayer=<...> isAttackable=<...> canBeAttacked=<...> isTargetable=<...>
```

Current guard behavior:

- `pause_in_pz=true` blocks targeting, rune shooter, spell rotation, and auto exeta.
- NPC/player/ignored names are rejected before attack.
- Unknown creature types are treated as non-monsters.
- The helper HUD and combat module share the same valid-target rules.
