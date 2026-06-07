"""AGENT 7: Looting action."""
import time

from .input_backend import is_available, press

LOOT_HOTKEY = "f3"


def loot_corpse() -> None:
    """Open corpse via hotkey (Shift+click in real Tibia — hotkey approach for OTS)."""
    if not is_available():
        return
    press(LOOT_HOTKEY)
    time.sleep(0.2)
