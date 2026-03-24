from datetime import UTC, datetime

from scripts.ops.evidence_retention import apply_retention_policy


def _entry(path: str, recorded_at: str) -> dict:
    return {
        "kind": "ci-artifact",
        "path": path,
        "sha256": "deadbeef",
        "recorded_at": recorded_at,
    }


def test_apply_retention_policy_prunes_by_age_and_count():
    now = datetime(2026, 3, 24, 12, 0, 0, tzinfo=UTC)
    entries = [
        _entry("runtime/ci-artifacts/a.json", "2026-03-24T11:00:00Z"),
        _entry("runtime/ci-artifacts/b.json", "2026-03-24T10:00:00Z"),
        _entry("runtime/ci-artifacts/c.json", "2026-03-20T10:00:00Z"),
        _entry("runtime/ci-artifacts/old.json", "2026-02-01T10:00:00Z"),
        _entry("runtime/ci-artifacts/bad.json", "not-a-date"),
    ]

    kept = apply_retention_policy(entries, max_entries=2, max_age_days=7, now=now)

    assert [item["path"] for item in kept] == [
        "runtime/ci-artifacts/a.json",
        "runtime/ci-artifacts/b.json",
    ]
