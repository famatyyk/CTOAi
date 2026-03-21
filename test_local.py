#!/usr/bin/env python3
"""
Local Testing Script - Test Bot Locally (Desktop)

This script allows you to test the bot locally with:
  - Screenshot capture (mss + PIL fallback)
  - Command execution (pynput keyboard/mouse)
  - Gameplay loops (combat, movement, loot)
  - Interactive mode (like Easybot)
  - AI mode (autonomous with LLM or heuristics)
  - Performance profiling

Usage:
    python test_local.py --mode auto --location "Wasp Cave" --duration 300
    python test_local.py --mode manual  # Interactive control
    python test_local.py --mode test    # Component tests

Prerequisites:
    - Tibia Client running (or Mythibia for testing)
    - Game window titled "Tibia Client" visible
    - Python 3.11+
    - Dependencies: mss, pynput, opencv-python, numpy, PIL
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s"
)
log = logging.getLogger("test_local")


def test_components() -> bool:
    """Test all components can be imported and instantiated."""
    log.info("=" * 60)
    log.info("COMPONENT TEST")
    log.info("=" * 60)
    
    try:
        log.info("Importing screenshot provider...")
        from runner.hybrid_bot.screenshot_provider import ScreenshotProvider
        provider = ScreenshotProvider(window_title="Tibia Client")
        log.info(f"✓ Screenshot provider ready")
        
        log.info("Importing command executor...")
        from runner.hybrid_bot.command_executor import CommandExecutor
        executor = CommandExecutor()
        log.info(f"✓ Command executor ready")
        
        log.info("Importing template library...")
        from runner.hybrid_bot.template_library import TemplateLibrary
        templates = TemplateLibrary()
        templates.load_creatures(["wasp", "cave spider"])
        log.info(f"✓ Template library ready ({len(templates.creatures)} creatures loaded)")
        
        log.info("Importing gameplay engine...")
        from runner.hybrid_bot.gameplay_engine import GameplayEngine, GameplayMode
        engine = GameplayEngine(mode=GameplayMode.AUTO)
        log.info(f"✓ Gameplay engine ready")
        
        log.info("Importing performance profiler...")
        from runner.hybrid_bot.performance_profiler import PerformanceProfiler
        profiler = PerformanceProfiler()
        log.info(f"✓ Performance profiler ready")
        
        log.info("Importing interactive mode...")
        from runner.hybrid_bot.interactive_mode import InteractiveMode
        interactive = InteractiveMode(executor.execute)
        log.info(f"✓ Interactive mode ready")
        
        log.info("")
        log.info("=" * 60)
        log.info("✓ ALL COMPONENTS READY")
        log.info("=" * 60)
        return True
    
    except Exception as e:
        log.error(f"✗ Component test failed: {e}", exc_info=True)
        return False


async def test_screenshot_capture(duration_sec: int = 5) -> bool:
    """Test screenshot capture for N seconds."""
    log.info("=" * 60)
    log.info("SCREENSHOT CAPTURE TEST")
    log.info("=" * 60)
    
    try:
        from runner.hybrid_bot.screenshot_provider import ScreenshotProvider
        from runner.hybrid_bot.performance_profiler import PerformanceProfiler
        
        provider = ScreenshotProvider(window_title="Tibia Client")
        profiler = PerformanceProfiler()
        
        start_time = time.time()
        capture_count = 0
        
        while time.time() - start_time < duration_sec:
            with profiler.measure("capture"):
                frame = provider.capture()
            
            if frame is not None:
                capture_count += 1
                log.debug(f"Captured frame {capture_count} ({frame.shape})")
            else:
                log.warning("Failed to capture frame")
            
            profiler.record_snapshot()
            await asyncio.sleep(0.05)  # 20 Hz sampling
        
        log.info("")
        log.info(profiler.print_report())
        
        elapsed = time.time() - start_time
        fps = capture_count / elapsed
        log.info(f"Captured {capture_count} frames in {elapsed:.1f}s = {fps:.1f} FPS")
        
        return True
    
    except Exception as e:
        log.error(f"Screenshot capture test failed: {e}", exc_info=True)
        return False


async def test_command_execution() -> bool:
    """Test command execution."""
    log.info("=" * 60)
    log.info("COMMAND EXECUTION TEST")
    log.info("=" * 60)
    
    try:
        from runner.hybrid_bot.command_executor import CommandExecutor
        
        executor = CommandExecutor()
        
        # Test a few commands
        test_commands = [
            ("numpad 8", "Move north"),
            ("say hello", "Send chat message"),
            ("shift+rightclick", "Attack"),
        ]
        
        for cmd, description in test_commands:
            log.info(f"Executing: {description}")
            executor.execute(cmd)
            await asyncio.sleep(0.2)
        
        log.info("")
        log.info("✓ Command execution test passed")
        return True
    
    except Exception as e:
        log.error(f"Command execution test failed: {e}", exc_info=True)
        return False


async def run_autonomous(
    duration_sec: int = 300,
    use_llm: bool = False,
    location: str = "Wasp Cave"
) -> bool:
    """Run bot in autonomous mode."""
    log.info("=" * 60)
    log.info("AUTONOMOUS BOT TEST")
    log.info("=" * 60)
    log.info(f"Duration: {duration_sec}s")
    log.info(f"Location: {location}")
    log.info(f"LLM: {'Yes' if use_llm else 'Heuristics'}")
    log.info("")
    
    try:
        from runner.hybrid_bot import BotConfig, HybridBotRunner
        from runner.hybrid_bot.screenshot_provider import ScreenshotProvider
        from runner.hybrid_bot.command_executor import CommandExecutor
        
        # Configure bot
        config = BotConfig(
            player_level=50,
            use_llm=use_llm,
            max_health_before_heal=60.0,
            critical_health=25.0,
            update_interval_ms=100,
        )
        
        # Initialize components
        provider = ScreenshotProvider(window_title="Tibia Client")
        executor = CommandExecutor()
        
        # Create and run bot
        bot = HybridBotRunner(
            config=config,
            screenshot_provider=provider,
            command_executor=executor,
        )
        
        bot.start_hunting_location(location)
        
        # Run for duration or until interrupted
        start_time = time.time()
        try:
            while time.time() - start_time < duration_sec:
                await bot._tick()
                await asyncio.sleep(config.update_interval_ms / 1000.0)
        except KeyboardInterrupt:
            log.info("Bot interrupted by user")
        
        bot.stop()
        return True
    
    except Exception as e:
        log.error(f"Autonomous bot test failed: {e}", exc_info=True)
        return False


async def run_interactive() -> bool:
    """Run bot in interactive mode (like Easybot)."""
    log.info("=" * 60)
    log.info("INTERACTIVE BOT TEST")
    log.info("=" * 60)
    log.info("Use keyboard to control bot:")
    log.info("  CTRL+A: Toggle auto-attack")
    log.info("  CTRL+H: Heal")
    log.info("  Arrow Keys: Move")
    log.info("  CTRL+P: Pause")
    log.info("  CTRL+Q: Quit")
    log.info("")
    
    try:
        from runner.hybrid_bot.command_executor import CommandExecutor
        from runner.hybrid_bot.interactive_mode import InteractiveMode
        
        executor = CommandExecutor()
        interactive = InteractiveMode(executor.execute)
        
        await interactive.run()
        return True
    
    except Exception as e:
        log.error(f"Interactive mode test failed: {e}", exc_info=True)
        return False


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Local Bot Testing - Test all components locally",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Component test
  python test_local.py --mode test
  
  # Screenshot capture test
  python test_local.py --mode capture --duration 10
  
  # Autonomous hunting (10 minutes)
  python test_local.py --mode auto --duration 600 --location "Wasp Cave"
  
  # Manual control (like Easybot)
  python test_local.py --mode manual
  
  # With LLM decisions (requires OPENAI_API_KEY)
  python test_local.py --mode auto --use-llm --duration 300
        """,
    )
    
    parser.add_argument(
        "--mode",
        choices=["test", "capture", "commands", "auto", "manual"],
        default="test",
        help="Test mode to run"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=300,
        help="Duration in seconds (for capture/auto modes)"
    )
    parser.add_argument(
        "--location",
        default="Wasp Cave",
        help="Hunting location (for auto mode)"
    )
    parser.add_argument(
        "--use-llm",
        action="store_true",
        help="Use LLM for decisions (requires OPENAI_API_KEY)"
    )
    
    args = parser.parse_args()
    
    try:
        # Always test components first
        if not test_components():
            return 1
        
        # Run selected mode
        if args.mode == "test":
            pass  # Already ran component tests
        
        elif args.mode == "capture":
            result = asyncio.run(test_screenshot_capture(args.duration))
            if not result:
                return 1
        
        elif args.mode == "commands":
            result = asyncio.run(test_command_execution())
            if not result:
                return 1
        
        elif args.mode == "auto":
            result = asyncio.run(
                run_autonomous(
                    duration_sec=args.duration,
                    use_llm=args.use_llm,
                    location=args.location
                )
            )
            if not result:
                return 1
        
        elif args.mode == "manual":
            result = asyncio.run(run_interactive())
            if not result:
                return 1
        
        log.info("")
        log.info("=" * 60)
        log.info("✓ TEST COMPLETED SUCCESSFULLY")
        log.info("=" * 60)
        return 0
    
    except KeyboardInterrupt:
        log.info("Test interrupted by user")
        return 0
    except Exception as e:
        log.error(f"Test failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
