#!/usr/bin/env python3
"""Catalog Agent – discovers and scores OT servers from listing sources.

Goal:
  - find candidate server URLs from public catalog/listing pages,
  - score each candidate for strategic signals:
      * NEW launch signal,
      * LONG_TERM signal,
      * HIGH_POP signal,
  - upsert discovered servers into `servers` table,
  - persist scouting metadata into `game_data` as `catalog_signal`.

Run:
  python3 -m runner.agents.catalog_agent
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
from datetime import datetime, timezone, timedelta
from typing import Any

from runner.agents import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [catalog] %(levelname)s %(message)s",
)
log = logging.getLogger("catalog")

REQUEST_TIMEOUT = int(os.environ.get("CTOA_CATALOG_TIMEOUT", "12"))
MAX_HTML_BYTES = int(os.environ.get("CTOA_CATALOG_MAX_HTML_BYTES", "250000"))
MAX_CANDIDATES_PER_SOURCE = int(os.environ.get("CTOA_CATALOG_MAX_CANDIDATES", "80"))
AUTO_APPROVE_THRESHOLD = int(os.environ.get("CTOA_CATALOG_AUTO_APPROVE_THRESHOLD", "70"))

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)

BLOCKED_HOST_SNIPPETS = (
    "github.com",
    "discord.gg",
    "discord.com",
    "facebook.com",
    "instagram.com",
    "youtube.com",
    "tiktok.com",
    "x.com",
    "twitter.com",
    "reddit.com",
    "wikipedia.org",
    "google-analytics.com",
    "googletagmanager.com",
    "doubleclick.net",
    "w3.org",
)

BLOCKED_PATH_SUFFIXES = (
    ".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".woff", ".woff2", ".ttf",
)

ALLOWED_HOST_HINTS = ("ot", "tibia", "rpg", "mmo", "server")

SIGNAL_KEYWORDS = {
    "new": ["new", "launch", "launched", "fresh", "start", "opening", "otwar", "nowy", "startuje"],
    "long_term": ["long term", "long-term", "stable", "since", "years", "legacy", "stabilny", "dlugotermin"],
    "high_pop": ["online", "players", "population", "concurrent", "aktywn", "graczy"],
}

SOURCE_PRIORITY_RULES: list[tuple[str, int, str]] = [
    ("otservlist.org", 45, "ots_list_tier1"),
    ("tibiaservers.net", 40, "ots_list_tier1"),
    ("open-tibia.com", 35, "ots_list_tier1"),
    ("ots-list.com", 35, "ots_list_tier1"),
    ("tibiaots.pl", 30, "ots_list_pl"),
    ("vatira.pl", 28, "ots_list_pl"),
    ("otlist.pl", 26, "ots_list_pl"),
    ("otland.net", 18, "forum_global"),
    ("native-servers.com", 14, "forum_secondary"),
]

CATALOG_PROFILE_SOURCES: dict[str, list[str]] = {
    "GLOBAL": [
        "https://otservlist.org/",
        "https://otservlist.org/list-server_players-desc.html",
        "https://open-tibia.com/",
        "https://tibiaservers.net/",
    ],
    "PL": [
        "https://otservlist.org/",
        "https://tibiaots.pl/",
        "https://otlist.pl/",
        "https://open-tibia.com/",
    ],
    "BR": [
        "https://otservlist.org/",
        "https://tibiaservers.net/",
        "https://open-tibia.com/",
        "https://otland.net/forums/brazilian-servers.379/",
    ],
}


def _catalog_profile() -> str:
    raw = os.environ.get("CTOA_CATALOG_PROFILE", "GLOBAL")
    profile = str(raw or "GLOBAL").strip().upper()
    if profile not in CATALOG_PROFILE_SOURCES:
        return "GLOBAL"
    return profile


def _parse_window_hours(window: str, fallback_start: int, fallback_end: int) -> tuple[int, int]:
    text = (window or "").strip()
    if not text:
        return fallback_start, fallback_end
    parts = text.split("-", 1)
    if len(parts) != 2:
        return fallback_start, fallback_end
    try:
        start = int(parts[0].strip())
        end = int(parts[1].strip())
    except Exception:
        return fallback_start, fallback_end
    if start < 0 or start > 23 or end < 0 or end > 23:
        return fallback_start, fallback_end
    return start, end


def _hour_in_window(hour: int, start: int, end: int) -> bool:
    if start <= end:
        return start <= hour <= end
    return hour >= start or hour <= end


def _source_allowed_now(source_url: str, profile: str) -> bool:
    # Windows are intentionally UTC-based to keep behavior deterministic on VPS.
    host = (urllib.parse.urlparse(source_url).netloc or "").lower()
    if not host:
        return False

    if profile == "PL":
        base = datetime.now(timezone.utc) + timedelta(hours=1)
        start, end = _parse_window_hours(os.environ.get("CTOA_CATALOG_WINDOW_PL", "16-23"), 16, 23)
    elif profile == "BR":
        base = datetime.now(timezone.utc) - timedelta(hours=3)
        start, end = _parse_window_hours(os.environ.get("CTOA_CATALOG_WINDOW_BR", "18-03"), 18, 3)
    else:
        base = datetime.now(timezone.utc)
        start, end = _parse_window_hours(os.environ.get("CTOA_CATALOG_WINDOW_GLOBAL", "00-23"), 0, 23)

    if not _hour_in_window(base.hour, start, end):
        return False

    # Keep global top lists always allowed when launch window is open.
    if "otservlist.org" in host or "open-tibia.com" in host or "tibiaservers.net" in host:
        return True
    if profile == "PL" and ("tibiaots.pl" in host or "otlist.pl" in host or "vatira.pl" in host):
        return True
    if profile == "BR" and ("otland.net" in host or "br" in host):
        return True
    return profile == "GLOBAL"


def _source_priority(source_url: str) -> tuple[int, str]:
    host = (urllib.parse.urlparse(source_url).netloc or "").lower()
    for needle, score, bucket in SOURCE_PRIORITY_RULES:
        if needle in host:
            return score, bucket
    return 5, "unknown"


def _default_sources() -> list[str]:
    raw = os.environ.get("CTOA_CATALOG_SOURCES", "").strip()
    if raw:
        return [u.strip() for u in raw.split(",") if u.strip()]
    return CATALOG_PROFILE_SOURCES[_catalog_profile()][:]


def _fetch_text(url: str) -> tuple[int, str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "CTOACatalog/1.0 (+https://github.com/famatyyk/CTOAi)",
            "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT, context=_SSL_CTX) as r:
            status = int(r.status)
            raw = r.read(MAX_HTML_BYTES).decode("utf-8", errors="replace")
            return status, raw
    except urllib.error.HTTPError as exc:
        return int(exc.code), ""
    except Exception:
        return 0, ""


def _is_candidate_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").lower()
    if not host:
        return False
    if any(snippet in host for snippet in BLOCKED_HOST_SNIPPETS):
        return False
    if "/forum" in path or "/forums" in path or "/thread" in path:
        return False
    if path.endswith(BLOCKED_PATH_SUFFIXES):
        return False
    if host.startswith("localhost") or host.startswith("127."):
        return False
    if not any(h in host for h in ALLOWED_HOST_HINTS):
        return False
    return True


def _extract_candidates(source_url: str, body: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    source_host = (urllib.parse.urlparse(source_url).netloc or "").lower()

    for m in URL_RE.finditer(body):
        url = m.group(0).rstrip("),.;\"'")
        if not _is_candidate_url(url):
            continue
        host = (urllib.parse.urlparse(url).netloc or "").lower()
        if source_host and (host == source_host or host.endswith(f".{source_host}")):
            # Skip internal catalog/forum links; we only want candidate server domains.
            continue
        if url in seen:
            continue

        left = max(0, m.start() - 180)
        right = min(len(body), m.end() + 180)
        context = body[left:right]

        seen.add(url)
        out.append((url, context))
        if len(out) >= MAX_CANDIDATES_PER_SOURCE:
            break

    return out


def _count_players_hint(text: str) -> int | None:
    lower = text.lower()
    if "online" not in lower and "players" not in lower and "graczy" not in lower:
        return None

    nums = re.findall(r"\b(\d{2,5})\b", text)
    if not nums:
        return None
    try:
        return max(int(n) for n in nums)
    except Exception:
        return None


def _score_candidate(source_url: str, context: str) -> tuple[int, list[str], int | None, dict[str, int | str | bool]]:
    c = context.lower()
    priority_score, source_bucket = _source_priority(source_url)
    score = priority_score
    tags: list[str] = []
    detail: dict[str, int | str | bool] = {
        "source_priority": priority_score,
        "source_bucket": source_bucket,
        "fresh_launch_boost": 0,
        "auto_approved": False,
    }

    for word in SIGNAL_KEYWORDS["new"]:
        if word in c:
            score += 20
            tags.append("new")
            # Lists are most decisive in first 24h of launch.
            if source_bucket.startswith("ots_list"):
                score += 25
                detail["fresh_launch_boost"] = 25
            break

    for word in SIGNAL_KEYWORDS["long_term"]:
        if word in c:
            score += 20
            tags.append("long_term")
            break

    pop_hint = _count_players_hint(context)
    if pop_hint is not None:
        if pop_hint >= 500:
            score += 40
            tags.append("high_pop")
        elif pop_hint >= 200:
            score += 25
            tags.append("mid_pop")
        elif pop_hint >= 100:
            score += 10
            tags.append("low_pop")

    tags = sorted(set(tags))
    if score >= AUTO_APPROVE_THRESHOLD and any(tag in tags for tag in ("new", "high_pop", "long_term")):
        detail["auto_approved"] = True
    return score, tags, pop_hint, detail


def _upsert_server(url: str) -> int | None:
    row = db.query_one("SELECT id FROM servers WHERE url=%s", (url,))
    if row and row.get("id"):
        return int(row["id"])

    db.execute(
        "INSERT INTO servers (url, status) VALUES (%s, 'NEW') "
        "ON CONFLICT (url) DO UPDATE SET updated_at=now()",
        (url,),
    )
    row2 = db.query_one("SELECT id FROM servers WHERE url=%s", (url,))
    if not row2:
        return None
    return int(row2["id"])


def _write_signal(
    server_id: int,
    source_url: str,
    score: int,
    tags: list[str],
    pop_hint: int | None,
    context: str,
    detail: dict[str, Any] | None = None,
) -> None:
    payload = {
        "kind": "catalog_signal",
        "source": source_url,
        "score": score,
        "tags": tags,
        "population_hint": pop_hint,
        "auto_approved": bool((detail or {}).get("auto_approved", False)),
        "source_priority": (detail or {}).get("source_priority", 0),
        "source_bucket": (detail or {}).get("source_bucket", "unknown"),
        "fresh_launch_boost": (detail or {}).get("fresh_launch_boost", 0),
        "observed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "context": context[:500],
    }
    db.execute(
        "INSERT INTO game_data (server_id, data_type, raw, fetched_at) VALUES (%s, %s, %s::jsonb, now())",
        (server_id, "catalog_signal", json.dumps(payload, ensure_ascii=True)),
    )


def _enrich_existing_servers() -> int:
    """Add catalog_signal for existing servers based on age + online metrics."""
    rows = db.query_all(
        """
        SELECT s.id, s.url, s.created_at,
               (
                 SELECT raw
                 FROM game_data g
                 WHERE g.server_id=s.id AND g.data_type='server_info'
                 ORDER BY g.fetched_at DESC
                 LIMIT 1
               ) AS server_info
        FROM servers s
        ORDER BY s.id
        """
    )

    written = 0
    now = datetime.now(timezone.utc)
    for row in rows:
        tags: list[str] = []
        score = 0
        pop_hint: int | None = None

        created_at = row.get("created_at")
        age_days = None
        if created_at is not None:
            try:
                age_days = max(0, int((now - created_at).total_seconds() // 86400))
            except Exception:
                age_days = None

        if age_days is not None:
            if age_days <= 7:
                tags.append("new")
                score += 20
            if age_days >= 45:
                tags.append("long_term")
                score += 20

        si = row.get("server_info")
        if isinstance(si, dict):
            try:
                pop_hint = int(si.get("online", si.get("players_online", 0)) or 0)
            except Exception:
                pop_hint = None

        if pop_hint is not None:
            if pop_hint >= 500:
                tags.append("high_pop")
                score += 40
            elif pop_hint >= 200:
                tags.append("mid_pop")
                score += 25
            elif pop_hint >= 100:
                tags.append("low_pop")
                score += 10

        if not tags:
            continue

        _write_signal(
            server_id=int(row["id"]),
            source_url="db:server_info",
            score=score,
            tags=sorted(set(tags)),
            pop_hint=pop_hint,
            context=f"age_days={age_days}; url={row.get('url','')}",
            detail={
                "source_priority": 10,
                "source_bucket": "db_enrichment",
                "fresh_launch_boost": 0,
                "auto_approved": score >= AUTO_APPROVE_THRESHOLD and any(tag in tags for tag in ("new", "high_pop", "long_term")),
            },
        )
        written += 1

    return written


def run_once() -> None:
    profile = _catalog_profile()
    sources = _default_sources()
    if not sources:
        log.info("No catalog sources configured")
        return

    eligible_sources = [src for src in sources if _source_allowed_now(src, profile)]
    if not eligible_sources:
        log.info("No eligible sources in current launch window for profile=%s", profile)
        return

    discovered = 0
    signaled = 0

    for source in eligible_sources:
        status, body = _fetch_text(source)
        if status not in (200, 206) or not body:
            log.warning("Source skipped %s (status=%s)", source, status)
            continue

        candidates = _extract_candidates(source, body)
        log.info("Source %s -> %d candidates", source, len(candidates))

        for url, context in candidates:
            server_id = _upsert_server(url)
            if not server_id:
                continue
            discovered += 1

            score, tags, pop_hint, detail = _score_candidate(source, context)
            if score <= 0 and not tags:
                continue

            _write_signal(server_id, source, score, tags, pop_hint, context, detail)
            signaled += 1

    enriched = _enrich_existing_servers()
    msg = (
        f"catalog discovered={discovered}, signaled={signaled}, "
        f"enriched_existing={enriched}, sources={len(eligible_sources)}, profile={profile}"
    )
    log.info(msg)
    db.log_run("catalog_agent", "ok", msg)


if __name__ == "__main__":
    run_once()