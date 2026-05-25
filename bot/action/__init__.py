"""AGENT 7: Action dispatcher."""
from .movement import walk_to, idle_move
from .combat import attack_target, use_hp_potion, use_mp_potion
from .loot import loot_corpse


_ACTION_MAP = {
    "attack":         attack_target,
    "use_hp_potion":  use_hp_potion,
    "use_mp_potion":  use_mp_potion,
    "loot":           loot_corpse,
    "find_monster":   idle_move,
    "flee_to_depot":  lambda: walk_to(0, 0),   # depot coords TBD by Agent 6
    "go_to_depot":    lambda: walk_to(0, 0),
    "idle":           lambda: None,
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
