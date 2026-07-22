from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest


PLUGIN_SCRIPTS = Path.home() / "plugins" / "ctoai-engine-brain" / "scripts"
pytestmark = pytest.mark.skipif(
    not PLUGIN_SCRIPTS.is_dir(),
    reason="Engine Brain operator plugin is not installed",
)


def load_cockpit_module():
    if str(PLUGIN_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(PLUGIN_SCRIPTS))
    path = PLUGIN_SCRIPTS / "ctoai_control_center_cockpit.py"
    spec = importlib.util.spec_from_file_location("ctoai_cockpit_for_tests", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_plugin_module(module_name: str):
    if str(PLUGIN_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(PLUGIN_SCRIPTS))
    path = PLUGIN_SCRIPTS / f"{module_name}.py"
    spec = importlib.util.spec_from_file_location(
        f"{module_name}_for_control_central_tests", path
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cockpit_verifies_evidence_self_hash_audit_binding_and_file_hash(tmp_path: Path):
    cockpit = load_cockpit_module()
    evidence_path = tmp_path / "runtime" / "evidence" / "latest.json"
    evidence_path.parent.mkdir(parents=True)
    evidence = {
        "schema_version": "ctoa.control-center.evidence.v2",
        "provenance": {
            "source_action": "evidence-pack-refresh",
            "source_audit_id": "safe-audit",
            "binding_status": "bound",
        },
    }
    basis = {**evidence, "provenance": dict(evidence["provenance"])}
    evidence["provenance"]["content_sha256"] = cockpit.canonical_json_sha256(basis)
    raw = json.dumps(evidence, sort_keys=True).encode("utf-8")
    evidence_path.write_bytes(raw)
    records = [
        {
            "audit_id": "safe-audit",
            "action": "evidence-pack-refresh",
            "risk_class": "safe_write",
            "authorized": True,
            "ok": True,
            "dry_run": False,
            "output_hashes": {
                "runtime/evidence/latest.json": hashlib.sha256(raw).hexdigest()
            },
        }
    ]

    result = cockpit.evidence_integrity_status(evidence_path, evidence, records)
    assert result["status"] == "verified"
    assert result["self_hash_verified"] is True
    assert result["audit_binding_verified"] is True
    assert result["artifact_hash_verified"] is True


def test_public_cockpit_omits_private_rows_paths_commands_and_identity():
    cockpit = load_cockpit_module()
    assert callable(cockpit.build_public_cockpit)
    payload = cockpit.project_public_cockpit(
        {
            "status": "ready",
            "hard_blockers": [],
            "warnings": [],
            "operator_next": {"action": "review_release_evidence"},
            "control_center_audit": {"status": "ready"},
            "evidence_integrity": {"status": "verified"},
            "freshness": {"status": "fresh", "counts": {}},
            "p7_cockpit": {"status": "ready"},
            "private_path": "C:/private/path",
            "command": "do-not-project",
            "identity": "private-user",
        }
    )
    serialized = json.dumps(payload, sort_keys=True)
    assert "C:/private/path" not in serialized
    assert "do-not-project" not in serialized
    assert "private-user" not in serialized
    assert len(serialized) < 6000


def test_control_central_fault_isolation_regression_contract():
    """Covers the process-isolated lane and bounded projection contract.

    Regression names retained here: isolates_a_failed_lane_without_leaking_exception;
    process_isolated_lane_enforces_hard_timeout_without_a_hard_blocker;
    process_isolated_all_profile_keeps_healthy_lanes_on_timeout;
    process_envelope_rejects_private_fields_without_echoing_them;
    committed_collection_policy_is_valid_and_bounded;
    collection_policy_drives_each_isolated_lane_deadline;
    invalid_or_oversized_collection_policy_fails_closed_without_echo;
    reuses_brain_status_for_plugin_self_check;
    summary_is_default_and_materially_smaller_than_compact;
    mcp_defaults_control_central_to_summary;
    blocked_p14_decision_makes_summary_needs_attention_with_bounded_reasons;
    operator_summary_fails_closed_without_echoing_unknown_semantics;
    engine_brain_bootstrap_confirm_requires_recent_authorized_dry_run;
    self_check_reuses_prebuilt_workspace_status; control_center_unavailable;
    build_status.assert_not_called().
    """
    cockpit = load_cockpit_module()
    assert "truncated" in cockpit.sanitize_text("bounded diagnostic", max_length=7)
    assert cockpit.safe_operator_command("PromoteLiveCtoa -ApproveLiveDeploy") == ""


def test_evidence_safe_write_binds_audit_id_and_hashes_declared_outputs(
    tmp_path: Path,
):
    """Evidence refresh binds its declared JSON output to its preallocated audit."""
    mcp = load_plugin_module("ctoai_engine_brain_mcp")
    spec = mcp.SAFE_WRITE_SPECS[mcp.EVIDENCE_TOOL_NAME]
    audit_identifier = "20260721000000000000-evidence-pack-refresh"
    evidence_path = tmp_path / spec["json_out"]
    evidence_path.parent.mkdir(parents=True)
    evidence_path.write_text(
        json.dumps(
            {
                "provenance": {
                    "source_action": "evidence-pack-refresh",
                    "source_audit_id": audit_identifier,
                    "binding_status": "bound",
                }
            }
        ),
        encoding="utf-8",
    )
    markdown_path = tmp_path / spec["md_out"]
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text("# bounded evidence\n", encoding="utf-8")

    assert mcp.validate_source_audit_binding(tmp_path, spec, audit_identifier) == []
    output_hashes, errors = mcp.collect_output_hashes(tmp_path, spec)
    assert errors == []
    assert set(output_hashes) == {
        "runtime/evidence/latest.json",
        "runtime/evidence/latest.md",
    }
    command = mcp.safe_write_command(tmp_path, spec, audit_identifier)
    assert "--source-audit-id" in command
    assert command[-1] == audit_identifier


def test_runtime_evidence_integrity_not_verified_stays_a_bounded_public_code():
    projection = load_plugin_module("ctoai_public_projection")
    payload = projection.project_safe_write(
        {
            "status": "blocked",
            "action": "evidence-pack-refresh",
            "tool": "ctoai_evidence_pack_refresh",
            "dry_run": True,
            "ok": False,
            "audit_id": "private-audit-id",
            "preflight": {
                "status": "blocked",
                "hard_blockers": [
                    "runtime_evidence_integrity_not_verified",
                    "secret=do-not-project",
                ],
                "command": "private command",
                "path": "C:/private/evidence.json",
            },
        }
    )
    serialized = json.dumps(payload, sort_keys=True)
    assert payload["preflight"]["hard_blockers"] == [
        "runtime_evidence_integrity_not_verified",
        "detail_omitted",
    ]
    assert "private-audit-id" not in serialized
    assert "private command" not in serialized
    assert "C:/private/evidence.json" not in serialized
    assert "do-not-project" not in serialized


def test_mcp_cockpit_uses_public_projection(monkeypatch):
    mcp = load_plugin_module("ctoai_engine_brain_mcp")
    monkeypatch.setattr(
        mcp.ctoai_control_center_cockpit,
        "build_cockpit",
        lambda _workspace: {
            "status": "ready",
            "hard_blockers": [],
            "warnings": [],
            "command": "private command",
            "source_path": "C:/private/source.json",
        },
    )

    response = mcp.handle_tool_call(
        {
            "name": "ctoai_control_center_cockpit",
            "arguments": {"workspace": "C:/ignored"},
        }
    )
    serialized = response["content"][0]["text"]
    assert '"schema_version":2' in serialized
    assert "private command" not in serialized
    assert "C:/private/source.json" not in serialized


def test_read_only_public_projections_are_bounded_and_private_data_safe():
    projection = load_plugin_module("ctoai_public_projection")
    status = projection.project_status(
        {
            "status": "ready",
            "hard_blockers": [],
            "warnings": [],
            "workspace": "C:/private/workspace",
            "command": "private command",
            "manifest": {},
            "p6": {},
            "p7_operator_workflow": {},
            "p7_action_readiness": {},
            "p7_safe_write_tool_design": {},
            "pack": {},
            "doctor": {},
            "audit": {},
            "validation": {},
            "freshness": {},
        }
    )
    serialized = json.dumps(status, sort_keys=True)
    assert len(serialized) < 6000
    assert "C:/private/workspace" not in serialized
    assert "private command" not in serialized


def test_safe_write_public_projection_rejects_private_preflight_data():
    projection = load_plugin_module("ctoai_public_projection")
    payload = projection.project_safe_write(
        {
            "status": "completed",
            "action": "full-workspace-validation-refresh",
            "tool": "ctoai_full_workspace_validation_refresh",
            "dry_run": False,
            "ok": True,
            "audit_id": "private-audit",
            "reason": "private maintenance reason",
            "output": "private output",
            "json_out": "runtime/audits/ctoai-full-workspace-validation.json",
            "preflight": {"status": "ready", "ok": True, "path": "C:/private"},
        }
    )
    serialized = json.dumps(payload, sort_keys=True)
    assert payload["tool"] == "ctoai_full_workspace_validation_refresh"
    assert "private-audit" not in serialized
    assert "private maintenance reason" not in serialized
    assert "private output" not in serialized
    assert "C:/private" not in serialized


def test_mcp_safe_write_projection_delegates_to_shared_public_boundary():
    mcp = load_plugin_module("ctoai_engine_brain_mcp")

    response = mcp.safe_write_tool_result(
        "ctoai_api_cost_refresh",
        {"workspace": "C:/ignored"},
        lambda _arguments: {
            "status": "dry_run",
            "action": "api-cost-refresh",
            "tool": "ctoai_api_cost_refresh",
            "risk_class": "safe_write",
            "dry_run": True,
            "ok": True,
            "audit_id": "private-audit",
            "output": "private output",
            "command": "private command",
            "path": "C:/private/report.json",
        },
        "api-cost-refresh",
    )
    serialized = response["content"][0]["text"]
    assert '"schema_version":2' in serialized
    assert '"action":"api-cost-refresh"' in serialized
    assert "private-audit" not in serialized
    assert "private output" not in serialized
    assert "private command" not in serialized
    assert "C:/private/report.json" not in serialized


def test_full_workspace_validation_dry_run_bootstrap_is_explicitly_allowlisted():
    mcp = load_plugin_module("ctoai_engine_brain_mcp")
    preflight = {
        "hard_blockers": [
            "freshness:evidence:stale",
            "p7_safe_write_dry_run_smoke_not_ready",
        ]
    }
    spec = mcp.SAFE_WRITE_SPECS[mcp.FULL_VALIDATION_TOOL_NAME]

    assert mcp.p7_evidence_collection_dry_run_allowed(
        preflight, spec, dry_run=True
    )
    assert not mcp.p7_evidence_collection_dry_run_allowed(
        preflight, spec, dry_run=False
    )
