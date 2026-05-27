from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_cross_surface_navigation_panel_exists_on_start_console_live_dashboard() -> None:
    root = _repo_root()
    start_html = (root / "docs" / "site" / "index.html").read_text(encoding="utf-8")
    console_html = (root / "mobile_console" / "static" / "index.html").read_text(encoding="utf-8")
    live_html = (root / "docs" / "site" / "live-dashboard.html").read_text(encoding="utf-8")

    assert 'class="global-nav container"' in start_html
    assert 'href="/" class="active">Start<' in start_html
    assert 'href="/console">Console<' in start_html
    assert 'href="/live-dashboard">Live Dashboard<' in start_html

    assert 'class="global-nav"' in console_html
    assert 'href="/">Start<' in console_html
    assert 'href="/console" class="active">Console<' in console_html
    assert 'href="/live-dashboard">Live Dashboard<' in console_html

    assert 'class="quick-nav"' in live_html
    assert 'href="/">Start<' in live_html
    assert 'href="/console">Console<' in live_html
    assert 'href="/live-dashboard" class="active">Live Dashboard<' in live_html


def test_start_surface_auth_header_toggles_owner_operator_controls() -> None:
    root = _repo_root()
    start_js = (root / "docs" / "site" / "script.js").read_text(encoding="utf-8")

    assert "function isOwnerSession()" in start_js
    assert "openConsoleButton.hidden = !ownerMode" in start_js
    assert "pricesToggle.disabled = !ownerMode" in start_js
    assert "resetButton.disabled = !ownerMode" in start_js
    assert 'session.role === "owner"' in start_js


def test_console_header_role_badge_and_owner_live_dashboard_shortcut_are_wired() -> None:
    root = _repo_root()
    console_html = (root / "mobile_console" / "static" / "index.html").read_text(encoding="utf-8")
    console_js = (root / "mobile_console" / "static" / "app.js").read_text(encoding="utf-8")

    assert 'id="roleBadge"' in console_html
    assert 'id="ownerLiveDashboardBtn"' in console_html
    assert 'id="authState"' in console_html

    assert "function applyRoleState(role)" in console_js
    assert "setRoleBadge(normalized);" in console_js
    assert "ownerLiveDashboardBtn.style.display = normalized === 'owner' ? 'inline-block' : 'none';" in console_js


def test_live_dashboard_session_badge_and_owner_gate_for_accounts_management() -> None:
    root = _repo_root()
    live_html = (root / "docs" / "site" / "live-dashboard.html").read_text(encoding="utf-8")

    assert 'id="sessionBadge"' in live_html
    assert "function renderAuthControls()" in live_html
    assert "el.sessionBadge.textContent = `Sesja: ${who} (${role})`;" in live_html
    assert "state.role === \"owner\" ? \"\" : \"none\"" in live_html


