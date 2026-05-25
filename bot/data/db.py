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
