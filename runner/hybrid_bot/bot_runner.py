"""
Hybrid Bot Runner - Main Orchestration Engine

Coordinates:
  1. Vision layer (screenshot analysis)
  2. Pathfinding (A* to waypoints)
  3. Prompt logic (LLM/heuristic decisions)
  4. State tracking
  5. Metrics collection
  6. Action execution

Main loop runs at ~10Hz (100ms ticks).
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Callable, Any

from .vision_layer import VisionLayer, extract_healthbar_region, extract_minimap_region
from .pathfinding import Pathfinder, Coordinate, WaypointBuffer
from .prompt_logic import PromptLogic, Action
from .state_manager import StateManager
from .metrics import MetricsCollector

log = logging.getLogger("hybrid_bot.runner")


@dataclass
class BotConfig:
    """Configuration for hybrid bot."""
    player_level: int = 50
    use_llm: bool = False
    llm_model: str = "gpt-3.5-turbo"
    max_health_before_heal: float = 60.0
    critical_health: float = 25.0
    update_interval_ms: int = 100  # Tick rate ~10Hz
    screenshot_dir: Optional[Path] = None
    metrics_dir: Path = Path("./metrics")


class ActionExecutor:
    """Converts Action decisions into game commands."""
    
    def __init__(self, send_command: Callable[[str], None]):
        """
        Initialize executor.
        
        Args:
            send_command: Callback to send commands to game (e.g., via keyboard)
        """
        self.send_command = send_command
    
    def execute(self, action: Action, parameters: dict | None = None) -> bool:
        """
        Execute an action in the game.
        
        Returns True if successful, False otherwise.
        """
        try:
            if action == Action.WALK:
                # Walking is handled by pathfinding
                return True
            
            elif action == Action.HEAL:
                spell = parameters.get("spell", "exura") if parameters else "exura"
                self.send_command(f"say {spell}")
                return True
            
            elif action == Action.ATTACK:
                self.send_command("shift+rightclick")  # Standard Tibia attack
                return True
            
            elif action == Action.CAST_SPELL:
                spell = parameters.get("spell", "") if parameters else ""
                if spell:
                    self.send_command(f"say {spell}")
                return True
            
            elif action == Action.FLEE:
                # Random direction movement
                self.send_command("numpad 4")  # West
                return True
            
            elif action == Action.WAIT:
                # No action
                return True
            
            else:
                log.warning(f"Unknown action: {action}")
                return False
        
        except Exception as e:
            log.error(f"Failed to execute {action.value}: {e}")
            return False


class HybridBotRunner:
    """
    Main bot orchestration engine.
    
    Pseudocode:
    ```
    while running:
        1. Capture screen
        2. Run vision layer (detect position, health, targets)
        3. Update state manager
        4. Create game state snapshot
        5. Prompt logic: decide next action
        6. Execute action
        7. Record metrics
        8. Sleep until next tick
    ```
    """
    
    def __init__(
        self,
        config: BotConfig,
        screenshot_provider,  # ScreenshotProvider instance or callable
        command_executor,     # CommandExecutor instance or callable
    ):
        """
        Initialize bot runner.
        
        Args:
            config: Bot configuration
            screenshot_provider: ScreenshotProvider instance (with .capture() method) or callable returning np.ndarray
            command_executor: CommandExecutor instance (with .execute(cmd) method) or callable(cmd)
        """
        self.config = config
        self.screenshot_provider = screenshot_provider
        self.command_executor = command_executor
        
        # Create command adapter based on type
        if hasattr(command_executor, 'execute') and callable(command_executor.execute):
            # It's a CommandExecutor instance
            command_callback = lambda cmd: command_executor.execute(cmd)
        else:
            # It's already a callable
            command_callback = command_executor
        
        # Component initialization
        self.vision = VisionLayer(templates_dir=config.screenshot_dir)
        self.pathfinder = Pathfinder(player_level=config.player_level)
        self.prompt_logic = PromptLogic(
            use_llm=config.use_llm,
            model_name=config.llm_model
        )
        self.state = StateManager(initial_level=config.player_level)
        self.metrics = MetricsCollector(output_dir=config.metrics_dir)
        self.action_executor = ActionExecutor(command_callback)
        
        # Waypoint tracking
        self.waypoint_buffer: Optional[WaypointBuffer] = None
        
        # Execution state
        self.running = False
        self.pause_until: Optional[datetime] = None
        self.last_action_time = datetime.utcnow()
        self.tick_count = 0
    
    # ─── Main Loop ────────────────────────────────────────────────────────
    
    async def run(self) -> None:
        """Start main bot loop."""
        self.running = True
        log.info("🤖 Hybrid Bot Runner started")
        
        try:
            while self.running:
                await self._tick()
                await asyncio.sleep(self.config.update_interval_ms / 1000.0)
        
        except KeyboardInterrupt:
            log.info("Bot interrupted by user")
        except Exception as e:
            log.error(f"Fatal error in bot loop: {e}", exc_info=True)
        finally:
            self.stop()
    
    async def _tick(self) -> None:
        """Single bot tick (100ms default)."""
        self.tick_count += 1
        
        try:
            # 1. Capture frame
            if hasattr(self.screenshot_provider, 'capture') and callable(self.screenshot_provider.capture):
                # It's a ScreenshotProvider instance
                frame = self.screenshot_provider.capture()
            else:
                # It's a callable
                frame = self.screenshot_provider()
            
            if frame is None or frame.size == 0:
                log.warning("No screenshot available")
                return
            
            # 2. Run vision layer
            position = self.vision.detect_position_from_minimap(
                extract_minimap_region(frame)
            )
            health = self.vision.detect_health_from_healthbar(
                extract_healthbar_region(frame)
            )
            creatures = self.vision.detect_creatures_from_sprites(frame)
            
            # 3. Update state
            if position:
                self.state.update_player_state(
                    position.x, position.y, position.z,
                    hp_percent=health.hp_percent if health else 100.0,
                    mp_percent=0,  # TODO: detect mana
                    is_poisoned=health.is_poisoned if health else False
                )
            
            if creatures:
                # Target closest creature
                closest = creatures[0]
                self.state.update_target(
                    name=closest.name,
                    x=closest.x,
                    y=closest.y,
                    distance=closest.distance,
                    is_engaged=closest.is_engaged
                )
            else:
                self.state.clear_target()
            
            # 4. Snapshot state for decisions
            game_state = self.state.snapshot()
            
            # 5. Prompt logic: decide action
            decision = self.prompt_logic.make_decision(game_state)
            
            # 6. Execute action
            success = self.action_executor.execute(
                decision.action,
                decision.parameters
            )
            
            # 7. Record decision (for debugging)
            if self.tick_count % 100 == 0:  # Every 10s at 10Hz
                log.debug(f"Tick {self.tick_count}: {decision.action.value} (priority {decision.priority})")
                log.debug(self.state.print_summary())
            
        except Exception as e:
            log.error(f"Tick error: {e}", exc_info=True)
    
    def stop(self) -> None:
        """Stop bot gracefully."""
        self.running = False
        log.info("Stopping Hybrid Bot")
        self._print_final_report()
    
    # ─── Waypoint Management ──────────────────────────────────────────────
    
    def set_waypoints(self, waypoints: list[tuple[int, int, int]]) -> None:
        """Set circular hunting path."""
        coords = [Coordinate(x, y, z) for x, y, z in waypoints]
        self.waypoint_buffer = WaypointBuffer(coords)
        log.info(f"Set {len(coords)} waypoints for cavebot")
    
    def start_hunting_location(self, name: str) -> None:
        """Start hunting session at named location."""
        self.state.start_location(name)
        log.info(f"🏹 Starting hunt at: {name}")
    
    # ─── Reporting ────────────────────────────────────────────────────────
    
    def _print_final_report(self) -> None:
        """Print final session report."""
        print("\n" + self.metrics.print_session_report())
        
        # Location breakdown
        summary = self.metrics.get_session_summary()
        if summary.total_duration_hours > 0:
            for location in summary.locations_visited:
                stats = self.metrics.get_location_stats(location)
                print(f"\n📍 {location}:")
                print(f"   Snapshots: {stats['snapshots']}")
                print(f"   Total XP: {stats['total_xp']:,}")
                print(f"   XP/hour: {stats['average_xp_per_hour']:.0f}")
                print(f"   Profit/hour: {stats['average_balance_per_hour']:.0f}g")
    
    def get_status(self) -> dict:
        """Get current bot status."""
        summary = self.metrics.get_session_summary()
        return {
            "running": self.running,
            "ticks": self.tick_count,
            "player": {
                "position": (self.state.player.x, self.state.player.y, self.state.player.z),
                "health": f"{self.state.player.hp_percent:.0f}%",
                "level": self.state.player.level,
            },
            "target": {
                "name": self.state.target.name,
                "distance": self.state.target.distance,
                "engaged": self.state.target.is_engaged,
            },
            "location": self.state.location_metrics.location_name,
            "metrics": {
                "xp_per_hour": f"{summary.average_xp_per_hour:.0f}",
                "balance_per_hour": f"{summary.average_balance_per_hour:.0f}g",
                "session_xp": f"{summary.total_xp:,}",
                "session_duration": f"{summary.total_duration_hours:.1f}h",
            }
        }
