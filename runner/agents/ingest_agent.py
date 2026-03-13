#!/usr/bin/env python3
"""Ingest Agent – fetches live game data from discovered API endpoints and normalises
it into a standard schema stored in the game_data table.

Standard schema (stored as JSONB):
  monsters  → [{"name": str, "hp": int, "exp": int, "location": str}, ...]
  items     → [{"name": str, "id": int, "type": str, "weight": float}, ...]
  players   → [{"name": str, "level": int, "vocation": str}, ...]
  server_info → {"name": str, "pvp_type": str, "max_level": int, ...}
  highscores → [{"rank": int, "name": str, "level": int, "vocation": str}, ...]

Run: python3 -m runner.agents.ingest_agent
"""
from __future__ import annotations

import json
import logging
import ssl
import urllib.request
from typing import Any

from runner.agents import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [ingest] %(levelname)s %(message)s",
)
log = logging.getLogger("ingest")

REQUEST_TIMEOUT = 10
MAX_BODY_BYTES = 512 * 1024  # 512 KB per endpoint

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


def _fetch_json(url: str) -> Any | None:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "CTOAIngest/1.0",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT, context=_SSL_CTX) as r:
            raw = r.read(MAX_BODY_BYTES).decode("utf-8", errors="replace")
            return json.loads(raw)
    except Exception as exc:
        log.debug("fetch_json %s → %s", url, exc)
        return None


# ─── Normalizers: map arbitrary server response to standard schema ────────────

def _normalise_monsters(data: Any) -> list[dict]:
    results = []
    items = data if isinstance(data, list) else data.get("data", data.get("monsters", data.get("creatures", [])))
    if not isinstance(items, list):
        return results
    for m in items[:200]:
        if not isinstance(m, dict):
            continue
        results.append({
            "name": str(m.get("name", m.get("creature_name", m.get("title", "Unknown")))),
            "hp":   int(m.get("hp", m.get("health", m.get("hitpoints", 0))) or 0),
            "exp":  int(m.get("exp", m.get("experience", m.get("experience_points", 0))) or 0),
            "location": str(m.get("location", m.get("area", m.get("spawn", "")))),
        })
    return results


def _normalise_items(data: Any) -> list[dict]:
    results = []
    items = data if isinstance(data, list) else data.get("data", data.get("items", []))
    if not isinstance(items, list):
        return results
    for it in items[:200]:
        if not isinstance(it, dict):
            continue
        results.append({
            "name":   str(it.get("name", it.get("title", "Unknown"))),
            "id":     int(it.get("id", it.get("item_id", 0)) or 0),
            "type":   str(it.get("type", it.get("item_type", ""))),
            "weight": float(it.get("weight", it.get("oz", 0)) or 0),
        })
    return results


def _normalise_players(data: Any) -> list[dict]:
    results = []
    items = data if isinstance(data, list) else data.get("data", data.get("players", data.get("characters", [])))
    if not isinstance(items, list):
        return results
    for p in items[:100]:
        if not isinstance(p, dict):
            continue
        results.append({
            "name":     str(p.get("name", p.get("character_name", "Unknown"))),
            "level":    int(p.get("level", p.get("char_level", 1)) or 1),
            "vocation": str(p.get("vocation", p.get("class", p.get("job", "?")))),
        })
    return results


def _normalise_highscores(data: Any) -> list[dict]:
    results = []
    items = data if isinstance(data, list) else data.get("data", data.get("highscores", data.get("scores", [])))
    if not isinstance(items, list):
        return results
    for i, h in enumerate(items[:50]):
        if not isinstance(h, dict):
            continue
        results.append({
            "rank":     int(h.get("rank", h.get("position", i + 1)) or i + 1),
            "name":     str(h.get("name", h.get("character", "Unknown"))),
            "level":    int(h.get("level", h.get("value", 0)) or 0),
            "vocation": str(h.get("vocation", h.get("class", "?"))),
        })
    return results


def _normalise_server_info(data: Any) -> dict:
    if not isinstance(data, dict):
        return {}
    return {
        "name":      str(data.get("name", data.get("server_name", data.get("world", "")))),
        "pvp_type":  str(data.get("pvp_type", data.get("type", data.get("pvp", "unknown")))),
        "max_level": int(data.get("max_level", data.get("level_cap", 0)) or 0),
        "rate_exp":  float(data.get("exp_rate", data.get("rate_exp", data.get("xp_rate", 1))) or 1),
        "online":    int(data.get("online", data.get("online_count", data.get("players_online", 0))) or 0),
    }


# Map path fragments → (data_type, normaliser)
_PATH_MAP: list[tuple[str, str, Any]] = [
    ("monsters",    "monsters",    _normalise_monsters),
    ("creatures",   "monsters",    _normalise_monsters),
    ("items",       "items",       _normalise_items),
    ("players",     "players",     _normalise_players),
    ("characters",  "players",     _normalise_players),
    ("highscores",  "highscores",  _normalise_highscores),
    ("server",      "server_info", _normalise_server_info),
    ("status",      "server_info", _normalise_server_info),
    ("worldinfo",   "server_info", _normalise_server_info),
]


def _detect_type(path: str) -> tuple[str, Any] | None:
    p = path.lower()
    for fragment, dtype, norm in _PATH_MAP:
        if fragment in p:
            return dtype, norm
    return None


def ingest_server(server_id: int, base_url: str) -> int:
    log.info("Ingesting server #%d %s", server_id, base_url)
    endpoints = db.query_all(
        "SELECT path FROM api_endpoints WHERE server_id=%s AND last_status=200",
        (server_id,),
    )

    ingested = 0
    for ep in endpoints:
        path = ep["path"]
        detected = _detect_type(path)
        if not detected:
            continue
        data_type, normalise = detected

        url = base_url.rstrip("/") + path
        raw = _fetch_json(url)
        if raw is None:
            log.debug("  skip %s – empty response", path)
            continue

        normalised = normalise(raw)
        if not normalised:
            continue

        db.execute(
            """
            INSERT INTO game_data (server_id, data_type, raw, fetched_at)
            VALUES (%s, %s, %s, now())
            """,
            (server_id, data_type, json.dumps(normalised)),
        )
        ingested += 1
        log.info("  ✓ %s → %s (%d items)", path, data_type, len(normalised) if isinstance(normalised, list) else 1)

    # Mark server READY when we have at least one data block
    if ingested > 0:
        db.execute(
            "UPDATE servers SET status='READY', updated_at=now() WHERE id=%s",
            (server_id,),
        )
        log.info("Server #%d READY (%d data blocks)", server_id, ingested)
    else:
        # No data fetched → still usable in no-data mode (generic templates)
        db.execute(
            "UPDATE servers SET status='READY', updated_at=now() WHERE id=%s",
            (server_id,),
        )
        log.info("Server #%d READY (generic mode – no game_data)", server_id)

    db.log_run("ingest_agent", "ok", f"server #{server_id}: {ingested} data blocks")
    return ingested


def run_once() -> None:
    servers = db.query_all(
        "SELECT id, url FROM servers WHERE status='INGESTED' ORDER BY id LIMIT 5"
    )
    if not servers:
        log.info("No INGESTED servers to process")
        return
    for srv in servers:
        try:
            ingest_server(srv["id"], srv["url"])
        except Exception as exc:
            log.error("Ingest error for %s: %s", srv["url"], exc)
            db.execute(
                "UPDATE servers SET status='ERROR', scout_error=%s, updated_at=now() WHERE id=%s",
                (f"ingest: {exc}"[:500], srv["id"]),
            )
            db.log_run("ingest_agent", "error", str(exc))


if __name__ == "__main__":
    run_once()
