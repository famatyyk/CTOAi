"""Local-first Tibia.com snapshot archive, parser adapters, and diff ledger."""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urljoin, urlparse

import httpx


SOURCE_DEFINITIONS: dict[str, dict[str, Any]] = {
    "news": {
        "label": "Tibia.com News",
        "url": "https://www.tibia.com/news/",
        "normalized_kinds": [
            "news/security",
            "news/fixes",
            "weapon_proficiency",
            "boss_difficulty",
            "monk_virtues",
        ],
    },
    "library": {
        "label": "Tibia.com Library",
        "url": "https://www.tibia.com/library/",
        "normalized_kinds": [
            "creatures",
            "spells",
            "achievements",
            "world_quests",
            "maps",
        ],
    },
    "character_trade": {
        "label": "Tibia.com Character Trade",
        "url": "https://www.tibia.com/charactertrade/",
        "normalized_kinds": ["char_bazaar"],
    },
    "community_test": {
        "label": "Tibia.com Community/Test",
        "url": "https://www.test.tibia.com/forum/",
        "normalized_kinds": [
            "weapon_proficiency",
            "boss_difficulty",
            "monk_virtues",
        ],
    },
}

ALLOWED_HOSTS = {"www.tibia.com", "www.test.tibia.com"}
MAX_SNAPSHOT_BYTES = 2 * 1024 * 1024
SCHEMA_VERSION = "ctoa-tibia-sources-v1"
WEB_INDEX_SCHEMA_VERSION = "ctoa-tibia-source-archive-v1"


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class CollectedSource:
    source_kind: str
    fetched_at: str
    url: str
    content: bytes
    content_type: str
    http_status: int | None = None
    blocked_reason: str | None = None


@dataclass(frozen=True)
class RawSnapshot:
    snapshot_id: str
    source_kind: str
    fetched_at: str
    url: str
    content_hash: str
    content_type: str
    byte_count: int
    http_status: int | None
    blocked_reason: str | None
    raw_path: str


@dataclass(frozen=True)
class NormalizedRecord:
    entity_kind: str
    entity_id: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class UpdateEvent:
    event_id: str
    source_kind: str
    entity_kind: str
    entity_id: str
    detected_at: str
    diff_type: str
    payload: dict[str, Any]


class SourceCollector(Protocol):
    def fetch(self, source_kind: str, cursor: str | None = None) -> CollectedSource:
        """Fetch one source page without persisting it."""


class SourceParser(Protocol):
    def parse(self, snapshot: RawSnapshot) -> list[NormalizedRecord]:
        """Parse a persisted raw snapshot into normalized records."""


class ClientAdapter(Protocol):
    def detect(self) -> dict[str, Any]:
        """Return a client capability report."""


class HttpTibiaCollector:
    """Bounded HTTP collector restricted to official Tibia hosts."""

    def __init__(self, *, timeout_seconds: float = 15.0) -> None:
        self.timeout_seconds = timeout_seconds

    def fetch(self, source_kind: str, cursor: str | None = None) -> CollectedSource:
        definition = source_definition(source_kind)
        url = cursor or str(definition["url"])
        return self._fetch(source_kind, url, redirects_remaining=3)

    def _fetch(
        self,
        source_kind: str,
        url: str,
        *,
        redirects_remaining: int,
    ) -> CollectedSource:
        _validate_source_url(url)
        headers = {
            "Accept": "text/html,application/xhtml+xml",
            "User-Agent": "CTOAi-Tibia-Snapshot/1.0 (local observability)",
        }
        try:
            with httpx.Client(
                follow_redirects=False,
                timeout=self.timeout_seconds,
                headers=headers,
            ) as client:
                response = client.get(url)
        except httpx.HTTPError as exc:
            return CollectedSource(
                source_kind=source_kind,
                fetched_at=utc_now(),
                url=url,
                content=str(exc.__class__.__name__).encode("ascii", errors="replace"),
                content_type="text/plain",
                blocked_reason="source_blocked",
            )

        if response.is_redirect:
            location = response.headers.get("location", "")
            redirected = urljoin(url, location)
            try:
                _validate_source_url(redirected)
            except ValueError:
                return CollectedSource(
                    source_kind=source_kind,
                    fetched_at=utc_now(),
                    url=url,
                    content=response.content[:MAX_SNAPSHOT_BYTES],
                    content_type=response.headers.get("content-type", "text/html"),
                    http_status=response.status_code,
                    blocked_reason="source_blocked",
                )
            if redirects_remaining <= 0:
                return CollectedSource(
                    source_kind=source_kind,
                    fetched_at=utc_now(),
                    url=url,
                    content=response.content[:MAX_SNAPSHOT_BYTES],
                    content_type=response.headers.get("content-type", "text/html"),
                    http_status=response.status_code,
                    blocked_reason="source_blocked",
                )
            return self._fetch(
                source_kind,
                redirected,
                redirects_remaining=redirects_remaining - 1,
            )

        content = response.content
        if len(content) > MAX_SNAPSHOT_BYTES:
            raise ValueError("snapshot exceeds maximum size")
        blocked = _blocked_reason(response.status_code, content)
        return CollectedSource(
            source_kind=source_kind,
            fetched_at=utc_now(),
            url=url,
            content=content,
            content_type=response.headers.get("content-type", "text/html"),
            http_status=response.status_code,
            blocked_reason=blocked,
        )


class _AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._href: str | None = None
        self._text: list[str] = []
        self.anchors: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a" or self._href is not None:
            return
        values = dict(attrs)
        href = values.get("href")
        if href:
            self._href = href
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or self._href is None:
            return
        text = " ".join("".join(self._text).split())
        if text:
            self.anchors.append((self._href, text))
        self._href = None
        self._text = []


class LinkRecordParser:
    """Conservative HTML adapter that normalizes visible links only."""

    def __init__(self, archive_root: Path) -> None:
        self.archive_root = archive_root

    def parse(self, snapshot: RawSnapshot) -> list[NormalizedRecord]:
        raw_path = _safe_archive_path(self.archive_root, snapshot.raw_path)
        content = raw_path.read_bytes()
        parser = _AnchorParser()
        parser.feed(content.decode("utf-8", errors="replace"))
        records: list[NormalizedRecord] = []
        seen: set[str] = set()
        for href, text in parser.anchors:
            url = urljoin(snapshot.url, href)
            parsed = urlparse(url)
            if parsed.hostname and parsed.hostname.lower() not in ALLOWED_HOSTS:
                continue
            entity_id = hashlib.sha256(f"{url}\n{text}".encode()).hexdigest()[:24]
            if entity_id in seen:
                continue
            seen.add(entity_id)
            records.append(
                NormalizedRecord(
                    entity_kind="source_link",
                    entity_id=entity_id,
                    payload={"title": text[:500], "url": url},
                )
            )
        return records


class SnapshotArchive:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.raw_root = self.root / "raw"
        self.metadata_root = self.root / "metadata"
        self.latest_root = self.root / "latest"
        self.events_path = self.root / "events.jsonl"
        self.inventory_path = self.root / "inventory.json"
        self.index_path = self.root / "source-index.json"

    def ingest(
        self,
        collected: CollectedSource,
        parser: SourceParser | None = None,
    ) -> tuple[RawSnapshot, list[UpdateEvent]]:
        source_definition(collected.source_kind)
        _validate_source_url(collected.url)
        if len(collected.content) > MAX_SNAPSHOT_BYTES:
            raise ValueError("snapshot exceeds maximum size")

        content_hash = hashlib.sha256(collected.content).hexdigest()
        timestamp = _timestamp_slug(collected.fetched_at)
        snapshot_id = f"{timestamp}-{content_hash[:16]}"
        raw_relative = Path("raw") / collected.source_kind / f"{snapshot_id}.html"
        raw_path = self.root / raw_relative
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        if not raw_path.exists():
            _atomic_write_bytes(raw_path, collected.content)

        snapshot = RawSnapshot(
            snapshot_id=snapshot_id,
            source_kind=collected.source_kind,
            fetched_at=collected.fetched_at,
            url=collected.url,
            content_hash=content_hash,
            content_type=collected.content_type,
            byte_count=len(collected.content),
            http_status=collected.http_status,
            blocked_reason=collected.blocked_reason,
            raw_path=raw_relative.as_posix(),
        )
        previous = self.latest(collected.source_kind)
        metadata_path = self.metadata_root / collected.source_kind / f"{snapshot_id}.json"
        _atomic_write_json(metadata_path, asdict(snapshot))
        _atomic_write_json(self.latest_root / f"{collected.source_kind}.json", asdict(snapshot))

        events = self._diff_events(previous, snapshot)
        if parser and not snapshot.blocked_reason:
            try:
                records = parser.parse(snapshot)
                events.extend(self._record_diff_events(previous, snapshot, records))
                _atomic_write_json(
                    self.metadata_root / collected.source_kind / f"{snapshot_id}.records.json",
                    {"schema_version": SCHEMA_VERSION, "records": [asdict(item) for item in records]},
                )
                (self.latest_root / f"{collected.source_kind}.parser-error.json").unlink(
                    missing_ok=True
                )
            except Exception as exc:  # Parser failure must preserve raw evidence.
                parser_event = UpdateEvent(
                        event_id=f"parser-{snapshot.snapshot_id}",
                        source_kind=snapshot.source_kind,
                        entity_kind="source_status",
                        entity_id=snapshot.source_kind,
                        detected_at=utc_now(),
                        diff_type="parser_error",
                        payload={
                            "status": "parser_broken",
                            "error_type": exc.__class__.__name__,
                            "snapshot_id": snapshot.snapshot_id,
                            "preserve_raw_snapshot": True,
                        },
                    )
                events.append(parser_event)
                _atomic_write_json(
                    self.latest_root / f"{collected.source_kind}.parser-error.json",
                    asdict(parser_event),
                )
        self._append_events(events)
        self._write_inventory()
        return snapshot, events

    def _record_diff_events(
        self,
        previous: RawSnapshot | None,
        current: RawSnapshot,
        records: list[NormalizedRecord],
    ) -> list[UpdateEvent]:
        previous_records = self._records_for(previous)
        previous_by_id = {item.entity_id: item for item in previous_records}
        current_by_id = {item.entity_id: item for item in records}
        events: list[UpdateEvent] = []
        for entity_id in sorted(current_by_id):
            item = current_by_id[entity_id]
            prior = previous_by_id.get(entity_id)
            if prior is None:
                diff_type = "added"
            elif prior.payload != item.payload or prior.entity_kind != item.entity_kind:
                diff_type = "changed"
            else:
                continue
            events.append(
                UpdateEvent(
                    event_id=f"record-{diff_type}-{current.snapshot_id}-{entity_id}",
                    source_kind=current.source_kind,
                    entity_kind=item.entity_kind,
                    entity_id=entity_id,
                    detected_at=utc_now(),
                    diff_type=diff_type,
                    payload={
                        **item.payload,
                        "snapshot_id": current.snapshot_id,
                        **(
                            {"previous": prior.payload}
                            if diff_type == "changed" and prior
                            else {}
                        ),
                    },
                )
            )
        for entity_id in sorted(previous_by_id.keys() - current_by_id.keys()):
            item = previous_by_id[entity_id]
            events.append(
                UpdateEvent(
                    event_id=f"record-removed-{current.snapshot_id}-{entity_id}",
                    source_kind=current.source_kind,
                    entity_kind=item.entity_kind,
                    entity_id=entity_id,
                    detected_at=utc_now(),
                    diff_type="removed",
                    payload={
                        **item.payload,
                        "snapshot_id": current.snapshot_id,
                    },
                )
            )
        return events

    def _records_for(self, snapshot: RawSnapshot | None) -> list[NormalizedRecord]:
        if snapshot is None:
            return []
        path = (
            self.metadata_root
            / snapshot.source_kind
            / f"{snapshot.snapshot_id}.records.json"
        )
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return []
        records = payload.get("records", []) if isinstance(payload, dict) else []
        result: list[NormalizedRecord] = []
        for item in records:
            if not isinstance(item, dict) or not isinstance(item.get("payload"), dict):
                continue
            try:
                result.append(
                    NormalizedRecord(
                        entity_kind=str(item["entity_kind"]),
                        entity_id=str(item["entity_id"]),
                        payload=item["payload"],
                    )
                )
            except KeyError:
                continue
        return result

    def latest(self, source_kind: str) -> RawSnapshot | None:
        path = self.latest_root / f"{source_kind}.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return RawSnapshot(**payload)
        except (FileNotFoundError, json.JSONDecodeError, TypeError):
            return None

    def _diff_events(
        self,
        previous: RawSnapshot | None,
        current: RawSnapshot,
    ) -> list[UpdateEvent]:
        detected_at = utc_now()
        if current.blocked_reason:
            return [
                UpdateEvent(
                    event_id=f"blocked-{current.snapshot_id}",
                    source_kind=current.source_kind,
                    entity_kind="source_status",
                    entity_id=current.source_kind,
                    detected_at=detected_at,
                    diff_type="blocked",
                    payload={
                        "status": "source_blocked",
                        "snapshot_id": current.snapshot_id,
                        "preserve_raw_snapshot": True,
                    },
                )
            ]
        if previous and previous.content_hash == current.content_hash:
            return []
        diff_type = "added" if previous is None else "changed"
        return [
            UpdateEvent(
                event_id=f"{diff_type}-{current.snapshot_id}",
                source_kind=current.source_kind,
                entity_kind="raw_snapshot",
                entity_id=current.source_kind,
                detected_at=detected_at,
                diff_type=diff_type,
                payload={
                    "snapshot_id": current.snapshot_id,
                    "previous_snapshot_id": previous.snapshot_id if previous else None,
                    "content_hash": current.content_hash,
                    "previous_content_hash": previous.content_hash if previous else None,
                },
            )
        ]

    def _append_events(self, events: list[UpdateEvent]) -> None:
        if not events:
            return
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        with self.events_path.open("a", encoding="utf-8", newline="\n") as handle:
            for event in events:
                handle.write(json.dumps(asdict(event), sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def _write_inventory(self) -> None:
        sources: list[dict[str, Any]] = []
        for source_kind, definition in SOURCE_DEFINITIONS.items():
            latest = self.latest(source_kind)
            parser_error = self._latest_parser_error(source_kind)
            if latest is None:
                status = "stale_snapshot"
                freshness = "stale"
                parser_status = "pending_fixture"
                raw_snapshot: dict[str, Any] = {
                    "source_kind": source_kind,
                    "fetched_at": None,
                    "url": definition["url"],
                    "content_hash": None,
                    "blocked_reason": "stale_snapshot",
                }
            else:
                status = (
                    "source_blocked"
                    if latest.blocked_reason
                    else "parser_broken"
                    if parser_error
                    else "fresh"
                )
                freshness = (
                    "blocked"
                    if latest.blocked_reason
                    else "failed"
                    if parser_error
                    else "live"
                )
                parser_status = (
                    "blocked"
                    if latest.blocked_reason
                    else "broken"
                    if parser_error
                    else "ready"
                )
                raw_snapshot = {
                    "source_kind": source_kind,
                    "fetched_at": latest.fetched_at,
                    "url": latest.url,
                    "content_hash": latest.content_hash,
                    **({"blocked_reason": latest.blocked_reason} if latest.blocked_reason else {}),
                }
            sources.append(
                {
                    "source_kind": source_kind,
                    "label": definition["label"],
                    "url": definition["url"],
                    "status": status,
                    "freshness": freshness,
                    "raw_snapshot": raw_snapshot,
                    "parser": {
                        "status": parser_status,
                        "normalized_kinds": definition["normalized_kinds"],
                        "last_error": (
                            str(parser_error.get("payload", {}).get("error_type"))
                            if parser_error
                            else None
                        ),
                    },
                    "next_action": _next_action(status),
                }
            )
        inventory = {
            "schema_version": SCHEMA_VERSION,
            "generated_at": utc_now(),
            "mode": "snapshot_archive",
            "sources": sources,
        }
        _atomic_write_json(
            self.inventory_path,
            inventory,
        )
        _atomic_write_json(
            self.index_path,
            {
                "schema_version": WEB_INDEX_SCHEMA_VERSION,
                "generated_at": inventory["generated_at"],
                "sources": {item["source_kind"]: item for item in sources},
                "events": self._recent_events(200),
            },
        )

    def _latest_parser_error(self, source_kind: str) -> dict[str, Any] | None:
        path = self.latest_root / f"{source_kind}.parser-error.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else None
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def _recent_events(self, limit: int) -> list[dict[str, Any]]:
        try:
            lines = self.events_path.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            return []
        events: list[dict[str, Any]] = []
        for line in lines[-limit:]:
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                events.append(payload)
        return events


def source_definition(source_kind: str) -> dict[str, Any]:
    try:
        return SOURCE_DEFINITIONS[source_kind]
    except KeyError as exc:
        raise ValueError(f"unsupported source kind: {source_kind}") from exc


def collected_from_file(source_kind: str, path: Path, *, url: str | None = None) -> CollectedSource:
    definition = source_definition(source_kind)
    content = path.read_bytes()
    if len(content) > MAX_SNAPSHOT_BYTES:
        raise ValueError("snapshot exceeds maximum size")
    source_url = url or str(definition["url"])
    _validate_source_url(source_url)
    return CollectedSource(
        source_kind=source_kind,
        fetched_at=utc_now(),
        url=source_url,
        content=content,
        content_type="text/html",
    )


def _validate_source_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() not in ALLOWED_HOSTS:
        raise ValueError("Tibia source URL must use HTTPS on an allowlisted official host")
    if parsed.username or parsed.password or parsed.fragment:
        raise ValueError("Tibia source URL must not include credentials or fragments")


def _blocked_reason(status_code: int, content: bytes) -> str | None:
    sample = content[:131072].decode("utf-8", errors="ignore").lower()
    markers = ("cloudflare", "cf-chl-", "captcha", "access denied")
    if status_code in {403, 429, 503} or any(marker in sample for marker in markers):
        return "source_blocked"
    return None


def _timestamp_slug(value: str) -> str:
    slug = re.sub(r"[^0-9]", "", value)[:14]
    return slug or datetime.now(UTC).strftime("%Y%m%d%H%M%S")


def _safe_archive_path(root: Path, relative: str) -> Path:
    candidate = (root.resolve() / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError("snapshot path escapes archive root") from exc
    return candidate


def _temporary_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = _temporary_path(path)
    try:
        with temporary.open("wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    content = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    _atomic_write_bytes(path, content)


def _next_action(status: str) -> str:
    if status == "fresh":
        return "Poll on schedule and review the diff ledger for changes."
    if status == "source_blocked":
        return "Preserve the blocked response and retry with bounded backoff."
    if status == "parser_broken":
        return "Repair the parser against the preserved raw snapshot, then re-ingest."
    return "Ingest the first approved raw HTML snapshot."
