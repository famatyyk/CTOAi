from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "ctoa-p14-visual-baseline.schema.json"
BASELINE_CAPTURE = ROOT / "scripts" / "windows" / "otclient_p14_baseline_capture.ps1"
GUEST_PROVISION = ROOT / "scripts" / "windows" / "otclient_p14_guest_provision.ps1"
RUNBOOK = ROOT / "docs" / "otclient" / "P14_APPLIANCE_BOOTSTRAP_RUNBOOK.md"


def _receipt() -> dict[str, object]:
    return {
        "schema_version": "ctoa.p14-visual-baseline.v1",
        "status": "awaiting_owner_approval",
        "source_revision": "a" * 40,
        "image_name": "p14-baseline-" + "a" * 40 + ".png",
        "image_sha256": "b" * 64,
        "image_bytes": 640,
        "capture_report_sha256": "c" * 64,
        "runtime_marker_sha256": "d" * 64,
        "isolation": {
            "isolated_environment": True,
            "operator_workstation_focus_used": False,
            "operator_workstation_input_used": False,
            "network_dispatch_used": False,
            "live_client_accessed": False,
            "promotion_attempted": False,
            "capture_context": "guest",
        },
        "authority": {
            "runtime_actions": False,
            "live_authority": False,
            "promotion_approved": False,
            "network_dispatch_used": False,
        },
    }


def test_visual_baseline_receipt_schema_is_strict() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)

    validator.validate(_receipt())

    unexpected = copy.deepcopy(_receipt())
    unexpected["unreviewed_export"] = True
    with pytest.raises(ValidationError):
        validator.validate(unexpected)

    unapproved = copy.deepcopy(_receipt())
    unapproved["status"] = "approved"
    with pytest.raises(ValidationError):
        validator.validate(unapproved)


def test_baseline_capture_binds_a_fixed_guest_capture_to_a_local_receipt() -> None:
    source = BASELINE_CAPTURE.read_text(encoding="utf-8")

    assert "Set-StrictMode -Version Latest" in source
    assert "$P14CaptureScript = 'C:\\P14Runner\\repo\\scripts\\windows\\otclient_p14_vm_capture.ps1'" in source
    assert "$P14BaselineRoot = 'C:\\P14Runner\\baseline'" in source
    assert "$P14MaximumImageBytes = 32MB" in source
    assert "& $P14CaptureScript -SourceRevision $sourceRevision" in source
    assert "CTOA_P14_CAPTURE_CONTEXT = 'guest'" in source
    assert "CTOA_P14_OPERATOR_WORKSTATION_INPUT_USED = 'false'" in source
    assert "network_adapter_not_isolated" in source
    assert "visual_capture_dimensions_invalid" in source
    assert "baseline_root_not_empty" in source
    assert "awaiting_owner_approval" in source
    assert "runtime_actions = $false" in source
    assert "promotion_approved = $false" in source
    assert "guestcontrol" not in source.lower()
    assert "keyboardputscancode" not in source.lower()
    assert "mouseput" not in source.lower()
    assert "sendkeys" not in source.lower()
    assert "start-process" not in source.lower()
    assert "vboxmanage" not in source.lower()


def test_provisioner_derives_the_baseline_hash_from_an_explicitly_approved_receipt() -> None:
    source = GUEST_PROVISION.read_text(encoding="utf-8")

    assert "[switch]$ApproveVisualBaseline" in source
    assert "visual_baseline_approval_required" in source
    assert "Get-P14VisualBaseline $revision" in source
    assert "baseline-receipt.json" in source
    assert "visual_baseline_hash_mismatch" in source
    assert "Assert-P14BaselineContents $imageName" in source
    assert "visual_baseline_contents_invalid" in source
    assert "Set-P14ImmutableTree $P14BaselineRoot" in source
    assert "[string]$VisualBaselineSha256" not in source
    assert "visual_baseline_sha256 = $visualBaselineSha256" in source


def test_bootstrap_runbook_uses_no_hand_typed_baseline_hash() -> None:
    source = RUNBOOK.read_text(encoding="utf-8")

    assert "otclient_p14_baseline_capture.ps1 -Apply" in source
    assert "otclient_p14_guest_provision.ps1 -Apply" in source
    assert "-ApproveVisualBaseline" in source
    assert "baseline-receipt.json" in source
    assert "transient\nread-only shared folder" in source
    assert "remove the shared\nfolder completely" in source
    assert "resolves the snapshot UUID from that predeclared\nname at runtime" in source
    assert "post-provision source\nchange" in source
    assert "<SHA256" not in source
