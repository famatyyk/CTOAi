"""
Unit tests for Hybrid Tibia Bot modules.

Run with: pytest tests/test_hybrid_bot.py -v
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from runner.hybrid_bot import (
    VisionLayer,
    Pathfinder,
    Coordinate,
    SQMType,
    PromptLogic,
    GameState,
    StateManager,
    MetricsCollector,
    BotConfig,
    HybridBotRunner,
)


# ─── Vision Layer Tests ─────────────────────────────────────────────────

class TestVisionLayer:
    
    def test_vision_init(self):
        """Test vision layer initialization."""
        vision = VisionLayer()
        assert vision is not None
        assert len(vision.minimap_templates) == 0  # No templates dir provided
    
    def test_gps_position_type(self):
        """Test GPS position dataclass."""
        from runner.hybrid_bot.vision_layer import GPSPosition
        
        pos = GPSPosition(x=1000, y=2000, z=7, confidence=0.95)
        assert pos.x == 1000
        assert pos.y == 2000
        assert pos.z == 7
        assert pos.confidence == 0.95
    
    def test_health_state_type(self):
        """Test health state dataclass."""
        from runner.hybrid_bot.vision_layer import HealthState
        
        health = HealthState(hp_percent=75.0, is_critical=False, is_poisoned=True)
        assert health.hp_percent == 75.0
        assert not health.is_critical
        assert health.is_poisoned
    
    def test_target_info_type(self):
        """Test target info dataclass."""
        from runner.hybrid_bot.vision_layer import TargetInfo
        
        target = TargetInfo(
            name="Wasp",
            x=100,
            y=150,
            distance=3,
            is_engaged=True,
            confidence=0.85
        )
        assert target.name == "Wasp"
        assert target.distance == 3
        assert target.is_engaged


# ─── Pathfinding Tests ──────────────────────────────────────────────────

class TestPathfinding:
    
    def test_coordinate_creation(self):
        """Test coordinate creation and properties."""
        c1 = Coordinate(100, 200, 7)
        c2 = Coordinate(110, 210, 7)
        
        assert c1.x == 100
        assert c2.distance_to(c1) > 0
    
    def test_pathfinder_init(self):
        """Test pathfinder initialization."""
        pf = Pathfinder(player_level=100)
        assert pf.player_level == 100
        assert pf.level_bonus > 1.0  # Higher level affects bonus
    
    def test_pathfinding_basic(self):
        """Test basic A* pathfinding."""
        pf = Pathfinder(player_level=50)
        
        start = Coordinate(100, 100, 7)
        goal = Coordinate(110, 100, 7)
        
        path = pf.find_path(start, goal)
        
        assert isinstance(path, list)
        # Path should exist for adjacent tiles
        if len(path) > 0:
            assert path[-1].to_pos == goal
    
    def test_terrain_cost_calculation(self):
        """Test SQM terrain cost calculation."""
        pf = Pathfinder(player_level=50)
        
        # Grass should be cheaper than swamp
        grass_cost = pf._calculate_move_cost(SQMType.GRASS)
        swamp_cost = pf._calculate_move_cost(SQMType.SWAMP)
        
        assert grass_cost < swamp_cost
    
    def test_waypoint_buffer(self):
        """Test waypoint circular buffer."""
        from runner.hybrid_bot.pathfinding import WaypointBuffer
        
        waypoints = [
            Coordinate(100, 100, 7),
            Coordinate(110, 100, 7),
            Coordinate(110, 110, 7),
        ]
        
        buffer = WaypointBuffer(waypoints)
        
        # Test circular advancement
        assert buffer.get_current_waypoint() == waypoints[0]
        buffer.advance()
        assert buffer.get_current_waypoint() == waypoints[1]
        buffer.advance()
        assert buffer.get_current_waypoint() == waypoints[2]
        buffer.advance()
        assert buffer.get_current_waypoint() == waypoints[0]  # Wrap around


# ─── Prompt Logic Tests ─────────────────────────────────────────────────

class TestPromptLogic:
    
    def test_prompt_logic_init(self):
        """Test prompt logic initialization."""
        logic = PromptLogic(use_llm=False)
        assert logic is not None
        assert not logic.use_llm
    
    def test_action_enum(self):
        """Test action enum values."""
        from runner.hybrid_bot.prompt_logic import Action
        
        assert Action.WALK.value == "walk"
        assert Action.HEAL.value == "heal"
        assert Action.ATTACK.value == "attack"
        assert Action.FLEE.value == "flee"
    
    def test_game_state_creation(self):
        """Test game state dataclass."""
        state = GameState(
            hp_percent=75.0,
            mp_percent=80.0,
            is_poisoned=False,
            is_engaged=True,
            distance_to_target=5,
            target_name="Wasp",
            current_location="Wasp Cave",
            xp_per_hour=5000,
            supplies_cost_per_hour=500,
            balance_per_hour=4500,
            item_count=15,
            capacity_percent=75.0,
            time_at_location_minutes=30
        )
        
        assert state.hp_percent == 75.0
        assert state.is_engaged is True
        assert state.target_name == "Wasp"
    
    def test_heuristic_decision_flee(self):
        """Test flee decision at low health."""
        logic = PromptLogic(use_llm=False)
        
        state = GameState(
            hp_percent=20.0,  # Critical
            mp_percent=50.0,
            is_poisoned=False,
            is_engaged=True,  # Engaged = flee
            distance_to_target=2,
            target_name="Dragon",
            current_location="Dragon Lair",
            xp_per_hour=6000,
            supplies_cost_per_hour=1000,
            balance_per_hour=5000,
            item_count=10,
            capacity_percent=50.0,
            time_at_location_minutes=20
        )
        
        decision = logic.decide_action_heuristic(state)
        
        assert decision.action.value == "flee"
        assert decision.priority == 10  # Highest priority
    
    def test_heuristic_decision_heal(self):
        """Test healing decision."""
        logic = PromptLogic(use_llm=False)
        
        state = GameState(
            hp_percent=50.0,  # Below 60% threshold
            mp_percent=80.0,
            is_poisoned=False,
            is_engaged=False,
            distance_to_target=None,
            target_name=None,
            current_location="Camp",
            xp_per_hour=0,
            supplies_cost_per_hour=0,
            balance_per_hour=0,
            item_count=5,
            capacity_percent=25.0,
            time_at_location_minutes=5
        )
        
        decision = logic.decide_action_heuristic(state)
        
        assert decision.action.value == "heal"
        assert "spell" in decision.parameters


# ─── State Manager Tests ────────────────────────────────────────────────

class TestStateManager:
    
    def test_state_manager_init(self):
        """Test state manager initialization."""
        sm = StateManager(initial_level=50)
        
        assert sm.player.level == 50
        assert sm.player.hp_percent == 100.0
        assert not sm.target.is_valid
    
    def test_player_state_update(self):
        """Test player state update."""
        sm = StateManager()
        
        sm.update_player_state(
            x=1000, y=2000, z=7,
            hp_percent=75.0,
            mp_percent=85.0,
            is_poisoned=True
        )
        
        assert sm.player.x == 1000
        assert sm.player.y == 2000
        assert sm.player.hp_percent == 75.0
        assert sm.player.is_poisoned
    
    def test_target_update(self):
        """Test target update."""
        sm = StateManager()
        
        sm.update_target(
            name="Wasp",
            x=1010,
            y=2010,
            distance=3,
            is_engaged=True
        )
        
        assert sm.target.name == "Wasp"
        assert sm.target.distance == 3
        assert sm.target.is_engaged
    
    def test_location_metrics(self):
        """Test location metrics tracking."""
        sm = StateManager()
        
        sm.start_location("Wasp Cave")
        sm.record_monster_kill(xp_gain=1000, loot_value=500.0)
        sm.record_supply_cost(50.0)
        
        metrics = sm.location_metrics
        assert metrics.location_name == "Wasp Cave"
        assert metrics.monsters_killed == 1
        assert metrics.experience_gained == 1000
        assert metrics.loot_value == 500.0
        assert metrics.supplies_cost == 50.0
    
    def test_game_state_snapshot(self):
        """Test game state snapshot for prompts."""
        sm = StateManager()
        sm.update_player_state(1000, 2000, 7, 75.0, 80.0)
        sm.update_target("Wasp", 1010, 2010, 3, is_engaged=True)
        sm.start_location("Wasp Cave")
        
        snapshot = sm.snapshot()
        
        assert isinstance(snapshot, GameState)
        assert snapshot.hp_percent == 75.0
        assert snapshot.target_name == "Wasp"
        assert snapshot.current_location == "Wasp Cave"


# ─── Metrics Tests ──────────────────────────────────────────────────────

class TestMetrics:
    
    def test_metrics_collector_init(self):
        """Test metrics collector initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = MetricsCollector(output_dir=tmpdir)
            
            assert collector.session_id is not None
            assert len(collector.snapshots) == 0
    
    def test_record_snapshot(self):
        """Test recording a metrics snapshot."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = MetricsCollector(output_dir=tmpdir, disable_file_output=True)
            
            snapshot = collector.record_snapshot(
                location="Wasp Cave",
                duration_seconds=3600,
                xp_gained=5000,
                monsters_killed=50,
                loot_value_gold=2500,
                supplies_cost_gold=500,
                player_health_percent=85.0
            )
            
            assert snapshot.location == "Wasp Cave"
            assert snapshot.xp_gained == 5000
            assert snapshot.xp_per_hour == 5000  # 1 hour
            assert len(collector.snapshots) == 1
    
    def test_session_summary(self):
        """Test session summary calculation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = MetricsCollector(output_dir=tmpdir, disable_file_output=True)
            
            # Record multiple snapshots
            collector.record_snapshot(
                location="Wasp Cave",
                duration_seconds=1800,  # 30 min
                xp_gained=2500,
                monsters_killed=25,
                loot_value_gold=1500,
                supplies_cost_gold=300
            )
            
            collector.record_snapshot(
                location="Nomads",
                duration_seconds=1800,
                xp_gained=3000,
                monsters_killed=30,
                loot_value_gold=1800,
                supplies_cost_gold=400
            )
            
            summary = collector.get_session_summary()
            
            assert summary.total_xp == 5500
            assert summary.total_monsters == 55
            assert summary.total_duration_hours == 1.0
            assert len(summary.locations_visited) == 2


# ─── Config Tests ───────────────────────────────────────────────────────

class TestBotConfig:
    
    def test_bot_config_defaults(self):
        """Test default bot configuration."""
        config = BotConfig()
        
        assert config.player_level == 50
        assert config.use_llm is False
        assert config.update_interval_ms == 100
        assert config.critical_health == 25.0
    
    def test_bot_config_custom(self):
        """Test custom bot configuration."""
        config = BotConfig(
            player_level=150,
            use_llm=True,
            llm_model="gpt-4",
            max_health_before_heal=70.0
        )
        
        assert config.player_level == 150
        assert config.use_llm is True
        assert config.llm_model == "gpt-4"
        assert config.max_health_before_heal == 70.0


# ─── Integration Tests ──────────────────────────────────────────────────

class TestIntegration:
    
    def test_decision_loop_heuristic(self):
        """Test full decision loop with heuristic logic."""
        # Setup components
        state = StateManager(initial_level=100)
        logic = PromptLogic(use_llm=False)
        
        # Simulate gameplay
        state.update_player_state(1000, 2000, 7, hp_percent=75, mp_percent=100)
        state.start_location("Wasp Cave")
        
        # Get decision
        game_state = state.snapshot()
        decision = logic.make_decision(game_state)
        
        assert decision is not None
        assert decision.action is not None
        assert 1 <= decision.priority <= 10


# ─── Run tests ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
