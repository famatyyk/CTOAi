import importlib.util
import datetime as dt
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "ops" / "release_evidence_pack.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("release_evidence_pack", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _background_payload(generated_at: str) -> dict[str, object]:
    return {
        "schema_version": "ctoa.otclient-headless-status.v1",
        "status": "ready",
        "mode": "background_no_screen",
        "generated_at_utc": generated_at,
        "advisory_only": True,
        "safe_to_run_while_playing": True,
        "promotion_allowed": False,
        "dispatch_allowed": False,
        "runtime_actions": False,
        "process_state": "running",
        "interaction_contract": {
            "gui_automation": False,
            "mouse_keyboard_input": False,
            "window_focus": False,
            "screenshot_capture": False,
            "client_launch": False,
            "client_stop": False,
            "live_file_writes": False,
            "passive_reads_only": True,
            "evidence_write_scope": "runtime/solteria_helper_dev",
        },
        "checks": {
            "no_screen_contract": True,
            "client_process_stable_during_wrapper": True,
            "screenshot_count_stable_during_wrapper": True,
        },
        "wrapper_invariants": {
            "client_process_stable": True,
            "screenshot_count_stable": True,
        },
        "intrusive_actions_performed": [],
        "integrity": {
            "status": "passed",
            "matched_file_count": 58,
            "manifest_file_count": 58,
            "mutable_drift_count": 0,
            "profile_drift_count": 0,
            "mismatch_count": 0,
            "missing_count": 0,
            "invalid_path_count": 0,
            "oversize_count": 0,
            "live_files_unchanged_during_observation": True,
        },
        "capability": {
            "status": "fresh",
            "fresh": True,
            "runtime_state": "disarmed",
            "runtime_actions": False,
            "runtime_core_actions": False,
        },
        "blockers": [],
    }


def _write_p10_payload(module, path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        module.equipment_operator_readiness.documents.canonical_bytes(payload) + b"\n"
    )


def _write_blocked_p10_chain(module, helper_dev_dir: Path, now_ms: int) -> None:
    readiness = module.equipment_operator_readiness
    documents = readiness.documents
    preview = readiness.observation_preview
    dependency = readiness.dependency_preflight
    catalog = readiness.candidate_catalog
    change_plan = readiness.change_plan

    observation = {
        "status": "valid",
        "present": True,
        "valid": True,
        "schema_version": preview.OBSERVATION_SCHEMA,
        "observed_at_unix_ms": now_ms - 1_000,
        "observation_id": "equipment-release-evidence-1",
        "online": "online",
        "alive": "alive",
        "protection_zone": "outside",
        "protection_zone_source": "player_method",
        "inventory_api_available": True,
        "containers_complete": True,
        "ring": {"present": True, "item_id": 3051, "count": 1},
        "candidates": [
            {"container_id": 2, "slot_index": 1, "item_id": 3048, "count": 1}
        ],
        "cooldown": "ready",
        "cooldown_source": "game_cooldown_group",
        "producer_source": "otclient_guarded_adapter",
        "dispatch_allowed": False,
        "runtime_actions": False,
        "executes_plan": False,
        "execute_once_allowed": False,
        "promotion_allowed": False,
        "validation_errors": [],
        "p10_blocker": None,
    }
    background = {
        "schema_version": preview.BACKGROUND_SCHEMA,
        "mode": "background_no_screen",
        "status": "blocked",
        "advisory_only": True,
        "safe_to_run_while_playing": True,
        "dispatch_allowed": False,
        "runtime_actions": False,
        "promotion_allowed": False,
        "intrusive_actions_performed": [],
        "interaction_contract": dict(preview.INTERACTION_CONTRACT),
        "wrapper_invariants": {
            "client_process_stable": True,
            "screenshot_count_stable": True,
        },
        "capability": {
            "fresh": True,
            "contract_valid": True,
            "version_match": True,
            "runtime_actions": False,
            "runtime_core_actions": False,
            "equipment_shadow_observation": observation,
        },
        "blockers": ["waiting_for_p8_refresh"],
    }
    background_path = helper_dev_dir / "background_status.json"
    _write_p10_payload(module, background_path, background)
    background_document = documents.read_document(background_path)

    doctor = {
        "schema_version": "ctoa.equipment-capture-profile-doctor.v1",
        "status": "ready",
        "source": "local_operator_override",
        "path": str(
            ROOT / ".ctoa-local" / "otclient" / "equipment-shadow-capture-profile.json"
        ),
        "sha256": "a" * 64,
        "configured_by_operator": True,
        "slot": "ring",
        "identifiers_present": True,
        "candidate_slot_index_valid": True,
        "no_action_contract": True,
        "blockers": [],
        "next_action": "Run the separate P10 dependency preflight.",
        "runtime_actions": False,
        "live_file_writes": False,
        "runtime_readiness_claimed": False,
    }
    doctor_path = helper_dev_dir / "equipment_capture_profile_doctor.json"
    _write_p10_payload(module, doctor_path, doctor)
    doctor_document = documents.read_document(doctor_path)

    preview_payload = preview.build_preview(
        background=background_document,
        generated_at_unix_ms=now_ms,
    )
    preview_path = helper_dev_dir / "equipment_observation_preview.json"
    _write_p10_payload(module, preview_path, preview_payload)
    preview_document = documents.read_document(preview_path)

    missing = documents.document_from_payload(None, "missing")
    dependency_payload = dependency.evaluate_preflight(
        dependency.EvidenceBundle(
            p8_report=background_document,
            p9_report=missing,
            p9_receipt=missing,
            capture_doctor=doctor_document,
            observation_preview=preview_document,
        ),
        evaluated_at_unix_ms=now_ms,
    )
    dependency_path = helper_dev_dir / "equipment_dependency_preflight.json"
    _write_p10_payload(module, dependency_path, dependency_payload)

    catalog_payload = catalog.build_catalog(
        preview_document=preview_document,
        generated_at_unix_ms=now_ms,
    )
    catalog_path = helper_dev_dir / "equipment_candidate_catalog.json"
    _write_p10_payload(module, catalog_path, catalog_payload)

    plan_payload = change_plan.evaluate_change_plan(
        change_plan.CanonicalInputs(
            capture_doctor=doctor_document,
            observation_preview=preview_document,
        ),
        generated_at_unix_ms=now_ms,
    )
    plan_path = helper_dev_dir / "equipment_capture_profile_change_plan.json"
    _write_p10_payload(module, plan_path, plan_payload)

    source_documents = {
        "capture_doctor": documents.read_document(doctor_path),
        "observation_preview": documents.read_document(preview_path),
        "dependency_preflight": documents.read_document(dependency_path),
        "candidate_catalog": documents.read_document(catalog_path),
        "change_plan": documents.read_document(plan_path),
    }
    readiness_payload = readiness.evaluate_readiness(
        source_documents,
        generated_at_unix_ms=now_ms,
    )
    _write_p10_payload(
        module,
        helper_dev_dir / "equipment_operator_readiness.json",
        readiness_payload,
    )


def test_build_evidence_pack_handles_missing_artifacts(tmp_path: Path):
    module = _load_module()

    pack = module.build_evidence_pack(
        tmp_path / "releases" / "evidence",
        tmp_path / "runtime" / "repo-hygiene" / "local-pr-quality.json",
        tmp_path / "runtime" / "api-cost" / "latest.json",
        tmp_path / "runtime" / "control-center" / "action-audit.jsonl",
        tmp_path / "runtime" / "solteria_helper_dev",
        tmp_path / "AI" / "generated" / "P7_OPERATOR_BRIEF.json",
    )

    assert pack["release_evidence_file_count"] == 0
    assert pack["repo_hygiene"]["status"] == "missing"
    assert pack["api_cost_report"]["status"] == "missing"
    assert pack["control_center_audit"]["record_count"] == 0
    assert pack["otclient_helper"]["status"] == "missing"
    assert pack["otclient_helper"]["background_status"]["status"] == "missing"
    assert pack["otclient_helper"]["background_status"]["contract_valid"] is False
    assert pack["otclient_helper"]["background_status"]["fresh"] is False
    equipment_operator = pack["otclient_helper"]["equipment_operator_readiness"]
    assert (
        equipment_operator["schema_version"]
        == module.P10_EQUIPMENT_CONSUMER_PARITY_SCHEMA
    )
    assert equipment_operator["status"] == "missing"
    assert equipment_operator["reported_status"] == "missing"
    assert equipment_operator["contract_valid"] is False
    assert equipment_operator["operator_inputs_ready"] is False
    assert equipment_operator["eligibility_changed"] is False
    assert equipment_operator["eligibility_state"] == "unchanged"
    assert equipment_operator["acceptance_granted"] is False
    assert equipment_operator["read_only"] is True
    assert set(equipment_operator["artifacts"]) == set(
        module.EQUIPMENT_OPERATOR_ARTIFACT_FILES
    )
    assert all(
        artifact["status"] == "missing"
        for artifact in equipment_operator["artifacts"].values()
    )
    assert pack["p7_operator_brief"]["status"] == "missing"
    assert pack["p7_operator_brief"]["roadmap_generation"]["status"] == "missing"
    assert (
        "missing_p7_operator_brief"
        in pack["p7_operator_brief"]["roadmap_generation"]["hard_blockers"]
    )
    assert any("repo hygiene" in item.lower() for item in pack["recommendations"])
    assert any("api_cost_report" in item for item in pack["recommendations"])


def test_p10_equipment_readiness_projects_strict_read_only_blocked_chain(
    tmp_path: Path,
):
    module = _load_module()
    helper_dev_dir = tmp_path / "runtime" / "solteria_helper_dev"
    now = dt.datetime(2026, 7, 12, 12, 0, tzinfo=dt.UTC)
    now_ms = int(now.timestamp() * 1_000)
    _write_blocked_p10_chain(module, helper_dev_dir, now_ms)

    summary = module._equipment_operator_readiness_summary(
        helper_dev_dir,
        helper_dir_safe=True,
        now=now,
    )

    assert summary["status"] == "blocked"
    assert summary["schema_version"] == module.P10_EQUIPMENT_CONSUMER_PARITY_SCHEMA
    assert summary["reported_status"] == "blocked"
    assert summary["contract_valid"] is True
    assert summary["fresh"] is True
    assert summary["operator_inputs_ready"] is False
    assert summary["eligibility_changed"] is False
    assert summary["eligibility_state"] == "unchanged"
    assert summary["acceptance_granted"] is False
    assert summary["operational_readiness_claimed"] is False
    assert summary["read_only"] is True
    assert summary["blockers"]
    assert summary["next_actions"]
    assert all(
        action["changes_eligibility"] is False for action in summary["next_actions"]
    )
    assert all(
        summary[key] is False
        for key in (
            "live_file_writes",
            "dispatch_allowed",
            "runtime_actions",
            "executes_plan",
            "execute_once_allowed",
            "promotion_allowed",
        )
    )
    assert summary["intrusive_actions_performed"] == []
    assert set(summary["artifacts"]) == set(module.EQUIPMENT_OPERATOR_ARTIFACT_FILES)
    for artifact, projection in summary["artifacts"].items():
        assert projection["path"] == (
            "runtime/solteria_helper_dev/"
            + module.EQUIPMENT_OPERATOR_ARTIFACT_FILES[artifact]
        )
        assert projection["load_status"] == "loaded"
        assert (
            projection["schema_version"]
            == (module.EQUIPMENT_OPERATOR_EXPECTED_SCHEMAS[artifact])
        )
        assert len(projection["sha256"]) == 64
        assert projection["contract_valid"] is True
        assert projection["fresh"] is True


@pytest.mark.parametrize(
    ("artifact", "mutation"),
    [
        ("equipment_capture_profile_doctor", "schema"),
        ("equipment_observation_preview", "status"),
        ("equipment_candidate_catalog", "hash"),
        ("equipment_capture_profile_change_plan", "path"),
        ("equipment_dependency_preflight", "no_action"),
    ],
)
def test_p10_equipment_readiness_rejects_schema_status_hash_path_and_action_tamper(
    tmp_path: Path,
    artifact: str,
    mutation: str,
):
    module = _load_module()
    helper_dev_dir = tmp_path / "runtime" / "solteria_helper_dev"
    now = dt.datetime(2026, 7, 12, 12, 0, tzinfo=dt.UTC)
    now_ms = int(now.timestamp() * 1_000)
    _write_blocked_p10_chain(module, helper_dev_dir, now_ms)
    path = helper_dev_dir / module.EQUIPMENT_OPERATOR_ARTIFACT_FILES[artifact]
    payload = json.loads(path.read_text(encoding="utf-8"))
    if mutation == "schema":
        payload["schema_version"] = "ctoa.equipment-capture-profile-doctor.v2"
    elif mutation == "status":
        payload["status"] = "ready_to_dispatch"
    elif mutation == "hash":
        payload["preview_sha256"] = "f" * 64
    elif mutation == "path":
        payload["sources"]["capture_doctor"] = "runtime/override/doctor.json"
    else:
        payload["runtime_actions"] = True
    _write_p10_payload(module, path, payload)

    summary = module._equipment_operator_readiness_summary(
        helper_dev_dir,
        helper_dir_safe=True,
        now=now,
    )

    assert summary["status"] == "invalid"
    assert summary["contract_valid"] is False
    assert summary["operator_inputs_ready"] is False
    assert summary["eligibility_changed"] is False
    assert summary["acceptance_granted"] is False
    assert summary["artifacts"][artifact]["status"] == "invalid"
    assert summary["artifacts"][artifact]["contract_valid"] is False
    commands = [action["command"] for action in summary["next_actions"]]
    expected_source_commands = {
        "equipment_capture_profile_doctor": ".\\ctoa.ps1 otp10doctor",
        "equipment_observation_preview": ".\\ctoa.ps1 otp10preview",
        "equipment_dependency_preflight": ".\\ctoa.ps1 otp10preflight",
        "equipment_candidate_catalog": ".\\ctoa.ps1 otp10catalog",
        "equipment_capture_profile_change_plan": ".\\ctoa.ps1 otp10plan",
    }
    assert expected_source_commands[artifact] in commands
    assert commands[-1] == ".\\ctoa.ps1 otp10ready"
    assert all(
        action["changes_eligibility"] is False for action in summary["next_actions"]
    )


def test_p10_equipment_readiness_expires_without_changing_release_eligibility(
    tmp_path: Path,
):
    module = _load_module()
    helper_dev_dir = tmp_path / "runtime" / "solteria_helper_dev"
    generated_at = dt.datetime(2026, 7, 12, 12, 0, tzinfo=dt.UTC)
    _write_blocked_p10_chain(
        module,
        helper_dev_dir,
        int(generated_at.timestamp() * 1_000),
    )

    summary = module._equipment_operator_readiness_summary(
        helper_dev_dir,
        helper_dir_safe=True,
        now=generated_at
        + dt.timedelta(milliseconds=module.EQUIPMENT_OPERATOR_MAX_AGE_MS + 1),
    )

    assert summary["status"] == "stale"
    assert summary["reported_status"] == "blocked"
    assert summary["contract_valid"] is True
    assert summary["fresh"] is False
    assert summary["operator_inputs_ready"] is False
    assert summary["eligibility_changed"] is False
    assert summary["eligibility_state"] == "unchanged"
    assert summary["acceptance_granted"] is False
    assert any(blocker.endswith("_stale") for blocker in summary["blockers"])


def test_background_status_expires_without_affecting_live_promotion(tmp_path: Path):
    module = _load_module()
    helper_dev_dir = tmp_path / "runtime" / "solteria_helper_dev"
    helper_dev_dir.mkdir(parents=True)
    generated_at = (
        dt.datetime.now(dt.UTC)
        - dt.timedelta(seconds=module.BACKGROUND_STATUS_MAX_AGE_SECONDS + 1)
    ).isoformat()
    (helper_dev_dir / "background_status.json").write_text(
        json.dumps(_background_payload(generated_at)), encoding="utf-8"
    )

    helper = module._helper_status(helper_dev_dir)
    background = helper["background_status"]

    assert background["reported_status"] == "ready"
    assert background["status"] == "stale"
    assert background["contract_valid"] is True
    assert background["fresh"] is False
    assert background["promotion_allowed"] is False
    assert background["dispatch_allowed"] is False
    assert helper["live_promoted"] is False
    assert helper["releasable_to_live"] is False


def test_background_status_accepts_consistent_untrusted_pin_as_blocked_evidence(
    tmp_path: Path,
):
    module = _load_module()
    payload = _background_payload(dt.datetime.now(dt.UTC).isoformat())
    payload["status"] = "blocked"
    payload["blockers"] = ["live_manifest_pin_untrusted"]
    integrity = payload["integrity"]
    capability = payload["capability"]
    assert isinstance(integrity, dict)
    assert isinstance(capability, dict)
    integrity["status"] = "untrusted_pin"
    integrity["matched_file_count"] = 0
    integrity["live_files_unchanged_during_observation"] = False
    integrity["pin_errors"] = [
        "live_manifest_origin_invalid",
        "live_promotion_manifest_path_mismatch",
        "live_promotion_manifest_sha256_mismatch",
        "live_promotion_timestamp_mismatch",
    ]
    integrity["pin_remediation"] = {
        "classification": "legacy_or_unbound_attestation",
        "required_action": "refresh_official_live_promotion_after_current_gates",
        "observer_can_write_trust_anchor": False,
        "historical_rebinding_allowed": False,
        "requires_current_release_gate": True,
        "requires_explicit_live_approval": True,
    }
    integrity["diagnostic_parity"] = {
        "attempted": True,
        "status": "failed",
        "manifest_file_count": 58,
        "matched_file_count": 57,
        "mismatch_count": 0,
        "mutable_drift_count": 1,
        "profile_drift_count": 1,
        "missing_count": 0,
        "invalid_path_count": 0,
        "oversize_count": 0,
        "actual_total_bytes": 1000,
        "stable_during_observation": True,
        "acceptance_allowed": False,
    }
    capability["status"] = "missing"
    capability["fresh"] = False

    summary = module._background_status_summary(
        payload,
        tmp_path / "background_status.json",
        artifact_present=True,
    )

    assert summary["status"] == "blocked"
    assert summary["contract_valid"] is True
    assert summary["fresh"] is True
    assert summary["integrity_status"] == "untrusted_pin"
    assert summary["blockers"] == ["live_manifest_pin_untrusted"]
    assert summary["pin_errors"] == integrity["pin_errors"]
    assert summary["pin_classification"] == "legacy_or_unbound_attestation"
    assert summary["pin_required_action"] == (
        "refresh_official_live_promotion_after_current_gates"
    )
    assert summary["pin_historical_rebinding_allowed"] is False
    assert summary["pin_requires_explicit_live_approval"] is True
    assert summary["diagnostic_parity_status"] == "failed"
    assert summary["diagnostic_parity_attempted"] is True
    assert summary["diagnostic_profile_drift_count"] == 1
    assert summary["diagnostic_stable_during_observation"] is True
    assert summary["diagnostic_acceptance_allowed"] is False


def test_background_status_invalid_contract_and_counts_fail_closed(tmp_path: Path):
    module = _load_module()
    helper_dev_dir = tmp_path / "runtime" / "solteria_helper_dev"
    helper_dev_dir.mkdir(parents=True)
    payload = _background_payload(dt.datetime.now(dt.UTC).isoformat())
    payload["promotion_allowed"] = True
    payload["blockers"] = "not-a-list"
    integrity = payload["integrity"]
    assert isinstance(integrity, dict)
    integrity["matched_file_count"] = "not-a-number"
    (helper_dev_dir / "background_status.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )

    background = module._helper_status(helper_dev_dir)["background_status"]

    assert background["status"] == "blocked"
    assert background["contract_valid"] is False
    assert background["fresh"] is False
    assert background["matched_file_count"] == 0
    assert background["blockers"] == []
    assert {"promotion_allowed", "blockers", "matched_file_count"}.issubset(
        background["contract_errors"]
    )


@pytest.mark.parametrize(
    ("mutation", "expected_error"),
    [
        ("interaction_input", "interaction_contract"),
        ("interaction_numeric", "interaction_contract"),
        ("interaction_extra", "interaction_contract"),
        ("wrapper_process", "wrapper_invariants"),
        ("no_screen_check", "checks_no_screen_contract"),
        (
            "wrapper_process_check",
            "checks_client_process_stable_during_wrapper",
        ),
        (
            "wrapper_screenshot_check",
            "checks_screenshot_count_stable_during_wrapper",
        ),
        ("intrusive_action", "intrusive_actions_performed"),
        ("status_type", "status"),
        ("count_overflow", "integrity_count_consistency"),
        ("drift_alias", "integrity_drift_consistency"),
        ("passed_with_mismatch", "integrity_status_consistency"),
        ("pin_errors_shape", "pin_errors"),
        ("pin_rebinding", "pin_remediation"),
        ("diagnostic_acceptance", "diagnostic_parity"),
    ],
)
def test_background_status_full_no_action_contract_mutations_fail_closed(
    tmp_path: Path, mutation: str, expected_error: str
):
    module = _load_module()
    payload = _background_payload(dt.datetime.now(dt.UTC).isoformat())

    interaction = payload["interaction_contract"]
    wrapper = payload["wrapper_invariants"]
    status_checks = payload["checks"]
    integrity = payload["integrity"]
    assert isinstance(interaction, dict)
    assert isinstance(wrapper, dict)
    assert isinstance(status_checks, dict)
    assert isinstance(integrity, dict)

    if mutation == "interaction_input":
        interaction["mouse_keyboard_input"] = True
    elif mutation == "interaction_numeric":
        interaction["mouse_keyboard_input"] = 0
    elif mutation == "interaction_extra":
        interaction["unvalidated_action"] = False
    elif mutation == "wrapper_process":
        wrapper["client_process_stable"] = False
    elif mutation == "no_screen_check":
        status_checks["no_screen_contract"] = False
    elif mutation == "wrapper_process_check":
        status_checks["client_process_stable_during_wrapper"] = False
    elif mutation == "wrapper_screenshot_check":
        status_checks["screenshot_count_stable_during_wrapper"] = False
    elif mutation == "intrusive_action":
        payload["intrusive_actions_performed"] = ["screenshot_capture"]
    elif mutation == "status_type":
        payload["status"] = []
    elif mutation == "count_overflow":
        integrity["mismatch_count"] = 1
    elif mutation == "drift_alias":
        integrity["profile_drift_count"] = 1
    elif mutation == "passed_with_mismatch":
        integrity["matched_file_count"] = 57
        integrity["mismatch_count"] = 1
    elif mutation == "pin_errors_shape":
        integrity["pin_errors"] = [{"unexpected": "shape"}]
    elif mutation == "pin_rebinding":
        integrity["pin_remediation"] = {
            "classification": "legacy_or_unbound_attestation",
            "required_action": "refresh_official_live_promotion_after_current_gates",
            "observer_can_write_trust_anchor": False,
            "historical_rebinding_allowed": True,
            "requires_current_release_gate": True,
            "requires_explicit_live_approval": True,
        }
    elif mutation == "diagnostic_acceptance":
        integrity["diagnostic_parity"] = {
            "attempted": True,
            "status": "passed",
            "manifest_file_count": 58,
            "matched_file_count": 58,
            "mismatch_count": 0,
            "mutable_drift_count": 0,
            "profile_drift_count": 0,
            "missing_count": 0,
            "invalid_path_count": 0,
            "oversize_count": 0,
            "actual_total_bytes": 1000,
            "stable_during_observation": True,
            "acceptance_allowed": True,
        }
    else:  # pragma: no cover - the parametrization is exhaustive
        raise AssertionError(f"unsupported mutation: {mutation}")

    summary = module._background_status_summary(
        payload,
        tmp_path / "background_status.json",
        artifact_present=True,
    )

    assert summary["status"] == "blocked"
    assert summary["contract_valid"] is False
    assert summary["fresh"] is False
    assert expected_error in summary["contract_errors"]


def test_build_evidence_pack_reads_current_artifacts(tmp_path: Path):
    module = _load_module()
    background_generated_at = dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()

    releases_dir = tmp_path / "releases" / "evidence"
    sprint_dir = releases_dir / "sprint-056"
    sprint_dir.mkdir(parents=True)
    evidence_file = sprint_dir / "CTOA-300.md"
    evidence_file.write_text("# Evidence\n", encoding="utf-8")

    quality_path = tmp_path / "runtime" / "repo-hygiene" / "local-pr-quality.json"
    quality_path.parent.mkdir(parents=True, exist_ok=True)
    quality_path.write_text(
        """
{
  "status": "PASS",
  "finding_count": 0,
  "summary": {
    "private_count": 0,
    "public_count": 0,
    "review_count": 0
  }
}
""".strip(),
        encoding="utf-8",
    )

    cost_path = tmp_path / "runtime" / "api-cost" / "latest.json"
    cost_path.parent.mkdir(parents=True, exist_ok=True)
    cost_path.write_text(
        """
{
  "records_seen": 3,
  "total_tokens": 1234,
  "total_cost_usd": 1.25,
  "anomalies": [{"component": "prompt-forge"}]
}
""".strip(),
        encoding="utf-8",
    )

    audit_path = tmp_path / "runtime" / "control-center" / "action-audit.jsonl"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text('{"ok": true}\n{"ok": false}\n', encoding="utf-8")

    helper_dev_dir = tmp_path / "runtime" / "solteria_helper_dev"
    helper_dev_dir.mkdir(parents=True)
    (helper_dev_dir / "manifest.json").write_text(
        json.dumps(
            {"helper_version": "v1.1b", "files": [{"path": "ctoa_otclient_loader.lua"}]}
        ),
        encoding="utf-8",
    )
    (helper_dev_dir / "validation.json").write_text(
        json.dumps({"status": "passed"}), encoding="utf-8"
    )
    (helper_dev_dir / "release_readiness.json").write_text(
        json.dumps(
            {
                "status": "static-passed",
                "zip": {"path": "ctoa_otclient_v1.1b.zip", "sha256": "abc123"},
            }
        ),
        encoding="utf-8",
    )
    (helper_dev_dir / "release_gate.json").write_text(
        json.dumps(
            {
                "status": "blocked",
                "releasable_to_live": False,
                "next_action": "Run SmokeAttachAll after sandbox character is in-world.",
                "next_command": "launch",
                "gates": [
                    {
                        "name": "SmokeAttachAll",
                        "status": "pending",
                        "reason": "Run SmokeAttachAll after sandbox character is in-world.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (helper_dev_dir / "smoke_preflight.json").write_text(
        json.dumps({"status": "passed"}), encoding="utf-8"
    )
    (helper_dev_dir / "module_contract.json").write_text(
        json.dumps(
            {
                "status": "passed",
                "passed_count": 16,
                "check_count": 16,
                "forbidden_count": 0,
            }
        ),
        encoding="utf-8",
    )
    (helper_dev_dir / "module_audit.json").write_text(
        json.dumps(
            {
                "status": "needs_modularization",
                "helper_budget_status": "over_budget",
                "helper_line_count": 5100,
                "helper_line_budget": 4500,
                "next_supplemental_id": "",
                "next_module_id": "heal_friend",
            }
        ),
        encoding="utf-8",
    )
    (helper_dev_dir / "smoke_status.json").write_text(
        json.dumps({"status": "not_running"}), encoding="utf-8"
    )
    (helper_dev_dir / "background_status.json").write_text(
        json.dumps(_background_payload(background_generated_at)),
        encoding="utf-8",
    )
    (helper_dev_dir / "goal_status.json").write_text(
        json.dumps(
            {
                "status": "blocked",
                "next_action": "Run SmokeAttachModules after sandbox character is in-world.",
                "next_command": "launch",
                "blockers": [
                    "ModuleAttachSmoke: Run SmokeAttachModules after sandbox character is in-world."
                ],
                "sandbox_smoke_queue": {
                    "status": "ready_for_operator",
                    "path": str(helper_dev_dir / "sandbox_smoke_queue.json"),
                    "runtime_status": "not_running",
                    "release_gate_status": "blocked",
                    "next_action": "Launch sandbox client and enter test character",
                    "required_count": 5,
                    "queued_count": 4,
                    "next_steps": [
                        {
                            "order": 2,
                            "step_id": "launch_sandbox",
                            "status": "required",
                            "command": "powershell -Action Launch",
                        },
                        {
                            "order": 4,
                            "step_id": "module_attach_group",
                            "status": "required",
                            "command": "powershell -Action SmokeAttachModules",
                        },
                    ],
                },
            }
        ),
        encoding="utf-8",
    )

    operator_brief_path = tmp_path / "AI" / "generated" / "P7_OPERATOR_BRIEF.json"
    operator_brief_path.parent.mkdir(parents=True)
    operator_brief_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-07-07T04:28:38+00:00",
                "decision": "ready_for_p7_operator_workflow",
                "status": "ready",
                "hard_blockers": [],
                "warnings": ["brain_doctor", "diff_check"],
                "next_safe_command": "Start a fresh Codex thread and use the ctoai_engine_brain_brief MCP tool.",
                "policy": "Read-only generated operator brief. Do not run deploy/live actions from this artifact.",
                "action_readiness": {
                    "status": "safe_write_tools_enabled",
                    "decision": "monitor_enabled_safe_write_tools",
                    "candidate_count": 5,
                    "audited_candidate_count": 5,
                    "mcp_write_tool_count": 5,
                    "enabled_safe_write_tools": [
                        {
                            "action_id": "repo-hygiene-refresh",
                            "mcp_tool": "ctoai_repo_hygiene_refresh",
                            "risk_class": "safe_write",
                        },
                        {
                            "action_id": "api-cost-refresh",
                            "mcp_tool": "ctoai_api_cost_refresh",
                            "risk_class": "safe_write",
                        },
                        {
                            "action_id": "evidence-pack-refresh",
                            "mcp_tool": "ctoai_evidence_pack_refresh",
                            "risk_class": "safe_write",
                        },
                        {
                            "action_id": "engine-brain-refresh",
                            "mcp_tool": "ctoai_engine_brain_refresh",
                            "risk_class": "safe_write",
                        },
                        {
                            "action_id": "p7-cockpit-smoke-refresh",
                            "mcp_tool": "ctoai_p7_cockpit_smoke_refresh",
                            "risk_class": "safe_write",
                        },
                    ],
                    "next_safe_command": "Run ctoai_repo_hygiene_refresh, ctoai_api_cost_refresh, ctoai_evidence_pack_refresh, ctoai_engine_brain_refresh, and ctoai_p7_cockpit_smoke_refresh with dry_run=true.",
                },
                "safe_write_tool_design": {
                    "status": "implemented",
                    "decision": "ready_for_dry_run_operation",
                    "selected_action_id": "evidence-pack-refresh",
                    "proposed_mcp_tool": "ctoai_evidence_pack_refresh",
                    "risk_class": "safe_write",
                    "mode": "dry_run_first",
                    "mcp_enabled": True,
                    "next_safe_command": "Run ctoai_evidence_pack_refresh with dry_run=true.",
                },
                "roadmap_generation": {
                    "status": "ready",
                    "doc_sync_status": "passed",
                    "doc_count": 3,
                    "ready_doc_count": 3,
                    "hard_blockers": [],
                    "next_action": "Keep roadmap generation read-only in Control Center Evidence.",
                    "blocked_until": "risk model coverage, audit replay evidence, Control Center gates, and tests exist before adding any new MCP write tool.",
                },
            }
        ),
        encoding="utf-8",
    )

    pack = module.build_evidence_pack(
        releases_dir,
        quality_path,
        cost_path,
        audit_path,
        helper_dev_dir,
        operator_brief_path,
    )

    assert pack["release_evidence_file_count"] == 1
    assert pack["repo_hygiene"]["status"] == "PASS"
    assert pack["api_cost_report"]["status"] == "ready"
    assert pack["api_cost_report"]["records_seen"] == 3
    assert pack["api_cost_report"]["anomaly_count"] == 1
    assert pack["control_center_audit"]["record_count"] == 2
    assert pack["otclient_helper"]["status"] == "blocked"
    assert pack["otclient_helper"]["helper_version"] == "v1.1b"
    assert pack["otclient_helper"]["release_gate_status"] == "blocked"
    assert pack["otclient_helper"]["smoke_preflight_status"] == "passed"
    assert pack["otclient_helper"]["module_contract"]["status"] == "passed"
    assert pack["otclient_helper"]["module_contract"]["passed_count"] == 16
    assert pack["otclient_helper"]["module_contract"]["check_count"] == 16
    assert pack["otclient_helper"]["module_contract"]["forbidden_count"] == 0
    assert pack["otclient_helper"]["module_audit"]["status"] == "needs_modularization"
    assert (
        pack["otclient_helper"]["module_audit"]["helper_budget_status"] == "over_budget"
    )
    assert pack["otclient_helper"]["module_audit"]["helper_line_count"] == 5100
    assert pack["otclient_helper"]["module_audit"]["helper_line_budget"] == 4500
    assert pack["otclient_helper"]["module_audit"]["next_supplemental_id"] == ""
    assert pack["otclient_helper"]["module_audit"]["next_module_id"] == "heal_friend"
    assert pack["otclient_helper"]["package_sha256"] == "abc123"
    assert (
        pack["otclient_helper"]["sandbox_smoke_queue"]["status"] == "ready_for_operator"
    )
    assert pack["otclient_helper"]["sandbox_smoke_queue"]["required_count"] == 5
    assert pack["otclient_helper"]["sandbox_smoke_queue"]["queued_count"] == 4
    assert (
        pack["otclient_helper"]["sandbox_smoke_queue"]["next_steps"][0]["step_id"]
        == "launch_sandbox"
    )
    assert pack["otclient_helper"]["background_status"] == {
        "status": "ready",
        "reported_status": "ready",
        "mode": "background_no_screen",
        "generated_at_utc": background_generated_at,
        "max_age_seconds": 30,
        "age_seconds": pytest.approx(0, abs=2),
        "fresh": True,
        "contract_valid": True,
        "contract_errors": [],
        "advisory_only": True,
        "safe_to_run_while_playing": True,
        "promotion_allowed": False,
        "dispatch_allowed": False,
        "runtime_actions": False,
        "process_state": "running",
        "integrity_status": "passed",
        "pin_errors": [],
        "pin_classification": "unknown",
        "pin_required_action": "none",
        "pin_historical_rebinding_allowed": False,
        "pin_requires_explicit_live_approval": False,
        "diagnostic_parity_status": "unknown",
        "diagnostic_parity_attempted": False,
        "diagnostic_profile_drift_count": 0,
        "diagnostic_stable_during_observation": False,
        "diagnostic_acceptance_allowed": False,
        "matched_file_count": 58,
        "manifest_file_count": 58,
        "mutable_drift_count": 0,
        "capability_status": "fresh",
        "capability_fresh": True,
        "runtime_state": "disarmed",
        "blockers": [],
        "path": str(helper_dev_dir / "background_status.json").replace("\\", "/"),
    }
    assert pack["p7_operator_brief"]["status"] == "ready"
    assert pack["p7_operator_brief"]["decision"] == "ready_for_p7_operator_workflow"
    assert pack["p7_operator_brief"]["warning_count"] == 2
    assert (
        pack["p7_operator_brief"]["action_readiness"]["status"]
        == "safe_write_tools_enabled"
    )
    assert pack["p7_operator_brief"]["action_readiness"][
        "enabled_safe_write_tools"
    ] == [
        {
            "action_id": "repo-hygiene-refresh",
            "mcp_tool": "ctoai_repo_hygiene_refresh",
            "risk_class": "safe_write",
        },
        {
            "action_id": "api-cost-refresh",
            "mcp_tool": "ctoai_api_cost_refresh",
            "risk_class": "safe_write",
        },
        {
            "action_id": "evidence-pack-refresh",
            "mcp_tool": "ctoai_evidence_pack_refresh",
            "risk_class": "safe_write",
        },
        {
            "action_id": "engine-brain-refresh",
            "mcp_tool": "ctoai_engine_brain_refresh",
            "risk_class": "safe_write",
        },
        {
            "action_id": "p7-cockpit-smoke-refresh",
            "mcp_tool": "ctoai_p7_cockpit_smoke_refresh",
            "risk_class": "safe_write",
        },
    ]
    assert (
        pack["p7_operator_brief"]["safe_write_tool_design"]["status"] == "implemented"
    )
    assert (
        pack["p7_operator_brief"]["safe_write_tool_design"]["proposed_mcp_tool"]
        == "ctoai_evidence_pack_refresh"
    )
    assert pack["p7_operator_brief"]["safe_write_tool_design"]["mcp_enabled"] is True
    assert pack["p7_operator_brief"]["roadmap_generation"]["status"] == "ready"
    assert (
        pack["p7_operator_brief"]["roadmap_generation"]["doc_sync_status"] == "passed"
    )
    assert pack["p7_operator_brief"]["roadmap_generation"]["ready_doc_count"] == 3
    assert pack["p7_operator_brief"]["roadmap_generation"]["doc_count"] == 3
    assert pack["p7_operator_brief"]["roadmap_generation"]["hard_blockers"] == []
    assert pack["latest_release_evidence"]["path"].endswith("CTOA-300.md")
    assert pack["release_sprints"][0]["sprint"] == "sprint-056"

    markdown = module.render_markdown(pack)
    assert "- P7 roadmap generation: `ready`" in markdown
    assert "- Roadmap docs ready: `3/3`" in markdown
    assert "- Sandbox smoke queue: `ready_for_operator`" in markdown
    assert "- ModuleContract: `passed` (16/16)" in markdown
    assert "### Sandbox Smoke Queue" in markdown
    assert "`launch_sandbox` `required`" in markdown


def test_build_evidence_pack_uses_configured_defaults(tmp_path: Path, monkeypatch):
    releases_dir = tmp_path / "configured" / "releases" / "evidence"
    sprint_dir = releases_dir / "sprint-099"
    sprint_dir.mkdir(parents=True)
    (sprint_dir / "CTOA-999.md").write_text("# Evidence\n", encoding="utf-8")

    quality_path = (
        tmp_path / "configured" / "runtime" / "repo-hygiene" / "local-pr-quality.json"
    )
    quality_path.parent.mkdir(parents=True, exist_ok=True)
    quality_path.write_text(
        json.dumps({"status": "PASS", "finding_count": 0, "summary": {}}),
        encoding="utf-8",
    )

    cost_path = tmp_path / "configured" / "runtime" / "api-cost" / "latest.json"
    cost_path.parent.mkdir(parents=True, exist_ok=True)
    cost_path.write_text(
        json.dumps({"records_seen": 1, "total_tokens": 10, "total_cost_usd": 0.1}),
        encoding="utf-8",
    )

    audit_path = (
        tmp_path / "configured" / "runtime" / "control-center" / "action-audit.jsonl"
    )
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text('{"ok": true}\n', encoding="utf-8")

    helper_dev_dir = tmp_path / "configured" / "runtime" / "solteria_helper_dev"
    helper_dev_dir.mkdir(parents=True)
    (helper_dev_dir / "manifest.json").write_text(
        json.dumps({"helper_version": "v1.1b", "files": []}), encoding="utf-8"
    )
    operator_brief_path = (
        tmp_path / "configured" / "AI" / "generated" / "P7_OPERATOR_BRIEF.json"
    )
    operator_brief_path.parent.mkdir(parents=True)
    operator_brief_path.write_text(
        json.dumps({"status": "ready", "decision": "ready_for_p7_operator_workflow"}),
        encoding="utf-8",
    )

    monkeypatch.setenv("CTOA_RELEASES_DIR", str(releases_dir))
    monkeypatch.setenv("CTOA_REPO_HYGIENE_PATH", str(quality_path))
    monkeypatch.setenv("CTOA_API_COST_REPORT_PATH", str(cost_path))
    monkeypatch.setenv("CTOA_ACTION_AUDIT_PATH", str(audit_path))
    monkeypatch.setenv("CTOA_HELPER_DEV_DIR", str(helper_dev_dir))
    monkeypatch.setenv(
        "CTOA_ENGINE_BRAIN_OPERATOR_BRIEF_PATH", str(operator_brief_path)
    )

    module = _load_module()
    pack = module.build_evidence_pack()

    assert pack["releases_dir"] == str(releases_dir).replace("\\", "/")
    assert pack["quality_path"] == str(quality_path).replace("\\", "/")
    assert pack["cost_report_path"] == str(cost_path).replace("\\", "/")
    assert pack["action_audit_path"] == str(audit_path).replace("\\", "/")
    assert pack["helper_dev_dir"] == str(helper_dev_dir).replace("\\", "/")
    assert pack["engine_brain_operator_brief_path"] == str(operator_brief_path).replace(
        "\\", "/"
    )
    assert pack["otclient_helper"]["helper_version"] == "v1.1b"
    assert pack["p7_operator_brief"]["decision"] == "ready_for_p7_operator_workflow"
    assert pack["latest_release_evidence"]["path"].endswith("CTOA-999.md")


def test_build_evidence_pack_rejects_symlinked_configured_json_and_audit(
    tmp_path: Path,
):
    module = _load_module()
    releases_dir = tmp_path / "releases" / "evidence"
    releases_dir.mkdir(parents=True)
    quality_path = tmp_path / "runtime" / "repo-hygiene" / "local-pr-quality.json"
    quality_path.parent.mkdir(parents=True)
    audit_path = tmp_path / "runtime" / "control-center" / "action-audit.jsonl"
    audit_path.parent.mkdir(parents=True)
    outside_quality = tmp_path / "outside-quality.json"
    outside_audit = tmp_path / "outside-audit.jsonl"
    outside_quality.write_text(
        json.dumps({"status": "PASS", "finding_count": 0}), encoding="utf-8"
    )
    outside_audit.write_text(
        '{"ok": true, "token": "audit-secret-token"}\n', encoding="utf-8"
    )

    try:
        quality_path.symlink_to(outside_quality)
        audit_path.symlink_to(outside_audit)
    except OSError as exc:
        pytest.skip(f"symlinks are not available: {exc}")

    pack = module.build_evidence_pack(
        releases_dir,
        quality_path,
        tmp_path / "runtime" / "api-cost" / "latest.json",
        audit_path,
        tmp_path / "runtime" / "solteria_helper_dev",
        tmp_path / "AI" / "generated" / "P7_OPERATOR_BRIEF.json",
    )
    serialized = json.dumps(pack)

    assert pack["repo_hygiene"]["status"] == "missing"
    assert pack["control_center_audit"]["record_count"] == 0
    assert "audit-secret-token" not in serialized
    assert "outside-quality.json" not in serialized
    assert "outside-audit.jsonl" not in serialized


def test_build_evidence_pack_ignores_symlinked_release_markdown(tmp_path: Path):
    module = _load_module()
    releases_dir = tmp_path / "releases" / "evidence"
    sprint_dir = releases_dir / "sprint-777"
    sprint_dir.mkdir(parents=True)
    outside_markdown = tmp_path / "outside-evidence.md"
    linked_markdown = sprint_dir / "CTOA-777.md"
    outside_markdown.write_text(
        "# External evidence\nsecret=outside-markdown-secret\n", encoding="utf-8"
    )

    try:
        linked_markdown.symlink_to(outside_markdown)
    except OSError as exc:
        pytest.skip(f"symlinks are not available: {exc}")

    pack = module.build_evidence_pack(
        releases_dir,
        tmp_path / "runtime" / "repo-hygiene" / "local-pr-quality.json",
        tmp_path / "runtime" / "api-cost" / "latest.json",
        tmp_path / "runtime" / "control-center" / "action-audit.jsonl",
        tmp_path / "runtime" / "solteria_helper_dev",
        tmp_path / "AI" / "generated" / "P7_OPERATOR_BRIEF.json",
    )
    serialized = json.dumps(pack)

    assert pack["release_evidence_file_count"] == 0
    assert pack["latest_release_evidence"] is None
    assert pack["release_sprints"][0]["file_count"] == 0
    assert "outside-markdown-secret" not in serialized
    assert "outside-evidence.md" not in serialized


def test_build_evidence_pack_rejects_symlinked_p7_operator_brief(tmp_path: Path):
    module = _load_module()
    releases_dir = tmp_path / "releases" / "evidence"
    releases_dir.mkdir(parents=True)
    operator_brief_path = tmp_path / "AI" / "generated" / "P7_OPERATOR_BRIEF.json"
    operator_brief_path.parent.mkdir(parents=True)
    outside_brief = tmp_path / "outside-p7-brief.json"
    outside_brief.write_text(
        json.dumps(
            {
                "status": "ready",
                "decision": "secret decision token=operator-secret-token",
                "next_safe_command": "leak password=operator-secret-password",
            }
        ),
        encoding="utf-8",
    )

    try:
        operator_brief_path.symlink_to(outside_brief)
    except OSError as exc:
        pytest.skip(f"symlinks are not available: {exc}")

    pack = module.build_evidence_pack(
        releases_dir,
        tmp_path / "runtime" / "repo-hygiene" / "local-pr-quality.json",
        tmp_path / "runtime" / "api-cost" / "latest.json",
        tmp_path / "runtime" / "control-center" / "action-audit.jsonl",
        tmp_path / "runtime" / "solteria_helper_dev",
        operator_brief_path,
    )
    serialized = json.dumps(pack)

    assert pack["p7_operator_brief"]["status"] == "missing"
    assert pack["p7_operator_brief"]["decision"] == "missing"
    assert "operator-secret-token" not in serialized
    assert "operator-secret-password" not in serialized
    assert "outside-p7-brief.json" not in serialized


def test_helper_status_rejects_symlinked_helper_dev_dir(tmp_path: Path):
    module = _load_module()
    outside_helper = tmp_path / "outside-helper"
    outside_helper.mkdir()
    (outside_helper / "manifest.json").write_text(
        json.dumps({"helper_version": "v9-unsafe", "files": []}),
        encoding="utf-8",
    )
    helper_dev_dir = tmp_path / "runtime" / "solteria_helper_dev"
    helper_dev_dir.parent.mkdir(parents=True)

    try:
        helper_dev_dir.symlink_to(outside_helper, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlinks are not available: {exc}")

    status = module._helper_status(helper_dev_dir)

    assert status["status"] == "missing"
    assert status["helper_version"] == "unknown"


def test_helper_status_blocks_inconsistent_releasable_gate_with_pending_blocker(
    tmp_path: Path,
):
    module = _load_module()
    helper_dev_dir = tmp_path / "runtime" / "solteria_helper_dev"
    helper_dev_dir.mkdir(parents=True)
    (helper_dev_dir / "manifest.json").write_text(
        json.dumps({"helper_version": "v1.1b", "files": []}), encoding="utf-8"
    )
    (helper_dev_dir / "release_gate.json").write_text(
        json.dumps(
            {
                "status": "passed",
                "releasable_to_live": True,
                "gates": [
                    {
                        "name": "live_approval",
                        "status": "pending",
                        "reason": "Live deployment requires explicit user approval.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    status = module._helper_status(helper_dev_dir)

    assert status["release_gate_releasable_to_live"] is True
    assert status["releasable_to_live"] is False
    assert status["status"] == "blocked"
    assert status["blockers"] == [
        "live_approval: Live deployment requires explicit user approval."
    ]


def test_helper_status_promoted_requires_durable_live_promotion_evidence(
    tmp_path: Path,
):
    module = _load_module()
    helper_dev_dir = tmp_path / "runtime" / "solteria_helper_dev"
    helper_dev_dir.mkdir(parents=True)
    (helper_dev_dir / "manifest.json").write_text(
        json.dumps(
            {"helper_version": "v1.1b", "files": [{"path": "ctoa_native_helper.lua"}]}
        ),
        encoding="utf-8",
    )
    (helper_dev_dir / "release_readiness.json").write_text(
        json.dumps(
            {
                "status": "static-passed",
                "zip": {"path": "ctoa_otclient_v1.1b.zip", "sha256": "abc123"},
            }
        ),
        encoding="utf-8",
    )
    (helper_dev_dir / "release_gate.json").write_text(
        json.dumps(
            {
                "status": "passed",
                "releasable_to_live": True,
                "next_action": "Release gate passed.",
                "next_command": "",
                "gates": [
                    {"name": "PrepareDev", "status": "passed"},
                    {"name": "ValidateDev", "status": "passed"},
                    {
                        "name": "live_approval",
                        "status": "passed",
                        "evidence": "-ApproveLiveDeploy",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    (helper_dev_dir / "goal_status.json").write_text(
        json.dumps(
            {"next_command": "stale command that must not leak into promoted evidence"}
        ),
        encoding="utf-8",
    )
    (helper_dev_dir / "live_promotion.json").write_text(
        json.dumps(
            {
                "created_at": "2026-07-06T11:06:46",
                "helper_version": "v1.1b",
                "approval_switch": "ApproveLiveDeploy",
                "verification": "stage_live_sha256_match",
                "verified_file_count": 1,
                "live_client": "C:/Users/zycie/AppData/Local/Solteria/client",
                "backup": "runtime/solteria_helper_dev/live_backup_20260706-110646",
            }
        ),
        encoding="utf-8",
    )

    status = module._helper_status(helper_dev_dir)

    assert status["status"] == "promoted"
    assert status["releasable_to_live"] is True
    assert status["live_promoted"] is True
    assert status["live_promotion_status"] == "promoted"
    assert status["live_promotion_created_at"] == "2026-07-06T11:06:46"
    assert status["next_command"] == ""
    assert status["equipment_operator_readiness"]["status"] == "missing"
    assert status["equipment_operator_readiness"]["eligibility_state"] == "unchanged"
    assert status["equipment_operator_readiness"]["acceptance_granted"] is False
    assert status["paths"]["live_promotion"].endswith("live_promotion.json")
def test_equipment_operator_refresh_run_summary_fails_closed(tmp_path: Path) -> None:
    module = _load_module()
    artifact = tmp_path / "equipment_operator_refresh_run.json"
    missing = module._equipment_operator_refresh_run_summary(None, artifact, artifact_present=False)
    assert missing["status"] == "missing"
    assert missing["contract_valid"] is False
    assert missing["dispatch_allowed"] is False
    assert missing["eligibility_changed"] is False

    invalid = module._equipment_operator_refresh_run_summary(
        {"schema_version": module.P10_EQUIPMENT_OPERATOR_REFRESH_RUN_SCHEMA, "status": "completed"},
        artifact,
        artifact_present=True,
    )
    assert invalid["status"] == "invalid"
    assert invalid["run_id"] == ""
    assert invalid["artifact_hashes"] == {}
    assert invalid["no_action_verified"] is False
