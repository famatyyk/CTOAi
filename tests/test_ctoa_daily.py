from pathlib import Path

from scripts.ops import ctoa_daily as daily


def test_sanitize_tokens_rejects_shell_chars():
    try:
        daily._sanitize_tokens(["tests/test_suite.py;rm"])
        assert False, "expected ValueError"
    except ValueError:
        assert True


def test_render_report_contains_sections():
    result = daily.DailyResult(
        ts="2026-06-24T10:00:00Z",
        doctor={"status": "OK", "checks": []},
        git_status="## main",
        smoke_cmd=["python", "-m", "pytest", "-q"],
        smoke_exit=0,
        smoke_stdout="passed",
        smoke_stderr="",
        plan_text="Plan body",
    )
    report = daily.render_report(result)
    assert "## AI Daily Plan" in report
    assert "Doctor status: `OK`" in report


def test_save_report_writes_file(tmp_path: Path):
    path = daily.save_report("# report", out_dir=tmp_path)
    assert path.exists()
    assert path.read_text(encoding="utf-8") == "# report"

