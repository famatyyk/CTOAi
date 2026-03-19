import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
import pytest

playwright_sync = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")
sync_playwright = playwright_sync.sync_playwright
expect = playwright_sync.expect

ROOT = Path(__file__).resolve().parents[2]
SITE_DIR = ROOT / "docs" / "site"


@pytest.mark.e2e
@pytest.mark.integration
@pytest.mark.timeout(180)
def test_browser_smoke_login_settings_ideas():
    backend_port = _free_port()
    frontend_port = _free_port()

    backend_url = f"http://127.0.0.1:{backend_port}"
    frontend_url = f"http://127.0.0.1:{frontend_port}"

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        backend_env = os.environ.copy()
        backend_env.update(
            {
                "CTOA_MOBILE_TOKEN": "test-mobile-token",
                "CTOA_OWNER_USER": "CTO",
                "CTOA_OWNER_PASSWORD": "asdzxc12",
                "CTOA_OPERATOR_USER": "ctoa-bot",
                "CTOA_OPERATOR_PASSWORD": "jakpod22",
                "CTOA_ADMIN_SETTINGS_FILE": str(tmp_path / "admin-settings.json"),
                "CTOA_IDEA_PARKING_FILE": str(tmp_path / "idea-parking.json"),
                "CTOA_CORS_ORIGINS": frontend_url,
            }
        )

        backend = _start_process(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "mobile_console.app:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(backend_port),
                "--log-level",
                "warning",
            ],
            cwd=ROOT,
            env=backend_env,
        )
        frontend = _start_process(
            [sys.executable, "-m", "http.server", str(frontend_port), "--bind", "127.0.0.1"],
            cwd=SITE_DIR,
            env=os.environ.copy(),
        )

        try:
            _wait_for_http(f"{backend_url}/api/auth/auto-check")
            _wait_for_http(f"{frontend_url}/index.html")

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                page.goto(frontend_url, wait_until="domcontentloaded")
                page.add_style_tag(content="*, *::before, *::after { animation: none !important; transition: none !important; }")

                page.click("#open-auth")
                page.fill("#auth-api-base", backend_url)
                page.fill("#auth-user", "cto")
                page.fill("#auth-pass", "asdzxc12")
                page.click("#auth-submit")

                expect(page.locator("#auth-modal")).to_have_attribute("aria-hidden", "true")
                expect(page.locator("#admin-status")).to_contain_text("Zalogowano przez backend")

                expect(page.locator("#prices-toggle")).to_be_enabled()
                page.fill("#hero-note", "E2E smoke hero note")
                page.check("#prices-toggle")
                page.evaluate("document.getElementById('save-admin')?.click()")

                expect(page.locator("#admin-status")).to_contain_text("Ustawienia zapisane w backendzie")
                expect(page.locator(".home-text")).to_contain_text("E2E smoke hero note")

                page.click("body")
                page.keyboard.press("ArrowDown")
                page.keyboard.press("ArrowDown")
                page.keyboard.press("ArrowDown")
                page.fill("#idea-input", "E2E smoke idea")
                page.evaluate("document.getElementById('idea-form')?.requestSubmit()")

                expect(page.locator("#idea-count")).to_contain_text("Zaparkowane: 1")
                expect(page.locator("#idea-list")).to_contain_text("E2E smoke idea")

                browser.close()
        finally:
            _stop_process(frontend)
            _stop_process(backend)


@pytest.mark.e2e
@pytest.mark.integration
@pytest.mark.timeout(180)
def test_browser_smoke_operator_owner_only_block():
    backend_port = _free_port()
    frontend_port = _free_port()

    backend_url = f"http://127.0.0.1:{backend_port}"
    frontend_url = f"http://127.0.0.1:{frontend_port}"

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        backend_env = os.environ.copy()
        backend_env.update(
            {
                "CTOA_MOBILE_TOKEN": "test-mobile-token",
                "CTOA_OWNER_USER": "CTO",
                "CTOA_OWNER_PASSWORD": "asdzxc12",
                "CTOA_OPERATOR_USER": "ctoa-bot",
                "CTOA_OPERATOR_PASSWORD": "jakpod22",
                "CTOA_ADMIN_SETTINGS_FILE": str(tmp_path / "admin-settings.json"),
                "CTOA_IDEA_PARKING_FILE": str(tmp_path / "idea-parking.json"),
                "CTOA_CORS_ORIGINS": frontend_url,
            }
        )

        backend = _start_process(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "mobile_console.app:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(backend_port),
                "--log-level",
                "warning",
            ],
            cwd=ROOT,
            env=backend_env,
        )
        frontend = _start_process(
            [sys.executable, "-m", "http.server", str(frontend_port), "--bind", "127.0.0.1"],
            cwd=SITE_DIR,
            env=os.environ.copy(),
        )

        try:
            _wait_for_http(f"{backend_url}/api/auth/auto-check")
            _wait_for_http(f"{frontend_url}/index.html")

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                page.goto(frontend_url, wait_until="domcontentloaded")
                page.add_style_tag(content="*, *::before, *::after { animation: none !important; transition: none !important; }")

                page.click("#open-auth")
                page.fill("#auth-api-base", backend_url)
                page.fill("#auth-user", "ctoa-bot")
                page.fill("#auth-pass", "jakpod22")
                page.click("#auth-submit")

                expect(page.locator("#auth-modal")).to_have_attribute("aria-hidden", "true")
                expect(page.locator("#admin-status")).to_contain_text("Zalogowano przez backend")

                expect(page.locator("#prices-toggle")).to_be_disabled()
                expect(page.locator("#reset-admin")).to_be_disabled()

                # Force a forbidden owner-only save attempt to verify backend rejection path.
                page.evaluate(
                    """
                    () => {
                        const prices = document.getElementById('prices-toggle');
                        if (prices) {
                            prices.disabled = false;
                            prices.checked = true;
                        }
                    }
                    """
                )
                page.evaluate("document.getElementById('save-admin')?.click()")

                expect(page.locator("#admin-status")).to_contain_text("Save error: Owner role required")

                browser.close()
        finally:
            _stop_process(frontend)
            _stop_process(backend)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _start_process(cmd: list[str], cwd: Path, env: dict[str, str]) -> subprocess.Popen:
    return subprocess.Popen(
        cmd,
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _wait_for_http(url: str, timeout_s: float = 25.0) -> None:
    deadline = time.time() + timeout_s
    last_error = ""
    while time.time() < deadline:
        try:
            response = httpx.get(url, timeout=1.5)
            if response.status_code < 500:
                return
            last_error = f"HTTP {response.status_code}"
        except Exception as exc:  # pragma: no cover - retry loop
            last_error = str(exc)
        time.sleep(0.25)
    raise AssertionError(f"Service did not become ready: {url}. Last error: {last_error}")


def _stop_process(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)
