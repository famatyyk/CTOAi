"""Tests for Agent 6/7 hunt strategy integration."""
import pytest
from bot.perception.state import GameState
from bot.decision.hunt_strategy import best_target_from_nearby, get_active_route, next_waypoint
from bot.decision.rules import evaluate_rules


def make_state(**kwargs) -> GameState:
    s = GameState(hp=100, hp_max=100, mp=100, mp_max=100)
    for k, v in kwargs.items():
        setattr(s, k, v)
    return s


def test_best_target_no_nearby():
    s = make_state(level=15, nearby_monsters=[])
    assert best_target_from_nearby(s) is None


def test_best_target_picks_highest_exp():
    s = make_state(level=20, nearby_monsters=["Troll", "Orc", "Minotaur"])
    result = best_target_from_nearby(s)
    assert result == "Minotaur"  # highest exp for lvl 20


def test_best_target_fallback_unknown_monster():
    s = make_state(level=10, nearby_monsters=["Unknown Dragon Boss"])
    result = best_target_from_nearby(s)
    assert result == "Unknown Dragon Boss"  # fallback to first


def test_active_route_returns_route_for_level():
    route = get_active_route(15)
    assert route is not None
    assert route["min_level"] <= 15 <= route["max_level"]


def test_active_route_none_for_impossible_level():
    # Level 1 has no routes — should return None or lowest risk route
    route = get_active_route(1, max_risk="low")
    # acceptable: None or a valid route
    if route is not None:
        assert route["min_level"] <= route["max_level"]


def test_next_waypoint_returns_coords():
    wp = next_waypoint(15)
    assert wp is None or (isinstance(wp, tuple) and len(wp) == 2)


def test_next_waypoint_advances_with_cursor(monkeypatch):
    import bot.decision.hunt_strategy as hs

    hs._route_cursors.clear()
    route = {
        "id": "test-route",
        "waypoints": [
            {"x": 0, "y": 0, "action": "start"},
            {"x": 1, "y": 1, "action": "move"},
            {"x": 2, "y": 2, "action": "move"},
            {"x": 0, "y": 0, "action": "loop_back"},
        ],
    }
    monkeypatch.setattr(hs, "get_active_route", lambda *_args, **_kwargs: route)

    assert hs.next_waypoint(20) == (1, 1)
    assert hs.next_waypoint(20) == (2, 2)
    assert hs.next_waypoint(20) == (1, 1)


def test_rules_select_target_when_nearby():
    s = make_state(target_id=None, nearby_monsters=["Troll"])
    action = evaluate_rules(s)
    assert action == "select_target"


def test_rules_follow_route_when_no_monsters():
    s = make_state(target_id=None, nearby_monsters=[])
    action = evaluate_rules(s)
    assert action == "follow_route"


def test_rules_flee_takes_priority_over_route():
    s = make_state(hp=5, hp_max=100, nearby_monsters=["Dragon"])
    action = evaluate_rules(s)
    assert action == "flee_to_depot"
