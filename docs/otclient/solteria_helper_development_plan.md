# Solteria Helper Development Plan

## Objective

Build new Helper features in an isolated lane first, then promote them to the
live Solteria client only after static validation, sandbox smoke, and log
evidence pass.

## Non-Interference Rule

The active play client under:

```text
C:\Users\zycie\AppData\Local\Solteria\client
```

must not be restarted, stopped, or overwritten during normal development work.
Development work uses:

```text
runtime\solteria_helper_dev
C:\Users\zycie\AppData\Local\SolteriaCodexTest\client
```

Sandbox operations must keep `SandboxClient` under `%LOCALAPPDATA%` with
separator-aware path containment, and `SandboxClient` must not equal or sit
inside `SourceClient`. This prevents manual smoke/status/stop commands from
aliasing the live Solteria client.

Use `PrepareDev` and `ValidateDev` first. Use live copy only when the user
explicitly asks to deploy to the active play client.

## Environment Commands

Prepare a package and manifest without launching a client:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action PrepareDev
```

Run static validation without touching the live client:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ValidateDev
```

Prepare the sandbox client without touching the live client:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action Setup
```

Verify sandbox files match the staged dev package without launching a client:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokePreflight
```

Inspect sandbox smoke readiness without launching or stopping a client:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeStatus
```

Refresh and print the full development goal status without launching or stopping
a client:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action GoalStatus
```

Only the sandbox client should be launched for interactive smoke:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action Launch
```

## Promotion Gates

1. `PrepareDev` writes a fresh package under `runtime\solteria_helper_dev`.
2. `PrepareDev` writes `manifest.json`, `CHANGELOG.md`, `validation.json`, and
   a versioned ZIP without touching the live client.
3. `ValidateDev` passes helper/API/report tests, static UI preview, and API
   catalog refresh.
4. `SmokePreflight` verifies sandbox files match the staged dev package.
5. Sandbox launch loads the Helper and writes fresh `ctoa_local.log` evidence.
6. `SmokeAttachAll` passes after a sandbox test character is in-world.
7. Only then copy to the active client with
   `PromoteLiveCtoa -ApproveLiveDeploy`.

## Feature Roadmap

### P0: Development Lane

- Keep `PrepareDev` and `ValidateDev` green.
- Keep package manifest evidence current.
  Status: the release gate verifies every staged file listed in
  `manifest.json` still exists under `latest` and matches its SHA256.
- Keep `CHANGELOG.md` and `validation.json` attached to every dev package.
- Never use active play-client restart as the first validation step.

### P1: Runtime Observability

- Add an in-client diagnostics tab that renders the last API probe snapshot.
  Status: `Tools / Diag` added in source; validate through `ValidateDev`.
- Add bounded log export for HP/MP, movement, combat, magic, and container APIs.
  Status: bounded diagnostics buffer and `ctoa_diag_export.lua` export added in
  source; validate through `ValidateDev`.
- Add feature flags for experimental modules.
  Status: profile-backed flags added for diagnostics, cavebot, loot, and combat.

### P2: Healing And Mana

- Use real `LocalPlayer:getHealth/getMaxHealth/getMana/getMaxMana` reads first.
  Status: `readPlayerVitals()` added in source; percent APIs are fallback only.
- Keep spell rotation by HP thresholds.
- Keep potion/rune selection actionbar-compatible: choose item/actionbar slot in
  the same model as the client actionbar assignment flow.
  Status: HP/MP/rune box selectors remain actionbar-slot backed, and runtime
  item actions resolve `*_actionbar_slot` before legacy hotkey fields.

### P3: CaveBot

- Keep movement disabled separately from route editing.
- Route editor first: add/current/delete/reorder waypoints without movement.
  Status: add/delete/select/reorder controls added; editor functions only mutate
  route/profile state and do not call movement APIs.
- Movement execution only through `LocalPlayer:autoWalk(destination, retry)`.
- Add stuck detection, retry budget, and PZ/offline guards before looped movement.
  Status: movement runtime now checks offline/PZ/player-position guards, tracks
  same-position retries, passes the retry flag into `LocalPlayer:autoWalk`, and
  disables movement after the retry budget is reached while keeping the edited
  route intact.

### P4: Combat And Magic

- Keep monster-only targeting guards.
  Status: targeting clears non-monster/unsafe targets and retargets only
  monster candidates inside configured range.
- Add visible decision state for spell rotation, exeta, rune, and target lock.
  Status: magic footer and HUD render the next action with target, action-lock,
  exeta cooldown, and rune readiness/cooldown state.
- Keep all offensive actions rate-limited and PZ-aware.
  Status: offensive action execution rechecks PZ/runtime block, action lock, and
  recovery gap before casting exeta, rotation spells, or rune actions.

### P5: Packaging And Release

- Build a versioned zip from canonical source files.
  Status: `PrepareDev` stages canonical OTClient files and creates
  `ctoa_otclient_<version>.zip` with SHA256 manifest evidence. The release gate
  verifies the ZIP exists and its SHA256 matches `release_readiness.json`.
- Generate a changelog from manifest + validation evidence.
  Status: `ValidateDev` refreshes `CHANGELOG.md`, `validation.json`, and
  `release_readiness.json` after tests, UI preview, and API audit pass. It also
  writes `release_gate.json`, which stays `blocked` until `SmokePreflight`
  passes, in-world `SmokeAttachAll` evidence exists, and live
  approval/promotion evidence exists. The gate auto-discovers only
  `solteria-helper-smokeall-inworld-*.json` reports, ignores modal-limited
  coverage reports, and verifies that the report contains every expected helper
  view with an existing screenshot file.
- Promote to live only with explicit approval and fresh backup.
  Status: live promotion is a separate `PromoteLiveCtoa` action that refuses to
  run without `-ApproveLiveDeploy`, checks the existing strict `release_gate`
  for the current staged package without regenerating the manifest, then writes
  a fresh `live_backup_<timestamp>` with `backup_manifest.json`, copies staged
  files without stopping, restarting, or launching the live client by default,
  and records `live_promotion.json` as durable post-promotion evidence. A live
  client launch after promotion is available only through the explicit
  `-LaunchAfterPromote` switch; it starts the live executable when it is not
  already running and never restarts an existing live client.
- Prepare sandbox smoke without interfering with live play.
  Status: `SmokePreflight` uses the latest staged package, creates one only
  when it is missing, runs sandbox setup, verifies staged package hashes against
  sandbox files, writes the current manifest fingerprint into
  `smoke_preflight.json`, and does not launch, stop, or overwrite the live
  client. The release gate blocks stale preflight evidence after a new manifest
  is generated.
- Inspect sandbox smoke state without changing client state.
  Status: `SmokeStatus` writes `smoke_status.json` from existing sandbox
  process/log state and does not launch, stop, or overwrite any client. It also
  rejects a `SandboxClient` path that aliases `SourceClient`.
- Inspect full goal state without changing client state.
  Status: `GoalStatus` refreshes `release_gate.json` and `goal_audit.json`,
  writes `goal_status.json`, prints P0-P5 status and the next command when a
  next gate exists, and does not launch, stop, or overwrite any client.

### P6: Module Lane And New Features

- Keep the generated module workplan current before adding new helper behavior.
  Status: `scripts/ops/otclient_helper_module_audit.py` writes
  `runtime/solteria_helper_dev/module_audit.json` and
  `docs/otclient/solteria_helper_module_workplan.md`.
- Treat the 5k-line helper as a module host, not as the default place for new
  behavior. New features must enter through a named lane with profile keys,
  safe boot defaults, tests, sandbox smoke evidence, and release-gate evidence.
- Extract or isolate shared domains before extending runtime behavior:
  recovery/vitals, target guards, actionbar actions, diagnostics, and module
  registry.
- Convert placeholders in order: Heal Friend, Conditions diagnostics,
  Equipment safe swaps, then Scripting policy shell.
- Do not implement arbitrary scripting or live-client actions until the risk
  model, audit logging, Control Center evidence, and targeted tests exist.
  Status: this remains a planning lane; runtime enablement is blocked until the
  module-specific gates in `solteria_helper_module_workplan.md` pass.

### P7: Next Module Design Queue

- Keep the supplemental next-module plan current after the extraction map is
  complete.
  Status: `scripts/ops/otclient_helper_next_modules_plan.py` writes
  `runtime/solteria_helper_dev/next_modules_plan.json` and
  `docs/otclient/solteria_helper_next_modules_plan.md`.
- Treat local ZeroBot material as a capability/API reference, not as a visual
  or runtime copy target.
- Treat vBot or other external bot logic as `source_required` until the actual
  source/archive is present, reviewed for provenance, and mapped into CTOAi
  safe-boot gates.
- Build the next functions in this order unless sandbox evidence changes the
  priority: HUD overlay domain, hotkey normalization, confirmation modal
  lifecycle, route engine split, target scorer split, then external vBot import
  review.
