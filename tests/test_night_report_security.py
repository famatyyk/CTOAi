import importlib.util
from pathlib import Path

from _pytest.monkeypatch import MonkeyPatch


ROOT = Path(__file__).resolve().parents[1]
NIGHT_REPORT = ROOT / "scripts" / "ops" / "night-report.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("night_report_security", NIGHT_REPORT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_night_report_reads_bounded_tail_sample_for_large_logs(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    module = _load_module()
    monkeypatch.setenv("CTOA_NIGHT_REPORT_LOG_MAX_BYTES", "4096")
    log_file = tmp_path / "orchestrator.log"
    filler = "\n".join(f"filler line {idx}" for idx in range(700))
    log_file.write_text(
        "\n".join(
            [
                "error old-secret-token=SHOULD-NOT-LEAK",
                filler,
                "LOOP_TICK start",
                "Server #7: 3 tasks queued",
                "Validated module VALIDATED",
                "Exception recent failure detail",
            ]
        ),
        encoding="utf-8",
    )

    report = module.build_report(
        log_file=log_file,
        manifest_dir=None,
        window_hours=12,
    )

    assert "Log sample: 4096/" in report
    assert "(tail sample)" in report
    assert "Loop ticks: 1" in report
    assert "Tasks queued total: 3" in report
    assert "Modules validated OK: 1" in report
    assert "Exception recent failure detail" in report
    assert "SHOULD-NOT-LEAK" not in report


def test_night_report_full_small_log_is_not_marked_truncated(tmp_path: Path) -> None:
    module = _load_module()
    log_file = tmp_path / "small.log"
    log_file.write_text("LOOP_TICK start\n", encoding="utf-8")

    report = module.build_report(
        log_file=log_file,
        manifest_dir=None,
        window_hours=12,
    )

    assert "(tail sample)" not in report
    assert "Loop ticks: 1" in report
