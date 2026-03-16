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
import os
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

# ─── Generic paths to probe on every server ─────────────────────────────────
COMMON_PROBE_PATHS: list[str] = [
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

# ─── Host-based API profiles (adapter per server family) ────────────────────
PROFILE_HINTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"tibiantis", re.IGNORECASE), "tibiantis"),
    (re.compile(r"otservbr|canary", re.IGNORECASE), "otservbr"),
    (re.compile(r"forgotten|tfs", re.IGNORECASE), "tfs"),
    (re.compile(r"myaac", re.IGNORECASE), "myaac"),
]

PROFILE_PATHS: dict[str, list[str]] = {
    "tibiantis": [
        "/highscores",
        "/community/highscores.php",
        "/community/players.php",
        "/newsarchive.php?type=1",
        "/whoisonline",
        "/characters/Gamemaster",
        "/character/Gamemaster",
        "/characterprofile.php?name=Gamemaster",
    ],
    "otservbr": [
        "/api/v1/server",
        "/api/v1/status",
        "/api/v1/highscores",
        "/api/v1/players/online",
        "/api/v1/guilds",
    ],
    "tfs": [
        "/api/server",
        "/api/status",
        "/api/highscores",
        "/api/players/online",
        "/api/players",
    ],
    "myaac": [
        "/api/status",
        "/api/server",
        "/highscores",
        "/news",
        "/guilds",
    ],
}

# ─── Automatic fallback path-sets for common OT engines ─────────────────────
ENGINE_FALLBACK_PATHS: dict[str, list[str]] = {
    "tfs": [
        "/api/v1/server",
        "/api/v1/status",
        "/api/v1/highscores",
        "/api/v1/players",
        "/api/v1/players/online",
        "/api/v1/monsters",
        "/api/v1/items",
    ],
    "otservbr": [
        "/api/server",
        "/api/status",
        "/api/highscores",
        "/api/players",
        "/api/players/online",
        "/api/worlds",
        "/api/guilds",
    ],
    "canary": [
        "/api/v2/server",
        "/api/v2/status",
        "/api/v2/highscores",
        "/api/v2/players/online",
        "/api/v2/worlds",
    ],
    "myaac": [
        "/api/status",
        "/api/server",
        "/highscores",
        "/players",
        "/news",
    ],
    "gesior": [
        "/community/highscores.php",
        "/community/players.php",
        "/newsarchive.php?type=1",
        "/characters/Gamemaster",
    ],
}

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


def _dedupe_paths(paths: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for p in paths:
        path = p if p.startswith("/") else f"/{p}"
        if path not in seen:
            seen.add(path)
            out.append(path)
    return out


def _infer_profile(base_url: str) -> str:
    host = urllib.parse.urlparse(base_url).netloc.lower()
    for pattern, profile in PROFILE_HINTS:
        if pattern.search(host):
            return profile
    return "generic"


def _force_generic_hosts() -> set[str]:
    raw = os.environ.get("CTOA_FORCE_GENERIC_HOSTS", "mythibia.online")
    return {h.strip().lower() for h in raw.split(",") if h.strip()}


def _probe_paths(
    server_id: int,
    base_url: str,
    paths: list[str],
    source: str,
    probed: set[str],
) -> tuple[int, int]:
    found = 0
    errors = 0

    for path in paths:
        if path in probed:
            continue
        probed.add(path)

        url = base_url.rstrip("/") + path
        status, schema = _fetch(url)

        if status in (200, 206):
            found += 1
            if isinstance(schema, dict):
                schema = {**schema, "_probe_source": source}

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
            log.info("  ✓ [%s] %s → %d", source, path, status)
        elif status >= 400:
            errors += 1

    return found, errors


def scout_server(server_id: int, base_url: str) -> None:
    log.info("Scouting server #%d %s", server_id, base_url)

    # Mark as SCOUTING
    db.execute(
        "UPDATE servers SET status='SCOUTING', updated_at=now() WHERE id=%s",
        (server_id,),
    )

    found = 0
    errors = 0
    probed: set[str] = set()

    profile = _infer_profile(base_url)
    primary_paths = _dedupe_paths(PROFILE_PATHS.get(profile, []) + COMMON_PROBE_PATHS)
    fallback_engines = [e for e in ENGINE_FALLBACK_PATHS.keys() if e != profile]

    # --- try to detect game name from root page title
    root_status, _ = _fetch(base_url.rstrip("/") + "/")
    game_type = "unknown"
    if root_status in (200, 403):
        game_type = "tibia-ot"  # assume Tibia OT for now; ingest will refine

    p_found, p_errors = _probe_paths(server_id, base_url, primary_paths, f"profile:{profile}", probed)
    found += p_found
    errors += p_errors

    detected_engine: str | None = profile if p_found > 0 and profile != "generic" else None

    # If nothing responded, try common OT engine-specific fallback sets.
    if found == 0:
        for engine in fallback_engines:
            f_found, f_errors = _probe_paths(
                server_id,
                base_url,
                _dedupe_paths(ENGINE_FALLBACK_PATHS[engine]),
                f"fallback:{engine}",
                probed,
            )
            found += f_found
            errors += f_errors
            if f_found > 0:
                detected_engine = engine
                log.info("Fallback matched engine profile: %s", engine)
                break

    host = urllib.parse.urlparse(base_url).netloc.lower()
    force_by_host = any(h in host for h in _force_generic_hosts())
    force_generic_ingest = found == 0 and (profile == "tibiantis" or force_by_host)
    new_status = "INGESTED" if (found > 0 or force_generic_ingest) else "ERROR"
    if detected_engine:
        game_type = f"tibia-ot:{detected_engine}"
    elif profile != "generic":
        game_type = f"tibia-ot:{profile}"

    scout_error = None
    if force_generic_ingest:
        scout_error = (
            "No machine API found; forced generic ingest mode "
            f"for profile={profile}, host={host} (total_probed={len(probed)})"
        )
    elif found == 0:
        scout_error = (
            "No accessible endpoints found "
            f"(profile={profile}, primary={len(primary_paths)}, "
            f"fallback_engines={len(fallback_engines)}, total_probed={len(probed)})"
        )

    db.execute(
        "UPDATE servers SET status=%s, game_type=%s, scout_error=%s, updated_at=now() WHERE id=%s",
        (new_status, game_type, scout_error, server_id),
    )
    log.info(
        "Scout done: %d paths OK, %d errors, profile=%s, probed=%d → status=%s",
        found,
        errors,
        profile,
        len(probed),
        new_status,
    )
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
