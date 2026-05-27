"""Tests for Agent 3 telemetry: gold/hr, exp/hr, kills."""
import pytest
import os
import tempfile
from bot.data import db as db_module
from bot.data.telemetry import set_session, log_event, log_loot, log_exp, get_stats
from bot.data.db import create_session, close_session, get_session_stats


@pytest.fixture(autouse=True)
def temp_db(tmp_path):
    """Use a temporary DB for each test."""
    db_path = str(tmp_path / "test_bot.db")
    original = db_module.DB_PATH
    db_module.DB_PATH = db_path
    yield db_path
    db_module.DB_PATH = original


def test_create_session_returns_id():
    sid = create_session()
    assert isinstance(sid, int) and sid > 0


def test_log_loot_increments_gold():
    sid = create_session()
    set_session(sid)
    log_loot("gold coin", 50)
    log_loot("platinum coin", 100)
    close_session(sid)
    stats = get_session_stats(sid)
    # session_hours may be 0 for instant session, gold_gained should be present in DB
    from bot.data.db import get_connection
    with get_connection() as conn:
        gold = conn.execute("SELECT gold_gained FROM sessions WHERE id=?", (sid,)).fetchone()[0]
    assert gold == 150


def test_log_exp_increments_xp():
    sid = create_session()
    set_session(sid)
    log_exp(50, "Troll")
    log_exp(115, "Minotaur Guard")
    close_session(sid)
    from bot.data.db import get_connection
    with get_connection() as conn:
        xp = conn.execute("SELECT xp_gained FROM sessions WHERE id=?", (sid,)).fetchone()[0]
        kills = conn.execute("SELECT COUNT(*) FROM exp_events WHERE session_id=?", (sid,)).fetchone()[0]
    assert xp == 165
    assert kills == 2


def test_log_event_writes_action():
    sid = create_session()
    set_session(sid)
    log_event("attack", "ok", 12)
    from bot.data.db import get_connection
    with get_connection() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM actions WHERE session_id=? AND action_type='attack'", (sid,)
        ).fetchone()[0]
    assert count == 1


def test_get_stats_returns_dict():
    sid = create_session()
    set_session(sid)
    stats = get_stats()
    assert "gold_hr" in stats
    assert "exp_hr" in stats
    assert "kills" in stats


def test_get_stats_no_session():
    set_session(None)
    stats = get_stats()
    assert stats["gold_hr"] == 0
