#!/usr/bin/env python3
"""Shared PostgreSQL connection pool for CTOA agents.

Env vars (loaded from /opt/ctoa/.env via systemd EnvironmentFile):
    DB_HOST         default 127.0.0.1
    DB_PORT         default 5432
    DB_NAME         default ctoa
    DB_USER         default ctoa
    DB_PASSWORD     required
"""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Generator

log = logging.getLogger(__name__)

try:
    import psycopg2
    from psycopg2 import pool as pg_pool
    from psycopg2.extras import RealDictCursor
    _HAS_PSYCOPG2 = True
except ImportError:
    _HAS_PSYCOPG2 = False
    log.warning("psycopg2 not installed – DB operations will fail")

_pool: "pg_pool.SimpleConnectionPool | None" = None


def _dsn() -> str:
    pw = os.environ.get("DB_PASSWORD", "")
    if not pw:
        raise RuntimeError("DB_PASSWORD env var is required but not set")
    return (
        f"host={os.environ.get('DB_HOST', '127.0.0.1')} "
        f"port={os.environ.get('DB_PORT', '5432')} "
        f"dbname={os.environ.get('DB_NAME', 'ctoa')} "
        f"user={os.environ.get('DB_USER', 'ctoa')} "
        f"password={pw} "
        f"connect_timeout=10"
    )


def get_pool() -> "pg_pool.SimpleConnectionPool":
    global _pool
    if not _HAS_PSYCOPG2:
        raise RuntimeError("psycopg2 is not installed")
    if _pool is None or _pool.closed:
        _pool = pg_pool.SimpleConnectionPool(1, 4, dsn=_dsn())
    return _pool


@contextmanager
def get_conn() -> Generator:
    """Yield a psycopg2 connection; commit on success, rollback on error."""
    p = get_pool()
    conn = p.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        p.putconn(conn)


def query_one(sql: str, params=()) -> dict | None:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else None


def query_all(sql: str, params=()) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]


def execute(sql: str, params=()) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)


def log_run(agent: str, status: str, message: str = "") -> None:
    """Write an audit record to agent_runs table."""
    try:
        execute(
            "INSERT INTO agent_runs (agent, finished_at, status, message) "
            "VALUES (%s, now(), %s, %s)",
            (agent, status, message[:4000] if message else ""),
        )
    except Exception as exc:
        log.error("Failed to write agent_runs: %s", exc)
