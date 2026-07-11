# Lua And OTClient Instructions

This folder contains standalone CTOAi Lua modules and the OTClient helper
package/source.

## Rules

- Keep standalone runtime scripts and OTClient-native scripts separate unless an
  adapter is explicitly added.
- For OTClient files, guard native globals such as `g_game`, `g_map`, `g_ui`,
  `g_keyboard`, `g_resources`, and `g_clock`.
- Preserve safe boot defaults. Do not enable combat, cavebot movement, rune
  casting, auto haste, exeta, timer, or healing during loader initialization.
- Use `connect(...)` for supported OTClient events and `cycleEvent` for bounded
  loops.
- Use `scheduleEvent` for delayed boot work; `addEvent` is only a fallback.
- Keep cooldowns, bounded retries, and explicit early exits in `onThink` logic.
- Preserve profile/UI key order when changing helper persistence.

## Validation

Run the narrowest available check:

```powershell
.\ctoa.ps1 brain refresh
.\.venv\Scripts\python.exe -m pytest tests\test_otclient_helper_zerobot_shell.py tests\test_ctoa_helper_smoke_report.py -q
```

For manual OTClient UI changes, also load the helper in the client and verify
fresh `ctoa_local.log` lines plus safe boot state.
