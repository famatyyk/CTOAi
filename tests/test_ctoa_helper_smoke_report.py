from pathlib import Path

from scripts.ops import ctoa_helper_smoke_report as report


def test_expected_views_cover_zerobot_shell():
    assert report.EXPECTED_VIEWS == [
        "overview",
        "healing",
        "heal_friend",
        "conditions",
        "hunting",
        "hunting_magic",
        "cavebot",
        "equipment",
        "tools",
        "tools_pvp",
        "tools_hud",
        "tools_timer",
        "tools_diag",
        "scripting",
        "profile",
        "ui",
    ]


def test_collect_report_detects_complete_coverage(tmp_path: Path):
    for view in report.EXPECTED_VIEWS:
        (tmp_path / f"solteria-helper-testenv-{view}-20260705-035200.png").write_bytes(b"png")

    result = report.collect_report(tmp_path, "20260705-035")

    assert result.expected_count == 16
    assert result.covered_count == 16
    assert result.missing == []
    assert result.acceptance_status == "blocked_by_character_modal"
    assert all(view.screenshot for view in result.views)


def test_collect_report_supports_attach_prefix(tmp_path: Path):
    for view in report.EXPECTED_VIEWS:
        (tmp_path / f"solteria-helper-attach-{view}-20260705-041200.png").write_bytes(b"png")

    result = report.collect_report(
        tmp_path,
        "20260705-041",
        modal_limited=False,
        prefix="solteria-helper-attach",
    )

    assert result.covered_count == 16
    assert result.modal_limited is False
    assert result.acceptance_status == "ready_for_visual_review"


def test_collect_report_reports_missing_views(tmp_path: Path):
    (tmp_path / "solteria-helper-testenv-overview-20260705-035200.png").write_bytes(b"png")

    result = report.collect_report(tmp_path, "20260705-035")

    assert result.covered_count == 1
    assert "healing" in result.missing
    assert "ui" in result.missing


def test_render_markdown_includes_modal_limited_acceptance_note(tmp_path: Path):
    for view in report.EXPECTED_VIEWS:
        (tmp_path / f"solteria-helper-testenv-{view}-20260705-035200.png").write_bytes(b"png")
    result = report.collect_report(tmp_path, "20260705-035")

    markdown = report.render_markdown(result)

    assert "Coverage: `16/16`" in markdown
    assert "Acceptance status: `blocked_by_character_modal`" in markdown
    assert "## ZeroBot Mapping" in markdown
    assert "`hunting_magic` -> Hunting / Magic Shooter" in markdown
    assert "Full in-world visual acceptance" in markdown


def test_render_markdown_inworld_note(tmp_path: Path):
    for view in report.EXPECTED_VIEWS:
        (tmp_path / f"solteria-helper-attach-{view}-20260705-041200.png").write_bytes(b"png")
    result = report.collect_report(
        tmp_path,
        "20260705-041",
        modal_limited=False,
        prefix="solteria-helper-attach",
    )

    markdown = report.render_markdown(result)

    assert "Acceptance status: `ready_for_visual_review`" in markdown
    assert "captured in-world without the Select Character modal" in markdown


def test_render_html_includes_visual_review_cards(tmp_path: Path):
    for view in report.EXPECTED_VIEWS:
        (tmp_path / f"solteria-helper-testenv-{view}-20260705-035200.png").write_bytes(b"png")
    result = report.collect_report(tmp_path, "20260705-035")

    html = report.render_html(result)

    assert "Solteria Helper Visual Review" in html
    assert "blocked_by_character_modal" in html
    assert "class=\"status blocked\"" in html
    assert "hunting_magic / Hunting / Magic Shooter" in html
    assert "<img src=" in html


def test_report_paths_are_browser_friendly(tmp_path: Path):
    screenshot_dir = report.ROOT / "runtime" / "otclient_ui_preview"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    path = screenshot_dir / "solteria-helper-testenv-overview-20990101-010101.png"
    path.write_bytes(b"png")
    try:
        result = report.collect_report(screenshot_dir, "20990101-010")

        overview = next(view for view in result.views if view.view == "overview")

        assert overview.screenshot == "runtime/otclient_ui_preview/solteria-helper-testenv-overview-20990101-010101.png"
    finally:
        path.unlink(missing_ok=True)


def test_render_html_inworld_status(tmp_path: Path):
    for view in report.EXPECTED_VIEWS:
        (tmp_path / f"solteria-helper-attach-{view}-20260705-041200.png").write_bytes(b"png")
    result = report.collect_report(
        tmp_path,
        "20260705-041",
        modal_limited=False,
        prefix="solteria-helper-attach",
    )

    html = report.render_html(result)

    assert "ready_for_visual_review" in html
    assert "class=\"status ready\"" in html
