"""AGENT 7: Combat actions — humanized with Agent 5 pauses."""
from __future__ import annotations

from ..safety.humanizer import combat_pause, potion_delay, think_pause
from .input_backend import is_available, press

# Hotkeys loaded from items.json if available, else defaults
try:
    from ..data.game_data import load_items as _load_items
    _hotkeys = _load_items().get("equipment_consumables", {}).get("hotkeys", {})
except Exception:
    _hotkeys = {}

HP_POTION_HOTKEY      = _hotkeys.get("hp_potion", "f1")
MP_POTION_HOTKEY      = _hotkeys.get("mp_potion", "f2")
STRONG_HP_POTION_KEY  = _hotkeys.get("strong_hp_potion", "f3")
ANTIDOTE_KEY          = _hotkeys.get("antidote_potion", "f4")
ATTACK_KEY            = _hotkeys.get("attack_target", "space")


def attack_target() -> None:
    if not is_available():
        return
    think_pause()               # rare hesitation before attacking
    press(ATTACK_KEY)
    combat_pause()              # micro-delay after attack input


def use_hp_potion() -> None:
    if not is_available():
        return
    press(HP_POTION_HOTKEY)
    potion_delay()


def use_strong_hp_potion() -> None:
    if not is_available():
        return
    press(STRONG_HP_POTION_KEY)
    potion_delay()


def use_mp_potion() -> None:
    if not is_available():
        return
    press(MP_POTION_HOTKEY)
    potion_delay()


def use_antidote() -> None:
    if not is_available():
        return
    press(ANTIDOTE_KEY)
    potion_delay()
