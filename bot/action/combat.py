"""AGENT 7: Combat actions."""
import time

try:
    import pyautogui
    _GUI_AVAILABLE = True
except Exception:
    _GUI_AVAILABLE = False

HP_POTION_HOTKEY = "f1"
MP_POTION_HOTKEY = "f2"
ATTACK_KEY       = "f6"   # Tibia: attack selected target


def attack_target() -> None:
    if not _GUI_AVAILABLE:
        return
    pyautogui.press(ATTACK_KEY)
    time.sleep(0.05)


def use_hp_potion() -> None:
    if not _GUI_AVAILABLE:
        return
    pyautogui.press(HP_POTION_HOTKEY)
    time.sleep(0.1)


def use_mp_potion() -> None:
    if not _GUI_AVAILABLE:
        return
    pyautogui.press(MP_POTION_HOTKEY)
    time.sleep(0.1)
