import json

import pytest

from runner.tibia_sources import (
    CollectedSource,
    LinkRecordParser,
    SnapshotArchive,
    collected_from_file,
    utc_now,
)


def test_snapshot_archive_preserves_raw_content_and_emits_added_then_changed(tmp_path):
    archive = SnapshotArchive(tmp_path / "archive")
    parser = LinkRecordParser(archive.root)
    first = CollectedSource(
        source_kind="news",
        fetched_at=utc_now(),
        url="https://www.tibia.com/news/",
        content=b'<html><a href="/news/?id=1">First update</a></html>',
        content_type="text/html",
        http_status=200,
    )
    first_snapshot, first_events = archive.ingest(first, parser=parser)

    assert first_events[0].diff_type == "added"
    assert any(event.entity_kind == "source_link" and event.diff_type == "added" for event in first_events)
    assert (archive.root / first_snapshot.raw_path).read_bytes() == first.content
    assert first_snapshot.content_hash

    second = CollectedSource(
        source_kind="news",
        fetched_at=utc_now(),
        url="https://www.tibia.com/news/",
        content=b'<html><a href="/news/?id=2">Second update</a></html>',
        content_type="text/html",
        http_status=200,
    )
    second_snapshot, second_events = archive.ingest(second, parser=parser)

    raw_change = next(event for event in second_events if event.entity_kind == "raw_snapshot")
    assert raw_change.diff_type == "changed"
    assert raw_change.payload["previous_snapshot_id"] == first_snapshot.snapshot_id
    assert any(event.entity_kind == "source_link" and event.diff_type == "removed" for event in second_events)
    assert second_snapshot.content_hash != first_snapshot.content_hash
    ledger = [json.loads(line) for line in archive.events_path.read_text(encoding="utf-8").splitlines()]
    raw_events = [event for event in ledger if event["entity_kind"] == "raw_snapshot"]
    assert [event["diff_type"] for event in raw_events] == ["added", "changed"]


def test_unchanged_snapshot_does_not_invent_a_diff_event(tmp_path):
    archive = SnapshotArchive(tmp_path / "archive")
    collected = CollectedSource(
        source_kind="library",
        fetched_at=utc_now(),
        url="https://www.tibia.com/library/",
        content=b"<html>same</html>",
        content_type="text/html",
        http_status=200,
    )
    archive.ingest(collected)
    _, events = archive.ingest(collected)
    assert events == []


def test_blocked_snapshot_is_preserved_and_inventory_reports_source_blocked(tmp_path):
    archive = SnapshotArchive(tmp_path / "archive")
    blocked = CollectedSource(
        source_kind="community_test",
        fetched_at=utc_now(),
        url="https://www.test.tibia.com/forum/",
        content=b"<html>Cloudflare challenge</html>",
        content_type="text/html",
        http_status=403,
        blocked_reason="source_blocked",
    )
    snapshot, events = archive.ingest(blocked)

    assert (archive.root / snapshot.raw_path).exists()
    assert events[0].diff_type == "blocked"
    inventory = json.loads(archive.inventory_path.read_text(encoding="utf-8"))
    source = next(item for item in inventory["sources"] if item["source_kind"] == "community_test")
    assert source["status"] == "source_blocked"
    assert source["raw_snapshot"]["content_hash"] == snapshot.content_hash


def test_parser_failure_keeps_raw_snapshot_and_emits_parser_error(tmp_path):
    class BrokenParser:
        def parse(self, _snapshot):
            raise ValueError("fixture changed")

    archive = SnapshotArchive(tmp_path / "archive")
    collected = CollectedSource(
        source_kind="character_trade",
        fetched_at=utc_now(),
        url="https://www.tibia.com/charactertrade/",
        content=b"<html>auction</html>",
        content_type="text/html",
        http_status=200,
    )
    snapshot, events = archive.ingest(collected, parser=BrokenParser())

    assert (archive.root / snapshot.raw_path).exists()
    parser_event = next(event for event in events if event.diff_type == "parser_error")
    assert parser_event.payload["preserve_raw_snapshot"] is True
    assert parser_event.payload["error_type"] == "ValueError"
    inventory = json.loads(archive.inventory_path.read_text(encoding="utf-8"))
    source = next(item for item in inventory["sources"] if item["source_kind"] == "character_trade")
    assert source["status"] == "parser_broken"
    assert source["freshness"] == "failed"
    assert source["parser"]["status"] == "broken"
    assert source["parser"]["last_error"] == "ValueError"


def test_archive_writes_control_center_source_index_contract(tmp_path):
    archive = SnapshotArchive(tmp_path / "archive")
    collected = CollectedSource(
        source_kind="news",
        fetched_at=utc_now(),
        url="https://www.tibia.com/news/",
        content=b"<html>news</html>",
        content_type="text/html",
        http_status=200,
    )
    archive.ingest(collected)

    index = json.loads(archive.index_path.read_text(encoding="utf-8"))
    assert index["schema_version"] == "ctoa-tibia-source-archive-v1"
    assert index["sources"]["news"]["status"] == "fresh"
    assert index["events"][0]["diff_type"] == "added"


def test_file_collector_rejects_non_official_url_and_oversized_input(tmp_path):
    snapshot = tmp_path / "snapshot.html"
    snapshot.write_text("<html></html>", encoding="utf-8")
    with pytest.raises(ValueError, match="allowlisted official host"):
        collected_from_file("news", snapshot, url="https://example.com/news/")

    snapshot.write_bytes(b"x" * (2 * 1024 * 1024 + 1))
    with pytest.raises(ValueError, match="maximum size"):
        collected_from_file("news", snapshot)
