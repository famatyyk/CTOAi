# ZeroBot / ZeroLauncher Reference

## Purpose

This note captures what is actually useful from the local `ZeroLauncher` package for CTOAi OTClient work.

Source inspected:

- `C:\Users\zycie\Downloads\ZeroLauncher (1).zip`
- `C:\Users\zycie\Downloads\ZeroLauncher`
- `C:\Users\zycie\Downloads\ZeroLauncher\data\core.zip`

This is not product documentation. It is a binary launcher package with a Lua runtime layer and client patch metadata.

## What The Package Contains

Top-level package contents:

- `ZeroBot.exe`
- `ZeroBotLauncher.exe`
- `ZeroBotLauncher64.exe`
- `data/core.zip`
- `data/sounds.zip`
- `data/ZeroBot-*.dll`
- `versions.txt`
- `patch_addresses.txt`
- `version_addresses.txt`

Practical reading:

- the package is useful for behavior and API patterns
- the package is not useful as a clean visual reference for the current helper panel
- the package does not provide a ready-made OTClient UI skin we should copy

## Lua Runtime Inventory

The main technical value sits in `data/core.zip`.

Relevant files:

- `hud.lua`
- `custom_modal_window.lua`
- `hotkeymanager.lua`
- `game.lua`
- `player.lua`
- `inventory.lua`
- `map.lua`
- `spells.lua`
- `cavebot.lua`
- `engine.lua`

These files describe the wrapper layer ZeroBot exposes to scripts.

## Useful Capabilities To Reuse Conceptually

### HUD wrapper

`hud.lua` exposes a structured HUD object with:

- creation of text, item, spell-icon, and outfit HUD nodes
- explicit `setPos`, `show`, `hide`, `setDraggable`
- visual controls such as `setColor`, `setFontSize`, `setScale`, `setOpacity`, `setZIndex`
- click callbacks with `setCallback`

Why this matters for CTOAi:

- our helper already has HUD behavior, but the ZeroBot wrapper is cleaner as an API surface
- it suggests separating panel UI from overlay HUD concerns
- it confirms that HUD state should be treated as a first-class subsystem, not just a couple of booleans in a larger panel

### Custom modal wrapper

`custom_modal_window.lua` exposes:

- modal creation
- caption and description setters
- button creation
- click callback registration
- explicit destroy lifecycle

Why this matters for CTOAi:

- confirms a good pattern for confirmation UI
- useful later if we want profile import/export confirmation, reset actions, or runtime warnings
- this is a logic/API reference, not a visual reference

### Hotkey parsing

`hotkeymanager.lua` exposes:

- string-to-keycode mapping
- parsing for combinations like `Ctrl+H`
- a normalization point for keyboard modifiers

Why this matters for CTOAi:

- our helper already binds hotkeys, but this file is a good reference if we later want stricter parsing or validation
- it suggests keeping hotkey parsing isolated from panel layout logic

### Runtime domain modules

The package also has focused runtime modules such as:

- player state
- map access
- inventory access
- cavebot orchestration
- spell helpers

Why this matters for CTOAi:

- these files are useful for capability mapping and naming conventions
- they are not a reason to change the current helper UI layout directly

## What Is Not Worth Copying

Do not copy from ZeroLauncher:

- launcher aesthetics inferred from the binaries
- old-school bot UX conventions with dense technical labeling everywhere
- modal-heavy workflows as the default interaction model
- version patch tables and address metadata
- opaque monolithic wrappers without a clean separation between domain state and presentation

## Direct Comparison With Current CTOAi Helper

Current CTOAi helper implementation:

- [ctoa_native_helper.lua](../../scripts/lua/otclient/ctoa_native_helper.lua)

Current CTOAi helper strengths:

- runtime/profile/UI prefs are already separated conceptually
- helper supports profile save/load and UI prefs persistence
- helper has explicit sections for healing, tools, profile, and UI
- helper already exposes HUD toggles and window placement

Current CTOAi helper weaknesses:

- layout is widget-heavy and visually noisy
- too many bordered boxes compete for attention
- labels, values, and controls do not produce a clear visual hierarchy
- the panel reads like a debug tool rather than a polished in-client operator surface

## Recommended Use Of ZeroLauncher Material

Use ZeroLauncher as:

- an API reference
- a behavior reference
- a capability checklist

Do not use ZeroLauncher as:

- the visual blueprint for the helper panel
- the design language for spacing, typography, or control composition

## Actionable Follow-Up

The right next step is not reverse-engineering more binaries. The right next step is rebuilding the helper panel around a quieter information architecture.

Companion design note:

- [helper_redesign.md](helper_redesign.md)
