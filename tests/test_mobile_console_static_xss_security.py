from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "mobile_console" / "static" / "app.js"
INDEX_HTML = ROOT / "mobile_console" / "static" / "index.html"


def test_mobile_console_app_does_not_render_api_payloads_with_inner_html() -> None:
    source = APP_JS.read_text(encoding="utf-8")

    assert "innerHTML" not in source
    assert "function createStatusBadge" in source
    assert "function renderTrendSummary" in source
    assert "replaceChildren()" in source
    assert "textContent" in source


def test_mobile_console_app_uses_dom_nodes_for_dashboard_tables() -> None:
    source = APP_JS.read_text(encoding="utf-8")

    assert "statusCell.appendChild(createStatusBadge" in source
    assert "appendEmptyTableRow(srvBody, 3, 'brak danych')" in source
    assert "appendEmptyTableRow(topBody, 4, 'brak danych')" in source


def test_mobile_console_legacy_ui_does_not_render_full_command_box() -> None:
    html = INDEX_HTML.read_text(encoding="utf-8")
    script = APP_JS.read_text(encoding="utf-8")

    assert "Full Command" not in html
    assert 'id="cmd"' not in html
    assert "runCmd').onclick = async" not in script
    assert "command_mode=" in script
