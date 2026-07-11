# Project Rulebook

## Global Rules

- Never claim a deploy, smoke, game action, or evidence artifact exists unless it
  has been checked in the current run or is clearly marked as historical.
- Do not edit `.env`, `runtime/`, `logs/`, `data/`, or generated local state
  unless the user explicitly asks for runtime repair.
- Keep operator commands Windows-friendly.
- Prefer repo-local `.venv/Scripts/python.exe` for Python execution.
- When changing release, sprint, or evidence logic, update docs/tests/evidence
  contracts together.
- For Engine Brain work, write current operational findings to
  `AI/OPERATIONS_AUDIT.md` and keep time-sensitive status separate from stable
  rules.
- Do not place Vercel env values, GitHub tokens, auth stores, local logs, or
  database dumps into `AI/`.

## CTOAi API Rules

- Auth, rate limiting, audit logging, and safety telemetry are shared behavior in
  `api/main.py`; changes must be tested with focused API tests.
- Do not bypass `_current_user`, `_require_roles`, or rate-limit grouping for new
  privileged endpoints.
- Do not expose raw backend/model errors to users; preserve friendly masking.
- Keep OpenAI-compatible `/v1/chat/completions` behavior aligned with `/api/chat`
  unless intentionally diverging.

## Infrastructure Rules

- Local Docker services should bind to loopback unless there is an explicit
  LAN/VPN requirement.
- Cloudflare WARP being connected does not make broad `0.0.0.0` binds safe.
- Use the explicit Git for Windows path when plain `git` is unavailable:
  `C:\Program Files\Git\cmd\git.exe`.
- For GitHub CLI work, ensure Git is on PATH or pass explicit `--repo` values.
- Vercel audits may list project metadata and env names, but not env values.

## Generator/Validator Rules

- Generated Lua must include deterministic control flow and bounded retries.
- Generated modules must have a clear header and validation path.
- Validator quality scoring must not silently pass empty, missing, or unknown
  output.
- For Lua generation, prefer server context from `game_data`; do not hard-code
  server-specific facts without evidence.
- If `luac` is unavailable, basic fallback syntax checks are acceptable but must
  be labeled as weaker validation.

## OTClient Runtime Rules

- Safe boot is the default. Do not auto-enable combat, cavebot movement, rune
  casting, auto haste, exeta, timer, or healing during loader initialization.
- Use `connect(...)` for real OTClient event hooks when the API supports it.
- Use `cycleEvent` for bounded periodic helper loops and keep intervals explicit.
- Use `scheduleEvent` for delayed boot work; `addEvent` is only a fallback where
  the client lacks `scheduleEvent`.
- Guard every native API call (`g_game`, `g_map`, `g_ui`, `g_keyboard`,
  `g_resources`) because custom OTClient forks differ.
- Do not assume a creature method exists. Probe with `pcall` or method checks.
- Combat target switching must be rate-limited and must clear state in PZ,
  offline, disabled, invalid target, or no target states.
- UI preferences and profile saves must preserve key order from the helper.
- Hotkey rebinding must unbind the old key before binding the new key.
- Runtime modules should log to `ctoa_local.log` or the configured fallback.

## Lua Module Rules

- Standalone Lua modules in `scripts/lua/` use small tables/functions and should
  remain deterministic.
- Keep public functions named by module table, for example
  `AutoHeal.nextAction`, `PathingHelper.nextWaypoint`.
- Avoid global writes unless intentionally exposing a module table.
- Do not introduce infinite `onThink` work; add cooldowns and early exits.
- Use explicit thresholds and cooldowns for heal, combat, movement, and supply
  logic.

## UI Rules

- OTClient helper UI is built by code in `ctoa_native_helper.lua`; extend existing
  row builders, tab switching, section visibility, and theme helpers.
- Keep fixed layout dimensions stable so widgets do not shift during updates.
- Use existing tabs/subtabs before adding a new panel.
- Smoke tabs should be addressable through `Helper.smoke_tab` and
  `Helper.smoke_subtab`.

## Packet/Protocol Rules

- Do not invent packet names, opcodes, or packet flow.
- Packet documentation must point to exact protocol source files.
- If packet source is absent, mark the packet work as blocked on source.

## TFS Rules

- TFS fork rules are pending source.
- Do not prescribe C++ class contracts until the TFS source tree is indexed.
- Once source is available, index `Creature`, `Player`, `Combat`, `ProtocolGame`,
  dispatcher/scheduler, Lua script interface, item/container classes, and custom
  systems before editing engine logic.
