"""AGENT 7: Action dispatcher — wires action strings to handler functions."""
from __future__ import annotations
from ..config.runtime_profile import get_bool
from .movement import walk_to, idle_move, auto_follow
from .combat import attack_target, use_hp_potion, use_mp_potion, use_strong_hp_potion
from .loot import loot_corpse
from .spell_rotation import cast_rotation_spell

try:
    from ..decision.hunt_strategy import best_target_from_nearby, next_waypoint
    _STRATEGY_AVAILABLE = True
except Exception:
    _STRATEGY_AVAILABLE = False

# Shared mutable state: current game state reference (set each tick by main loop)
_current_state = None

def set_current_state(state) -> None:
    global _current_state
    _current_state = state

def _select_target() -> None:
    """Pick best nearby monster and initiate attack."""
    if _STRATEGY_AVAILABLE and _current_state is not None:
        target = best_target_from_nearby(_current_state)
        if target:
            attack_target()
            return
    attack_target()


def _attack_with_rotation() -> None:
    """Attack target and rotate profession-aware spellbook."""
    attack_target()
    if _current_state is not None and get_bool("BOT_SPELL_ROTATION_ENABLED", True):
        cast_rotation_spell(int(getattr(_current_state, "level", 1) or 1))

def _follow_route() -> None:
    """Move to next waypoint on the active hunt route."""
    if _STRATEGY_AVAILABLE and _current_state is not None:
        wp = next_waypoint(_current_state.level)
        if wp:
            walk_to(wp[0], wp[1])
            return
    idle_move()

_ACTION_MAP = {
    "attack":                _attack_with_rotation,
    "use_hp_potion":         use_hp_potion,
    "use_strong_hp_potion":  use_strong_hp_potion,
    "use_mp_potion":         use_mp_potion,
    "loot":                  loot_corpse,
    "rotate_spell":          lambda: cast_rotation_spell(int(getattr(_current_state, "level", 1) or 1)) if get_bool("BOT_SPELL_ROTATION_ENABLED", True) else None,
    "auto_follow":           lambda: auto_follow(_current_state),
    "select_target":         _select_target,
    "find_monster":          idle_move,
    "follow_route":          _follow_route,
    "flee_to_depot":         lambda: walk_to(0, 0),
    "go_to_depot":           lambda: walk_to(0, 0),
    "idle":                  lambda: None,
}

def execute_action(action: str) -> str:
    """Execute the named action. Returns result string."""
    fn = _ACTION_MAP.get(action)
    if fn is None:
        return "unknown_action"
    try:
        fn()
        return "ok"
    except Exception as e:
        return f"error:{e}"
