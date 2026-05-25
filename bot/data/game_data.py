"""AGENT 6: Game data loader — monsters, hunt routes, item values."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).parents[2] / "data" / "game"


@lru_cache(maxsize=1)
def load_monsters() -> list[dict[str, Any]]:
    with open(_DATA_DIR / "monsters.json", encoding="utf-8") as f:
        return json.load(f)["monsters"]


@lru_cache(maxsize=1)
def load_routes() -> list[dict[str, Any]]:
    with open(_DATA_DIR / "hunt_routes.json", encoding="utf-8") as f:
        return json.load(f)["routes"]


@lru_cache(maxsize=1)
def load_items() -> dict[str, Any]:
    with open(_DATA_DIR / "items.json", encoding="utf-8") as f:
        return json.load(f)


def get_monsters_for_level(level: int) -> list[dict[str, Any]]:
    """Return monsters appropriate for given player level, sorted by exp desc."""
    return sorted(
        [m for m in load_monsters() if m["min_level"] <= level <= m["max_level"]],
        key=lambda m: m["exp"],
        reverse=True,
    )


def get_route_for_level(level: int, max_risk: str = "medium") -> dict[str, Any] | None:
    """Return best hunt route for level respecting max_risk."""
    risk_order = {"low": 0, "medium": 1, "high": 2, "very_high": 3}
    max_risk_val = risk_order.get(max_risk, 1)
    candidates = [
        r for r in load_routes()
        if r["min_level"] <= level <= r["max_level"]
        and risk_order.get(r["risk"], 99) <= max_risk_val
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda r: r["exp_per_hour_estimate"])


def should_loot_item(item_name: str) -> bool:
    """Return True if item is worth picking up."""
    data = load_items()
    if item_name in data.get("skip_items", []):
        return False
    for item in data.get("valuable_items", []):
        if item["name"] == item_name:
            return item.get("always_loot", False) or item.get("value_gp", 0) >= data["loot_config"]["min_value_gp"]
    return False



def get_all_routes() -> list:
    result = load_routes()
    return result if isinstance(result, list) else result.get('routes', [])


def get_all_monsters() -> list:
    result = load_monsters()
    return result if isinstance(result, list) else result.get('monsters', [])
