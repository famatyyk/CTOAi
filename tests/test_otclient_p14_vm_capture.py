from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "windows" / "otclient_p14_vm_capture.ps1"


def test_vm_capture_is_guest_bound_and_fail_closed() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "CTOA_P14_CAPTURE_CONTEXT = 'guest'" in source
    assert "CTOA_P14_OPERATOR_WORKSTATION_FOCUS_USED = 'false'" in source
    assert "CTOA_P14_OPERATOR_WORKSTATION_INPUT_USED = 'false'" in source
    assert "CTOA_P14_NETWORK_DISPATCH_USED = 'false'" in source
    assert "CTOA_P14_LIVE_CLIENT_ACCESSED = 'false'" in source
    assert "CTOA_P14_PROMOTION_ATTEMPTED = 'false'" in source
    assert "candidate.online -eq $true" in source
    assert "CopyFromScreen" in source
    assert "Start-Process -FilePath $client" in source
    assert "Stop-P14Capture('in_world_marker_timeout')" in source
    assert "VBoxManage" not in source


def test_vm_capture_keeps_client_and_evidence_roots_separate() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "Get-StrictPath $ClientPath $clientRoot 'client'" in source
    assert "New-Item -ItemType Directory -Path $EvidenceRoot -Force" in source
    assert "client-capabilities.json" in source
    assert "capture-report.json" in source
