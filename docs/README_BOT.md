# Tibia Bot — Technical Documentation

> **Agent 10: DOCUMENTATION SAGE** — Sprint 4 delivery  
> Protocol: Tibia 7.4 OTS (Canary) | Vocation: Knight | Levels: 8–50

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Quick Start](#quick-start)
3. [Module Reference](#module-reference)
4. [AI Decision Engine](#ai-decision-engine)
5. [Game Data](#game-data)
6. [Telemetry & Stats](#telemetry--stats)
7. [Safety & Anti-Detection](#safety--anti-detection)
8. [VPS Deployment](#vps-deployment)
9. [Configuration](#configuration)
10. [Agent Team](#agent-team)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                    bot/main.py                       │
│           500ms tick: Perceive→Decide→Act→Log        │
└──────┬──────────────┬──────────────┬────────────────┘
       │              │              │
  ┌────▼────┐   ┌─────▼─────┐  ┌───▼────────┐
  │perception│   │ decision  │  │   action   │
  │ screen  │   │ brain.py  │  │ combat.py  │
  │ parser  │   │ rules.py  │  │ movement   │
  │ state   │   │ ml_model  │  │ loot.py    │
  └─────────┘   │hunt_strat │  └────────────┘
                └─────┬─────┘
                      │
          ┌───────────┴────────────┐
          │                        │
    ┌─────▼──────┐         ┌───────▼──────┐
    │ data/      │         │ safety/      │
    │ db.py      │         │ humanizer.py │
    │ telemetry  │         │ session.py   │
    │ game_data  │         └──────────────┘
    └────────────┘
```

### Tick Loop (500ms)
```
1. capture_region_pixels()     — mss screen capture
2. parse_game_state(pixels)    — OpenCV HP/MP/target parsing
3. set_current_state(state)    — share state with action dispatcher
4. decide_action(state)        — Q-learning or rule engine
5. execute_action(action)      — pyautogui keypresses/mouse
6. log_event(action, result)   — SQLite telemetry
7. sleep(remainder of 500ms)
```

---

## Quick Start

### Local (Windows — Tibia OTS running)

```bash
# Install bot dependencies
pip install -r requirements-bot.txt

# Run bot
python -m bot.main
```

### Docker (VPS)

```bash
cd bot/infra
docker compose up -d
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BOT_DB_PATH` | `data/bot.db` | SQLite database path |

---

## Module Reference

### `bot/perception/`

| Module | Purpose |
|--------|---------|
| `screen.py` | Screen capture via `mss` (1024×768 region) |
| `parser.py` | OpenCV pixel-based HP/MP/target parsing |
| `state.py` | `GameState` dataclass — single source of truth per tick |

**`GameState` fields:**

| Field | Type | Description |
|-------|------|-------------|
| `hp`, `hp_max` | int | Current/max HP |
| `mp`, `mp_max` | int | Current/max MP |
| `hp_pct`, `mp_pct` | float (property) | Percentage 0-100 |
| `level` | int | Player level (parsed from UI) |
| `position` | Position | x, y, z tile coords |
| `target_id` | int\|None | Currently targeted creature ID |
| `target_hp_pct` | int | Target HP percentage |
| `bag_full` | bool | Inventory full flag |
| `is_attacking` | bool | Auto-attack active |
| `nearby_monsters` | list[str] | Monster names in battle window |

---

### `bot/decision/`

| Module | Purpose |
|--------|---------|
| `brain.py` | Decision dispatcher — ML or rules |
| `rules.py` | Priority-based rule engine (Phase 1 fallback) |
| `ml_model.py` | Q-learning model (Phase 2, **ACTIVE**) |
| `hunt_strategy.py` | Level-aware target + route selection |

---

### `bot/action/`

| Module | Purpose |
|--------|---------|
| `__init__.py` | Action dispatcher, `execute_action(str)` |
| `combat.py` | Attack, potions (hotkeys from `items.json`) |
| `movement.py` | `walk_to(x, y)`, `idle_move()` |
| `loot.py` | Loot corpse hotkey |

**Action strings:**

| Action | Trigger condition |
|--------|------------------|
| `flee_to_depot` | HP < 10% (critical) |
| `use_hp_potion` | HP < 30% |
| `use_mp_potion` | MP < 20% |
| `go_to_depot` | Bag full |
| `loot` | Target dead |
| `attack` | Target alive, not attacking |
| `select_target` | Nearby monsters, no target |
| `follow_route` | No monsters nearby |
| `idle` | Default fallback |

---

### `bot/data/`

| Module | Purpose |
|--------|---------|
| `db.py` | SQLite schema + `create_session()`, `get_session_stats()` |
| `telemetry.py` | `log_event()`, `log_loot()`, `log_exp()`, `get_stats()` |
| `game_data.py` | Loader for `data/game/*.json` |

---

### `bot/safety/`

| Module | Purpose |
|--------|---------|
| `humanizer.py` | All randomization — delays, bezier mouse, combat pauses |
| `session.py` | Session limits (4–8h), breaks (45–90min), night pause 02–07h |

---

## AI Decision Engine

### Phase 1: Rule Engine (`rules.py`)

10 priority-ordered rules evaluated each tick:

```
1  critical_hp    HP < 10%           → flee_to_depot
2  flee_hp        HP < 15%           → flee_to_depot
3  low_hp_potion  HP < 30%           → use_hp_potion
4  low_mp_potion  MP < 20%           → use_mp_potion
5  bag_full       bag full           → go_to_depot
6  loot_dead      target dead        → loot
7  attack_target  target alive       → attack
8  find_nearby    monsters nearby    → select_target
9  follow_route   no monsters        → follow_route (waypoints)
10 idle           always             → idle
```

Thresholds loaded dynamically from `data/game/items.json`.

### Phase 2: Q-Learning (`ml_model.py`) — **ACTIVE**

```
State:  (hp_bucket/20%, mp_bucket/20%, has_target, bag_full, level_tier/10, has_nearby)
Actions: 10 (attack, flee, hp_pot, mp_pot, loot, select_target, follow_route, ...)
α = 0.10  (learning rate)
γ = 0.90  (discount factor)
ε = 0.15  (exploration — 15% random actions)
```

**Reward shaping:**

| Event | Reward |
|-------|--------|
| Kill target | +15 |
| Loot corpse | +5 |
| HP loss (%) | -0.5× delta |
| Potion waste (HP>70%) | -3 |
| Flee unnecessarily | -2 |
| Idle | -0.5 |

Q-table persisted to `data/qtable.json` — survives restarts. Improves with every session.

**Fallback:** If ML raises any exception → rules engine takes over automatically.

---

## Game Data

### `data/game/monsters.json` — 14 monsters

| Level range | Monsters | Est. gold/hr |
|-------------|----------|-------------|
| 8–15 | Troll, Goblin | 800 |
| 10–22 | Orc | 1,500 |
| 15–32 | Minotaur, Rotworm | 2,000–3,000 |
| 22–38 | Minotaur Guard, Scarab | 4,500 |
| 25–40 | Demon Skeleton | 5,000 |
| 35–50 | Dragon Hatchling, Vampire | 8,000 |

### `data/game/hunt_routes.json` — 7 routes

Each route has: `min_level`, `max_level`, `risk`, `exp_per_hour_estimate`, `gold_per_hour_estimate`, `waypoints[]`.

### `data/game/items.json`

- Loot filter (min 10gp value)
- Always-loot list (crystals, valuable drops)
- Hotkey config (F1=HP pot, F2=MP pot, F3=strong HP, F4=antidote)
- Potion thresholds

---

## Telemetry & Stats

Stats printed every 2 minutes and on shutdown:

```
📊 STATS | Gold/hr: 3000 | Exp/hr: 6000 | Kills: 42 | Session: 1.20h
```

### SQLite Tables

| Table | Content |
|-------|---------|
| `sessions` | Session start/end, total gold, total xp, deaths |
| `actions` | Every action with result + duration_ms |
| `loot_events` | Each loot pickup with gold value |
| `exp_events` | Each kill with exp + monster name |
| `game_state_log` | HP/MP snapshots for analysis |

### API

```python
from bot.data.telemetry import log_loot, log_exp, get_stats

log_loot("platinum coin", 100)   # records pickup
log_exp(115, "Minotaur Guard")   # records kill
stats = get_stats()              # {gold_hr, exp_hr, kills, session_hours}
```

---

## Safety & Anti-Detection

### Humanizer delays (all actions)

| Function | Profile |
|----------|---------|
| `reaction_delay()` | 80–400ms before acting |
| `combat_pause()` | 70–200ms (80%), 200–500ms (15%), 500–1200ms (5%) |
| `potion_delay()` | 80–250ms after hotkey |
| `loot_delay()` | 100–600ms reading loot window |
| `think_pause()` | 300–1500ms, 1.5% chance (distraction) |
| `random_afk_twitch()` | Random mouse drift, 0.5% chance per tick |

### Mouse movement
Quadratic bezier curves with random control point ±40px + 1-4px click jitter.

### Session management
- Duration: 4–8h (randomized)
- Breaks: every 45–90min, duration 3–15min
- Night pause: 02:00–07:00 (no botting)

---

## VPS Deployment

**Auto-deploy:** push to `bot/` on `main` → GitHub Actions `cd_bot.yml` fires.

```
VPS: 116.202.96.250
User: ctoa
Method: docker build → SSH stream → docker run
```

### Manual deploy

```bash
./deploy-to-vps.sh 116.202.96.250 ctoa ~/.ssh/ctoa_vps_ed25519
```

### Monitor on VPS

```bash
ssh ctoa@116.202.96.250
docker logs -f tibia-bot
```

---

## Configuration

All tunable constants — no code changes needed:

| Location | Key | Default | Effect |
|----------|-----|---------|--------|
| `bot/main.py` | `TICK_MS` | 500 | Bot loop speed (ms) |
| `bot/main.py` | `STATS_EVERY` | 240 ticks | Stats print interval |
| `bot/decision/ml_model.py` | `EPSILON` | 0.15 | Exploration rate |
| `bot/decision/ml_model.py` | `ALPHA` | 0.10 | Q-learning rate |
| `bot/decision/brain.py` | `_USE_ML` | `True` | Enable Q-learning |
| `bot/safety/session.py` | `SESSION_MAX` | 28800s | Max session 8h |
| `env: BOT_DB_PATH` | — | `data/bot.db` | Database location |

---

## Agent Team

| # | Agent | Role | Key deliverables |
|---|-------|------|-----------------|
| 1 | STRATEGOS | Supreme Commander | Sprint planning, coordination |
| 2 | CORE ARCHITECT | Technical design | Module architecture |
| 3 | DATA ENGINEER | Data pipelines | SQLite schema, telemetry API |
| 4 | ML/AI BRAIN | Intelligence | Q-learning model, reward shaping |
| 5 | SECURITY GUARDIAN | Anti-detection | Humanizer, session safety |
| 6 | GAME LOGIC EXPERT | Domain knowledge | Monster DB, hunt routes, loot filter |
| 7 | CODE SMITH | Implementation | All `bot/` Python code |
| 8 | QA TERMINATOR | Quality | 45+ unit tests, CI gate |
| 9 | DEVOPS MASTER | Infrastructure | VPS, Docker, CD workflow |
| 10 | DOCUMENTATION SAGE | Knowledge | This document |

---

*Generated by AGENT 10: DOCUMENTATION SAGE — Sprint 4. Reviewed & Responsible.* 🎖️
