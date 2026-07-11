# Class and Module Index

## Python API Classes

`api/main.py`:

- `Message`
- `ChatRequest`
- `OpenAIChatRequest`
- `RegisterRequest`
- `LoginRequest`
- `InviteRequest`
- `AcceptInviteRequest`
- `RoleUpdateRequest`

## Python Hybrid Bot Classes

`runner/hybrid_bot/gameplay_engine.py`:

- `GameplayMode`
- `CombatStats`
- `CombatEngine`
- `MovementEngine`
- `LootEngine`
- spell/gameplay decision classes later in the same file

Other hybrid bot modules contain:

- command execution classes in `command_executor.py`
- template/library classes in `template_library.py`
- vision data/classes in `vision_layer.py`
- state/metrics/pathfinding classes in their matching files

## Python Bot Runtime Classes

`bot/perception/window.py`:

- Windows capture structs and `WindowHandle`.

`bot/safety/scheduler.py`:

- `SessionScheduler`.

Other runtime modules expose functional APIs for action/perception/safety
behavior.

## Agent Modules

`runner/agents/`:

- `catalog_agent.py`
- `ingest_agent.py`
- `brain_v2.py`
- `generator_agent.py`
- `validator_agent.py`
- `publisher_agent.py`
- `executor.py`
- `orchestrator.py`
- `db.py`

These are module-oriented scripts rather than class-heavy services.

## Lua Tables and Modules

Standalone Lua:

- `AutoHeal`
- `EventLogger`
- `PathingHelper`
- `SupplyManager`
- `TelemetryExporter`
- `SafetyInterrupt`
- target/loot helper tables depending on file

OTClient native:

- `CTOA_OTCLIENT`
- `HELPER_CONFIG`
- `Helper`
- `CTOA_Manager`
- `Combat`
- `HEAL_SETTINGS`
- `LOOT_CONFIG`
- `VALUABLE_LOOT`

## TFS Classes

Pending source. Expected classes to index after TFS source is available:

- `Creature`
- `Player`
- `Monster`
- `Npc`
- `Combat`
- `Game`
- `ProtocolGame`
- `Scheduler`
- `Dispatcher`
- `LuaScriptInterface`
- `Item`
- `Container`
- custom systems in the fork
