"""AGENT 7: Looting action."""
import time

try:
    import pyautogui
    _GUI_AVAILABLE = True
except Exception:
    _GUI_AVAILABLE = False

LOOT_HOTKEY = "f3"


def loot_corpse() -> None:
    """Open corpse via hotkey (Shift+click in real Tibia — hotkey approach for OTS)."""
    if not _GUI_AVAILABLE:
        return
    pyautogui.press(LOOT_HOTKEY)
    time.sleep(0.2)
