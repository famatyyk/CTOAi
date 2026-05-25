"""Tests for AGENT6 game data loader."""
import pytest
from bot.data.game_data import (
    load_monsters,
    load_routes,
    load_items,
    get_monsters_for_level,
    get_route_for_level,
    should_loot_item,
)


def test_monsters_load():
    monsters = load_monsters()
    assert len(monsters) >= 10
    for m in monsters:
        assert "name" in m and "hp" in m and "exp" in m


def test_routes_load():
    routes = load_routes()
    assert len(routes) >= 5
    for r in routes:
        assert "name" in r and "min_level" in r and "waypoints" in r


def test_items_load():
    data = load_items()
    assert "valuable_items" in data
    assert "loot_config" in data


def test_monsters_for_level_8():
    results = get_monsters_for_level(8)
    names = [m["name"] for m in results]
    assert "Troll" in names or "Goblin" in names


def test_monsters_for_level_20():
    results = get_monsters_for_level(20)
    names = [m["name"] for m in results]
    assert "Minotaur" in names or "Orc" in names


def test_monsters_for_level_40():
    results = get_monsters_for_level(40)
    names = [m["name"] for m in results]
    assert "Dragon Hatchling" in names or "Vampire" in names


def test_route_for_level_10():
    route = get_route_for_level(10)
    assert route is not None
    assert route["min_level"] <= 10 <= route["max_level"]


def test_route_respects_risk():
    route_safe = get_route_for_level(30, max_risk="low")
    if route_safe:
        assert route_safe["risk"] == "low"


def test_should_loot_gold():
    assert should_loot_item("gold coin") is True


def test_should_not_loot_skip_item():
    assert should_loot_item("worm") is False


def test_should_loot_valuable():
    assert should_loot_item("vampire shield") is True
