"""
Gameplay Engine - Combat, Movement, and Loot Logic

Provides structured gameplay loops for different hunting modes.
Integrates with the decision-making system for autonomous/manual control.

Modes:
  - AUTO: AI-driven autonomous hunting (uses LLM or heuristics)
  - MANUAL: Interactive mode - player controls via keyboard shortcuts
  - HYBRID: AI suggests actions, player approves
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Callable

import numpy as np

log = logging.getLogger("hybrid_bot.gameplay")


class GameplayMode(Enum):
    """Bot operation mode."""
    AUTO = "auto"           # Fully autonomous AI control
    MANUAL = "manual"       # Player controls (like Easybot)
    HYBRID = "hybrid"       # AI suggests, player approves


@dataclass
class CombatStats:
    """Accumulated combat statistics."""
    creatures_killed: int = 0
    damage_dealt: int = 0
    damage_taken: int = 0
    heals_cast: int = 0
    total_xp_gained: int = 0
    total_loot_value: int = 0
    
    @property
    def dps(self) -> float:
        """Damage per second (approximate)."""
        # This would come from actual combat timing
        return 0.0
    
    def increment_kill(self, xp_gain: int, loot_value: int = 0) -> None:
        """Record a creature kill."""
        self.creatures_killed += 1
        self.total_xp_gained += xp_gain
        self.total_loot_value += loot_value


class CombatEngine:
    """Handles combat logic and targeting."""
    
    def __init__(self, player_level: int):
        """
        Initialize combat engine.
        
        Args:
            player_level: Player's current level (affects damage calculations)
        """
        self.player_level = player_level
        self.target_priority = self._build_priority_queue()
        self.combat_stats = CombatStats()
        self.last_target_change = time.time()
    
    def _build_priority_queue(self) -> dict:
        """Build creature priority for targeting."""
        return {
            # Lower score = higher priority
            "flying": 1,      # Dangerous, eliminate first
            "melee": 2,       # Standard threat
            "ranged": 3,      # Medium threat
            "harmless": 99,   # Ignore
        }
    
    def choose_target(self, visible_creatures: list) -> Optional[dict]:
        """
        Choose best target from visible creatures.
        
        Priority:
          1. Dangerous types (flying, ranged)
          2. Closest to player
          3. Already engaged creatures
        
        Returns:
            Target creature dict or None
        """
        if not visible_creatures:
            return None
        
        # Score each creature
        scored = []
        for creature in visible_creatures:
            type_priority = self.target_priority.get(
                creature.get("type", "melee"), 50
            )
            
            distance = creature.get("distance", 999)
            is_engaged = creature.get("is_engaged", False)
            
            # Lower score = higher priority
            score = (
                type_priority * 100 +
                (distance * 10) +
                (0 if is_engaged else 50)
            )
            
            scored.append((score, creature))
        
        scored.sort(key=lambda x: x[0])
        best_score, best_creature = scored[0]
        
        # Only switch targets if priority is significantly better
        if hasattr(self, 'current_target') and self.current_target:
            time_since_switch = time.time() - self.last_target_change
            if time_since_switch < 5.0:  # Cooldown on target switches
                return self.current_target
        
        self.current_target = best_creature
        self.last_target_change = time.time()
        return best_creature
    
    def should_flee(self, health_percent: float, critical_threshold: float) -> bool:
        """Decide if player should flee."""
        return health_percent < critical_threshold


class MovementEngine:
    """Handles navigation and pathfinding."""
    
    def __init__(self, max_distance_before_recall: float = 50.0):
        """
        Initialize movement engine.
        
        Args:
            max_distance_before_recall: Distance from last known position before
                                       using home spell/town portal
        """
        self.max_distance = max_distance_before_recall
        self.home_location = None
        self.waypoint_path = []
        self.current_waypoint_index = 0
    
    def set_home(self, x: int, y: int, z: int) -> None:
        """Set home location (for recalls)."""
        self.home_location = (x, y, z)
        log.info(f"Home set to ({x}, {y}, {z})")
    
    def set_hunting_path(self, waypoints: list[tuple[int, int, int]]) -> None:
        """Set circular hunting path."""
        self.waypoint_path = waypoints
        self.current_waypoint_index = 0
        log.info(f"Hunting path set: {len(waypoints)} waypoints")
    
    def get_next_waypoint(self, current_x: int, current_y: int) -> Optional[tuple[int, int, int]]:
        """Get next waypoint in hunting path."""
        if not self.waypoint_path:
            return None
        
        wp = self.waypoint_path[self.current_waypoint_index]
        
        # Check if we've reached current waypoint (within 1 sqm)
        dx = wp[0] - current_x
        dy = wp[1] - current_y
        distance = (dx*dx + dy*dy) ** 0.5
        
        if distance < 2:  # Reached waypoint
            self.current_waypoint_index = (self.current_waypoint_index + 1) % len(self.waypoint_path)
            return self.waypoint_path[self.current_waypoint_index]
        
        return wp
    
    def should_recall_home(self, current_x: int, current_y: int) -> bool:
        """Check if player should recall home."""
        if not self.home_location:
            return False
        
        dx = current_x - self.home_location[0]
        dy = current_y - self.home_location[1]
        distance = (dx*dx + dy*dy) ** 0.5
        
        return distance > self.max_distance


class LootEngine:
    """Handles loot pickup and management."""
    
    def __init__(self, max_backpack_items: int = 20, skip_items: Optional[set] = None):
        """
        Initialize loot engine.
        
        Args:
            max_backpack_items: Max items before dropping loot
            skip_items: Set of item names to never pickup
        """
        self.max_items = max_backpack_items
        self.skip_items = skip_items or {"rope", "shovel", "torch"}
        self.loot_whitelist = {
            "gold coin", "platinum coin", "crystal coin",
            "great health potion", "great mana potion",
        }
        self.pickup_enabled = True
    
    def should_pickup_loot(self, item_name: str) -> bool:
        """Decide if item should be picked up."""
        if not self.pickup_enabled:
            return False
        
        if item_name in self.skip_items:
            return False
        
        # TODO: Check backpack space
        # TODO: Check item value
        
        return True
    
    def should_drop_loot(self, backpack_items: list[str]) -> bool:
        """Check if loot needs to be dropped."""
        return len(backpack_items) >= self.max_items


class HealingEngine:
    """Manages healing and spell casting."""
    
    def __init__(self):
        """Initialize healing engine."""
        self.heal_cooldown = 1.0  # seconds
        self.last_heal_time = 0.0
        self.buff_cooldowns = {
            "strength": 300.0,
            "haste": 300.0,
            "protection": 300.0,
        }
    
    def should_cast_heal(self, health_percent: float, heal_threshold: float) -> bool:
        """Decide if healing spell should be cast."""
        if health_percent > heal_threshold:
            return False
        
        time_since_heal = time.time() - self.last_heal_time
        if time_since_heal < self.heal_cooldown:
            return False  # Still on cooldown
        
        return True
    
    def should_cast_buff(self, buff_name: str) -> bool:
        """Check if buff should be (re)cast."""
        last_cast = self.buff_cooldowns.get(buff_name, 0.0)
        cooldown = 300.0  # 5 min default
        
        return time.time() - last_cast > cooldown
    
    def record_heal(self) -> None:
        """Record that heal was cast."""
        self.last_heal_time = time.time()
    
    def record_buff(self, buff_name: str) -> None:
        """Record that buff was cast."""
        self.buff_cooldowns[buff_name] = time.time()


class GameplayEngine:
    """
    Unified gameplay engine combining combat, movement, loot, and healing.
    
    Provides decision-making layer above the bot runner.
    """
    
    def __init__(
        self,
        mode: GameplayMode = GameplayMode.AUTO,
        player_level: int = 50,
    ):
        """
        Initialize gameplay engine.
        
        Args:
            mode: Gameplay mode (AUTO, MANUAL, HYBRID)
            player_level: Player level (affects combat calculations)
        """
        self.mode = mode
        self.combat = CombatEngine(player_level)
        self.movement = MovementEngine()
        self.loot = LootEngine()
        self.healing = HealingEngine()
        
        self.last_decision_time = time.time()
        self.decision_rate_hz = 10  # Tick rate
    
    def make_decision(
        self,
        player_state: dict,
        visible_creatures: list,
        time_delta: float = 0.1,
    ) -> str:
        """
        Make high-level gameplay decision.
        
        Returns: Action string (e.g., "attack", "heal", "move_to_waypoint")
        """
        
        # Priority 1: Critical healing
        if player_state.get("health_percent", 100) < 20:
            if self.healing.should_cast_heal(player_state["health_percent"], 20):
                self.healing.record_heal()
                return "heal"
            else:
                return "wait"
        
        # Priority 2: Flee from danger
        if player_state.get("health_percent", 100) < 30:
            if len(visible_creatures) > 3:
                return "flee"
        
        # Priority 3: Attack nearest creature
        if visible_creatures:
            target = self.combat.choose_target(visible_creatures)
            if target:
                return f"attack:{target.get('name', 'creature')}"
        
        # Priority 4: Normal healing
        if player_state.get("health_percent", 100) < 60:
            if self.healing.should_cast_heal(player_state["health_percent"], 60):
                self.healing.record_heal()
                return "heal"
        
        # Priority 5: Move to next waypoint
        current_x = player_state.get("x", 0)
        current_y = player_state.get("y", 0)
        next_wp = self.movement.get_next_waypoint(current_x, current_y)
        
        if next_wp:
            return f"move_to:{next_wp[0]},{next_wp[1]}"
        
        # Priority 6: Wait
        return "wait"
    
    def set_mode(self, mode: GameplayMode) -> None:
        """Switch gameplay mode."""
        self.mode = mode
        log.info(f"Gameplay mode: {mode.value}")
    
    def get_stats(self) -> dict:
        """Get current combat statistics."""
        return {
            "creatures_killed": self.combat.combat_stats.creatures_killed,
            "total_xp_gained": self.combat.combat_stats.total_xp_gained,
            "total_loot_value": self.combat.combat_stats.total_loot_value,
        }
