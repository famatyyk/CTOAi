import importlib.util
from pathlib import Path


def _load_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "ops" / "phase5_nightly_sync.py"
    spec = importlib.util.spec_from_file_location("phase5_nightly_sync", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_remote_timestamps_filters_invalid_rows():
    module = _load_module()

    raw = "\n".join(
        [
            "20260515T185948Z",
            "phase5-drycheck-20260515T185948Z",
            "not-a-timestamp",
            "20260516T022021Z",
            "20260516T022021Z",
        ]
    )
    rows = module.parse_remote_timestamps(raw)

    assert rows == ["20260515T185948Z", "20260516T022021Z"]


def test_should_sync_snapshot_detects_missing_required_files(tmp_path: Path):
    module = _load_module()

    snapshot = tmp_path / "phase5-drycheck-20260516T022021Z"
    snapshot.mkdir()
    (snapshot / "summary.md").write_text("ok\n", encoding="utf-8")

    assert module.should_sync_snapshot(snapshot, sync_all=False) is True

    (snapshot / "report.txt").write_text("ok\n", encoding="utf-8")
    (snapshot / "status-porcelain.txt").write_text("", encoding="utf-8")

    assert module.should_sync_snapshot(snapshot, sync_all=False) is False
    assert module.should_sync_snapshot(snapshot, sync_all=True) is True


def test_render_short_status_includes_key_kpis():
    module = _load_module()

    payload = {
        "overall_status": "IN_PROGRESS",
        "selected_nightly_runs": 1,
        "target_runs": 3,
        "pending_runs": 2,
        "alerts_count": 0,
    }
    line = module.render_short_status(payload, pulled_new=2, skipped_existing=4)

    assert "status=IN_PROGRESS" in line
    assert "nightly_runs=1/3" in line
    assert "pending=2" in line
    assert "alerts=0" in line
    assert "pulled_new=2" in line
    assert "skipped_existing=4" in line