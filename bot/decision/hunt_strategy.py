"""AGENT 6/7: Level-aware hunt strategy — picks targets and routes from game_data."""
from __future__ import annotations
from typing import Any

from ..perception.state import GameState

try:
    from ..data.game_data import (
        get_monsters_for_level,
        get_route_for_level,
        load_items,
    )
    _GAME_DATA_AVAILABLE = True
except Exception:
    _GAME_DATA_AVAILABLE = False


def best_target_from_nearby(state: GameState) -> str | None:
    """Return name of highest-priority monster to attack from nearby list.

    Priority: highest exp monster that is appropriate for the level.
    Falls back to first nearby monster if no game data available.
    """
    if not state.nearby_monsters:
        return None
    if not _GAME_DATA_AVAILABLE:
        return state.nearby_monsters[0]

    valid = get_monsters_for_level(state.level)
    valid_names = {m["name"] for m in valid}
    # prefer monsters that match our level range (sorted by exp desc)
    ranked = [m for m in valid if m["name"] in state.nearby_monsters]
    if ranked:
        return ranked[0]["name"]
    # fallback: any nearby monster
    return state.nearby_monsters[0]


def get_active_route(level: int, max_risk: str = "medium") -> dict[str, Any] | None:
    """Return best hunt route dict for current level."""
    if not _GAME_DATA_AVAILABLE:
        return None
    return get_route_for_level(level, max_risk)


def get_potion_thresholds() -> dict[str, int]:
    """Return hotkey/threshold config from items.json."""
    if not _GAME_DATA_AVAILABLE:
        return {"use_hp_potion_at_pct": 60, "use_mp_potion_at_pct": 30,
                "flee_at_pct": 15, "critical_flee_at_pct": 10}
    try:
        data = load_items()
        return data.get("equipment_consumables", {}).get("thresholds", {})
    except Exception:
        return {"use_hp_potion_at_pct": 60, "use_mp_potion_at_pct": 30,
                "flee_at_pct": 15, "critical_flee_at_pct": 10}


def next_waypoint(level: int) -> tuple[int, int] | None:
    """Return (x, y) of next waypoint for current level route, or None."""
    route = get_active_route(level)
    if not route or not route.get("waypoints"):
        return None
    # Simple: return first non-start waypoint (real navigation done by movement module)
    for wp in route["waypoints"]:
        if wp.get("action") not in ("start", "loop_back"):
            return wp["x"], wp["y"]
    return None
