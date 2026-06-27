"""AGENT 3: SQLite database interface."""
from __future__ import annotations
import sqlite3
import os

DB_PATH = os.environ.get("BOT_DB_PATH", "data/bot.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    end_time DATETIME,
    xp_gained INTEGER DEFAULT 0,
    gold_gained INTEGER DEFAULT 0,
    deaths INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER REFERENCES sessions(id),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    action_type TEXT NOT NULL,
    result TEXT,
    duration_ms INTEGER
);

CREATE TABLE IF NOT EXISTS game_state_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER REFERENCES sessions(id),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    hp INTEGER, mp INTEGER,
    pos_x INTEGER, pos_y INTEGER,
    target_id INTEGER
);

CREATE TABLE IF NOT EXISTS loot_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER REFERENCES sessions(id),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    item_name TEXT NOT NULL,
    gold_value INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS exp_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER REFERENCES sessions(id),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    exp_gained INTEGER DEFAULT 0,
    monster_name TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS loop_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER REFERENCES sessions(id),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    component TEXT NOT NULL,
    stage TEXT NOT NULL,
    duration_ms INTEGER DEFAULT 0,
    ok INTEGER DEFAULT 1,
    error TEXT DEFAULT '',
    details TEXT DEFAULT ''
);
"""


def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    return conn


def create_session() -> int:
    with get_connection() as conn:
        cursor = conn.execute("INSERT INTO sessions DEFAULT VALUES")
        return cursor.lastrowid


def close_session(session_id: int) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE sessions SET end_time = CURRENT_TIMESTAMP WHERE id = ?",
                     (session_id,))


def get_session_stats(session_id: int) -> dict:
    """Return gold/hr, exp/hr, kills for a session."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """SELECT
                 (julianday(COALESCE(end_time, CURRENT_TIMESTAMP)) - julianday(start_time)) * 24.0 AS hours,
                 gold_gained, xp_gained
               FROM sessions WHERE id = ?""",
            (session_id,)
        ).fetchone()
        if not row or row["hours"] is None or row["hours"] <= 0:
            return {"gold_hr": 0, "exp_hr": 0, "kills": 0, "session_hours": 0}
        hours = row["hours"]
        kills = conn.execute(
            "SELECT COUNT(*) FROM exp_events WHERE session_id = ?", (session_id,)
        ).fetchone()[0]
        return {
            "gold_hr": int(row["gold_gained"] / hours),
            "exp_hr": int(row["xp_gained"] / hours),
            "kills": kills,
            "session_hours": round(hours, 2),
        }
