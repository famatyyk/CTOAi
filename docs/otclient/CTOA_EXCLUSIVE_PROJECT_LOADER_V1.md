# CTOA Exclusive Project Loader V1

Status: implemented in the repo and staged as Helper package `v2.4.0`; live
promotion remains separate and requires the normal sandbox and approval gates.

## Runtime Contract

The client has exactly one CTOA autoload entrypoint:
`mods/ctoa_chooser/ctoa_chooser.otmod`. It loads the neutral
`CTOA_PROJECT_LOADER`, not either automation project.

After every game login the loader displays a per-session choice:

- `helper` loads `mods/ctoa_otclient` only;
- `safe` loads `mods/ctoa_safe` only.

The choice is not persisted. Logout terminates the selected project, removes its
scheduled runtime state through that project's teardown, clears selection, and
requires a new choice after the next login.

## Mutual Exclusion

`ctoa_otclient.otmod` and `ctoa_safe.otmod` both declare `autoload: false`.
Their loaders accept `init()` only while the neutral loader has an online session,
the matching selected project, a pending activation, and no active project.
Selecting a second project in the same session fails closed.

Both runtime loops also check the selected active project. CTOA Safe refuses its
ENABLE action unless `active_project == "safe"`; the Helper think loop returns
without work when a neutral loader exists and Helper is not active.

## Safe Boundaries

CTOA Safe contains only its `.otmod`, explicit loader, and self-contained helper.
Copied Helper loaders, registries, native combat/heal/loot files, and their
autonomous `init()`/`cycleEvent` paths are not part of the Safe tree. Safe exposes
the fixed Healing, Combat, Conditions, and Timer labels. CaveBot and generic
Settings are absent. Loading Safe always forces `enabled=false`,
`safe_boot_runtime_disabled=true`, and `armed=false`.

Safe `v2.2.0` also removes the zero-argument `g_map.getSpectators()` call that
was reached only after ENABLE. Spectator sampling now uses the native-source-
proven `getSpectatorsInRange(centerPos, false, xRange, yRange)` signature, bounds
the range to 1..10, wraps every native map/creature read, and falls back to
`getSpectators(centerPos, false)` only when the range API is unavailable. This
closes a second crash candidate independently of the duplicate Helper runtime.

Safe persistence uses the dedicated `ctoa-safe-profile-v2` JSON contract in
`g_resources.getWorkDir()`. It validates and bounds editable values, ignores
unknown keys, never imports Helper Lua profiles, and never persists runtime
arming. Helper mutable profiles and UI preferences use root-level
`ctoa_user_*` files, outside the packaged `mods/ctoa_otclient` directory, so a
package refresh cannot overwrite user changes.

Safe `v2.2.0` expands the compact edit panels without adding general Settings:
Healing exposes normal/critical spell words and potion hotkeys; Combat exposes
editable Exeta lists, attack range, rotation interval, and custom entries in
`spell|min|max|cooldown_ms` form; Conditions exposes editable mana-shield,
paralyze, and poison support spells. All values remain bounded and persist in
the dedicated Safe JSON profile.

## Package And Boot Hook

The official package stages `ctoa_project_loader.lua` as the only CTOA root
loader and includes three separate mod directories: `ctoa_chooser`,
`ctoa_otclient`, and `ctoa_safe`. The boot hook loads the neutral root loader and
calls `CTOA_PROJECT_LOADER.init()` idempotently. Legacy root
`ctoa_otclient_loader.lua`, `ctoa_native_helper.lua`, remembered chooser files,
old root profiles, and copied Helper files under `mods/ctoa_safe` are removed
during an explicitly approved promotion or repair. Before cleanup, the wrapper
backs up the legacy tree and migrates existing Helper profiles/preferences to
`ctoa_user_*` targets only when those targets do not already exist.

## Diagnosed Live Drift (2026-07-12)

The inspected live Solteria tree still contained Safe `v1.0.0`, Helper
`v2.3.10`, an old root loader called by `init.lua`, both Helper and chooser
autoload entries, and `ctoa_chooser_prefs.lua` selecting Safe with
`skip_chooser=true`. Safe also contained copied Helper runtime and profile
files. Those independent activation paths explain why both windows appeared at
the character list, while shared/mod-local profile writes plus package sync
explained recurring option resets. The staged package fixes those paths; the
live tree remains unchanged until explicit promotion approval.

## Verification

- `tests/test_ctoa_exclusive_project_loader.py` executes the Lua lifecycle and
  proves one project per login, refusal of a second project, logout teardown,
  no persisted selection, and Safe arming rejection outside its selected lane.
- `tests/test_otclient_loader_cross_fork.py` proves the Helper loader refuses
  unauthorized initialization and remains idempotent across supported console
  message variants.
- `PrepareDev` must emit a manifest containing only `ctoa_project_loader.lua` at
  package root and exactly one `.otmod` with `autoload: true`.
- `SmokePreflight` must prove stage-to-sandbox SHA-256 parity before any in-world
  smoke or live promotion review.
