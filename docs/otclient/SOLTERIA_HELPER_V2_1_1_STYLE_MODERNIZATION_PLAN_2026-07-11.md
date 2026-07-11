# Solteria Helper v2.1.1 Style And Modernization Plan

- Status: completed and live-promoted; v2.1.1a carries the remaining stabilization work.
- Naming note: the former `v2.1.1-a` suggested slice below was an internal milestone, not the production v2.1.1a patch.

## Decision

Modernize the Helper as a compact layered tactical panel. Keep the established
dark OTClient character, but replace the flat stack of similar gray rectangles
with a clear visual hierarchy, stronger navigation states, grouped controls,
and consistent depth cues.

The implementation must use capabilities already confirmed in this client:
background color, border color and width, opacity, text alignment, font scale,
and layered widgets. Gradient, rounded-corner, shadow, and hover behavior must
not be treated as available until a sandbox capability probe proves them.

## Current problems from the live screenshots

1. `CaveBot` keeps the default centered button appearance because
   `switchTab` does not call `styleTabState` for `cavebot_tab`.
2. Navigation rows, settings rows, value cells, and summary bars use nearly the
   same visual weight, so the eye has no strong reading order.
3. Inactive tabs look disabled rather than selectable.
4. The active Settings state is only a thin amber border and `>` prefix.
5. The content region is a large uninterrupted dark surface with weak grouping.
6. Step buttons, values, ON/OFF states, Save, and Close lack a coherent button
   hierarchy.
7. Long summary text is visually dense and competes with the actual controls.
8. Sidebar profile/runtime information looks detached from module navigation.

## Target visual language

### Depth levels

- **Level 0 — window shell:** darkest outer frame and clear one-pixel border.
- **Level 1 — workspace:** slightly lighter sidebar and content wells.
- **Level 2 — cards/groups:** raised rows using a lighter body plus a darker
  lower/right edge simulated with layered labels.
- **Level 3 — interactive values:** darkest value wells with a bright focus or
  active border.
- **Level 4 — primary action:** amber accent fill/border reserved for selected
  navigation and Save/Apply actions.

### Color roles

- Keep amber as the single selection/action accent.
- Make inactive navigation text readable, not gray-disabled.
- Use green only for healthy/ON state and muted red/orange only for blocked or
  destructive state.
- Separate `panel_surface`, `row_fill`, and `value_fill` by a visible luminance
  step instead of near-identical blacks.
- Reduce the brightness of decorative borders so active borders stand out.

### Geometry

- Keep the v2.1 width of 690 px.
- Increase sidebar tab height from 18 to 21 px and use a 2 px visual gap.
- Add 6-8 px inner padding around major cards.
- Keep control rows aligned to a shared label/value grid.
- Use section bands to split Settings into `Healing` and `Visible modules`.

## Execution plan

### P1 — Navigation correctness and state system

- Add the missing `styleTabState` call for `cavebot_tab`.
- Replace per-tab repeated styling calls with one navigation metadata loop so a
  future tab cannot silently miss styling.
- Give every tab explicit states: inactive, active, hidden, and smoke-forced.
- Active tab: amber 2 px left rail, lighter raised fill, full-opacity label.
- Inactive tab: readable text, subtle border, consistent left alignment.
- Remove visual centering from every sidebar tab, including CaveBot.

Acceptance:

- All visible navigation labels share the same x alignment.
- CaveBot is indistinguishable from other inactive tabs except for its label.
- Static contract verifies every sidebar metadata entry receives tab styling.

### P2 — Reusable layered primitives

- Extend the theme with semantic tokens such as `surface_low`,
  `surface_raised`, `edge_highlight`, `edge_shadow`, `state_on`, and
  `state_blocked`.
- Add primitives for a raised card, inset value well, accent rail, and grouped
  section frame.
- Keep styling centralized in `ctoa_helper_ui.lua`; no panel-specific ad hoc
  color literals.
- Add a sandbox-only capability probe for hover/focus events. Implement hover
  only if the real client reports a supported callback.

Acceptance:

- No gameplay/runtime behavior changes.
- Theme switching continues to work for classic, graphite, amber, and emerald.
- New primitives remain guarded when a widget API is unavailable.

### P3 — Sidebar modernization

- Render navigation inside one framed module card rather than floating rows.
- Use consistent 21 px rows, 2 px gaps, left padding, and an active accent rail.
- Group `Engine` and `Settings` as utility navigation with a divider above them.
- Integrate Profile and Runtime status into one compact status card at the
  bottom of the sidebar.
- Replace raw `Runtime armed` checkbox styling with a state badge plus explicit
  label, without changing the guarded arming workflow.

Acceptance:

- Sidebar reads as navigation first, status second.
- Hidden modules do not leave gaps.
- A smoke-forced hidden module remains visibly marked as a test-only entry.

### P4 — Settings and control hierarchy

- Add visible section headers for `Healing` and `Visible modules`.
- Convert each field into a layered row: label surface, inset value well, and
  consistent minus/plus controls.
- Use green/gray state text for ON/OFF; reserve amber for the active field or
  selected navigation.
- Style `Save now` as the primary action and make disabled/saved state visibly
  different.
- Shorten the summary strip to essential state and move secondary detail into
  a muted footer.

Acceptance:

- Potion/rune names remain absent; hotkeys stay authoritative.
- Random `+/- 3%` remains clearly visible and editable.
- Every row fits without truncating the control value at 690 px.

### P5 — Overview and remaining modules

- Turn Overview rows into compact raised metric cards with stronger label/value
  contrast and small state rails.
- Apply the same section/card language to Healing, Targeting, Magic, CaveBot,
  Helper, and Engine.
- Distinguish passive observer modules from armed runtime modules through badges
  rather than different layouts.
- Standardize primary, secondary, neutral, and destructive buttons.

Acceptance:

- No screen returns to the old flat all-gray row stack.
- Status, action, and configuration elements are visually distinguishable at a
  glance.
- CaveBot action buttons use the same hierarchy as Save and Close.

### P6 — Visual evidence and rollout

- Update the static preview model for every changed primitive and geometry.
- Add screenshots for Overview, Settings, CaveBot, Healing, and Engine in all
  four themes.
- Compare before/after crops at native resolution.
- Run targeted UI/profile tests, `ValidateDev`, `ModuleStaticGates`,
  `SmokePreflight`, sandbox `ReadyCheck`, `SmokeAttachModules`, and
  `SmokeAttachAll`.
- Repeat the logout/login singleton check.
- Promote through the official approved wrapper only after visual review.

Acceptance:

- Preview reports zero overlap and zero out-of-bounds issues.
- Sandbox shows one Helper window after relog.
- Full smoke remains 4/4 modules and 16/16 views.
- Live promotion has a current backup, 49/49 hash verification, and a fresh
  `Initialization complete` log.

## Suggested implementation slices

1. **v2.1.1-a:** CaveBot/nav correctness plus navigation metadata loop.
2. **v2.1.1-b:** semantic theme tokens and layered primitives.
3. **v2.1.1-c:** sidebar and Settings redesign.
4. **v2.1.1-d:** Overview and remaining panel modernization.
5. **v2.1.1-rc:** multi-theme screenshots, sandbox gates, visual approval.
6. **v2.1.1:** approved live promotion and final evidence.

## Non-goals

- No new automation behavior, combat logic, or runtime permissions.
- No web-style effects unsupported by the OTClient widget API.
- No increase beyond the current 690 px window width.
- No unrelated cleanup or staging from the dirty worktree.
