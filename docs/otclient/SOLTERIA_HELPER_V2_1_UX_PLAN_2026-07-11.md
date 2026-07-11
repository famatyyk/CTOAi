# Solteria Helper v2.1 UX Plan

- Status: completed and live-promoted; retained as historical implementation evidence.

## Outcome

Make Helper a single compact window that survives logout/login without creating
duplicates, exposes only the modules selected in Settings, and treats actionbar
hotkeys as the source of potion and rune behavior.

## Delivery order

1. Keep one Helper singleton across `onGameEnd` / `onGameStart`, reuse the
   existing window, and remove stale duplicate windows left by older builds.
2. Add persisted module visibility settings. Core navigation remains available;
   optional Heal Friend, Conditions, CaveBot, Equipment, Helper tools, and
   Scripting tabs appear only when enabled.
3. Simplify healing settings to spell, HP/MP hotkeys, thresholds, and bounded
   threshold jitter. Remove potion and rune names from the operator UI because
   the configured actionbar slot is authoritative.
4. Apply deterministic per-cooldown jitter from `-3%` to `+3%` by default to HP
   potion, HP spell, mana potion, and healing-rotation thresholds.
5. Reduce width from 820 px to 690 px and replace the wide equipment-style
   Overview with compact full-width status rows.
6. Validate profile migration, render geometry, repeated sandbox login, full
   attach smoke, and a separately gated live promotion.

## Acceptance criteria

- Repeated logout/login produces exactly one `ctoaNativeHelperWindow`.
- Hidden optional modules have no sidebar button and remain configurable in
  Settings.
- No potion-name or rune-name selector appears in Settings.
- Jitter never exceeds the configured 0-5% bound and defaults to +/-3%.
- Static preview has no overlap or out-of-bounds findings at 690 px width.
- Runtime remains disarmed on boot and all live promotion gates stay mandatory.
