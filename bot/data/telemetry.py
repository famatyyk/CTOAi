"""AGENT 3: Telemetry — action events, loot, exp/hr, gold/hr."""
from __future__ import annotations
import time
import logging
from .db import get_connection, get_session_stats

logger = logging.getLogger(__name__)
_session_id: int | None = None


def set_session(session_id: int) -> None:
    global _session_id
    _session_id = session_id


def _sid() -> int | None:
    return _session_id


def log_event(action: str, result: str, duration_ms: int = 0) -> None:
    if _sid() is None:
        return
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO actions (session_id, action_type, result, duration_ms) VALUES (?,?,?,?)",
                (_sid(), action, result, duration_ms),
            )
    except Exception as e:
        logger.warning("Telemetry log_event failed: %s", e)


def log_loot(item_name: str, gold_value: int) -> None:
    """Record a loot pickup. Also increments session gold_gained."""
    if _sid() is None:
        return
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO loot_events (session_id, item_name, gold_value) VALUES (?,?,?)",
                (_sid(), item_name, gold_value),
            )
            conn.execute(
                "UPDATE sessions SET gold_gained = gold_gained + ? WHERE id = ?",
                (gold_value, _sid()),
            )
    except Exception as e:
        logger.warning("Telemetry log_loot failed: %s", e)


def log_exp(exp_gained: int, monster_name: str = "") -> None:
    """Record exp gain from a kill. Also increments session xp_gained."""
    if _sid() is None:
        return
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO exp_events (session_id, exp_gained, monster_name) VALUES (?,?,?)",
                (_sid(), exp_gained, monster_name),
            )
            conn.execute(
                "UPDATE sessions SET xp_gained = xp_gained + ? WHERE id = ?",
                (exp_gained, _sid()),
            )
    except Exception as e:
        logger.warning("Telemetry log_exp failed: %s", e)


def get_stats() -> dict:
    """Return current session stats (gold/hr, exp/hr, kills)."""
    if _sid() is None:
        return {"gold_hr": 0, "exp_hr": 0, "kills": 0, "session_hours": 0}
    try:
        return get_session_stats(_sid())
    except Exception as e:
        logger.warning("Telemetry get_stats failed: %s", e)
        return {"gold_hr": 0, "exp_hr": 0, "kills": 0, "session_hours": 0}
