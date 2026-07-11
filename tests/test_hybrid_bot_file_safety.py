from pathlib import Path

import pytest

from runner.hybrid_bot.file_safety import safe_child_path
from runner.hybrid_bot.metrics import MetricsCollector
from runner.hybrid_bot.performance_profiler import PerformanceProfiler, TimingSnapshot


def _record_sample(collector: MetricsCollector) -> None:
    collector.record_snapshot(
        location="Wasp Cave",
        duration_seconds=60.0,
        xp_gained=100,
        monsters_killed=2,
        loot_value_gold=50,
        supplies_cost_gold=10,
    )


def test_metrics_export_writes_under_metrics_dir(tmp_path: Path) -> None:
    collector = MetricsCollector(output_dir=tmp_path, disable_file_output=True)
    _record_sample(collector)

    collector.export_metrics_csv("exports/session.csv")

    output = tmp_path / "exports" / "session.csv"
    assert output.is_file()
    assert "Wasp Cave" in output.read_text(encoding="utf-8")


def test_metrics_load_reads_only_under_metrics_dir(tmp_path: Path) -> None:
    source = tmp_path / "session.jsonl"
    source.write_text(
        '{"timestamp":"2026-07-06T00:00:00+00:00","location":"Wasp Cave",'
        '"duration_seconds":60,"xp_gained":100,"monsters_killed":2,'
        '"loot_value_gold":50,"supplies_cost_gold":10,"balance_gold":40,'
        '"xp_per_hour":6000,"balance_per_hour":2400,"supplies_per_hour":600,'
        '"player_health_percent":100,"player_level":50,'
        '"distance_traveled_sqm":0,"notes":""}\n',
        encoding="utf-8",
    )
    collector = MetricsCollector(output_dir=tmp_path, disable_file_output=True)

    snapshots = collector.load_snapshots_from_file("session.jsonl")

    assert len(snapshots) == 1
    assert snapshots[0].location == "Wasp Cave"


@pytest.mark.parametrize(
    "relative_path",
    [
        "../escape.csv",
        "reports/../../escape.csv",
        "/tmp/escape.csv",
        "C:/temp/escape.csv",
        "reports\\escape.csv",
        "reports/bad:name.csv",
        "reports/bad\nname.csv",
        "reports/session.txt",
    ],
)
def test_safe_child_path_rejects_unsafe_metrics_paths(
    tmp_path: Path, relative_path: str
) -> None:
    with pytest.raises(ValueError):
        safe_child_path(tmp_path, relative_path, allowed_suffixes={".csv"})

    assert list(tmp_path.rglob("*")) == []


def test_metrics_export_rejects_unsafe_output_before_write(tmp_path: Path) -> None:
    collector = MetricsCollector(output_dir=tmp_path, disable_file_output=True)
    _record_sample(collector)

    collector.export_metrics_csv("../escape.csv")

    assert not (tmp_path.parent / "escape.csv").exists()
    assert list(tmp_path.rglob("*")) == []


def test_metrics_load_rejects_unsafe_input_before_read(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.jsonl"
    outside.write_text("not metrics\n", encoding="utf-8")
    collector = MetricsCollector(output_dir=tmp_path, disable_file_output=True)

    assert collector.load_snapshots_from_file("../outside.jsonl") == []


def test_profiler_export_rejects_unsafe_filename(tmp_path: Path) -> None:
    profiler = PerformanceProfiler(output_dir=tmp_path)
    profiler.snapshots.append(TimingSnapshot(timestamp=1.0, tick_total_ms=12.5))

    with pytest.raises(ValueError):
        profiler.export_to_json("../profile.jsonl")

    assert list(tmp_path.rglob("*")) == []


def test_safe_child_path_rejects_existing_symlink(tmp_path: Path) -> None:
    target = tmp_path / "target.csv"
    target.write_text("existing\n", encoding="utf-8")
    link = tmp_path / "link.csv"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("Symlink creation is not available in this environment")

    with pytest.raises(ValueError, match="must not be a symlink"):
        safe_child_path(tmp_path, "link.csv", allowed_suffixes={".csv"})

    assert target.read_text(encoding="utf-8") == "existing\n"
