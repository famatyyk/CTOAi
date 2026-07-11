"""Archive Tibia.com source snapshots and derive a local change ledger.

The collector is deliberately local-first: every poll attempt receives a unique
snapshot directory, including blocked and parser-failed attempts.  The current
index is a convenience view only; the raw HTML and per-snapshot metadata are
the durable evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Literal
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urljoin, urlparse
from urllib.request import Request, urlopen


ARCHIVE_SCHEMA_VERSION = "ctoa-tibia-source-archive-v1"
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_INDEX_EVENTS = 500
ALLOWED_TIBIA_HOSTS = {"tibia.com", "www.tibia.com", "test.tibia.com", "www.test.tibia.com"}

OperationalStatus = Literal["fresh", "source_blocked", "parser_broken", "stale_snapshot"]
ParserStatus = Literal["ready", "blocked", "broken", "pending_fixture"]
DiffType = Literal["added", "changed", "removed", "blocked", "parser_error"]


@dataclass(frozen=True)
class SourceDefinition:
    source_kind: str
    label: str
    url: str
    normalized_kinds: tuple[str, ...]


SOURCES: dict[str, SourceDefinition] = {
    "news": SourceDefinition(
        source_kind="news",
        label="Tibia.com News",
        url="https://www.tibia.com/news/",
        normalized_kinds=("news/security", "news/fixes", "weapon_proficiency", "boss_difficulty", "monk_virtues"),
    ),
    "library": SourceDefinition(
        source_kind="library",
        label="Tibia.com Library",
        url="https://www.tibia.com/library/",
        normalized_kinds=("creatures", "spells", "achievements", "world_quests", "maps"),
    ),
    "character_trade": SourceDefinition(
        source_kind="character_trade",
        label="Tibia.com Character Trade",
        url="https://www.tibia.com/charactertrade/",
        normalized_kinds=("char_bazaar",),
    ),
    "community_test": SourceDefinition(
        source_kind="community_test",
        label="Tibia.com Community/Test",
        url="https://www.test.tibia.com/forum/",
        normalized_kinds=("weapon_proficiency", "boss_difficulty", "monk_virtues"),
    ),
}


@dataclass(frozen=True)
class RawSnapshot:
    source_kind: str
    fetched_at: str
    url: str
    content_hash: str
    blocked_reason: str | None = None


@dataclass(frozen=True)
class UpdateEvent:
    event_id: str
    source_kind: str
    entity_kind: str
    entity_id: str
    detected_at: str
    diff_type: DiffType
    payload: dict[str, Any]


@dataclass(frozen=True)
class FetchResult:
    raw_snapshot: RawSnapshot
    body: bytes
    status: OperationalStatus
    fetch_error: str | None


class NewsParseError(ValueError):
    """Raised when a News snapshot cannot be normalized safely."""


class ParserPendingFixture(ValueError):
    """Raised when a source is archived but its parser has not been introduced."""


class NewsLinkParser(HTMLParser):
    """Read only explicit Tibia News archive links from an HTML snapshot."""

    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self._active: dict[str, str] | None = None
        self._text: list[str] = []
        self.links: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a" or self._active is not None:
            return
        values = {key.lower(): value or "" for key, value in attrs}
        href = values.get("href", "").strip()
        news_id = values.get("data-news-id", "").strip()
        if not news_id and "newsarchive" not in href.lower():
            return
        self._active = {"href": urljoin(self.base_url, href), "data_news_id": news_id}
        self._text = []

    def handle_data(self, data: str) -> None:
        if self._active is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or self._active is None:
            return
        title = _clean_text(" ".join(self._text))
        if title:
            self.links.append({**self._active, "title": title})
        self._active = None
        self._text = []


class SourceParser:
    """Adapter interface for normalized records derived from a raw snapshot."""

    def parse(self, snapshot: RawSnapshot, body: bytes) -> list[dict[str, Any]]:
        if snapshot.source_kind != "news":
            raise ParserPendingFixture(f"No parser fixture is registered for {snapshot.source_kind}.")
        return self._parse_news(snapshot, body)

    @staticmethod
    def _parse_news(snapshot: RawSnapshot, body: bytes) -> list[dict[str, Any]]:
        parser = NewsLinkParser(snapshot.url)
        parser.feed(body.decode("utf-8", errors="replace"))
        parser.close()

        records: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for link in parser.links:
            entity_id = _news_entity_id(link)
            if entity_id in seen_ids:
                continue
            seen_ids.add(entity_id)
            records.append(
                {
                    "source_kind": "news",
                    "entity_kind": "news",
                    "entity_id": entity_id,
                    "payload": {
                        "title": link["title"],
                        "url": link["href"],
                    },
                }
            )

        if not records:
            raise NewsParseError("No Tibia News archive links found in raw snapshot.")
        return records


class SourceCollector:
    """Bounded, allowlisted collector for public Tibia.com HTML surfaces."""

    def __init__(
        self,
        *,
        timeout_seconds: float = 15.0,
        opener: Callable[..., Any] = urlopen,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.opener = opener

    def fetch(self, source_kind: str, cursor: str | None = None) -> FetchResult:
        definition = _source_definition(source_kind)
        url = cursor.strip() if cursor else definition.url
        _validate_source_url(url)
        fetched_at = _utc_now()

        request = Request(
            url,
            headers={
                "User-Agent": "CTOAi-TibiaSnapshotCollector/1.0 (+local evidence archive)",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        try:
            with self.opener(request, timeout=self.timeout_seconds) as response:
                body, truncated = _read_limited(response)
                status_code = getattr(response, "status", 200)
            if truncated:
                return _fetch_result(source_kind, url, fetched_at, body, "stale_snapshot", f"Response exceeded {MAX_RESPONSE_BYTES} byte collector limit.")
            if _looks_blocked(body):
                return _fetch_result(source_kind, url, fetched_at, body, "source_blocked", "Cloudflare or access challenge detected.")
            if status_code >= 400:
                status = "source_blocked" if status_code in {401, 403, 429, 503} else "stale_snapshot"
                return _fetch_result(source_kind, url, fetched_at, body, status, f"HTTP {status_code}")
            return _fetch_result(source_kind, url, fetched_at, body, "fresh", None)
        except HTTPError as error:
            body, truncated = _read_limited(error)
            if truncated:
                return _fetch_result(source_kind, url, fetched_at, body, "stale_snapshot", f"HTTP {error.code}; response exceeded {MAX_RESPONSE_BYTES} byte collector limit.")
            status = "source_blocked" if error.code in {401, 403, 429, 503} or _looks_blocked(body) else "stale_snapshot"
            return _fetch_result(source_kind, url, fetched_at, body, status, f"HTTP {error.code}")
        except (TimeoutError, URLError, OSError) as error:
            return _fetch_result(source_kind, url, fetched_at, b"", "stale_snapshot", _bounded_error(error))

    def from_html_file(self, source_kind: str, html_file: Path, cursor: str | None = None) -> FetchResult:
        definition = _source_definition(source_kind)
        url = cursor.strip() if cursor else definition.url
        _validate_source_url(url)
        with html_file.open("rb") as handle:
            body = handle.read(MAX_RESPONSE_BYTES + 1)
        if len(body) > MAX_RESPONSE_BYTES:
            return _fetch_result(
                source_kind,
                url,
                _utc_now(),
                body[:MAX_RESPONSE_BYTES],
                "stale_snapshot",
                f"Fixture exceeded {MAX_RESPONSE_BYTES} byte collector limit.",
            )
        status: OperationalStatus = "source_blocked" if _looks_blocked(body) else "fresh"
        error = "Cloudflare or access challenge detected in fixture." if status == "source_blocked" else None
        return _fetch_result(source_kind, url, _utc_now(), body, status, error)


def archive_snapshot(
    archive_dir: Path,
    fetched: FetchResult,
    *,
    parser: SourceParser | None = None,
) -> dict[str, Any]:
    """Persist a raw attempt, its parser outcome, and an append-only diff ledger."""

    definition = _source_definition(fetched.raw_snapshot.source_kind)
    archive_dir = archive_dir.resolve()
    source_dir = archive_dir / definition.source_kind
    source_dir.mkdir(parents=True, exist_ok=True)
    snapshot_id = _snapshot_id(fetched.raw_snapshot.fetched_at)
    raw_path = source_dir / f"{snapshot_id}.html"
    raw_path.write_bytes(fetched.body)

    parser = parser or SourceParser()
    status = fetched.status
    parser_status: ParserStatus
    parser_error: str | None = None
    normalized_records: list[dict[str, Any]] = []
    if status == "source_blocked":
        parser_status = "blocked"
    elif status == "stale_snapshot":
        parser_status = "pending_fixture"
    else:
        try:
            normalized_records = parser.parse(fetched.raw_snapshot, fetched.body)
            parser_status = "ready"
        except ParserPendingFixture as error:
            status = "stale_snapshot"
            parser_status = "pending_fixture"
            parser_error = str(error)
        except NewsParseError as error:
            status = "parser_broken"
            parser_status = "broken"
            parser_error = str(error)

    with _ArchiveLock(archive_dir):
        index = _read_index(archive_dir)
        previous = _previous_records(index, definition.source_kind)
        events = _build_events(
            source_kind=definition.source_kind,
            snapshot_id=snapshot_id,
            detected_at=fetched.raw_snapshot.fetched_at,
            status=status,
            fetch_error=fetched.fetch_error,
            parser_error=parser_error,
            previous_records=previous,
            current_records=normalized_records,
        )
        source_entry = {
            "source_kind": definition.source_kind,
            "label": definition.label,
            "url": fetched.raw_snapshot.url,
            "status": status,
            "freshness": _freshness_for(status),
            "raw_snapshot": _raw_snapshot_dict(fetched.raw_snapshot),
            "parser": {
                "status": parser_status,
                "normalized_kinds": list(definition.normalized_kinds),
                "last_error": parser_error or fetched.fetch_error,
            },
            "next_action": _next_action_for(status, definition.source_kind, parser_status),
            "snapshot_id": snapshot_id,
            "raw_path": str(raw_path.relative_to(archive_dir)).replace("\\", "/"),
            "normalized_records": normalized_records,
            "events": [asdict(event) for event in events],
        }
        metadata_path = source_dir / f"{snapshot_id}.json"
        _atomic_write_json(metadata_path, source_entry)

        sources = index.get("sources", {})
        if not isinstance(sources, dict):
            sources = {}
        sources[definition.source_kind] = source_entry
        prior_events = index.get("events", [])
        if not isinstance(prior_events, list):
            prior_events = []
        index = {
            "schema_version": ARCHIVE_SCHEMA_VERSION,
            "generated_at": fetched.raw_snapshot.fetched_at,
            "sources": sources,
            "events": (prior_events + [asdict(event) for event in events])[-MAX_INDEX_EVENTS:],
        }
        _atomic_write_json(archive_dir / "source-index.json", index)
        _append_ledger(archive_dir / "update-ledger.jsonl", events)

    return source_entry


def _fetch_result(
    source_kind: str,
    url: str,
    fetched_at: str,
    body: bytes,
    status: OperationalStatus,
    fetch_error: str | None,
) -> FetchResult:
    return FetchResult(
        raw_snapshot=RawSnapshot(
            source_kind=source_kind,
            fetched_at=fetched_at,
            url=url,
            content_hash=hashlib.sha256(body).hexdigest(),
            blocked_reason="source_blocked" if status == "source_blocked" else None,
        ),
        body=body,
        status=status,
        fetch_error=fetch_error,
    )


def _raw_snapshot_dict(snapshot: RawSnapshot) -> dict[str, Any]:
    result = asdict(snapshot)
    if result["blocked_reason"] is None:
        result.pop("blocked_reason")
    return result


def _build_events(
    *,
    source_kind: str,
    snapshot_id: str,
    detected_at: str,
    status: OperationalStatus,
    fetch_error: str | None,
    parser_error: str | None,
    previous_records: list[dict[str, Any]],
    current_records: list[dict[str, Any]],
) -> list[UpdateEvent]:
    if status == "source_blocked":
        return [
            UpdateEvent(
                event_id=f"{source_kind}-{snapshot_id}-blocked",
                source_kind=source_kind,
                entity_kind="source_status",
                entity_id=source_kind,
                detected_at=detected_at,
                diff_type="blocked",
                payload={"status": "source_blocked", "snapshot_id": snapshot_id, "error": fetch_error},
            )
        ]
    if status == "parser_broken":
        return [
            UpdateEvent(
                event_id=f"{source_kind}-{snapshot_id}-parser-error",
                source_kind=source_kind,
                entity_kind="source_status",
                entity_id=source_kind,
                detected_at=detected_at,
                diff_type="parser_error",
                payload={"status": "parser_broken", "snapshot_id": snapshot_id, "error": parser_error},
            )
        ]
    if status != "fresh":
        return []

    previous_by_key = {_record_key(record): record for record in previous_records}
    current_by_key = {_record_key(record): record for record in current_records}
    events: list[UpdateEvent] = []
    for key, record in current_by_key.items():
        previous = previous_by_key.get(key)
        if previous is None:
            diff_type: DiffType = "added"
        elif _canonical_json(previous.get("payload")) != _canonical_json(record.get("payload")):
            diff_type = "changed"
        else:
            continue
        events.append(_record_event(source_kind, snapshot_id, detected_at, diff_type, record))
    for key, record in previous_by_key.items():
        if key not in current_by_key:
            events.append(_record_event(source_kind, snapshot_id, detected_at, "removed", record))
    return events


def _record_event(
    source_kind: str,
    snapshot_id: str,
    detected_at: str,
    diff_type: Literal["added", "changed", "removed"],
    record: dict[str, Any],
) -> UpdateEvent:
    entity_kind = str(record["entity_kind"])
    entity_id = str(record["entity_id"])
    return UpdateEvent(
        event_id=f"{source_kind}-{snapshot_id}-{diff_type}-{entity_kind}-{entity_id}",
        source_kind=source_kind,
        entity_kind=entity_kind,
        entity_id=entity_id,
        detected_at=detected_at,
        diff_type=diff_type,
        payload=dict(record.get("payload", {})),
    )


def _previous_records(index: dict[str, Any], source_kind: str) -> list[dict[str, Any]]:
    sources = index.get("sources")
    if not isinstance(sources, dict):
        return []
    previous = sources.get(source_kind)
    if not isinstance(previous, dict):
        return []
    if previous.get("status") != "fresh":
        return []
    records = previous.get("normalized_records")
    return [record for record in records if isinstance(record, dict)] if isinstance(records, list) else []


def _read_index(archive_dir: Path) -> dict[str, Any]:
    index_path = archive_dir / "source-index.json"
    if not index_path.is_file():
        return {"schema_version": ARCHIVE_SCHEMA_VERSION, "sources": {}, "events": []}
    try:
        value = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema_version": ARCHIVE_SCHEMA_VERSION, "sources": {}, "events": []}
    if not isinstance(value, dict) or value.get("schema_version") != ARCHIVE_SCHEMA_VERSION:
        return {"schema_version": ARCHIVE_SCHEMA_VERSION, "sources": {}, "events": []}
    return value


def _append_ledger(path: Path, events: list[UpdateEvent]) -> None:
    if not events:
        return
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for event in events:
            handle.write(json.dumps(asdict(event), ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


class _ArchiveLock:
    def __init__(self, archive_dir: Path, timeout_seconds: float = 5.0) -> None:
        self.path = archive_dir / ".collector.lock"
        self.timeout_seconds = timeout_seconds
        self.acquired = False

    def __enter__(self) -> None:
        deadline = time.monotonic() + self.timeout_seconds
        while True:
            try:
                descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                    handle.write(json.dumps({"pid": os.getpid(), "created_at": _utc_now()}))
                self.acquired = True
                return None
            except FileExistsError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"Timed out waiting for source archive lock: {self.path}")
                time.sleep(0.05)

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self.acquired:
            self.path.unlink(missing_ok=True)


def _news_entity_id(link: dict[str, str]) -> str:
    if link["data_news_id"]:
        return _safe_identifier(link["data_news_id"])
    query = parse_qs(urlparse(link["href"]).query)
    identifier = next(iter(query.get("id", [])), "")
    if identifier:
        return _safe_identifier(identifier)
    digest = hashlib.sha256(f"{link['href']}\n{link['title']}".encode("utf-8")).hexdigest()[:16]
    return f"news-{digest}"


def _safe_identifier(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-")
    if not normalized:
        raise NewsParseError("News link contains an empty identifier.")
    return normalized[:128]


def _record_key(record: dict[str, Any]) -> str:
    return f"{record.get('entity_kind', '')}:{record.get('entity_id', '')}"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _clean_text(value: str) -> str:
    return " ".join(unescape(value).split())[:512]


def _looks_blocked(body: bytes) -> bool:
    text = body[:65536].decode("utf-8", errors="ignore").lower()
    return any(marker in text for marker in ("cloudflare", "cf-chl-", "attention required", "access denied"))


def _read_limited(response: Any) -> tuple[bytes, bool]:
    body = response.read(MAX_RESPONSE_BYTES + 1)
    return body[:MAX_RESPONSE_BYTES], len(body) > MAX_RESPONSE_BYTES


def _bounded_error(error: BaseException) -> str:
    return _clean_text(str(error) or error.__class__.__name__)[:512]


def _freshness_for(status: OperationalStatus) -> Literal["live", "blocked", "failed", "stale"]:
    return {
        "fresh": "live",
        "source_blocked": "blocked",
        "parser_broken": "failed",
        "stale_snapshot": "stale",
    }[status]


def _next_action_for(status: OperationalStatus, source_kind: str, parser_status: ParserStatus) -> str:
    if status == "fresh":
        return "Poll again on the configured interval; the raw snapshot and diff ledger are current."
    if status == "source_blocked":
        return "Queue manual verification or provide an approved raw HTML fixture; do not claim live parser output."
    if status == "parser_broken":
        return f"Repair the {source_kind} parser against this preserved raw snapshot before treating the source as fresh."
    if parser_status == "pending_fixture":
        return f"Add a fixture-backed {source_kind} parser before treating this raw snapshot as fresh."
    return "Retry the bounded collector; retain this failed attempt and the previous successful snapshot."


def _source_definition(source_kind: str) -> SourceDefinition:
    try:
        return SOURCES[source_kind]
    except KeyError as error:
        raise ValueError(f"Unsupported Tibia source kind: {source_kind}") from error


def _validate_source_url(value: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_TIBIA_HOSTS:
        raise ValueError("Collector URLs must use HTTPS and an approved Tibia.com host.")


def _snapshot_id(fetched_at: str) -> str:
    timestamp = fetched_at.replace("-", "").replace(":", "").replace("+00:00", "Z").replace(".", "")
    return f"{timestamp}-{uuid.uuid4().hex[:12]}"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def main() -> int:
    argument_parser = argparse.ArgumentParser(description="Archive a bounded Tibia.com HTML source snapshot and diff it locally.")
    argument_parser.add_argument("source_kind", choices=sorted(SOURCES))
    argument_parser.add_argument("--archive-dir", type=Path, default=Path("runtime") / "tibia_source_archive")
    argument_parser.add_argument("--input-html", type=Path, help="Use a local HTML fixture instead of performing a network request.")
    argument_parser.add_argument("--url", help="Optional allowlisted Tibia.com URL or cursor for this source.")
    argument_parser.add_argument("--timeout", type=float, default=15.0)
    arguments = argument_parser.parse_args()

    collector = SourceCollector(timeout_seconds=arguments.timeout)
    fetched = (
        collector.from_html_file(arguments.source_kind, arguments.input_html, arguments.url)
        if arguments.input_html
        else collector.fetch(arguments.source_kind, arguments.url)
    )
    result = archive_snapshot(arguments.archive_dir, fetched)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
