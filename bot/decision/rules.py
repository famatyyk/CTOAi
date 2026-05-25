"""AGENT 4 / AGENT 7: Priority-based rule engine (Phase 1 AI)."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable
from ..perception.state import GameState


@dataclass
class Rule:
    name: str
    priority: int          # lower = higher priority
    condition: Callable[[GameState], bool]
    action: str


RULES: list[Rule] = [
    Rule("critical_hp",    1, lambda s: s.hp_pct < 15,    "flee_to_depot"),
    Rule("low_hp_potion",  2, lambda s: s.hp_pct < 30,    "use_hp_potion"),
    Rule("low_mp_potion",  3, lambda s: s.mp_pct < 20,    "use_mp_potion"),
    Rule("bag_full",       4, lambda s: s.bag_full,        "go_to_depot"),
    Rule("loot_dead",      5, lambda s: s.target_hp_pct == 0 and s.target_id is not None, "loot"),
    Rule("attack_target",  6, lambda s: s.target_id is not None and not s.is_attacking,   "attack"),
    Rule("find_target",    9, lambda s: s.target_id is None, "find_monster"),
    Rule("idle",          10, lambda s: True,               "idle"),
]


def evaluate_rules(state: GameState) -> str:
    """Return the highest-priority matching action."""
    for rule in sorted(RULES, key=lambda r: r.priority):
        if rule.condition(state):
            return rule.action
    return "idle"
