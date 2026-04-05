"""
Command Executor - Send keyboard/mouse commands to game

Implements game automation using pynput for cross-platform input.

Usage:
    from runner.hybrid_bot.command_executor import CommandExecutor

    executor = CommandExecutor()
    executor.execute("say heal")         # Type spell
    executor.execute("shift+rightclick") # Attack
    executor.execute("numpad 4")         # Walk west
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

try:
    from pynput.keyboard import Key, Controller as KeyboardController
    from pynput.mouse import Button, Controller as MouseController
    HAS_PYNPUT = True
except ImportError:
    class _FallbackKey:
        up = "up"
        down = "down"
        left = "left"
        right = "right"
        enter = "enter"
        shift = "shift"
        ctrl = "ctrl"

    class _FallbackButton:
        right = "right"

    Key = _FallbackKey
    Button = _FallbackButton
    KeyboardController = None
    MouseController = None
    HAS_PYNPUT = False

log = logging.getLogger("hybrid_bot.executor")


class CommandExecutor:
    """
    Execute bot commands (spells, movement, attacks) via keyboard/mouse.

    Supports:
      - Typing spells: "say heal", "say exura gran"
      - Movement: "numpad 4" (walk west), "numpad 2" (walk south), etc.
      - Combat: "shift+rightclick" (attack)
      - Special: "pause" (wait), "reconnect" (logout/login)

    Includes delays to mimic human input and avoid detection.
    """

    # Direction map using arrow keys (when numpad not available)
    # Tibia originally uses numpad, but we map to arrow keys as fallback
    DIRECTION_MAP = {
        "numpad 7": (Key.up, Key.left),        # NW (up + left)
        "numpad 8": Key.up,                     # N
        "numpad 9": (Key.up, Key.right),       # NE (up + right)
        "numpad 4": Key.left,                   # W
        "numpad 6": Key.right,                  # E
        "numpad 1": (Key.down, Key.left),      # SW (down + left)
        "numpad 2": Key.down,                   # S
        "numpad 3": (Key.down, Key.right),     # SE (down + right)
    }

    def __init__(
        self,
        base_delay_ms: float = 50.0,
        typing_delay_ms: float = 50.0,
        enable_delays: bool = True,
    ):
        """
        Initialize command executor.

        Args:
            base_delay_ms: Base delay between actions (milliseconds)
            typing_delay_ms: Delay between typed characters
            enable_delays: If False, no delays (testing mode)
        """
        if not HAS_PYNPUT:
            log.warning("pynput not installed; commands will not execute")

        self.keyboard = KeyboardController() if HAS_PYNPUT else None
        self.mouse = MouseController() if HAS_PYNPUT else None

        self.base_delay = base_delay_ms / 1000.0
        self.typing_delay = typing_delay_ms / 1000.0
        self.enable_delays = enable_delays

        self.command_count = 0
        self.last_command_time = time.time()

    def execute(self, command: str) -> bool:
        """
        Execute a bot command.

        Args:
            command: Command string (e.g., "say heal", "shift+rightclick")

        Returns:
            True if executed, False on error
        """
        if not HAS_PYNPUT or not self.keyboard:
            log.warning(f"Skipping command (pynput unavailable): {command}")
            return False

        try:
            # Apply inter-command delay
            if self.enable_delays:
                self._apply_delay()

            self.command_count += 1

            # Parse and execute command
            if command.startswith("say "):
                spell = command[4:].strip()
                self._type_spell(spell)
                log.debug(f"Cast: {spell}")
                return True

            elif command == "shift+rightclick":
                self._attack_target()
                log.debug("Attack target")
                return True

            elif command in self.DIRECTION_MAP:
                key = self.DIRECTION_MAP[command]
                self._press_key(key)
                log.debug(f"Move: {command}")
                return True

            elif command == "pause":
                self._wait()
                log.debug("Pause")
                return True

            elif command == "reconnect":
                self._reconnect()
                log.debug("Reconnect")
                return True

            else:
                log.warning(f"Unknown command: {command}")
                return False

        except Exception as e:
            log.error(f"Command execution failed ({command}): {e}")
            return False

    async def execute_async(self, command: str) -> bool:
        """Async wrapper for execute()."""
        return await asyncio.to_thread(self.execute, command)

    # ─── Action implementations ────────────────────────────────────────────

    def _type_spell(self, spell_name: str) -> None:
        """Type spell command and press Enter."""
        self.keyboard.type(spell_name)
        if self.enable_delays:
            time.sleep(self.typing_delay)
        self.keyboard.press(Key.enter)
        self.keyboard.release(Key.enter)
        if self.enable_delays:
            time.sleep(self.base_delay)

    def _press_key(self, key) -> None:
        """Press and release a key (or multiple keys for diagonal movement)."""
        # Handle diagonal movement (tuple of keys)
        if isinstance(key, tuple):
            # Press all keys
            for k in key:
                self.keyboard.press(k)
            if self.enable_delays:
                time.sleep(self.base_delay * 0.5)
            # Release all keys
            for k in key:
                self.keyboard.release(k)
        else:
            # Single key
            self.keyboard.press(key)
            if self.enable_delays:
                time.sleep(self.base_delay * 0.5)
            self.keyboard.release(key)

        if self.enable_delays:
            time.sleep(self.base_delay)

    def _attack_target(self) -> None:
        """Shift+right-click to attack current target."""
        # Press Shift
        self.keyboard.press(Key.shift)

        if self.enable_delays:
            time.sleep(self.base_delay * 0.3)

        # Right-click (mouse)
        self.mouse.press(Button.right)

        if self.enable_delays:
            time.sleep(self.base_delay * 0.3)

        self.mouse.release(Button.right)

        # Release Shift
        self.keyboard.release(Key.shift)

        if self.enable_delays:
            time.sleep(self.base_delay)

    def _wait(self) -> None:
        """Pause bot for a short time."""
        if self.enable_delays:
            time.sleep(self.base_delay * 2)

    def _reconnect(self) -> None:
        """Logout and reconnect to game."""
        # Logout hotkey (usually Ctrl+L in Tibia)
        self.keyboard.press(Key.ctrl)
        if self.enable_delays:
            time.sleep(0.05)
        logout_key = getattr(Key, "l", "l")
        self.keyboard.press(logout_key)
        self.keyboard.release(logout_key)
        self.keyboard.release(Key.ctrl)

        # Wait for logout
        if self.enable_delays:
            time.sleep(3)

        # Click "Connect" button or press Enter
        self.keyboard.press(Key.enter)
        self.keyboard.release(Key.enter)

    def _apply_delay(self) -> None:
        """Respect minimum delay between commands."""
        elapsed = time.time() - self.last_command_time
        if elapsed < self.base_delay:
            time.sleep(self.base_delay - elapsed)
        self.last_command_time = time.time()

    # ─── Advanced actions ──────────────────────────────────────────────────

    def set_delaying(self, enable: bool) -> None:
        """Enable/disable inter-command delays (for debugging)."""
        self.enable_delays = enable
        log.info(f"Delays: {'enabled' if enable else 'disabled'}")

    def get_stats(self) -> dict:
        """Get execution statistics."""
        return {
            "commands_executed": self.command_count,
            "last_command_time": self.last_command_time,
            "delays_enabled": self.enable_delays,
        }


# ─── Batch command executor ────────────────────────────────────────────────

class BatchCommandExecutor:
    """
    Execute a sequence of commands with timing control.

    Usage:
        batch = BatchCommandExecutor()
        batch.add("say exura")
        batch.add("wait", duration_ms=1000)
        batch.add("numpad 4")
        await batch.execute()
    """

    def __init__(self, executor: Optional[CommandExecutor] = None):
        """Initialize batch executor."""
        self.executor = executor or CommandExecutor()
        self.commands: list[tuple[str, float]] = []

    def add(self, command: str, duration_ms: float = 0) -> None:
        """
        Add command to batch.

        Args:
            command: Command to execute
            duration_ms: Additional wait after command (for timing-sensitive sequences)
        """
        self.commands.append((command, duration_ms / 1000.0))

    async def execute(self) -> bool:
        """Execute all commands in sequence."""
        for command, duration in self.commands:
            success = await self.executor.execute_async(command)
            if not success:
                log.warning(f"Batch execution stopped at: {command}")
                return False

            if duration > 0:
                await asyncio.sleep(duration)

        return True

    def clear(self) -> None:
        """Clear batch."""
        self.commands.clear()


# ─── Example usage ────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    if not HAS_PYNPUT:
        print("pynput not installed. Install with: pip install pynput")
        exit(1)

    executor = CommandExecutor(enable_delays=True)

    print("Testing command executor (press Ctrl+C to cancel)...")
    print()

    try:
        # Test spell casting
        print("1. Casting 'heal' spell in 3 seconds...")
        time.sleep(3)
        executor.execute("say heal")

        # Test movement
        print("2. Moving north in 3 seconds...")
        time.sleep(3)
        executor.execute("numpad 8")

        # Test batch
        print("3. Executing batch (spell -> wait -> move) in 3 seconds...")
        time.sleep(3)

        batch = BatchCommandExecutor(executor)
        batch.add("say exura")
        batch.add("wait", duration_ms=500)
        batch.add("numpad 6")

        asyncio.run(batch.execute())

        print("\nExecution complete!")
        print(f"Stats: {executor.get_stats()}")

    except KeyboardInterrupt:
        print("\nCancelled by user")
