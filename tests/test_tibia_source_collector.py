from __future__ import annotations

import json
from pathlib import Path

from scripts.ops.tibia_source_collector import FetchResult, RawSnapshot, SourceCollector, archive_snapshot


def _write_news_fixture(path: Path, entries: list[tuple[str, str]]) -> None:
    links = "\n".join(
        f'<a href="?subtopic=newsarchive&id={entry_id}">{title}</a>' for entry_id, title in entries
    )
    path.write_text(f"<html><body>{links}</body></html>", encoding="utf-8")


def test_archives_news_raw_html_and_emits_added_events(tmp_path: Path):
    fixture = tmp_path / "news.html"
    archive_dir = tmp_path / "archive"
    _write_news_fixture(fixture, [("101", "Summer Update: Weapon Proficiency"), ("102", "Boss Difficulty System")])

    result = archive_snapshot(archive_dir, SourceCollector().from_html_file("news", fixture))

    assert result["status"] == "fresh"
    assert result["parser"]["status"] == "ready"
    assert {event["diff_type"] for event in result["events"]} == {"added"}
    assert len(result["normalized_records"]) == 2
    assert (archive_dir / result["raw_path"]).read_text(encoding="utf-8") == fixture.read_text(encoding="utf-8")
    index = json.loads((archive_dir / "source-index.json").read_text(encoding="utf-8"))
    assert index["schema_version"] == "ctoa-tibia-source-archive-v1"
    assert index["sources"]["news"]["raw_snapshot"]["content_hash"]
    assert "blocked_reason" not in index["sources"]["news"]["raw_snapshot"]
    assert len((archive_dir / "update-ledger.jsonl").read_text(encoding="utf-8").splitlines()) == 2


def test_second_news_snapshot_emits_changed_and_removed_events(tmp_path: Path):
    archive_dir = tmp_path / "archive"
    first = tmp_path / "first.html"
    second = tmp_path / "second.html"
    _write_news_fixture(first, [("101", "Weapon Proficiency"), ("102", "Boss Difficulty")])
    _write_news_fixture(second, [("101", "Weapon Proficiency Revised")])

    archive_snapshot(archive_dir, SourceCollector().from_html_file("news", first))
    result = archive_snapshot(archive_dir, SourceCollector().from_html_file("news", second))

    event_types = {(event["diff_type"], event["entity_id"]) for event in result["events"]}
    assert ("changed", "101") in event_types
    assert ("removed", "102") in event_types


def test_blocked_and_parser_broken_attempts_keep_raw_evidence(tmp_path: Path):
    archive_dir = tmp_path / "archive"
    blocked = FetchResult(
        raw_snapshot=RawSnapshot(
            source_kind="news",
            fetched_at="2026-07-09T12:00:00.000Z",
            url="https://www.tibia.com/news/",
            content_hash="a" * 64,
            blocked_reason="source_blocked",
        ),
        body=b"<html>Cloudflare challenge</html>",
        status="source_blocked",
        fetch_error="HTTP 403",
    )
    blocked_result = archive_snapshot(archive_dir, blocked)

    assert blocked_result["status"] == "source_blocked"
    assert blocked_result["parser"]["status"] == "blocked"
    assert blocked_result["events"][0]["diff_type"] == "blocked"
    assert (archive_dir / blocked_result["raw_path"]).read_bytes() == blocked.body

    malformed = tmp_path / "malformed.html"
    malformed.write_text("<html><body>News landing page without archive links</body></html>", encoding="utf-8")
    broken_result = archive_snapshot(archive_dir, SourceCollector().from_html_file("news", malformed))

    assert broken_result["status"] == "parser_broken"
    assert broken_result["parser"]["status"] == "broken"
    assert broken_result["events"][0]["diff_type"] == "parser_error"
    assert (archive_dir / broken_result["raw_path"]).exists()


def test_unimplemented_source_parser_stays_pending_without_losing_its_raw_snapshot(tmp_path: Path):
    archive_dir = tmp_path / "archive"
    fixture = tmp_path / "library.html"
    fixture.write_text("<html><body>Library source capture</body></html>", encoding="utf-8")

    result = archive_snapshot(archive_dir, SourceCollector().from_html_file("library", fixture))

    assert result["status"] == "stale_snapshot"
    assert result["parser"]["status"] == "pending_fixture"
    assert result["parser"]["last_error"] == "No parser fixture is registered for library."
    assert (archive_dir / result["raw_path"]).read_text(encoding="utf-8") == fixture.read_text(encoding="utf-8")
