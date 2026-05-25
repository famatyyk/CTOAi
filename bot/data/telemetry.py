"""AGENT 3: Telemetry event logging."""
from __future__ import annotations
import time
import logging
from .db import get_connection

logger = logging.getLogger(__name__)
_session_id: int | None = None


def set_session(session_id: int) -> None:
    global _session_id
    _session_id = session_id


def log_event(action: str, result: str, duration_ms: int = 0) -> None:
    if _session_id is None:
        return
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO actions (session_id, action_type, result, duration_ms) VALUES (?,?,?,?)",
                (_session_id, action, result, duration_ms)
            )
    except Exception as e:
        logger.warning("Telemetry write failed: %s", e)
