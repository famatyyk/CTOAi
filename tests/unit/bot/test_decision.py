"""AGENT 8: Unit tests for decision engine."""
import pytest
from bot.perception.state import GameState
from bot.decision.rules import evaluate_rules
from bot.decision.brain import decide_action


def make_state(**kwargs) -> GameState:
    s = GameState(hp=100, hp_max=100, mp=100, mp_max=100)
    for k, v in kwargs.items():
        setattr(s, k, v)
    return s


def test_critical_hp_flees():
    s = make_state(hp=10, hp_max=100)
    assert evaluate_rules(s) == "flee_to_depot"


def test_low_hp_uses_potion():
    s = make_state(hp=25, hp_max=100)
    assert evaluate_rules(s) == "use_hp_potion"


def test_low_mp_uses_potion():
    s = make_state(hp=100, hp_max=100, mp=15, mp_max=100)
    assert evaluate_rules(s) == "use_mp_potion"


def test_loot_dead_target():
    s = make_state(target_id=42, target_hp_pct=0)
    assert evaluate_rules(s) == "loot"


def test_attack_live_target():
    s = make_state(target_id=42, target_hp_pct=50, is_attacking=False)
    assert evaluate_rules(s) == "attack"


def test_find_monster_when_no_target():
    s = make_state(target_id=None)
    assert evaluate_rules(s) == "find_monster"


def test_brain_delegates_to_rules():
    s = make_state(hp=10, hp_max=100)
    assert decide_action(s) == "flee_to_depot"


def test_bag_full_goes_depot():
    s = make_state(bag_full=True)
    assert evaluate_rules(s) == "go_to_depot"
