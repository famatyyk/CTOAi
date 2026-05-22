import json

from fastapi.testclient import TestClient

from labs.projects.intel_news_api import app as intel_api


client = TestClient(intel_api.app)


def test_status_when_files_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(intel_api, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(intel_api, "DIFF_FILE", tmp_path / "latest_diff.json")

    response = client.get("/api/intel/status")
    assert response.status_code == 200

    payload = response.json()
    assert payload["watcher"]["state_available"] is False
    assert payload["watcher"]["diff_available"] is False
    assert payload["watcher"]["current_count"] == 0
    assert payload["watcher"]["new_count"] == 0


def test_status_reads_watcher_outputs(tmp_path, monkeypatch) -> None:
    state_file = tmp_path / "state.json"
    diff_file = tmp_path / "latest_diff.json"

    state_file.write_text(
        json.dumps(
            {
                "updated_at": "2026-05-21T17:00:00+00:00",
                "digest": "digest-2",
                "source_url": "https://example.test/latestnews",
                "requested_url": "https://example.test/news",
                "items": [
                    {"title": "A", "url": "https://example.test/1"},
                    {"title": "B", "url": "https://example.test/2"},
                ],
            }
        ),
        encoding="utf-8",
    )

    diff_file.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-21T17:05:00+00:00",
                "source_url": "https://example.test/latestnews",
                "requested_url": "https://example.test/news",
                "current_count": 2,
                "new_count": 1,
                "removed_count": 0,
                "digest_changed": True,
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(intel_api, "STATE_FILE", state_file)
    monkeypatch.setattr(intel_api, "DIFF_FILE", diff_file)

    status = client.get("/api/intel/status")
    assert status.status_code == 200
    body = status.json()

    assert body["watcher"]["state_available"] is True
    assert body["watcher"]["diff_available"] is True
    assert body["watcher"]["current_count"] == 2
    assert body["watcher"]["new_count"] == 1
    assert body["watcher"]["digest_changed"] is True
    assert body["watcher"]["source_url"] == "https://example.test/latestnews"

    state_payload = client.get("/api/intel/state").json()
    diff_payload = client.get("/api/intel/diff").json()

    assert state_payload["available"] is True
    assert diff_payload["available"] is True
    assert len(state_payload["data"]["items"]) == 2
    assert diff_payload["data"]["new_count"] == 1
