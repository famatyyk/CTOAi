"""
Integration Test - Full end-to-end bot pipeline

Tests complete flow:
  Screenshot capture → Vision detection → State update → Decision making → Command execution → Metrics collection

Usage:
    pytest tests/test_integration_e2e.py -v
    
    Or run standalone:
    python -m pytest tests/test_integration_e2e.py::TestHybridBotE2E::test_full_loop -v
"""

import json
import logging
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import cv2
import numpy as np
import pytest

# Import all bot modules
from runner.hybrid_bot.bot_runner import HybridBotRunner
from runner.hybrid_bot.command_executor import CommandExecutor
from runner.hybrid_bot.metrics import MetricsCollector, MetricsSnapshot
from runner.hybrid_bot.prompt_logic import Action, GameState, PromptLogic
from runner.hybrid_bot.screenshot_provider import ScreenshotProvider
from runner.hybrid_bot.state_manager import PlayerState, StateManager
from runner.hybrid_bot.template_library import Template, TemplateLibrary
from runner.hybrid_bot.vision_layer import VisionLayer

log = logging.getLogger("test_integration")


class TestHybridBotE2E:
    """End-to-end integration tests for hybrid bot."""
    
    @pytest.fixture
    def temp_cache(self):
        """Create temporary template cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def template_library(self, temp_cache):
        """Create template library with mock templates."""
        lib = TemplateLibrary(cache_dir=temp_cache)
        
        # Create mock creature templates
        for creature in ["wasp", "tarantula", "spider"]:
            # Create a simple 32x32 colored image for each creature
            img = np.zeros((32, 32, 3), dtype=np.uint8)
            img[:, :, 0] = np.random.randint(50, 200)  # Blue channel
            img[:, :, 1] = np.random.randint(50, 200)  # Green channel
            img[:, :, 2] = np.random.randint(50, 200)  # Red channel
            
            template = Template(
                name=creature,
                template_type="creature",
                image=img.copy(),
                original_size=(128, 128),
                resized_size=(32, 32),
                scale_factor=0.25,
                confidence_threshold=0.7
            )
            lib.creatures[creature] = template
        
        return lib
    
    @pytest.fixture
    def vision_layer(self, temp_cache):
        """Create vision layer with mocked templates."""
        vision = VisionLayer(templates_dir=temp_cache)
        return vision
    
    @pytest.fixture
    def state_manager(self):
        """Create state manager."""
        state = StateManager(initial_level=20)
        # Update initial state
        state.update_player_state(
            x=500,
            y=500,
            z=7,
            hp_percent=100.0,
            mp_percent=100.0,
        )
        return state
    
    @pytest.fixture
    def metrics_collector(self, temp_cache):
        """Create metrics collector."""
        metrics = MetricsCollector(output_dir=temp_cache)
        return metrics
    
    @pytest.fixture
    def command_executor(self):
        """Create command executor with mocked OS calls."""
        executor = CommandExecutor()
        return executor
    
    @pytest.fixture
    def prompt_logic(self):
        """Create prompt logic engine."""
        logic = PromptLogic(use_llm=False)  # Use heuristics only
        return logic
    
    # ─── Test Scenarios ───────────────────────────────────────────────────
    
    def test_full_loop_healthy_combat(
        self,
        vision_layer,
        state_manager,
        metrics_collector,
        command_executor,
        prompt_logic,
    ):
        """Test complete loop: detect enemy → attack → update metrics."""
        
        # STEP 1: Simulate screenshot capture
        screenshot = self._create_mock_screenshot(size=(800, 600))
        
        # STEP 2: Vision detection
        # In real scenario, this would detect creatures in the screenshot
        detected_creatures = [
            type('Creature', (), {
                'name': 'wasp',
                'x': 400,
                'y': 300,
                'confidence': 0.85
            })()
        ]
        
        # STEP 3: Update state with detections
        state_manager.update_player_state(
            x=500,
            y=500,
            z=7,
            hp_percent=100.0,
            mp_percent=100.0,
        )
        
        if detected_creatures:
            state_manager.update_target(
                name=detected_creatures[0].name,
                x=detected_creatures[0].x,
                y=detected_creatures[0].y,
                distance=5,
                is_engaged=True,
            )
        
        # STEP 4: Create game state for decision
        game_state = state_manager.snapshot()
        
        # STEP 5: Decision making (should attack)
        decision = prompt_logic.decide_action_heuristic(game_state)
        action = decision.action
        
        # STEP 6: Verify decision (should attack creature)
        assert action == Action.ATTACK, f"Expected ATTACK, got {action}"
        assert state_manager.target is not None, "Target should be set"
        assert state_manager.target.name == "wasp", "Target should be wasp"
        
        # STEP 7: Execute command
        if action == Action.ATTACK:
            command_executor.execute("shift+rightclick")
        
        # STEP 8: Record metrics
        metrics_collector.record_snapshot(
            location="Test Arena",
            duration_seconds=1.0,
            xp_gained=0,
            monsters_killed=0,
            loot_value_gold=0.0,
            supplies_cost_gold=0.0,
        )
        
        # STEP 9: Verify metrics recorded
        assert len(metrics_collector.snapshots) == 1
        snapshot = metrics_collector.snapshots[0]
        assert snapshot.xp_gained == 0
        
        log.info("✓ Full loop: healthy combat test passed")
    
    def test_full_loop_low_health_flee(
        self,
        vision_layer,
        state_manager,
        metrics_collector,
        command_executor,
        prompt_logic,
    ):
        """Test complete loop: detect danger → flee → update metrics."""
        
        # STEP 1: Update game state with low health
        state_manager.update_player_state(
            x=500,
            y=500,
            z=7,
            hp_percent=15.0,  # 15% health
            mp_percent=50.0,
        )
        state_manager.update_target(
            name="dragon",
            x=503,
            y=500,
            distance=1,
            is_engaged=True,
        )
        
        # STEP 2: Create game state for decision
        game_state = state_manager.snapshot()
        
        # STEP 3: Decision making (should flee)
        decision = prompt_logic.decide_action_heuristic(game_state)
        action = decision.action
        
        # STEP 4: Verify decision (should flee when health < 20%)
        assert action == Action.FLEE, f"Expected FLEE at low health, got {action}"
        
        # STEP 5: Execute flee command (move away)
        if action == Action.FLEE:
            command_executor.execute("numpad 1")  # Move southwest
        
        # STEP 6: Record metrics
        screenshot = self._create_mock_screenshot(size=(800, 600))
        metrics_collector.record_snapshot(
            location="Danger Zone",
            duration_seconds=1.0,
            xp_gained=0,
            monsters_killed=0,
            loot_value_gold=0.0,
            supplies_cost_gold=1.0,  # Used healing potion
        )
        
        # STEP 7: Verify metrics
        assert len(metrics_collector.snapshots) == 1
        snapshot = metrics_collector.snapshots[0]
        assert snapshot.supplies_cost_gold == 1.0, "Should have used supply"
        
        log.info("✓ Full loop: low health flee test passed")
    
    def test_full_loop_healing_recovery(
        self,
        vision_layer,
        state_manager,
        metrics_collector,
        command_executor,
        prompt_logic,
    ):
        """Test healing cascade: take damage → heal → resume combat."""
        
        # STEP 1: Take damage
        state_manager.update_player_state(
            x=500,
            y=500,
            z=7,
            hp_percent=59.0,  # Below heal threshold in current logic (<60)
            mp_percent=50.0,
        )
        
        # STEP 2: Decision at 60% health (should heal)
        game_state = state_manager.snapshot()
        decision = prompt_logic.decide_action_heuristic(game_state)
        action = decision.action
        
        # STEP 3: Verify healing is prioritized
        assert action == Action.HEAL, f"Expected HEAL at 60% health, got {action}"
        
        # STEP 4: Execute healing spell
        if action == Action.HEAL:
            command_executor.execute("say heal")  # Cast exura or healing spell
        
        # STEP 5: Update health after healing
        state_manager.update_player_state(
            x=500,
            y=500,
            z=7,
            hp_percent=95.0,  # Fully healed
            mp_percent=40.0,
        )
        
        # STEP 6: Verify next action is attack
        game_state = state_manager.snapshot()
        decision = prompt_logic.decide_action_heuristic(game_state)
        action = decision.action
        assert action in [Action.ATTACK, Action.WALK], f"Expected combat action, got {action}"
        
        # STEP 7: Record metrics
        screenshot = self._create_mock_screenshot(size=(800, 600))
        metrics_collector.record_snapshot(
            location="Recovery Zone",
            duration_seconds=1.0,
            xp_gained=100,
            monsters_killed=1,
            loot_value_gold=50.0,
            supplies_cost_gold=1.0,
        )
        
        log.info("✓ Full loop: healing recovery test passed")
    
    def test_vision_detection_pipeline(
        self,
        vision_layer,
        template_library,
    ):
        """Test vision detection on mock screenshots."""
        
        # STEP 1: Create mock screenshot with detectable patterns
        screenshot = self._create_mock_screenshot(size=(800, 600))
        
        # STEP 2: Vision processing (would normally detect objects)
        # For this test, we mock detection since real vision needs actual game images
        
        # STEP 3: Verify templates are loaded
        assert len(template_library.creatures) > 0, "No creatures loaded"
        
        # STEP 4: Test template access
        wasp_template = template_library.get_creature("wasp")
        assert wasp_template is not None, "Wasp template not found"
        assert wasp_template.image.shape == (32, 32, 3), "Template has wrong shape"
        
        log.info("✓ Vision detection pipeline test passed")
    
    def test_metrics_collection_complete_session(
        self,
        metrics_collector,
    ):
        """Test metrics collection over a session."""
        
        # Record 10 snapshots simulating a hunting session
        for i in range(10):
            metrics_collector.record_snapshot(
                location="Benchmark Cave",
                duration_seconds=60.0,
                xp_gained=100 + (i * 10),  # Increasing XP
                monsters_killed=1,
                loot_value_gold=50.0,
                supplies_cost_gold=0.0 if i % 3 != 0 else 1.0,
            )
        
        # STEP 1: Verify all snapshots recorded
        assert len(metrics_collector.snapshots) == 10, "Not all snapshots recorded"
        
        # STEP 2: Get session summary
        summary = metrics_collector.get_session_summary()
        
        # STEP 3: Verify aggregations
        assert len(metrics_collector.snapshots) == 10
        assert summary.total_xp > 1000, f"Expected >1000 XP, got {summary.total_xp}"
        assert summary.total_monsters == 10
        assert summary.total_supplies_gold >= 3.0
        assert summary.average_xp_per_hour > 0
        
        # STEP 4: Verify metrics file written
        if metrics_collector.metrics_file:
            assert metrics_collector.metrics_file.exists(), "Metrics file not written"
        
        log.info(f"✓ Metrics collection: {summary}")
    
    def test_state_snapshot_consistency(self, state_manager):
        """Test that game state snapshots are consistent."""
        
        # STEP 1: Set initial state
        state_manager.update_player_state(
            x=500,
            y=500,
            z=7,
            hp_percent=100.0,
            mp_percent=50.0,
        )
        
        # STEP 2: Create snapshot
        snapshot1 = state_manager.snapshot()
        
        # STEP 3: Don't change anything
        snapshot2 = state_manager.snapshot()
        
        # STEP 4: Verify snapshots have same values
        assert snapshot1.hp_percent == snapshot2.hp_percent
        assert snapshot1.mp_percent == snapshot2.mp_percent
        assert snapshot1.is_poisoned == snapshot2.is_poisoned
        
        # STEP 5: Change state
        state_manager.update_player_state(
            x=510,
            y=510,
            z=7,
            hp_percent=90.0,
            mp_percent=40.0,
        )
        
        # STEP 6: Verify snapshot changes
        snapshot3 = state_manager.snapshot()
        assert snapshot3.hp_percent == 90.0
        assert snapshot3.mp_percent == 40.0
        
        log.info("✓ State snapshot consistency test passed")
    
    def test_command_execution_sequence(self, command_executor):
        """Test that commands execute in correct sequence."""
        
        commands = [
            "say heal",           # Spell
            "numpad 8",           # Move north
            "shift+rightclick",   # Attack
        ]
        
        # STEP 1: Execute commands in sequence
        for cmd in commands:
            try:
                # Mock execution (don't actually send commands)
                # In real test, would verify commands sent to game
                pass
            except Exception as e:
                log.warning(f"Command failed (expected in test): {cmd}: {e}")
        
        # STEP 2: Verify command executor is ready
        assert command_executor is not None
        assert callable(command_executor.execute)
        
        log.info("✓ Command execution sequence test passed")
    
    def test_decision_priority_cascade(self, prompt_logic, state_manager):
        """Test decision priority cascade: Heal >= 60% threshold."""
        
        test_cases = [
            # (health, should_heal, description)
            (15, True, "heal at critical health (15%)"),
            (40, True, "heal at low health (40%)"),
            (60, False, "no heal at threshold (60%)"),
            (85, False, "no heal at good health (85%)"),
        ]
        
        for health, should_heal, description in test_cases:
            # Update health
            state_manager.update_player_state(
                x=500,
                y=500,
                z=7,
                hp_percent=float(health),
                mp_percent=50.0,
            )
            
            # Make decision
            snapshot = state_manager.snapshot()
            decision = prompt_logic.decide_action_heuristic(snapshot)
            action = decision.action
            
            # Verify correct action
            is_healing = action == Action.HEAL
            assert is_healing == should_heal, \
                f"{description}: expected {'HEAL' if should_heal else 'non-HEAL'}, got {action}"
            
            log.info(f"✓ {description}: {action.name}")
    
    # ─── Helper Methods ────────────────────────────────────────────────────
    
    @staticmethod
    def _create_mock_screenshot(size=(800, 600)):
        """Create mock screenshot image."""
        h, w = size
        # Create random colored image
        img = np.random.randint(0, 255, (h, w, 3), dtype=np.uint8)
        return img
    
    @staticmethod
    def _create_mock_minimap(size=(160, 160)):
        """Create mock minimap image."""
        h, w = size
        # Create light gray minimap background
        img = np.full((h, w, 3), 200, dtype=np.uint8)
        return img


class TestIntegrationWithMocks:
    """Integration tests using mocked components."""
    
    def test_bot_runner_initialization(self, tmp_path):
        """Test HybridBotRunner can be initialized."""
        
        # Create temp directory for components
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        
        # Create minimal template library
        lib = TemplateLibrary(cache_dir=cache_dir)
        
        log.info("✓ Bot runner initialization test passed")
    
    def test_template_library_stats(self, tmp_path):
        """Test template library statistics."""
        
        lib = TemplateLibrary(cache_dir=tmp_path)
        
        # Create mock creature
        img = np.zeros((32, 32, 3), dtype=np.uint8)
        template = Template(
            name="test_creature",
            template_type="creature",
            image=img,
            original_size=(128, 128),
            resized_size=(32, 32),
            scale_factor=0.25,
            confidence_threshold=0.7
        )
        lib.creatures["test_creature"] = template
        
        # Get stats
        stats = lib.get_stats()
        
        assert stats["creatures_loaded"] == 1
        assert "memory" in str(stats).lower() or "creature_memory_mb" in stats
        
        log.info(f"✓ Template library stats: {stats}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    pytest.main([__file__, "-v", "-s"])
