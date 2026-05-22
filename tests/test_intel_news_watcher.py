import json

from labs.projects.intel_news_watcher import watcher


def test_diff_items_detects_new_and_removed() -> None:
    previous = [
        {"title": "One", "url": "https://example.test/1"},
        {"title": "Two", "url": "https://example.test/2"},
    ]
    current = [
        {"title": "Two", "url": "https://example.test/2"},
        {"title": "Three", "url": "https://example.test/3"},
    ]

    diff = watcher._diff_items(previous, current)

    assert diff["new_count"] == 1
    assert diff["removed_count"] == 1
    assert diff["new_items"][0]["url"] == "https://example.test/3"
    assert diff["removed_items"][0]["url"] == "https://example.test/1"


def test_run_once_updates_state_and_emits_diff(tmp_path, monkeypatch) -> None:
    runtime_dir = tmp_path / "runtime"
    archive_dir = runtime_dir / "archive"
    state_file = runtime_dir / "state.json"
    latest_diff_file = runtime_dir / "latest_diff.json"

    monkeypatch.setattr(watcher, "RUNTIME_DIR", runtime_dir)
    monkeypatch.setattr(watcher, "ARCHIVE_DIR", archive_dir)
    monkeypatch.setattr(watcher, "STATE_FILE", state_file)
    monkeypatch.setattr(watcher, "LATEST_DIFF_FILE", latest_diff_file)
    monkeypatch.setattr(watcher, "_resolve_target_url", lambda: "https://example.test/news")

    snapshots = [
        {
            "requested_url": "https://example.test/news",
            "source_url": "https://example.test/news",
            "count": 2,
            "digest": "digest-1",
            "items": [
                {"title": "Entry 1", "url": "https://example.test/1"},
                {"title": "Entry 2", "url": "https://example.test/2"},
            ],
        },
        {
            "requested_url": "https://example.test/news",
            "source_url": "https://example.test/news",
            "count": 2,
            "digest": "digest-2",
            "items": [
                {"title": "Entry 2", "url": "https://example.test/2"},
                {"title": "Entry 3", "url": "https://example.test/3"},
            ],
        },
    ]

    def fake_scraper_run_once(*, url: str, max_items: int, timeout: int):
        assert url == "https://example.test/news"
        assert max_items == 25
        assert timeout == 20
        return snapshots.pop(0)

    monkeypatch.setattr(watcher.scraper, "run_once", fake_scraper_run_once)

    first = watcher.run_once()
    second = watcher.run_once()

    assert first["new_count"] == 2
    assert first["removed_count"] == 0
    assert second["new_count"] == 1
    assert second["removed_count"] == 1
    assert second["new_items"][0]["url"] == "https://example.test/3"
    assert second["removed_items"][0]["url"] == "https://example.test/1"

    state = json.loads(state_file.read_text(encoding="utf-8"))
    latest_diff = json.loads(latest_diff_file.read_text(encoding="utf-8"))

    assert state["digest"] == "digest-2"
    assert len(state["items"]) == 2
    assert latest_diff["new_count"] == 1
