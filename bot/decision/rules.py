"""AGENT 4 / AGENT 7: Priority-based rule engine (Phase 1 AI).

Rules now use level-aware thresholds from hunt_strategy (Agent 6 data).
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable

from ..perception.state import GameState

try:
    from .hunt_strategy import get_potion_thresholds
    _thresh = get_potion_thresholds()
except Exception:
    _thresh = {}

_HP_CRITICAL  = _thresh.get("critical_flee_at_pct", 10)
_HP_POTION    = _thresh.get("use_hp_potion_at_pct", 30)
_MP_POTION    = _thresh.get("use_mp_potion_at_pct", 20)
_HP_FLEE      = _thresh.get("flee_at_pct", 15)


@dataclass
class Rule:
    name: str
    priority: int          # lower = higher priority
    condition: Callable[[GameState], bool]
    action: str


RULES: list[Rule] = [
    Rule("critical_hp",    1, lambda s: s.hp_pct < _HP_CRITICAL,  "flee_to_depot"),
    Rule("flee_hp",        2, lambda s: s.hp_pct < _HP_FLEE,      "flee_to_depot"),
    Rule("low_hp_potion",  3, lambda s: s.hp_pct < _HP_POTION,    "use_hp_potion"),
    Rule("low_mp_potion",  4, lambda s: s.mp_pct < _MP_POTION,    "use_mp_potion"),
    Rule("bag_full",       5, lambda s: s.bag_full,                "go_to_depot"),
    Rule("loot_dead",      6, lambda s: s.target_hp_pct == 0 and s.target_id is not None, "loot"),
    Rule("attack_target",  7, lambda s: s.target_id is not None and not s.is_attacking,   "attack"),
    Rule("find_nearby",    8, lambda s: s.target_id is None and bool(s.nearby_monsters),  "select_target"),
    Rule("follow_route",   9, lambda s: s.target_id is None,       "follow_route"),
    Rule("idle",          10, lambda s: True,                      "idle"),
]


def evaluate_rules(state: GameState) -> str:
    """Return the highest-priority matching action."""
    for rule in sorted(RULES, key=lambda r: r.priority):
        if rule.condition(state):
            return rule.action
    return "idle"
