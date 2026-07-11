# OTClient Helper Redesign

## Goal

Rebuild the `ctoa_native_helper.lua` panel so it stops looking like a debug slab and starts reading like a deliberate operator tool.

Primary implementation target:

- [ctoa_native_helper.lua](../../scripts/lua/otclient/ctoa_native_helper.lua)

This document is a redesign brief, not a visual mockup.

## Current Problems

From the current helper panel and code structure:

- too many outlined rectangles
- weak hierarchy between section headers, labels, values, and actions
- navigation on the left wastes space while still feeling cramped
- profile state, runtime state, and edit controls are mixed too tightly
- large amount of repeated chrome makes the panel feel heavy
- controls look mechanical rather than intentional

## Desired Direction

The panel should feel:

- compact
- readable at a glance
- operational rather than decorative
- consistent with Tibia/OTClient texture language without imitating a 2008 bot menu

The design target is a quiet tool surface:

- one clear active workspace
- restrained borders
- strong spacing rhythm
- clear section ownership
- values emphasized more than labels

## Information Architecture

### Keep four domains

The current four-domain split is correct and should remain:

- `Healing`
- `Tools`
- `Profile`
- `UI`

### Change the composition

Do not keep the current left-sidebar-plus-full-form approach as-is.

Preferred structure:

- narrow left navigation rail
- one active content pane on the right
- sticky top title row with helper state and profile name
- bottom strip for status, save state, and close action

### Surface priorities by tab

`Healing` should prioritize:

- enabled state
- spell thresholds
- potion mode and hotkey
- live summary

`Tools` should prioritize:

- rotation preset
- exeta behavior
- haste state
- live summary

`Profile` should prioritize:

- active profile name
- save/export/reset actions
- only editable fields that define behavior

`UI` should prioritize:

- toggle hotkey
- HUD enabled
- HUD position
- compact mode
- theme preset
- window placement

## Visual Rules

### Reduce box count

The current panel uses boxes for nearly everything. That creates noise.

Change to:

- one outer frame
- one card per major region only when needed
- rows separated mostly by spacing, not borders

### Make headers earn their size

Current section bars are visually loud but not especially informative.

Change to:

- one clear panel title
- smaller section titles
- muted helper text on the same line, not a second competing bar everywhere

### Improve value emphasis

Values should be easier to scan than labels.

Change to:

- muted labels
- brighter values
- consistent width for numeric controls
- state colors only for true state, not decoration

### Normalize controls

Current controls mix buttons, boxes, and text in a noisy way.

Target controls:

- segmented toggles for `ON/OFF`
- stepper rows for numeric values
- cycle selectors for presets and hotkeys
- one clear primary action style
- one subdued secondary action style

### Tighten spacing

The panel needs fewer gaps that do nothing and more consistent row rhythm.

Target:

- even row height
- even gap between related rows
- larger gap only between sections

## What To Keep From The Existing Implementation

Keep these product behaviors:

- persisted UI prefs
- persisted profile data
- hotkey toggle
- HUD positioning
- compact mode
- autosave behavior
- runtime status line

The redesign is presentation work first, not a feature rewrite.

## What To Borrow From ZeroLauncher

Borrow only these ideas:

- HUD is its own subsystem
- modal interactions should be explicit and narrow
- hotkey parsing should remain isolated from layout code

Do not borrow:

- legacy bot visual style
- binary launcher assumptions
- old dense utility-panel composition

## Suggested Implementation Sequence

### Phase 1: Layout cleanup inside current code

In `ctoa_native_helper.lua`:

- simplify the left navigation styling
- reduce border usage
- tighten row spacing
- standardize label/value row geometry
- improve title, subtitle, and footer hierarchy

Status 2026-07-06:

- narrowed the left navigation rail from the old account-heavy sidebar into a
  smaller module rail
- widened the active workspace so values and cycle controls have more room
- replaced the double `ZeroBot - Helper` title treatment with a single
  operator header plus profile/version state
- reduced body, row, table header, and sidebar border weight while keeping the
  same widget ids for smoke tooling

### Phase 2: Control system cleanup

- unify toggle rows, stepper rows, and cycle rows
- remove one-off row styling differences
- centralize active/inactive visual states

Status 2026-07-06:

- moved labels toward muted text and values toward brighter centered value
  fields
- made profile cycle rows, stepper rows, vector rows, subtabs, and navigation
  use shared quiet active/inactive styling
- added a regression contract in
  `tests/test_otclient_helper_zerobot_shell.py` to protect the redesigned
  geometry and header treatment

### Phase 3: Summary-driven UX

- add concise per-tab summaries
- show live profile/runtime information without forcing the user to parse every row
- make status text more deliberate and less log-like

Status 2026-07-06:

- added summary strips for Healing, Hunting Targeting, Hunting Magic,
  Tools Helper, Profile, and UI
- wired the title row to show helper version, active profile, and autosave state
- refreshed summaries after runtime arming, profile/UI autosave changes,
  API diagnostics refresh, and profile save
- replaced the old `Setting / Value` and `Recovery / Condition` header rows in
  redesigned tabs with operator-readable state summaries
- added a regression contract in
  `tests/test_otclient_helper_zerobot_shell.py` to protect Phase 3 summary
  wiring
- repo-side preview passes with no layout issues; final visual acceptance still
  requires fresh in-world `SmokeAttachAll` in the sandbox client

### Phase 4: Optional modal actions

If needed later:

- profile import confirmation
- reset-to-default confirmation
- unsafe action confirmation

## Code Areas To Touch First

Highest-value code areas in the current helper:

- `configureUILayout`
- `styleWidget`
- `addSectionBand`
- `addSettingRow`
- `addToggleSettingRow`
- `addProfileCycleRow`
- `addProfileStepRow`
- `addVectorStepRow`
- `rebuildUi`

These functions already define most of the visual system.

## Definition Of Done

The redesign is good enough when:

- the panel can be scanned in one pass
- the active tab is obvious
- values are easier to read than labels
- the UI section no longer looks heavier than the gameplay sections
- the helper stops reading like an internal tool and starts reading like a polished in-client operator panel

Current verification:

- `python scripts\ops\ctoa_helper_ui_preview.py` reports no layout issues
- `python -m pytest tests\test_otclient_helper_zerobot_shell.py -q` covers the
  redesign layout contract, Phase 3 summary wiring, and ZeroBot-like shell
- `solteria_helper_release_gate.py` now blocks stale `SmokeAttachAll` evidence
  when the in-world smoke report is older than the current dev manifest
- sandbox launch/ReadyCheck was attempted after the Phase 3 pass; screenshots
  confirmed the redesigned Helper behind the Select Character modal, and
  `ready_check.json` now records missing-window or modal/helper-offline blockers
- release gate next-command selection now consumes `smoke_status.json` and
  `ready_check.json`, so the operator handoff advances from `Launch` to
  `ReadyCheck` to `SmokeAttachAll` only when the sandbox evidence supports it
- final sandbox visual acceptance passed with
  `solteria-helper-smokeall-inworld-20260706-1025.json`: coverage `16/16`,
  `modal_limited=false`, and `acceptance_status=ready_for_visual_review`
- live promotion remains a separate explicit approval step and is not part of
  the redesign acceptance
