from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
LISTENER = ROOT / "scripts" / "ops" / "azure_activity_webhook_listener.py"
RUNNER = ROOT / "scripts" / "ops" / "azure-alerts-runner.ps1"
DOCS = ROOT / "docs" / "azure-alerts-automation-setup.md"


def _powershell() -> str:
    exe = shutil.which("powershell") or shutil.which("pwsh")
    if not exe:
        pytest.skip("PowerShell is not available")
    return exe


def test_azure_activity_listener_rejects_public_bind_without_ingest_secret() -> None:
    env = os.environ.copy()
    env.pop("CTOA_AZURE_INGEST_SECRET", None)

    result = subprocess.run(
        [
            sys.executable,
            str(LISTENER),
            "--host",
            "0.0.0.0",
            "--port",
            "8791",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=10,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "Refusing to expose Azure alert listener" in output
    assert "CTOA_AZURE_INGEST_SECRET" in output


def test_azure_alerts_runner_defaults_listener_to_loopback_and_secret_gate() -> None:
    script = RUNNER.read_text(encoding="utf-8")

    assert "[string]$ListenerHost = '127.0.0.1'" in script
    assert "'--host' $ListenerHost" in script
    assert "'--host' '0.0.0.0'" not in script
    assert "function Assert-AzureListenerExposure" in script
    assert "CTOA_AZURE_INGEST_SECRET" in script
    assert "Refusing to expose Azure alert listener" in script
    assert "--webhook-secret" not in script


def test_azure_alerts_runner_rejects_public_listener_before_start(
    tmp_path: Path,
) -> None:
    env = os.environ.copy()
    env.pop("CTOA_AZURE_INGEST_SECRET", None)

    result = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(RUNNER),
            "-Action",
            "listener",
            "-EnvFile",
            str(tmp_path / "missing.env"),
            "-ListenerHost",
            "0.0.0.0",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=20,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "Refusing to expose Azure alert listener" in output
    assert "CTOA_AZURE_INGEST_SECRET" in output
    assert "azure_activity_webhook_listener.py" not in output


def test_azure_alerts_docs_do_not_recommend_public_listener_without_secret() -> None:
    docs = DOCS.read_text(encoding="utf-8")

    assert "CTOA_AZURE_INGEST_SECRET (required before any non-loopback" in docs
    assert "http://127.0.0.1:8791/azure/activity" in docs
    assert "http://<host>:8791/azure/activity" not in docs
    assert "Do not run the webhook listener on 0.0.0.0 without" in docs
