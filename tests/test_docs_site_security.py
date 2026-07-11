from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE_SCRIPT = ROOT / "docs" / "site" / "script.js"
LIVE_DASHBOARD = ROOT / "docs" / "site" / "live-dashboard.html"


def _site_script() -> str:
    return SITE_SCRIPT.read_text(encoding="utf-8")


def _live_dashboard() -> str:
    return LIVE_DASHBOARD.read_text(encoding="utf-8")


def test_docs_site_script_avoids_dynamic_html_rendering() -> None:
    source = _site_script()

    assert "innerHTML" not in source
    assert "insertAdjacentHTML" not in source
    assert "document.write" not in source
    assert "replaceChildren()" in source


def test_docs_site_api_base_is_normalized_with_url_guardrails() -> None:
    source = _site_script()

    assert "new URL(raw)" in source
    assert 'url.protocol !== "http:" && url.protocol !== "https:"' in source
    assert "url.username || url.password || url.search || url.hash" in source
    assert 'url.pathname && url.pathname !== "/"' in source
    assert 'url.protocol === "http:" && !isLocalDevHost(url.hostname)' in source
    assert "return url.origin.replace" in source


def test_docs_site_does_not_persist_auth_secrets_in_local_storage() -> None:
    source = _site_script()

    assert "localStorage.setItem(ADMIN_API_TOKEN_KEY" not in source
    assert "saveJson(ADMIN_USERS_KEY" not in source
    assert "loadJson(ADMIN_USERS_KEY" not in source
    assert "saveSessionJson(ADMIN_USERS_KEY, users)" in source
    assert "loadSessionJson(ADMIN_USERS_KEY, fallback)" in source


def test_docs_site_owner_reset_clears_session_scoped_auth_state() -> None:
    source = _site_script()
    reset_start = source.index('resetButton.addEventListener("click"')
    reset_end = source.index("if (openConsoleButton)")
    reset_block = source[reset_start:reset_end]

    assert "function clearAdminSessionState()" in source
    assert 'setApiSession("", "", "")' in source
    assert "sessionStorage.removeItem(ADMIN_USERS_KEY)" in source
    assert "localStorage.clear()" in reset_block
    assert "clearAdminSessionState()" in reset_block


def test_live_dashboard_avoids_dynamic_html_and_inline_handlers() -> None:
    source = _live_dashboard()

    assert "innerHTML" not in source
    assert "insertAdjacentHTML" not in source
    assert "document.write" not in source
    assert "onclick=" not in source
    assert "onsubmit=" not in source


def test_live_dashboard_api_base_is_normalized_with_url_guardrails() -> None:
    source = _live_dashboard()

    assert "new URL(raw)" in source
    assert 'parsed.protocol !== "http:" && parsed.protocol !== "https:"' in source
    assert "parsed.username || parsed.password || parsed.search || parsed.hash" in source
    assert 'parsed.pathname && parsed.pathname !== "/"' in source
    assert 'parsed.protocol === "http:" && !isLocalDevHost(parsed.hostname)' in source
    assert 'return parsed.origin.replace(/\\/$/, "")' in source
    assert 'catch (_err) {\n          return "";' in source


def test_live_dashboard_keeps_auth_token_session_scoped() -> None:
    source = _live_dashboard()

    assert 'localStorage.setItem("ctoa_live_token"' not in source
    assert 'localStorage.getItem("ctoa_live_token"' not in source
    assert 'sessionStorage.setItem("ctoa_live_token", token)' in source
    assert 'sessionStorage.getItem("ctoa_live_token")' in source


def test_live_dashboard_uses_dom_render_helpers_for_api_payloads() -> None:
    source = _live_dashboard()

    assert "function clearNode" in source
    assert "function createTextNodeElement" in source
    assert "function appendTableMessage" in source
    assert 'addEventListener("submit", handleRegister)' in source
    assert "tr.innerHTML" not in source
