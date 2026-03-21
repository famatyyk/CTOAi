"""
State Manager - Game State Tracking and Snapshot

Maintains consistent view of bot's perception of the game world:
  - Player state (health, position, inventory)
  - Target tracking
  - Location/waypoint progress
  - Metrics accumulation
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from .pathfinding import Coordinate
from .prompt_logic import GameState

log = logging.getLogger("hybrid_bot.state_manager")


@dataclass
class PlayerState:
    """Local tracking of player character state."""
    x: int = 0
    y: int = 0
    z: int = 7  # Floor (0-15 in Tibia)
    hp_percent: float = 100.0
    mp_percent: float = 100.0
    is_poisoned: bool = False
    is_paralyzed: bool = False
    level: int = 50
    experience: int = 0
    equipment: dict[str, str] = field(default_factory=dict)
    inventory: list[dict] = field(default_factory=list)
    
    @property
    def position(self) -> Coordinate:
        return Coordinate(self.x, self.y, self.z)
    
    @property
    def is_alive(self) -> bool:
        return self.hp_percent > 0
    
    @property
    def is_critical(self) -> bool:
        return self.hp_percent < 25


@dataclass
class TargetState:
    """Current target monster."""
    name: str = ""
    x: int = 0
    y: int = 0
    distance: int = 0  # SQMs
    is_engaged: bool = False
    health_percent: float = 100.0
    
    @property
    def position(self) -> Coordinate:
        return Coordinate(self.x, self.y, 7)  # Assume same floor as player
    
    @property
    def is_valid(self) -> bool:
        return len(self.name) > 0 and self.distance < 100


@dataclass
class LocationMetrics:
    """Metrics collected at current hunting location."""
    location_name: str = ""
    start_time: datetime = field(default_factory=datetime.utcnow)
    monsters_killed: int = 0
    experience_gained: int = 0
    loot_value: float = 0.0  # Gold
    supplies_cost: float = 0.0  # Gold
    
    @property
    def elapsed_minutes(self) -> float:
        return (datetime.utcnow() - self.start_time).total_seconds() / 60.0
    
    @property
    def xp_per_hour(self) -> float:
        elapsed_hours = self.elapsed_minutes / 60.0
        return self.experience_gained / elapsed_hours if elapsed_hours > 0 else 0
    
    @property
    def balance_per_hour(self) -> float:
        elapsed_hours = self.elapsed_minutes / 60.0
        balance = self.loot_value - self.supplies_cost
        return balance / elapsed_hours if elapsed_hours > 0 else 0
    
    @property
    def supplies_per_hour(self) -> float:
        elapsed_hours = self.elapsed_minutes / 60.0
        return self.supplies_cost / elapsed_hours if elapsed_hours > 0 else 0


class StateManager:
    """
    Central state tracking for hybrid bot.
    
    Maintains:
      - Player state (health, position, inventory)
      - Current target
      - Location metrics (XP/hr, balance/hr)
      - Historical metrics for trending
    """
    
    def __init__(self, initial_level: int = 50):
        """Initialize state manager."""
        self.player = PlayerState(level=initial_level)
        self.target = TargetState()
        self.location_metrics = LocationMetrics()
        self.historical_locations: list[LocationMetrics] = []
        
        # Configuration
        self.max_health_percent_before_heal = 60
        self.critical_health_threshold = 25
        self.stagnation_xp_threshold = 50  # XP/hour
        self.rotation_time_minutes = 45
    
    # ─── Update Methods ──────────────────────────────────────────────────
    
    def update_player_state(
        self,
        x: int,
        y: int,
        z: int,
        hp_percent: float,
        mp_percent: float,
        is_poisoned: bool = False,
        is_paralyzed: bool = False
    ) -> None:
        """Update player position and status."""
        self.player.x = x
        self.player.y = y
        self.player.z = z
        self.player.hp_percent = max(0, min(100, hp_percent))
        self.player.mp_percent = max(0, min(100, mp_percent))
        self.player.is_poisoned = is_poisoned
        self.player.is_paralyzed = is_paralyzed
    
    def update_target(
        self,
        name: str,
        x: int,
        y: int,
        distance: int,
        is_engaged: bool = False,
        health_percent: float = 100.0
    ) -> None:
        """Update target tracking."""
        self.target.name = name
        self.target.x = x
        self.target.y = y
        self.target.distance = distance
        self.target.is_engaged = is_engaged
        self.target.health_percent = health_percent
    
    def clear_target(self) -> None:
        """Clear current target."""
        self.target = TargetState()
    
    def update_inventory(self, items: list[dict]) -> None:
        """Update inventory from vision system."""
        self.player.inventory = items
    
    # ─── Location Tracking ────────────────────────────────────────────────
    
    def start_location(self, name: str) -> None:
        """Start tracking metrics for new hunting location."""
        # Archive previous location
        if self.location_metrics.experience_gained > 0:
            self.historical_locations.append(self.location_metrics)
        
        self.location_metrics = LocationMetrics(
            location_name=name,
            start_time=datetime.utcnow()
        )
        log.info(f"Started hunting at: {name}")
    
    def record_monster_kill(self, xp_gain: int, loot_value: float = 0.0) -> None:
        """Record kill event and experience gain."""
        self.location_metrics.monsters_killed += 1
        self.location_metrics.experience_gained += xp_gain
        self.location_metrics.loot_value += loot_value
        self.player.experience += xp_gain
    
    def record_supply_cost(self, cost: float) -> None:
        """Record mana potion/resource cost."""
        self.location_metrics.supplies_cost += cost
    
    # ─── State Queries ────────────────────────────────────────────────────
    
    def should_heal(self) -> bool:
        """Check if health below healing threshold."""
        return self.player.hp_percent < self.max_health_percent_before_heal
    
    def is_critical_health(self) -> bool:
        """Check if in critical condition."""
        return self.player.hp_percent < self.critical_health_threshold
    
    def should_rotate_location(self) -> bool:
        """Check if current location is stagnant."""
        elapsed = self.location_metrics.elapsed_minutes
        xp_rate = self.location_metrics.xp_per_hour
        
        return (
            elapsed > self.rotation_time_minutes and
            xp_rate < self.stagnation_xp_threshold
        )
    
    def is_inventory_full(self, capacity_percent_threshold: float = 90.0) -> bool:
        """Check if inventory is approaching capacity."""
        # Simple heuristic: count items
        current_items = len(self.player.inventory)
        max_items = 20  # Tibia capacity
        capacity = (current_items / max_items) * 100
        return capacity > capacity_percent_threshold
    
    # ─── Game State Snapshot (for prompt logic) ──────────────────────────
    
    def snapshot(self) -> GameState:
        """
        Create current game state snapshot for decision making.
        
        Returns GameState object ready for LLM/heuristic decisions.
        """
        return GameState(
            hp_percent=self.player.hp_percent,
            mp_percent=self.player.mp_percent,
            is_poisoned=self.player.is_poisoned,
            is_engaged=self.target.is_engaged,
            distance_to_target=self.target.distance if self.target.is_valid else None,
            target_name=self.target.name if self.target.is_valid else None,
            current_location=self.location_metrics.location_name,
            xp_per_hour=self.location_metrics.xp_per_hour,
            supplies_cost_per_hour=self.location_metrics.supplies_per_hour,
            balance_per_hour=self.location_metrics.balance_per_hour,
            item_count=len(self.player.inventory),
            capacity_percent=(len(self.player.inventory) / 20) * 100,
            time_at_location_minutes=self.location_metrics.elapsed_minutes,
        )
    
    # ─── Reporting ────────────────────────────────────────────────────────
    
    def print_summary(self) -> str:
        """Format state summary for logging."""
        return f"""
╔═══════════════════════════════════════════════════════════╗
║ BOT STATE SUMMARY
╠═══════════════════════════════════════════════════════════╣
║ PLAYER
║   Position: ({self.player.x}, {self.player.y}, {self.player.z})
║   Health: {self.player.hp_percent:.0f}% | Mana: {self.player.mp_percent:.0f}%
║   Level: {self.player.level} | Experience: {self.player.experience:,}
║   Status: {'🔴 CRITICAL' if self.player.is_critical else '🟢 OK'}
║
║ TARGET
║   Name: {self.target.name or 'None'}
║   Distance: {self.target.distance}sqm | Engaged: {self.target.is_engaged}
║
║ LOCATION: {self.location_metrics.location_name}
║   Time: {self.location_metrics.elapsed_minutes:.0f}min
║   Kills: {self.location_metrics.monsters_killed}
║   XP/hr: {self.location_metrics.xp_per_hour:.0f} | Balance/hr: {self.location_metrics.balance_per_hour:.0f}g
║
╚═══════════════════════════════════════════════════════════╝
"""
    
    def get_location_history(self) -> list[dict]:
        """Return metrics from all visited locations."""
        locations = []
        for loc in self.historical_locations:
            locations.append({
                "name": loc.location_name,
                "duration_min": loc.elapsed_minutes,
                "kills": loc.monsters_killed,
                "xp_total": loc.experience_gained,
                "xp_per_hour": loc.xp_per_hour,
                "profit_per_hour": loc.balance_per_hour,
            })
        return locations
