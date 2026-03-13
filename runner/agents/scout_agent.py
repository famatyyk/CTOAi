#!/usr/bin/env python3
"""Scout Agent – discovers API endpoints for a registered server URL.

Flow:
  1. Find servers with status=NEW in DB.
  2. Probe a set of known game-server API paths.
  3. For each responding path record schema sample in api_endpoints.
  4. Update server status: INGESTED (has endpoints) or ERROR.

Run: python3 -m runner.agents.scout_agent
"""
from __future__ import annotations

import json
import logging
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from runner.agents import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [scout] %(levelname)s %(message)s",
)
log = logging.getLogger("scout")

# ─── Paths to probe on every server ─────────────────────────────────────────
PROBE_PATHS: list[str] = [
    "/api/",
    "/api/v1/",
    "/api/v2/",
    "/api/v3/",
    "/openapi.json",
    "/swagger.json",
    "/api/highscores",
    "/api/highscores.json",
    "/api/players/online",
    "/api/players",
    "/api/monsters",
    "/api/creatures",
    "/api/items",
    "/api/spells",
    "/api/guilds",
    "/api/news",
    "/api/worlds",
    "/api/status",
    "/api/server",
    "/characters/Gamemaster",
    "/character/Gamemaster",
    "/characterprofile.php?name=Gamemaster",
    "/newsarchive.php?type=1",
    "/community/highscores.php",
    "/community/players.php",
    "/health",
    "/healthz",
    "/ping",
]

MAX_BODY_BYTES = 8192
REQUEST_TIMEOUT = 8
MAX_RETRIES = 3

# Insecure SSL context only used to discover that an endpoint exists
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


def _fetch(url: str) -> tuple[int, dict[str, Any] | None]:
    """Return (http_status, json_sample_or_None)."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "CTOAScout/1.0 (+https://github.com/famatyyk/CTOAi)",
            "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT, context=_SSL_CTX) as r:
            status = r.status
            raw = r.read(MAX_BODY_BYTES).decode("utf-8", errors="replace")
            ct = r.headers.get("Content-Type", "")
            sample = None
            if "json" in ct.lower():
                try:
                    sample = json.loads(raw)
                    # Keep only first level keys / first list items to save space
                    if isinstance(sample, dict):
                        sample = {k: type(v).__name__ for k, v in list(sample.items())[:20]}
                    elif isinstance(sample, list):
                        sample = {"_list_len": len(sample), "_item": type(sample[0]).__name__ if sample else "empty"}
                except Exception:
                    sample = {"_raw_prefix": raw[:200]}
            return status, sample
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        return 0, None


def _safe_slug(url: str) -> str:
    return re.sub(r"[^a-z0-9_-]", "_", url.lower())[:60]


def scout_server(server_id: int, base_url: str) -> None:
    log.info("Scouting server #%d %s", server_id, base_url)

    # Mark as SCOUTING
    db.execute(
        "UPDATE servers SET status='SCOUTING', updated_at=now() WHERE id=%s",
        (server_id,),
    )

    found = 0
    errors = 0

    # --- try to detect game name from root page title
    root_status, _ = _fetch(base_url.rstrip("/") + "/")
    game_type = "unknown"
    if root_status in (200, 403):
        game_type = "tibia-ot"  # assume Tibia OT for now; ingest will refine

    for path in PROBE_PATHS:
        url = base_url.rstrip("/") + path
        status, schema = _fetch(url)

        if status in (200, 206):
            found += 1
            db.execute(
                """
                INSERT INTO api_endpoints (server_id, path, last_status, response_schema, last_checked)
                VALUES (%s, %s, %s, %s, now())
                ON CONFLICT (server_id, path) DO UPDATE
                  SET last_status=EXCLUDED.last_status,
                      response_schema=EXCLUDED.response_schema,
                      last_checked=now()
                """,
                (server_id, path, status, json.dumps(schema) if schema else None),
            )
            log.info("  ✓ %s → %d (schema keys: %s)", path, status, list(schema.keys()) if schema else "html")
        elif status >= 400:
            errors += 1
        # 0 = connection error, skip silently

    new_status = "INGESTED" if found > 0 else "ERROR"
    scout_error = None if found > 0 else f"No accessible endpoints found (probed {len(PROBE_PATHS)})"

    db.execute(
        "UPDATE servers SET status=%s, game_type=%s, scout_error=%s, updated_at=now() WHERE id=%s",
        (new_status, game_type, scout_error, server_id),
    )
    log.info("Scout done: %d paths OK, %d errors → status=%s", found, errors, new_status)
    db.log_run("scout_agent", "ok", f"server #{server_id} {base_url}: {found} endpoints")


def run_once() -> None:
    servers = db.query_all("SELECT id, url FROM servers WHERE status IN ('NEW', 'SCOUTING') ORDER BY id LIMIT 5")
    if not servers:
        log.info("No NEW servers to scout")
        return
    for srv in servers:
        try:
            scout_server(srv["id"], srv["url"])
        except Exception as exc:
            log.error("Scout error for %s: %s", srv["url"], exc)
            db.execute(
                "UPDATE servers SET status='ERROR', scout_error=%s, updated_at=now() WHERE id=%s",
                (str(exc)[:500], srv["id"]),
            )
            db.log_run("scout_agent", "error", str(exc))


if __name__ == "__main__":
    run_once()
