"""
Interactive Mode - Manual Bot Control (like Easybot)

Allows player to manually control the bot using keyboard shortcuts
while monitoring game state and collecting metrics.

Keyboard Shortcuts (for Tibia client):
  - CTRL+A: Auto-attack toggle
  - CTRL+H: Heal
  - CTRL+F: Flee
  - CTRL+W: Follow waypoints
  - CTRL+S: Screenshot (save to disk)
  - CTRL+P: Pause bot
  - CTRL+Q: Quit bot
  - Arrow Keys: Manual movement
  - Number Pad: Quick spells (1-9)
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Callable

log = logging.getLogger("hybrid_bot.interactive")


class InteractiveCommand(Enum):
    """Commands available in interactive mode."""
    TOGGLE_AUTO_ATTACK = "toggle_auto_attack"
    HEAL = "heal"
    FLEE = "flee"
    FOLLOW_WAYPOINTS = "follow_waypoints"
    SAVE_SCREENSHOT = "save_screenshot"
    PAUSE = "pause"
    RESUME = "resume"
    QUIT = "quit"
    MOVE_NORTH = "move_north"
    MOVE_SOUTH = "move_south"
    MOVE_EAST = "move_east"
    MOVE_WEST = "move_west"
    SPELL_1 = "spell_1"
    SPELL_2 = "spell_2"
    SPELL_3 = "spell_3"
    STATUS = "status"


@dataclass
class InteractiveState:
    """Current interactive mode state."""
    auto_attack_enabled: bool = False
    waypoint_following: bool = False
    paused: bool = False
    last_activity_time: float = 0.0
    
    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity_time = time.time()


class KeyboardListener:
    """
    Unified keyboard input listener.
    
    Can use pynput or Windows hooks depending on availability.
    """
    
    def __init__(self):
        """Initialize keyboard listener."""
        self.listeners = []
        self.command_queue: asyncio.Queue = None
    
    async def start(self, command_queue: asyncio.Queue) -> None:
        """
        Start listening for keyboard input.
        
        Args:
            command_queue: Queue to push commands to
        """
        self.command_queue = command_queue
        
        try:
            from pynput import keyboard
            
            def on_key_press(key):
                """Handle key press."""
                command = self._map_key_to_command(key)
                if command:
                    try:
                        asyncio.create_task(command_queue.put(command))
                    except RuntimeError:
                        pass
            
            listener = keyboard.Listener(on_press=on_key_press)
            listener.start()
            self.listeners.append(listener)
            
            log.info("Keyboard listener started")
        
        except ImportError:
            log.warning("pynput not available for keyboard listening")
    
    def _map_key_to_command(self, key) -> Optional[InteractiveCommand]:
        """Map keyboard key to command."""
        try:
            from pynput.keyboard import Key
            
            # Try to get character
            try:
                char = key.char
                if char == 'w':
                    return InteractiveCommand.FOLLOW_WAYPOINTS
                elif char == 's':
                    return InteractiveCommand.SAVE_SCREENSHOT
                elif char == 'p':
                    return InteractiveCommand.PAUSE
                elif char == 'q':
                    return InteractiveCommand.QUIT
            except AttributeError:
                pass
            
            # Try special keys
            if key == Key.ctrl_l:
                return InteractiveCommand.TOGGLE_AUTO_ATTACK
            elif key == Key.up:
                return InteractiveCommand.MOVE_NORTH
            elif key == Key.down:
                return InteractiveCommand.MOVE_SOUTH
            elif key == Key.left:
                return InteractiveCommand.MOVE_WEST
            elif key == Key.right:
                return InteractiveCommand.MOVE_EAST
        
        except Exception as e:
            log.debug(f"Key mapping error: {e}")
        
        return None
    
    def stop(self) -> None:
        """Stop all listeners."""
        for listener in self.listeners:
            try:
                listener.stop()
            except Exception as e:
                log.error(f"Error stopping listener: {e}")


class InteractiveMode:
    """
    Interactive bot control (like Easybot).
    
    Player manually controls bot while metrics/state monitoring continues.
    """
    
    def __init__(
        self,
        command_executor: Callable[[str], None],
        screenshot_callback: Optional[Callable[[], None]] = None,
    ):
        """
        Initialize interactive mode.
        
        Args:
            command_executor: Callback to execute game commands
            screenshot_callback: Callback to take screenshot
        """
        self.command_executor = command_executor
        self.screenshot_callback = screenshot_callback
        
        self.state = InteractiveState()
        self.keyboard = KeyboardListener()
        self.command_queue: asyncio.Queue = asyncio.Queue()
        
        self.stats = {
            "commands_executed": 0,
            "heals_cast": 0,
            "spells_cast": 0,
            "flees": 0,
        }
    
    async def run(self) -> None:
        """Run interactive mode event loop."""
        log.info("🎮 Interactive Mode started - use keyboard controls")
        
        await self.keyboard.start(self.command_queue)
        
        try:
            while not self.state.paused:
                try:
                    # Wait for command with timeout
                    command = await asyncio.wait_for(
                        self.command_queue.get(),
                        timeout=0.1
                    )
                    
                    await self._handle_command(command)
                    self.state.update_activity()
                
                except asyncio.TimeoutError:
                    # No command received, do periodic tasks
                    await self._periodic_update()
        
        except KeyboardInterrupt:
            log.info("Interactive mode interrupted")
        finally:
            self.keyboard.stop()
            self._print_session_stats()
    
    async def _handle_command(self, command: InteractiveCommand) -> None:
        """Handle interactive command."""
        try:
            if command == InteractiveCommand.TOGGLE_AUTO_ATTACK:
                self.state.auto_attack_enabled = not self.state.auto_attack_enabled
                status = "ON" if self.state.auto_attack_enabled else "OFF"
                log.info(f"Auto-attack: {status}")
            
            elif command == InteractiveCommand.HEAL:
                self.command_executor("say exura")
                self.stats["heals_cast"] += 1
                log.info("Heal cast")
            
            elif command == InteractiveCommand.FLEE:
                self.command_executor("numpad 4")  # Move west
                self.stats["flees"] += 1
                log.info("Fleeing")
            
            elif command == InteractiveCommand.FOLLOW_WAYPOINTS:
                self.state.waypoint_following = not self.state.waypoint_following
                status = "ON" if self.state.waypoint_following else "OFF"
                log.info(f"Waypoint following: {status}")
            
            elif command == InteractiveCommand.SAVE_SCREENSHOT:
                if self.screenshot_callback:
                    self.screenshot_callback()
                log.info("Screenshot saved")
            
            elif command == InteractiveCommand.PAUSE:
                self.state.paused = True
                log.info("Bot paused")
            
            elif command == InteractiveCommand.RESUME:
                self.state.paused = False
                log.info("Bot resumed")
            
            elif command == InteractiveCommand.QUIT:
                self.state.paused = True
                return
            
            elif command == InteractiveCommand.MOVE_NORTH:
                self.command_executor("numpad 8")
            elif command == InteractiveCommand.MOVE_SOUTH:
                self.command_executor("numpad 2")
            elif command == InteractiveCommand.MOVE_EAST:
                self.command_executor("numpad 6")
            elif command == InteractiveCommand.MOVE_WEST:
                self.command_executor("numpad 4")
            
            elif command == InteractiveCommand.SPELL_1:
                self.command_executor("say exura")
                self.stats["spells_cast"] += 1
            elif command == InteractiveCommand.SPELL_2:
                self.command_executor("say exura gran")
                self.stats["spells_cast"] += 1
            elif command == InteractiveCommand.SPELL_3:
                self.command_executor("say ultimate healing")
                self.stats["spells_cast"] += 1
            
            elif command == InteractiveCommand.STATUS:
                self._print_status()
            
            self.stats["commands_executed"] += 1
        
        except Exception as e:
            log.error(f"Error handling command {command.value}: {e}")
    
    async def _periodic_update(self) -> None:
        """Periodic tasks (every ~100ms)."""
        # Could add auto-healing, auto-mana, etc.
        pass
    
    def _print_status(self) -> None:
        """Print current status."""
        lines = [
            "",
            "╔════════════════════════════════════╗",
            "║     INTERACTIVE MODE STATUS        ║",
            "║════════════════════════════════════║",
            f"║ Auto-Attack: {'ON ' if self.state.auto_attack_enabled else 'OFF'}             ║",
            f"║ Waypoints:   {'ON ' if self.state.waypoint_following else 'OFF'}             ║",
            f"║ Commands:    {self.stats['commands_executed']:,}              ║",
            f"║ Heals:       {self.stats['heals_cast']}              ║",
            f"║ Spells:      {self.stats['spells_cast']}              ║",
            "╚════════════════════════════════════╝",
            "",
        ]
        print("\n".join(lines))
    
    def _print_session_stats(self) -> None:
        """Print final session statistics."""
        elapsed = time.time() - (self.state.last_activity_time or time.time())
        lines = [
            "",
            "=" * 40,
            "INTERACTIVE SESSION STATS",
            "=" * 40,
            f"Session Duration: {elapsed:.1f}s",
            f"Commands Executed: {self.stats['commands_executed']}",
            f"Heals Cast: {self.stats['heals_cast']}",
            f"Spells Cast: {self.stats['spells_cast']}",
            f"Flees: {self.stats['flees']}",
            "=" * 40,
        ]
        print("\n".join(lines))
