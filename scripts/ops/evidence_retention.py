"""Utilities for evidence index retention policy (CTOA-139)."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

DEFAULT_MAX_ENTRIES = 100
DEFAULT_MAX_AGE_DAYS = 30


def _parse_iso_utc(value: str) -> datetime | None:
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def read_retention_policy_from_env() -> tuple[int, int]:
    max_entries = DEFAULT_MAX_ENTRIES
    max_age_days = DEFAULT_MAX_AGE_DAYS

    raw_entries = os.getenv("CTOA_EVIDENCE_INDEX_MAX_ENTRIES", "").strip()
    if raw_entries:
        try:
            parsed_entries = int(raw_entries)
            if parsed_entries > 0:
                max_entries = parsed_entries
        except ValueError:
            pass

    raw_days = os.getenv("CTOA_EVIDENCE_INDEX_MAX_AGE_DAYS", "").strip()
    if raw_days:
        try:
            parsed_days = int(raw_days)
            if parsed_days > 0:
                max_age_days = parsed_days
        except ValueError:
            pass

    return max_entries, max_age_days


def apply_retention_policy(
    entries: list[dict],
    *,
    max_entries: int,
    max_age_days: int,
    now: datetime | None = None,
) -> list[dict]:
    now_utc = now.astimezone(UTC) if now is not None else datetime.now(UTC)
    cutoff = now_utc - timedelta(days=max_age_days)

    normalized: list[tuple[datetime, dict]] = []
    for item in entries:
        if not isinstance(item, dict):
            continue
        recorded_at = _parse_iso_utc(str(item.get("recorded_at", "")))
        if recorded_at is None:
            continue
        if recorded_at < cutoff:
            continue
        normalized.append((recorded_at, item))

    normalized.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in normalized[:max_entries]]
