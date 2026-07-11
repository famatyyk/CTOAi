# Project Context

## Repository Shape

Core Python code lives in:

- `runner/`: scheduled agents, generation, validation, reporting, hybrid bot.
- `agents/`: YAML/Markdown agent definitions.
- `api/`: FastAPI app, auth, chat routing, safety telemetry, release evidence.
- `bot/`: local perception/action/safety/overlay runtime.
- `scoring/`: quality and scoring support.
- `prompts/`: prompt packs and prompt infrastructure.

Operational and platform code lives in:

- `scripts/`: analysis utilities, Lua modules, local scripts.
- `scripts/ops/`: product bootstrap, validators, release/evidence tooling.
- `scripts/windows/`: Windows-specific helpers.
- `scripts/lua/`: standalone Lua modules and OTClient package.

Docs and evidence surfaces live in:

- `docs/`, `workflows/`, `policies/`, `releases/`, `evals/`, `training/`.

Tests live in:

- `tests/`
- `tests/unit/`
- `web/src/lib/__tests__/`

## CTOAi Runtime

The main API is `api/main.py`:

- FastAPI app title: `CTOAi API`
- Version: `1.3.0`
- Chat endpoints: `/api/chat`, `/v1/chat/completions`
- Status/health: `/health`, `/api/status`
- Auth/community: `/api/auth/*`, `/api/community/*`
- Evidence: `/api/release-evidence`
- Safety telemetry: `/api/safety/*`

The model router uses environment-driven local/OpenAI-compatible endpoints:

- `CTOA_LOCAL_MODEL_URL`
- `CTOA_LOCAL_MODEL_NAME`
- `CTOA_MODEL_SMALL`
- `CTOA_MODEL_LARGE`
- `CTOA_SMALL_MODEL_URL`
- `CTOA_LARGE_MODEL_URL`
- `CTOA_ROUTE_DEFAULT`

## Generator/Validator Loop

The generation lane is under `runner/agents/`:

- `brain_v2.py`: plans module/program generation based on available server data.
- `catalog_agent.py`: discovers and scores server candidates.
- `ingest_agent.py`: ingests server/game data.
- `generator_agent.py`: renders Lua/Python templates for queued modules.
- `validator_agent.py`: validates generated modules and quality score.
- `publisher_agent.py`: publishes validated output.
- `executor.py`, `orchestrator.py`: execution and scheduling surfaces.

Lua templates in `generator_agent.py` currently include auto heal, reconnect,
loot filter, cavebot pathing, target selector, anti-stuck, alarms, healer
profiles, flee logic, blacklists, loot maps, highscore/player trackers, hunt
orchestrator, economy bot, PvP guard, depot/bank/gold automation, human delay,
break scheduler, rune maker, combo spells, area spell control, exp tracker,
session log, and respawn optimizer.

## Hybrid Bot

`runner/hybrid_bot/` is the Python-side gameplay stack:

- `vision_layer.py`: screenshots and computer vision.
- `template_library.py`: creature/minimap template loading and caching.
- `gameplay_engine.py`: combat, movement, loot, spells, game mode logic.
- `command_executor.py`: keyboard/mouse command execution.
- `pathfinding.py`: path planning.
- `state_manager.py`: state persistence.
- `metrics.py`: runtime metrics.
- `interactive_mode.py`: manual/hybrid operator mode.

`bot/` is the local runtime stack:

- `bot/perception/`: window capture, parsing, memory reader, state.
- `bot/action/`: combat, movement, loot, spell rotation, input backend.
- `bot/safety/`: session scheduling, humanizer, session guard.
- `bot/overlay/`: macro/status overlay UI.

## OTClient Package

The OTClient source tree in `scripts/lua/otclient/` contains:

- `ctoa_otclient.otmod`
- `ctoa_otclient_loader.lua`
- `ctoa_native_helper.lua`
- `ctoa_native_combat.lua`
- `ctoa_native_heal.lua`
- `ctoa_native_loot.lua`
- `ctoa_ek_profile.lua`
- `README.md`

The helper is the main integration point. Runtime modules are configured through
`HELPER_CONFIG`, with safe boot disabling active automation unless explicitly
enabled.
