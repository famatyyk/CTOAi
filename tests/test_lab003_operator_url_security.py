from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SHIFT_GUARD = ROOT / "scripts" / "ops" / "lab003_shift_guard.ps1"
SHIFT_WEBHOOK_SMOKE = ROOT / "scripts" / "ops" / "lab003_shift_smoke_webhook.ps1"
MOBILE_PROXY_SMOKE = ROOT / "scripts" / "ops" / "lab003_mobile_proxy_smoke.ps1"
VALIDATE_BUNDLE = ROOT / "scripts" / "ops" / "lab003_validate_bundle.ps1"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _powershell() -> str:
    exe = shutil.which("powershell") or shutil.which("pwsh")
    if not exe:
        pytest.skip("PowerShell is not available")
    return exe


def _run_script(path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(path),
            *args,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=30,
    )


def test_lab003_scripts_validate_local_base_url_before_network_or_child_process() -> (
    None
):
    shift_guard = _read(SHIFT_GUARD)
    webhook_smoke = _read(SHIFT_WEBHOOK_SMOKE)
    mobile_smoke = _read(MOBILE_PROXY_SMOKE)
    validate_bundle = _read(VALIDATE_BUNDLE)

    for script in (shift_guard, webhook_smoke, mobile_smoke, validate_bundle):
        assert "function Assert-LocalApiBaseUrl" in script
        assert "localhost, 127.0.0.1, or [::1]" in script
        assert "$uri.UserInfo" in script
        assert "$uri.Query -or $uri.Fragment" in script
        assert '$uri.AbsolutePath -and $uri.AbsolutePath -ne "/"' in script

    assert shift_guard.index("$BaseUrl = Assert-LocalApiBaseUrl") < shift_guard.index(
        "$validateScript = Join-Path"
    )
    assert webhook_smoke.index(
        "$BaseUrl = Assert-LocalApiBaseUrl"
    ) < webhook_smoke.index("$args = @(")
    assert mobile_smoke.index(
        "$normalizedBaseUrl = Assert-LocalApiBaseUrl"
    ) < mobile_smoke.index("$loginResponse = Invoke-RestMethod")
    assert validate_bundle.index(
        "$BaseUrl = Assert-LocalApiBaseUrl"
    ) < validate_bundle.index("$args = @(")
    assert "$normalizedBaseUrl = $BaseUrl.TrimEnd" not in mobile_smoke


def test_lab003_child_processes_use_current_powershell_executable() -> None:
    shift_guard = _read(SHIFT_GUARD)
    webhook_smoke = _read(SHIFT_WEBHOOK_SMOKE)
    validate_bundle = _read(VALIDATE_BUNDLE)

    for script in (shift_guard, webhook_smoke, validate_bundle):
        assert "function Get-CurrentPowerShellPath" in script
        assert "Join-Path $PSHOME $exeName" in script
        assert "Test-Path -LiteralPath $candidate -PathType Leaf" in script
        assert "& $powerShell @args" in script
        assert "& powershell @args" not in script


def test_lab003_webhook_urls_are_validated_before_env_transfer_or_post() -> None:
    shift_guard = _read(SHIFT_GUARD)
    webhook_smoke = _read(SHIFT_WEBHOOK_SMOKE)

    for script in (shift_guard, webhook_smoke):
        assert "function Assert-AlertWebhookUrl" in script
        assert "must use https:// for non-local webhook hosts" in script
        assert "$uri.UserInfo" in script
        assert "$uri.Fragment" in script

    assert shift_guard.index(
        "$safeWebhookUrl = Assert-AlertWebhookUrl"
    ) < shift_guard.index("Invoke-RestMethod -Method Post")
    assert webhook_smoke.index(
        "$resolvedWebhookUrl = Assert-AlertWebhookUrl"
    ) < webhook_smoke.index(
        '[Environment]::SetEnvironmentVariable("CTOA_LAB003_ALERT_WEBHOOK_URL"'
    )


def test_lab003_shift_guard_rejects_unsafe_base_url_before_missing_bundle_check() -> (
    None
):
    result = _run_script(
        SHIFT_GUARD,
        "-DurationHours",
        "1",
        "-IntervalMinutes",
        "1",
        "-BaseUrl",
        "file:///tmp/ctoa",
    )

    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "BaseUrl must use http:// or https://" in output
    assert "Validation script not found" not in output


def test_lab003_mobile_proxy_rejects_remote_base_url_before_password_lookup() -> None:
    result = _run_script(MOBILE_PROXY_SMOKE, "-BaseUrl", "https://example.com")

    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "BaseUrl must use localhost, 127.0.0.1, or [::1]" in output
    assert "Missing password" not in output


def test_lab003_webhook_smoke_rejects_remote_http_before_env_transfer() -> None:
    result = _run_script(
        SHIFT_WEBHOOK_SMOKE,
        "-AlertWebhookUrl",
        "http://example.com/hook",
        "-BaseUrl",
        "http://127.0.0.1:8787",
    )

    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "AlertWebhookUrl must use https:// for non-local webhook hosts" in output
    assert "Alert webhook URL is required" not in output


def test_lab003_validate_bundle_rejects_unsafe_base_url_before_child_process() -> None:
    result = _run_script(VALIDATE_BUNDLE, "-BaseUrl", "http://example.com")

    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "BaseUrl must use localhost, 127.0.0.1, or [::1]" in output
    assert "Missing password" not in output
