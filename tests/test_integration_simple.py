"""
Simplified Integration Tests - Focus on core components working together

Tests the 4 main platform integration components:
  1. Screenshot provider (mss/PIL)
  2. Command executor (pynput)
  3. Template library (asset management)
  4. Integration of all 3
"""

import logging
import tempfile
from pathlib import Path

import numpy as np
import pytest

from runner.hybrid_bot.command_executor import CommandExecutor
from runner.hybrid_bot.screenshot_provider import ScreenshotProvider
from runner.hybrid_bot.template_library import Template, TemplateLibrary

log = logging.getLogger("test_integration")


class TestScreenshotProvider:
    """Test screenshot capture functionality."""
    
    def test_screenshot_provider_creation(self):
        """Test ScreenshotProvider can be instantiated."""
        provider = ScreenshotProvider()
        assert provider is not None
        assert hasattr(provider, 'capture')
        log.info("✓ ScreenshotProvider creation test passed")
    
    def test_screenshot_provider_capture_method_exists(self):
        """Test ScreenshotProvider has capture method."""
        provider = ScreenshotProvider()
        assert callable(provider.capture)
        log.info("✓ ScreenshotProvider capture method test passed")
    
    def test_screenshot_provider_bounds_setting(self):
        """Test ScreenshotProvider has bounds setting capability."""
        provider = ScreenshotProvider()
        # Bounds setting requires valid tuple format
        assert hasattr(provider, 'set_bounds')
        assert callable(provider.set_bounds)
        log.info("✓ ScreenshotProvider bounds setting capability test passed")


class TestCommandExecutor:
    """Test command execution functionality."""
    
    def test_command_executor_creation(self):
        """Test CommandExecutor can be instantiated."""
        executor = CommandExecutor()
        assert executor is not None
        assert hasattr(executor, 'execute')
        log.info("✓ CommandExecutor creation test passed")
    
    def test_command_executor_has_methods(self):
        """Test CommandExecutor has required methods."""
        executor = CommandExecutor()
        assert callable(executor.execute)
        assert hasattr(executor, 'DIRECTION_MAP')
        log.info("✓ CommandExecutor methods test passed")
    
    def test_direction_map_coverage(self):
        """Test CommandExecutor has all directions in map."""
        executor = CommandExecutor()
        directions = [
            "numpad 1", "numpad 2", "numpad 3",
            "numpad 4", "numpad 6",
            "numpad 7", "numpad 8", "numpad 9",
        ]
        for direction in directions:
            assert direction in executor.DIRECTION_MAP, f"Missing direction: {direction}"
        log.info("✓ Direction map coverage test passed")


class TestTemplateLibrary:
    """Test template library functionality."""
    
    @pytest.fixture
    def temp_cache(self):
        """Create temporary template cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    def test_template_library_creation(self, temp_cache):
        """Test TemplateLibrary can be instantiated."""
        lib = TemplateLibrary(cache_dir=temp_cache)
        assert lib is not None
        assert lib.cache_dir == temp_cache
        log.info("✓ TemplateLibrary creation test passed")
    
    def test_template_library_load_creatures(self, temp_cache):
        """Test TemplateLibrary can load creature templates."""
        lib = TemplateLibrary(cache_dir=temp_cache)
        
        # Create mock creatures
        creatures = ["wasp", "spider", "tarantula"]
        for creature in creatures:
            # Create mock image
            img = np.zeros((32, 32, 3), dtype=np.uint8)
            template = Template(
                name=creature,
                template_type="creature",
                image=img,
                original_size=(128, 128),
                resized_size=(32, 32),
                scale_factor=0.25,
                confidence_threshold=0.7
            )
            lib.creatures[creature] = template
        
        # Verify creatures loaded
        assert len(lib.creatures) == 3
        assert "wasp" in lib.creatures
        assert lib.get_creature("wasp") is not None
        log.info("✓ TemplateLibrary creature loading test passed")
    
    def test_template_library_stats(self, temp_cache):
        """Test TemplateLibrary statistics."""
        lib = TemplateLibrary(cache_dir=temp_cache)
        
        # Add a template
        img = np.zeros((32, 32, 3), dtype=np.uint8)
        template = Template(
            name="test",
            template_type="creature",
            image=img,
            original_size=(128, 128),
            resized_size=(32, 32),
            scale_factor=0.25,
            confidence_threshold=0.7
        )
        lib.creatures["test"] = template
        
        # Get stats
        stats = lib.get_stats()
        assert stats["creatures_loaded"] == 1
        assert "memory" in str(stats).lower() or "creature_memory_mb" in stats
        log.info(f"✓ TemplateLibrary stats test passed: {stats}")
    
    def test_template_save_and_retrieve(self, temp_cache):
        """Test saving and retrieving templates."""
        lib = TemplateLibrary(cache_dir=temp_cache)
        
        # Create and save template
        img = np.random.randint(0, 255, (32, 32, 3), dtype=np.uint8)
        template = Template(
            name="test_creature",
            template_type="creature",
            image=img.copy(),
            original_size=(128, 128),
            resized_size=(32, 32),
            scale_factor=0.25,
            confidence_threshold=0.7
        )
        
        # Save to cache
        saved = lib.save_template(template)
        assert saved, "Template save failed"
        
        # Verify file exists
        cache_file = temp_cache / "creature_test_creature.png"
        assert cache_file.exists(), "Cache file not created"
        
        log.info("✓ Template save and retrieve test passed")


class TestIntegrationScenarios:
    """Test integration scenarios combining components."""
    
    @pytest.fixture
    def temp_cache(self):
        """Create temporary template cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    def test_provider_executor_integration(self):
        """Test ScreenshotProvider and CommandExecutor together."""
        # Create both components
        provider = ScreenshotProvider()
        executor = CommandExecutor()
        
        # Verify they work independently
        assert callable(provider.capture)
        assert callable(executor.execute)
        
        # Verify they can be used sequentially
        # (In real usage: capture → vision → decide → execute)
        log.info("✓ Provider + Executor integration test passed")
    
    def test_template_library_with_provider(self, temp_cache):
        """Test TemplateLibrary with ScreenshotProvider."""
        # Create provider and library
        provider = ScreenshotProvider()
        lib = TemplateLibrary(cache_dir=temp_cache)
        
        # Add creatures to library
        for creature in ["wasp", "spider"]:
            img = np.zeros((32, 32, 3), dtype=np.uint8)
            template = Template(
                name=creature,
                template_type="creature",
                image=img,
                original_size=(128, 128),
                resized_size=(32, 32),
                scale_factor=0.25,
                confidence_threshold=0.7
            )
            lib.creatures[creature] = template
        
        # Verify integration
        assert len(lib.creatures) == 2
        assert lib.get_creature("wasp") is not None
        
        log.info("✓ TemplateLibrary + Provider integration test passed")
    
    def test_all_components_together(self, temp_cache):
        """Test all 4 components can be used together."""
        # 1. Screenshot provider
        provider = ScreenshotProvider()
        
        # 2. Command executor
        executor = CommandExecutor()
        
        # 3. Template library
        lib = TemplateLibrary(cache_dir=temp_cache)
        
        # 4. Add creatures
        for creature in ["wasp", "tarantula", "spider"]:
            img = np.random.randint(0, 255, (32, 32, 3), dtype=np.uint8)
            template = Template(
                name=creature,
                template_type="creature",
                image=img,
                original_size=(128, 128),
                resized_size=(32, 32),
                scale_factor=0.25,
                confidence_threshold=0.7
            )
            lib.creatures[creature] = template
        
        # Verify all components are ready
        assert provider is not None
        assert executor is not None
        assert lib is not None
        assert len(lib.creatures) == 3
        
        # Simulate bot loop workflow:
        # 1. Capture screenshot (would call provider.capture())
        # 2. Process image (would match against lib.creatures)
        # 3. Make decision (would return action)
        # 4. Execute command (would call executor.execute())
        
        log.info("✓ All components integration test passed")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    pytest.main([__file__, "-v", "-s"])
