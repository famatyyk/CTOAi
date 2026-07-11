# Solteria Helper v2.1.1a Stabilization And Refactor Plan

- Status: in progress
- Base release: v2.1.1 live
- Target release: v2.1.1a
- Runtime scope: unchanged; no new automation permissions

## Outcome

Close the remaining v2.1.1 visual-contract gaps, reduce native shell pressure,
and publish repeatable four-theme visual evidence without changing profile
schema or enabling prototype runtime modules.

## Delivery Order

1. Version runtime, loader, module manifest, package, and evidence as v2.1.1a.
2. Use Graphite surfaces with an amber accent and state-specific ON, OFF, and
   BLOCKED colors.
3. Add adaptive sidebar geometry, utility navigation divider, runtime state
   badge, and primary/secondary/neutral/destructive button roles.
4. Keep `ctoa_native_helper.lua` at or below 4350 lines and 159 functions by
   delegating passive UI helpers while retaining every OTClient/runtime action
   in the guarded shell.
5. Add sandbox-only `ThemeSnapshotMatrix` evidence for five views in four
   themes and restore Graphite when complete.
6. Repeat ValidateDev, static gates, preview, sandbox attach, singleton relog,
   and separately approved live promotion.

## Compatibility And Safety

- Keep the current profile schema and key order.
- Preserve saved theme, module visibility, hotkey, healing, and layout values.
- Keep runtime disarmed on boot and prototype modules action-disabled.
- Never use ThemeSnapshotMatrix against the live client.
- Preserve the official untracked Windows wrapper in the Helper commit bundle.

## Acceptance

- UI preview has no overlap or out-of-bounds controls at 690x560.
- Sidebar geometry passes for 8, 10, 11, and 12 visible entries.
- Shell budget is at most 4350 lines and 159 functions.
- Theme matrix contains 20 named sandbox screenshots and restores Graphite.
- Sandbox passes ReadyCheck, 4/4 module attach, 16/16 full attach, and relog
  singleton evidence.
- Live requires fresh explicit approval, backup, full manifest hash parity,
  fresh v2.1.1a boot, and release gate passed.

## Next Phase

After v2.1.1a is stable, resume P6 Module Lane design. Heal Friend,
Conditions, Equipment, Loot, and Scripting runtime enablement remain outside
this patch.
