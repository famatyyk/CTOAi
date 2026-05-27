from pathlib import Path


def test_mobile_console_dashboard_has_direct_status_context_panel():
    html_path = Path(__file__).resolve().parents[1] / "mobile_console" / "static" / "index.html"
    html = html_path.read_text(encoding="utf-8")

    required_ids = [
        'id="dashStatusPanel"',
        'id="dashStatusMessage"',
        'id="dashStatusSeverity"',
        'id="dashStatusDetail"',
        'id="dashStatusImpacted"',
        'id="dashStatusActions"',
    ]
    for marker in required_ids:
        assert marker in html, f"Missing dashboard status panel marker: {marker}"

    assert "dash-impact-chip-critical" in html
    assert "dash-impact-chip-warning" in html


def test_mobile_console_dashboard_status_context_renderer_is_wired():
    js_path = Path(__file__).resolve().parents[1] / "mobile_console" / "static" / "app.js"
    js = js_path.read_text(encoding="utf-8")

    assert "function renderDashboardStatusContext(payload)" in js
    assert "renderDashboardStatusContext(d);" in js
    assert "status_context" in js
    assert "critical_sections" in js
    assert "dash-impact-chip-critical" in js
    assert "dash-impact-chip-warning" in js


def test_live_dashboard_page_renders_status_context_panel():
    html_path = Path(__file__).resolve().parents[1] / "docs" / "site" / "live-dashboard.html"
    html = html_path.read_text(encoding="utf-8")

    assert 'id="statusHeadline"' in html
    assert 'id="statusDetail"' in html
    assert 'id="statusImpacted"' in html
    assert 'id="statusActions"' in html
    assert "function renderStatusContext(dashboard)" in html
    assert "renderStatusContext(dashboard);" in html

