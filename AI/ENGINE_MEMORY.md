# Engine Memory

## Current Fork

- Repo: `C:/Users/zycie/CTOAi`
- Primary language stack: Python, TypeScript, Lua, PowerShell.
- Platform assumption: Windows/PowerShell local operator environment, with VPS
  deployment support under `deploy/vps/`.
- TFS fork source: not present in this snapshot.
- OTClient source tree: `scripts/lua/otclient/`.

## Current Protocol

- Server packet format and opcode map are not confirmed from source.
- OTClient automation uses native Lua APIs where available: `g_game`, `g_map`,
  `g_ui`, `g_keyboard`, `connect`, `cycleEvent`, and `scheduleEvent`.
- Do not infer TFS protocol flow without server/client protocol source.

## Current Lua API

Standalone generated Lua modules in `scripts/lua/` use simple `register(...)`
style hooks for generic runtimes.

OTClient native modules use OTClient APIs directly:

- Healing: `LocalPlayer.onHealthChanged`, `LocalPlayer.onManaChanged`,
  `g_game.talk`.
- Combat: `g_game.attack`, `g_game.follow`, `g_game.cancelAttack`,
  `g_map.getSpectatorsInRange`, `g_map.getCreaturesInRange`, `Creature.onDeath`.
- Loot: `Container.onOpen`, `Map.onItemAppear`, item/container scans.
- UI/helper: `g_ui`, `g_keyboard`, `cycleEvent`, profile save/load, HUD and tab
  rendering.

## Current Scheduler

- Python service scheduling lives in `deploy/vps/systemd/`.
- Bot session timing is guarded by `bot/safety/scheduler.py` and
  `bot/safety/session.py`.
- OTClient helper uses `cycleEvent(onThink, HELPER_CONFIG.tick_ms)`.
- Combat native module uses `cycleEvent(onThink, 100)`.
- Loader delays helper load through `scheduleEvent(loadHelperOnly, 1500)` or
  `addEvent(loadHelperOnly)` fallback.

## Current Packet Format

Pending source. No packet index can be considered authoritative until TFS and
client protocol files are provided.

## Known TODO

- Create server-side TFS index once source is available.
- Add real packet/opcode index from client/server protocol code.
- Add a generated machine-readable inventory for Lua functions and config keys.
- Decide whether OTClient package should be committed as source files, ZIP only,
  or both.

## Known Bugs

See `KNOWN_BUGS.md`.

## Known Technical Debt

See `TECH_DEBT.md`.

## Coding Standards

- Python: 4 spaces, `snake_case`, type hints where local code uses them.
- Classes: `PascalCase`.
- Constants: `UPPER_SNAKE_CASE`.
- PowerShell: `Set-StrictMode -Version Latest`, fail fast, PascalCase functions.
- Config/evidence: preserve existing key order.
- Tests: narrow, reproducible, contract/evidence-focused.

## Architecture Decisions

- Evidence-first delivery is a core product rule.
- Generated artifacts must have validation records.
- Runtime action should be gated, observable, and reversible.
- Control Center evidence paths belong in shared config, not scattered literals.
- OTClient helper must boot safely and keep runtime automation disabled by
  default unless the profile explicitly opts in.

## Roadmap

See `FEATURE_ROADMAP.md`.
