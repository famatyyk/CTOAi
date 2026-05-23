import importlib.util
from pathlib import Path


def _load_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "ops" / "phase5_nightly_checklist.py"
    spec = importlib.util.spec_from_file_location("phase5_nightly_checklist", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_snapshot(root: Path, stamp: str, summary: dict[str, str], status_porcelain: str = "") -> None:
    folder = root / f"phase5-drycheck-{stamp}"
    folder.mkdir(parents=True, exist_ok=True)

    lines = ["# Phase 5 Nightly Worktree Dry-Check Summary", ""]
    for key, value in summary.items():
        lines.append(f"{key}: {value}")

    (folder / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (folder / "status-porcelain.txt").write_text(status_porcelain, encoding="utf-8")


def test_build_report_tracks_pending_and_non_nightly_runs(tmp_path: Path):
    module = _load_module()

    _write_snapshot(
        tmp_path,
        "20260515T185948Z",
        {
            "timestamp_utc": "20260515T185948Z",
            "branch": "main",
            "head": "9fe04e8",
            "status": "CLEAN",
            "mirror_policy": "SATISFIED",
            "result": "PASS",
        },
    )
    _write_snapshot(
        tmp_path,
        "20260516T022015Z",
        {
            "timestamp_utc": "20260516T022015Z",
            "branch": "main",
            "head": "9fe04e8",
            "status": "CLEAN",
            "mirror_policy": "SATISFIED",
            "result": "PASS",
        },
    )

    report = module.build_report(
        evidence_dir=tmp_path,
        target_runs=3,
        nightly_hour=2,
        nightly_minute=20,
        window_minutes=45,
    )

    assert report["overall_status"] == "IN_PROGRESS"
    assert report["selected_nightly_runs"] == 1
    assert report["pending_runs"] == 2
    assert report["alerts_count"] == 0
    assert len(report["non_nightly_runs"]) == 1
    assert report["nightly_runs"][0]["ok"] is True

    markdown = module.render_markdown(report)
    assert "- [x] Run 1:" in markdown
    assert "- [ ] Run 2:" in markdown


def test_build_report_raises_alert_when_nightly_run_is_dirty(tmp_path: Path):
    module = _load_module()

    _write_snapshot(
        tmp_path,
        "20260516T021959Z",
        {
            "timestamp_utc": "20260516T021959Z",
            "branch": "main",
            "head": "9fe04e8",
            "status": "CLEAN",
            "mirror_policy": "SATISFIED",
            "result": "PASS",
        },
    )
    _write_snapshot(
        tmp_path,
        "20260517T022020Z",
        {
            "timestamp_utc": "20260517T022020Z",
            "branch": "main",
            "head": "9fe04e8",
            "status": "CLEAN",
            "mirror_policy": "SATISFIED",
            "result": "PASS",
        },
        status_porcelain=" M scripts/ops/ctoa-root-action.sh\n",
    )
    _write_snapshot(
        tmp_path,
        "20260518T022030Z",
        {
            "timestamp_utc": "20260518T022030Z",
            "branch": "main",
            "head": "9fe04e8",
            "status": "CLEAN",
            "mirror_policy": "SATISFIED",
            "result": "PASS",
        },
    )

    report = module.build_report(
        evidence_dir=tmp_path,
        target_runs=3,
        nightly_hour=2,
        nightly_minute=20,
        window_minutes=45,
    )

    assert report["overall_status"] == "ATTENTION"
    assert report["selected_nightly_runs"] == 3
    assert report["pending_runs"] == 0
    assert report["alerts_count"] == 1

    failing = [row for row in report["nightly_runs"] if not row["ok"]]
    assert len(failing) == 1
    assert "porcelain_not_empty" in failing[0]["alerts"]
    assert module.determine_exit_code(report, require_complete=False) == 1