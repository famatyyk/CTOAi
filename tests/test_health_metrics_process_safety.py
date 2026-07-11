from runner import health_metrics

import json
from pathlib import Path

import pytest


class _Result:
    returncode = 0
    stdout = "cleanup complete\n"
    stderr = ""


def test_disk_cleanup_uses_resolved_bash(monkeypatch) -> None:
    calls: dict[str, object] = {}

    def fake_resolve(name: str, env_var: str | None = None) -> str:
        calls["resolve"] = (name, env_var)
        return "/trusted/bash"

    def fake_run(command: list[str], **kwargs):
        calls["command"] = command
        calls["kwargs"] = kwargs
        return _Result()

    monkeypatch.setattr(
        health_metrics.process_safety, "resolve_executable", fake_resolve
    )
    monkeypatch.setattr(health_metrics.process_safety, "run_trusted", fake_run)

    last_run, message = health_metrics.maybe_run_disk_cleanup(
        {"disk_used_pct": 91.0},
        now_ts=1234.0,
        enabled=True,
        threshold=90.0,
        cooldown_seconds=0,
        command="echo cleanup",
        last_run_ts=0.0,
    )

    assert last_run == 1234.0
    assert message and "cleanup OK" in message
    assert calls["resolve"] == ("bash", "CTOA_BASH_BIN")
    assert calls["command"] == ["/trusted/bash", "-lc", "echo cleanup"]


def test_health_publish_validates_github_url_before_requests_post(monkeypatch) -> None:
    calls: dict[str, object] = {}

    class Response:
        status_code = 201
        text = ""

    def fake_require_github_api_url(url: str) -> str:
        calls["validated_url"] = url
        return "https://safe.example/comments"

    def fake_post(url: str, **kwargs):
        calls["post_url"] = url
        calls["post_kwargs"] = kwargs
        return Response()

    monkeypatch.setattr(health_metrics, "GITHUB_PAT", "test-token")
    monkeypatch.setattr(health_metrics, "REPO_OWNER", "owner")
    monkeypatch.setattr(health_metrics, "REPO_NAME", "repo")
    monkeypatch.setattr(health_metrics, "HEALTH_ISSUE_ID", 7)
    monkeypatch.setattr(
        health_metrics.http_safety,
        "require_github_api_url",
        fake_require_github_api_url,
    )
    monkeypatch.setattr(health_metrics.requests, "post", fake_post)

    assert health_metrics.publish_to_github("dashboard") is True
    assert (
        calls["validated_url"]
        == "https://api.github.com/repos/owner/repo/issues/7/comments"
    )
    assert calls["post_url"] == "https://safe.example/comments"
    assert calls["post_kwargs"]["json"] == {"body": "dashboard"}
    assert calls["post_kwargs"]["timeout"] == 15


def test_health_publish_rejects_unsafe_repo_id_before_requests_post(monkeypatch) -> None:
    def fail_post(*_args, **_kwargs):
        raise AssertionError("unsafe repo id must be rejected before requests.post")

    monkeypatch.setattr(health_metrics, "GITHUB_PAT", "test-token")
    monkeypatch.setattr(health_metrics, "REPO_OWNER", "owner/path")
    monkeypatch.setattr(health_metrics, "REPO_NAME", "repo")
    monkeypatch.setattr(health_metrics.requests, "post", fail_post)

    with pytest.raises(ValueError):
        health_metrics.publish_to_github("dashboard")


def _make_file_symlink(link_path: Path, target_path: Path) -> None:
    try:
        link_path.symlink_to(target_path)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"file symlinks unavailable: {exc}")


def test_persist_snapshot_uses_atomic_latest_json_write(monkeypatch, tmp_path: Path) -> None:
    latest = tmp_path / "health-latest.json"
    history = tmp_path / "health-history.jsonl"
    monkeypatch.setattr(health_metrics, "RUNTIME_DIR", tmp_path)
    monkeypatch.setattr(health_metrics, "HEALTH_LATEST_FILE", latest)
    monkeypatch.setattr(health_metrics, "HEALTH_HISTORY_FILE", history)

    health_metrics.persist_snapshot({"timestamp": "now", "disk_used_pct": 12.0}, [])

    payload = json.loads(latest.read_text(encoding="utf-8"))
    assert payload["metrics"]["disk_used_pct"] == 12.0
    assert history.read_text(encoding="utf-8").strip()
    assert not list(tmp_path.glob("*.tmp"))
    assert not list(tmp_path.glob(".*.tmp"))


def test_persist_snapshot_replaces_latest_symlink_without_touching_target(
    monkeypatch,
    tmp_path: Path,
) -> None:
    latest = tmp_path / "health-latest.json"
    history = tmp_path / "health-history.jsonl"
    outside = tmp_path / "outside.json"
    outside.write_text("outside stays unchanged\n", encoding="utf-8")
    _make_file_symlink(latest, outside)

    monkeypatch.setattr(health_metrics, "RUNTIME_DIR", tmp_path)
    monkeypatch.setattr(health_metrics, "HEALTH_LATEST_FILE", latest)
    monkeypatch.setattr(health_metrics, "HEALTH_HISTORY_FILE", history)

    health_metrics.persist_snapshot({"timestamp": "now", "disk_used_pct": 34.0}, [])

    assert outside.read_text(encoding="utf-8") == "outside stays unchanged\n"
    assert not latest.is_symlink()
    assert json.loads(latest.read_text(encoding="utf-8"))["metrics"]["disk_used_pct"] == 34.0
