import json
from pathlib import Path

import pytest

from runner import generator_validator_samples
from runner import weekly_report
from runner.generated_manifest_safety import (
    iter_safe_manifest_files,
    public_manifest_path,
    resolve_latest_manifest_path,
)


def _make_dir_symlink(link_path: Path, target_path: Path) -> None:
    try:
        link_path.symlink_to(target_path, target_is_directory=True)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"directory symlinks unavailable: {exc}")


def test_latest_manifest_path_prefers_safe_run_manifest_over_external_pointer(
    tmp_path: Path,
) -> None:
    manifests_dir = tmp_path / "generated" / "manifests"
    safe_manifest = manifests_dir / "run-1" / "manifest.json"
    safe_manifest.parent.mkdir(parents=True)
    safe_manifest.write_text('{"run_id":"run-1","generated":[]}', encoding="utf-8")
    outside_manifest = tmp_path / "outside" / "manifest.json"
    outside_manifest.parent.mkdir()
    outside_manifest.write_text(
        '{"run_id":"outside","generated":[{"task_id":"leak"}]}',
        encoding="utf-8",
    )

    resolved = resolve_latest_manifest_path(
        manifests_dir,
        {"run_id": "run-1", "manifest_path": str(outside_manifest)},
    )

    assert resolved == safe_manifest.resolve()
    assert public_manifest_path(resolved, manifests_dir) == (
        "generated/manifests/run-1/manifest.json"
    )


def test_iter_safe_manifest_files_skips_symlinked_run_dir_escape(
    tmp_path: Path,
) -> None:
    manifests_dir = tmp_path / "generated" / "manifests"
    safe_manifest = manifests_dir / "run-safe" / "manifest.json"
    safe_manifest.parent.mkdir(parents=True)
    safe_manifest.write_text(
        json.dumps({"run_id": "run-safe", "generated": [{"task_id": "ok"}]}),
        encoding="utf-8",
    )

    outside_manifest = tmp_path / "outside-run" / "manifest.json"
    outside_manifest.parent.mkdir()
    outside_manifest.write_text(
        json.dumps({"run_id": "SHOULD-NOT-LEAK", "failed": [{"task_id": "leak"}]}),
        encoding="utf-8",
    )
    _make_dir_symlink(manifests_dir / "run-evil-link", outside_manifest.parent)

    manifest_files = iter_safe_manifest_files(manifests_dir)

    assert manifest_files == [safe_manifest.resolve()]
    assert outside_manifest.resolve() not in manifest_files


def test_generator_validator_samples_reject_external_manifest_pointer(
    tmp_path: Path,
) -> None:
    manifests_dir = tmp_path / "generated" / "manifests"
    manifests_dir.mkdir(parents=True)
    outside_manifest = tmp_path / "outside" / "manifest.json"
    outside_manifest.parent.mkdir()
    outside_manifest.write_text(
        json.dumps({"run_id": "outside", "generated": [{"task_id": "leak"}]}),
        encoding="utf-8",
    )
    (manifests_dir / "latest.json").write_text(
        json.dumps({"run_id": "missing", "manifest_path": str(outside_manifest)}),
        encoding="utf-8",
    )

    assert generator_validator_samples.load_latest_manifest(manifests_dir) is None


def test_generator_validator_samples_uses_public_manifest_path(tmp_path: Path) -> None:
    manifests_dir = tmp_path / "generated" / "manifests"
    safe_manifest = manifests_dir / "run-1" / "manifest.json"
    safe_manifest.parent.mkdir(parents=True)
    safe_manifest.write_text(
        json.dumps({"run_id": "run-1", "generated": [], "failed": []}),
        encoding="utf-8",
    )
    (manifests_dir / "latest.json").write_text(
        json.dumps({"run_id": "run-1", "manifest_path": str(safe_manifest)}),
        encoding="utf-8",
    )

    payload = generator_validator_samples.load_latest_manifest(manifests_dir)

    assert payload is not None
    assert payload["manifest_path"] == "generated/manifests/run-1/manifest.json"
    assert str(tmp_path) not in payload["manifest_path"]


def test_weekly_report_latency_kpi_rejects_external_manifest_pointer(
    tmp_path: Path, monkeypatch
) -> None:
    manifests_dir = tmp_path / "generated" / "manifests"
    manifests_dir.mkdir(parents=True)
    outside_manifest = tmp_path / "outside" / "manifest.json"
    outside_manifest.parent.mkdir()
    outside_manifest.write_text(
        json.dumps(
            {
                "run_id": "outside",
                "generated": [
                    {
                        "queued_at": "2026-07-07T00:00:00+00:00",
                        "generated_at": "2026-07-07T00:00:02+00:00",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (manifests_dir / "latest.json").write_text(
        json.dumps({"run_id": "missing", "manifest_path": str(outside_manifest)}),
        encoding="utf-8",
    )
    monkeypatch.setenv("CTOA_GENERATOR_MANIFEST_DIR", str(manifests_dir))

    payload = weekly_report._read_latency_kpi()

    assert payload == {"available": False, "reason": "manifest.json not found"}
