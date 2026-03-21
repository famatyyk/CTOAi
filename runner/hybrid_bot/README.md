# Hybrid Tibia Bot

**Template Matching + A* Pathfinding + oCTObot LLM Logic**

A Tibia bot architecture that combines computer vision, pathfinding, and decision-making logic, aligned with concepts described in academic research from Federal University of Tocantins (2021).

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   HYBRID BOT RUNNER                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ VISION LAYER │  │ PATHFINDING  │  │ PROMPT LOGIC │    │
│  │              │  │              │  │              │    │
│  │ • GPS (GPS   │  │ • A* search  │  │ • State      │    │
│  │   template   │  │ • SQM costs  │  │   snapshot   │    │
│  │   matching)  │  │ • Waypoints  │  │ • LLM query  │    │
│  │ • Health bar │  │              │  │ • Heuristics │    │
│  │   detection  │  │              │  │              │    │
│  │ • Creature   │  │              │  │              │    │
│  │   detection  │  │              │  │              │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│         ↓                  ↓                   ↓           │
│  ┌──────────────────────────────────────────────────┐    │
│  │        STATE MANAGER (Game Snapshot)            │    │
│  │ • Position, health, target, inventory           │    │
│  │ • Location tracking, metrics                    │    │
│  └──────────────────────────────────────────────────┘    │
│                        ↓                                  │
│  ┌──────────────────────────────────────────────────┐    │
│  │      ACTION EXECUTOR (Send Commands)             │    │
│  │ • Keyboard/mouse simulation                      │    │
│  │ • Spell casting, walking, attacking              │    │
│  └──────────────────────────────────────────────────┘    │
│                        ↓                                  │
│  ┌──────────────────────────────────────────────────┐    │
│  │    METRICS COLLECTOR (XP, Balance, Supplies)    │    │
│  │ • JSONL event log                                │    │
│  │ • Session summaries, location stats              │    │
│  └──────────────────────────────────────────────────┘    │
│                                                           │
└─────────────────────────────────────────────────────────────┘
```

## Key Features

### Vision Layer (Template Matching)
Based on Federal University of Tocantins research paper algorithms:
- **GPS Algorithm**: Minimap template matching (resized 25% for speed optimization)
- **Healing Algorithm**: Pixel color detection on health bar
- **Target Algorithm**: Creature sprite template matching against preconfigured hunting list

Advantages: low CPU usage (no deep learning), deterministic behavior, suitable for long-running sessions.

### Pathfinding (A* with Game Weights)
- **SQM-aware costs**: Grass, swamp, water, mountains each have different movement speeds
- **Player level bonus**: Higher levels move faster (20% bonus per 50 levels)
- **Cooldown integration**: Respects Tibia's movement/spell cooldown system
- **Waypoint buffers**: Circular hunting path patterns
- **Combat priority**: Pauses walking when engaged in combat

### oCTObot Prompt Logic
Intelligent decision-making via LLM or hardcoded heuristics:
- **Priority cascade**: Flee > Heal > Attack > Manage Inventory > Continue > Rotate
- **State-based decisions**: "If health < 60%, cast healing"
- **Efficiency tracking**: Monitors XP/hour, profit/hour, supplies cost
- **Location rotation**: Automatically changes hunting spots if experience stagnates

### Metrics Collection
Per research paper validation metrics:
- **XP Gain** (main measure of effectiveness)
- **Supplies Cost** (gold spent on potions)
- **Balance** (loot - supplies = profit)
- **Monsters Killed** (linear dependent on XP)
- **Loot Value** (linear dependent on XP)

Output: JSONL event log for post-session analysis, CSV export, session summaries

## Quick Start

### Installation

```bash
# Clone repo and setup venv
cd C:\Users\zycie\CTOAi
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements_hybrid.txt
```

### Dependencies
```
opencv-python  # Image processing
numpy          # Numerical computing
aiofiles       # Async file I/O
pyyaml         # Config serialization
openai         # LLM integration (optional)
```

### Run Bot (Heuristic Mode)

```bash
# Run at Wasp Cave, level 50
python -m runner.hybrid_bot.cli run --level 50 --location "Wasp Cave" --tick-ms 100
```

### Run Bot (LLM Mode - GPT-4)

```bash
# Requires OpenAI API key in environment
set OPENAI_API_KEY=sk-...
# PowerShell alternative:
# $env:OPENAI_API_KEY = "sk-..."

python -m runner.hybrid_bot.cli run --level 100 --location "Dragons" --use-llm --llm-model gpt-4 --heal-threshold 65
```

### Benchmark Against Manual

```bash
# Compare bot XP/profit rates against manual player metrics
python -m runner.hybrid_bot.cli benchmark --metrics-file ./metrics/metrics_20260321_120000.jsonl --manual-xp 5000 --manual-profit 500
```

Output:
```
═══════════════════════════════════════════════════════════════
Bot vs MANUAL COMPARISON
───────────────────────────────────────────────────────────────
Bot XP/hour:             5234
Manual XP/hour:          5000
Performance:             105% (EXCEEDS MANUAL)

Bot Profit/hour:         520g
Manual Profit/hour:      500g
Profitability:           104% (EXCEEDS MANUAL)
═══════════════════════════════════════════════════════════════
```

## Module Documentation

### `vision_layer.py`
Computer vision using template matching.

```python
from runner.hybrid_bot import VisionLayer

vision = VisionLayer(templates_dir="./templates")

# Detect position from minimap
position = vision.detect_position_from_minimap(minimap_screenshot)
# → GPSPosition(x=1000, y=2000, z=7, confidence=0.92)

# Detect health from bar
health = vision.detect_health_from_healthbar(healthbar_region)
# → HealthState(hp_percent=75.0, is_critical=False, is_poisoned=False)

# Detect creatures
creatures = vision.detect_creatures_from_sprites(game_screen)
# → [TargetInfo(name="Wasp", distance=3, is_engaged=True, confidence=0.89), ...]
```

### `pathfinding.py`
A* pathfinding with game-aware costs.

```python
from runner.hybrid_bot.pathfinding import Pathfinder, Coordinate, SQMType

pathfinder = Pathfinder(player_level=100)

# Find path with terrain map
path = pathfinder.find_path(
    start=Coordinate(1000, 2000, 7),
    goal=Coordinate(1050, 2050, 7),
    sqm_terrain={
        Coordinate(1001, 2000, 7): SQMType.GRASS,
        Coordinate(1002, 2000, 7): SQMType.SWAMP,  # Higher cost
    }
)

# Each segment has cost and expected travel time
for segment in path:
    print(f"{segment.from_pos} → {segment.to_pos}: {segment.expected_ms:.0f}ms")
```

### `prompt_logic.py`
oCTObot LLM-based or heuristic decision engine.

```python
from runner.hybrid_bot.prompt_logic import PromptLogic, GameState

logic = PromptLogic(use_llm=True, model_name="gpt-4")

state = GameState(
    hp_percent=45.0,
    mp_percent=80.0,
    is_poisoned=False,
    is_engaged=True,
    target_name="Dragon",
    xp_per_hour=5000
)

decision = logic.make_decision(state)
# → Decision(action=Action.HEAL, priority=9, reasoning="...")

# Execute it
executor.execute(decision.action, decision.parameters)
```

### `state_manager.py`
Game state tracking and snapshots.

```python
from runner.hybrid_bot.state_manager import StateManager

state = StateManager(initial_level=50)

# Update from vision
state.update_player_state(x=1000, y=2000, z=7, hp_percent=75.0, mp_percent=100.0)
state.update_target(name="Wasp", x=1010, y=2005, distance=3, is_engaged=True)

# Track location metrics
state.start_location("Wasp Cave")
state.record_monster_kill(xp_gain=1000, loot_value=500.0)
state.record_supply_cost(50.0)

# Check conditions
if state.should_heal():
    # Cast healing spell

if state.should_rotate_location():
    # Go to next hunting spot

# Get snapshot for decisions
game_state = state.snapshot()  # GameState object
```

### `metrics.py`
Performance metrics collection (JSONL + CSV).

```python
from runner.hybrid_bot.metrics import MetricsCollector

metrics = MetricsCollector(output_dir="./metrics")

# Record snapshots
metrics.record_snapshot(
    location="Wasp Cave",
    duration_seconds=3600,  # 1 hour
    xp_gained=5000,
    monsters_killed=47,
    loot_value_gold=2500,
    supplies_cost_gold=500,
    player_health_percent=85.0
)

# Get session summary
summary = metrics.get_session_summary()
print(f"Total XP: {summary.total_xp:,}")
print(f"Profit: {summary.total_balance_gold:.0f}g/hr")

# Export to CSV
metrics.export_metrics_csv("metrics_export.csv")

# Compare with manual
from runner.hybrid_bot.metrics import compare_with_manual_metrics
comparison = compare_with_manual_metrics(summary, manual_xp_per_hour=5000, manual_balance_per_hour=500)
print(f"Performance: {comparison['performance_relative_to_manual']}")
```

### `bot_runner.py`
Main orchestration engine.

```python
import asyncio
from runner.hybrid_bot import HybridBotRunner, BotConfig

config = BotConfig(
    player_level=100,
    use_llm=True,
    llm_model="gpt-4",
    max_health_before_heal=60.0,
    critical_health=25.0
)

bot = HybridBotRunner(
    config=config,
    screenshot_provider=lambda: get_screen(),  # Your screenshot func
    command_executor=lambda cmd: send_to_game(cmd)  # Your executor
)

# Set hunting waypoints
bot.set_waypoints([
    (1000, 2000, 7),
    (1050, 2000, 7),
    (1050, 2050, 7),
    (1000, 2050, 7),  # Circular path
])

# Start hunting
bot.start_hunting_location("Wasp Cave")

# Run main loop (10Hz default)
await bot.run()

# Check status
status = bot.get_status()
print(status)
```

## Research Validation

This bot is based on the academic paper:

> **"Development of an intelligent agent for Tibia MMORPG"**
> Authors: Thiago Castanheira Retes, Rafael lima de Carvalho
> Published: August 2021, Federal University of Tocantins
> Journal: Academic Journal on Computing, Engineering and Applied Mathematics, Vol 2, No 2

### Validation Metrics (from paper)
The paper validates bot performance using:
1. **XP Gain** – Primary measure; bot should match/exceed manual
2. **Supplies Cost** – Track potion spending
3. **Balance** (Loot - Supplies) – Profit margin
4. **Monsters Killed** – Linear correlate of XP
5. **Loot Value** – Linear correlate of XP

### Expected Performance
Per paper's 3 test scenarios over 10×15min + 5×1hr sessions:
- **Consistent XP rates** across sessions
- **Stable profit margins** (balance/supplies ratio)
- **Scalable with level** (higher level = faster rates)
- **24/7 capable** (no GPU needed, pure heuristics)

## Integration with CTOA Toolkit

The hybrid bot integrates with CTOAi runner:

```bash
# Add to runner backlog
agents:
  - id: "CTOA-HYBRID-001"
    name: "Hybrid Bot Executor"
    description: "Spawn and manage hybrid Tibia bot session"
    command: "python runner/hybrid_bot/cli.py run --level {PLAYER_LEVEL} --location {HUNTING_SPOT}"

# Track in metrics
metrics_dir: "./metrics/hybrid_sessions/"
```

## Troubleshooting

### Bot runs but no decisions made
- Check `log_level=DEBUG` for decision traces
- Verify screenshot provider returns valid numpy arrays
- Confirm template directory exists with creature/minimap templates

### High CPU usage
- Reduce `--tick-ms` if set too low
- Template matching should be < 50ms per frame at 1280x1024
- Consider disabling LLM (`--use-llm False`) if API latency high

### Inaccurate positioning (GPS)
- Load correct minimap templates for your server
- Ensure minimap region extraction matches your UI layout
- Confidence threshold is 0.7 by default (adjust in `vision_layer.py`)

### Action not executing
- Verify `CommandExecutor.execute()` actually sends input to game
- Check for blocked input (game window focus, permissions)
- Add logging to executor to verify commands reach game

## Known limitations / supported OS

Supported OS:
- Windows 10/11 is the primary target (capture/input stack and examples are Windows-first).
- Linux/macOS may work partially, but behavior depends on windowing and input backend compatibility.

Known limitations:
- Template matching quality depends on real server assets and UI layout consistency.
- Capture/input automation can be blocked by OS permissions, anti-cheat, or focus restrictions.
- LLM mode adds external latency/cost and requires valid API credentials.
- Current pipeline is single-session oriented; multi-account orchestration requires additional coordination.

## Roadmap

- [x] **Screenshot Integration**: Actual game window capture (PIL/mss)
- [x] **Keyboard Input**: Real keyboard/mouse simulation (pynput)
- [ ] **Server Detection**: Auto-detect Tibia server type (TFS/OTServBR/etc.)
- [ ] **Multi-Account**: Run multiple bot sessions in parallel
- [ ] **Web Dashboard**: Real-time metrics visualization
- [ ] **Model Training**: Train creature detection with actual server assets
- [ ] **Advanced Evasion**: Anti-detection measures

## License

Part of CTOAi project. See root LICENSE file.

## References

Refer to:
- **Architecture details**: docs/ARCHITECTURE.md
- **Research paper analysis**: docs/PAPER_ANALYSIS_BOT_DECISION.md
- **Tibia mechanics**: docs/pathing-spec.md, docs/targeting-rules.md
