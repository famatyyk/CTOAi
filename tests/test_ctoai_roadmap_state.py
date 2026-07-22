from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from scripts.ops import ctoai_roadmap_state as roadmap


def _copy_inputs(destination: Path) -> None:
    relatives = {
        roadmap.REGISTRY_PATH.as_posix(),
        roadmap.REGISTRY_SCHEMA_PATH.as_posix(),
        roadmap.STATE_SCHEMA_PATH.as_posix(),
        *roadmap.SOURCE_HEALTH_PATHS.values(),
        *roadmap.FIXED_ENTRY_PATHS.values(),
        *roadmap.FIXED_BINDING_PATHS,
    }
    missing = [
        relative for relative in relatives if not (roadmap.ROOT / relative).is_file()
    ]
    if missing:
        pytest.skip(
            "local terminal roadmap evidence is unavailable: "
            + ", ".join(sorted(missing))
        )
    for relative in relatives:
        source = roadmap.ROOT / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    operator_brief_path = destination / roadmap.SOURCE_HEALTH_PATHS["operator_brief"]
    operator_brief = json.loads(operator_brief_path.read_text(encoding="utf-8"))
    operator_brief["status"] = "ready"
    operator_brief["hard_blockers"] = []
    operator_brief_path.write_text(json.dumps(operator_brief), encoding="utf-8")


def _copy_contract_files(destination: Path) -> None:
    for relative in (
        roadmap.REGISTRY_PATH,
        roadmap.REGISTRY_SCHEMA_PATH,
        roadmap.STATE_SCHEMA_PATH,
    ):
        source = roadmap.ROOT / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def _now() -> datetime:
    return datetime(2026, 7, 15, 12, 20, tzinfo=timezone.utc)


def test_committed_p13_contract_and_state_are_self_validating() -> None:
    registry_schema_raw = (roadmap.ROOT / roadmap.REGISTRY_SCHEMA_PATH).read_bytes()
    registry_raw = (roadmap.ROOT / roadmap.REGISTRY_PATH).read_bytes()
    state_schema_raw = (roadmap.ROOT / roadmap.STATE_SCHEMA_PATH).read_bytes()
    state_raw = (roadmap.ROOT / roadmap.OUTPUT_JSON_PATH).read_bytes()

    registry_schema = json.loads(registry_schema_raw)
    registry = json.loads(registry_raw)
    state_schema = json.loads(state_schema_raw)
    state = json.loads(state_raw)

    Draft202012Validator.check_schema(registry_schema)
    Draft202012Validator.check_schema(state_schema)
    Draft202012Validator(registry_schema).validate(registry)
    Draft202012Validator(state_schema).validate(state)
    assert (
        hashlib.sha256(registry_schema_raw).hexdigest()
        == roadmap.REGISTRY_SCHEMA_SHA256
    )
    assert hashlib.sha256(registry_raw).hexdigest() == roadmap.REGISTRY_V1_SHA256
    assert hashlib.sha256(state_schema_raw).hexdigest() == roadmap.STATE_SCHEMA_SHA256
    assert state["schema_version"] == "ctoa.roadmap-state.v2"
    assert state["phase"] == "P13"
    assert state["phase_status"] == "runtime_evidence_ready"
    assert state["next_phase"] == "P14"
    assert state["blockers"] == []
    assert state["readiness_status"] in {"ready", "awaiting_external"}
    assert state["state_sha256"] == roadmap._canonical_sha256(
        {key: value for key, value in state.items() if key != "state_sha256"}
    )


def test_p13_state_schema_registry_and_ledger_are_complete(tmp_path: Path) -> None:
    _copy_inputs(tmp_path)

    state = roadmap.build_state(tmp_path, now=_now())
    state_schema = json.loads(
        (tmp_path / roadmap.STATE_SCHEMA_PATH).read_text(encoding="utf-8")
    )
    registry_schema = json.loads(
        (tmp_path / roadmap.REGISTRY_SCHEMA_PATH).read_text(encoding="utf-8")
    )
    registry = json.loads(
        (tmp_path / roadmap.REGISTRY_PATH).read_text(encoding="utf-8")
    )

    Draft202012Validator.check_schema(state_schema)
    Draft202012Validator.check_schema(registry_schema)
    Draft202012Validator(registry_schema).validate(registry)
    Draft202012Validator(state_schema).validate(state)
    assert state["status"] == "ready"
    assert state["freshness_status"] == "current"
    assert state["tamper_status"] == "passed"
    assert state["summary"] == {
        "ledger_count": 7,
        "accepted_count": 6,
        "closed_no_action_count": 1,
        "blocked_count": 0,
        "tampered_count": 0,
        "total_attempt_count": 2,
        "runtime_authority_count": 0,
        "live_authority_count": 0,
    }
    assert [item["decision_id"] for item in state["ledger"]] == list(
        roadmap.FIXED_ENTRY_PATHS
    )
    closure = state["ledger"][-1]
    assert closure["decision_status"] == "closed_no_action"
    assert closure["attempt_count"] == 0
    assert closure["final_state"] == "disarmed"
    assert closure["downstream_authority_granted"] is False
    assert state["authority"] == {
        "control_center_mode": "read_only",
        "runtime_executor_added": False,
        "runtime_actions": False,
        "live_authority": False,
        "p12_heal_friend_reopened": False,
        "runtime_mcp_write_tool_enabled": False,
        "roadmap_refresh_tool_enabled": True,
        "roadmap_refresh_risk_class": "safe_write",
        "allowed_output_paths": roadmap.ALLOWED_OUTPUT_PATHS,
    }
    serialized = json.dumps(state).lower()
    assert "target_name" not in serialized
    assert "target_id" not in serialized
    assert "appdata" not in serialized


def test_dry_run_writes_only_sanitized_audit(tmp_path: Path) -> None:
    _copy_inputs(tmp_path)

    result = roadmap.execute(
        tmp_path,
        dry_run=True,
        reason="P13 token=secret-value password=legacy-password",
        now=_now(),
    )

    assert result["status"] == "dry_run"
    assert result["ok"] is True
    assert result["written_paths"] == []
    assert not (tmp_path / roadmap.OUTPUT_JSON_PATH).exists()
    assert not (tmp_path / roadmap.OUTPUT_MD_PATH).exists()
    audit = (tmp_path / roadmap.AUDIT_PATH).read_text(encoding="utf-8")
    assert "roadmap-state-refresh" in audit
    assert "secret-value" not in audit
    assert "legacy-password" not in audit
    assert "[redacted]" in audit


def test_audit_redacts_github_token_variants(tmp_path: Path) -> None:
    tokens = [
        "sk-test_secret_value",
        "ghp-test_secret_value",
        "ghp_test_secret_value",
        "gho_test_secret_value",
        "ghu_test_secret_value",
        "ghs_test_secret_value",
        "ghr_test_secret_value",
        "github_pat_test_secret_value",
        "github_pat-test_secret_value",
    ]

    _, audit_path = roadmap._append_audit(
        tmp_path,
        dry_run=True,
        authorized=True,
        ok=True,
        reason=f"P13 audit redaction {' '.join(tokens)}",
        output_hashes={},
        written_paths=[],
    )

    audit = (tmp_path / audit_path).read_text(encoding="utf-8")
    assert all(token not in audit for token in tokens)
    assert audit.count("[redacted]") >= len(tokens)


def test_future_sandbox_gate_is_advisory_not_a_p13_outage(tmp_path: Path) -> None:
    _copy_inputs(tmp_path)
    gate_path = tmp_path / roadmap.SOURCE_HEALTH_PATHS["runtime_module_gates"]
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    gate["status"] = "blocked"
    gate["failed"] = ["interactive_session_required"]
    gate_path.write_text(json.dumps(gate), encoding="utf-8")

    state = roadmap.build_state(tmp_path, now=_now())

    gate_health = next(
        item for item in state["source_health"] if item["name"] == "runtime_module_gates"
    )
    assert state["status"] == "ready"
    assert state["readiness_status"] == "awaiting_external"
    assert state["blockers"] == []
    assert state["warnings"] == ["runtime_module_gates_pending"]
    assert gate_health["impact"] == "advisory"
    assert gate_health["availability"] == "awaiting_external"
    assert gate_health["contract_status"] == "pending"


def test_malformed_sandbox_gate_observation_is_advisory(tmp_path: Path) -> None:
    gate_path = tmp_path / roadmap.SOURCE_HEALTH_PATHS["runtime_module_gates"]
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    gate_path.write_text(
        json.dumps({"observed": []}),
        encoding="utf-8",
    )

    state = roadmap.build_state(tmp_path, now=_now())

    gate_health = next(
        item for item in state["source_health"] if item["name"] == "runtime_module_gates"
    )
    assert state["status"] == "blocked"
    assert "runtime_module_gates_pending" in state["warnings"]
    assert gate_health["availability"] == "awaiting_external"
    assert gate_health["contract_status"] == "pending"


def test_generated_plugin_cache_gap_is_advisory_during_safe_bootstrap(
    tmp_path: Path,
) -> None:
    _copy_inputs(tmp_path)
    brief_path = tmp_path / roadmap.SOURCE_HEALTH_PATHS["operator_brief"]
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    brief["status"] = "needs_attention"
    brief["hard_blockers"] = [
        "p6_readiness_status",
        "p6:ctoai_plugin_installed_cache",
        "p7_operator_workflow_status",
    ]
    brief_path.write_text(json.dumps(brief), encoding="utf-8")

    state = roadmap.build_state(tmp_path, now=_now())

    assert state["status"] == "ready"
    assert state["readiness_status"] == "awaiting_external"
    assert state["blockers"] == []
    assert "control_center_preflight_pending" in state["warnings"]
    assert state["control_center_preflight"]["ready"] is True
    assert state["control_center_preflight"]["hard_blockers"] == []


def test_unrecognized_operator_blocker_still_fails_closed(tmp_path: Path) -> None:
    _copy_inputs(tmp_path)
    brief_path = tmp_path / roadmap.SOURCE_HEALTH_PATHS["operator_brief"]
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    brief["status"] = "needs_attention"
    brief["hard_blockers"] = ["untrusted_runtime_authority"]
    brief_path.write_text(json.dumps(brief), encoding="utf-8")

    state = roadmap.build_state(tmp_path, now=_now())

    assert state["status"] == "blocked"
    assert "control_center_preflight:untrusted_runtime_authority" in state["blockers"]


def test_confirmed_refresh_writes_atomic_json_markdown_and_hash_audit(
    tmp_path: Path,
) -> None:
    _copy_inputs(tmp_path)

    result = roadmap.execute(
        tmp_path,
        dry_run=False,
        confirmation=roadmap.CONFIRMATION,
        reason="P13 confirmed generation",
        now=_now(),
    )

    json_path = tmp_path / roadmap.OUTPUT_JSON_PATH
    markdown_path = tmp_path / roadmap.OUTPUT_MD_PATH
    assert result["status"] == "completed"
    assert result["written_paths"] == [
        roadmap.OUTPUT_JSON_PATH.as_posix(),
        roadmap.OUTPUT_MD_PATH.as_posix(),
    ]
    state = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")
    assert state["state_sha256"] in markdown
    assert "P12 Heal Friend remains closed" in markdown
    assert "No runtime executor" in markdown
    assert (
        result["output_hashes"][roadmap.OUTPUT_JSON_PATH.as_posix()]
        == hashlib.sha256(json_path.read_bytes()).hexdigest()
    )
    assert (
        result["output_hashes"][roadmap.OUTPUT_MD_PATH.as_posix()]
        == hashlib.sha256(markdown_path.read_bytes()).hexdigest()
    )
    audit_record = json.loads(
        (tmp_path / roadmap.AUDIT_PATH).read_text(encoding="utf-8").splitlines()[-1]
    )
    assert audit_record["authorized"] is True
    assert audit_record["ok"] is True
    assert audit_record["output_hashes"] == result["output_hashes"]


def test_confirmed_refresh_rejects_wrong_confirmation(tmp_path: Path) -> None:
    _copy_inputs(tmp_path)

    result = roadmap.execute(
        tmp_path,
        dry_run=False,
        confirmation="approve something else",
        now=_now(),
    )

    assert result["status"] == "blocked"
    assert result["authorized"] is False
    assert result["ok"] is False
    assert not (tmp_path / roadmap.OUTPUT_JSON_PATH).exists()
    record = json.loads(
        (tmp_path / roadmap.AUDIT_PATH).read_text(encoding="utf-8").splitlines()[-1]
    )
    assert record["authorized"] is False
    assert record["output_hashes"] == {}


def test_binding_tamper_blocks_heal_friend_closure(tmp_path: Path) -> None:
    _copy_inputs(tmp_path)
    preflight_path = (
        tmp_path
        / "runtime/solteria_helper_dev/p12_heal_friend_execution_preflight.json"
    )
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    preflight["attempt_count"] = 1
    preflight_path.write_text(json.dumps(preflight), encoding="utf-8")

    state = roadmap.build_state(tmp_path, now=_now())

    closure = state["ledger"][-1]
    assert state["status"] == "blocked"
    assert closure["integrity_status"] == "blocked"
    assert "binding_preflight_loaded" in closure["blockers"]
    assert state["authority"]["p12_heal_friend_reopened"] is False


def test_previous_terminal_evidence_drift_is_reported_as_tamper(
    tmp_path: Path,
) -> None:
    _copy_inputs(tmp_path)
    first = roadmap.execute(
        tmp_path,
        dry_run=False,
        confirmation=roadmap.CONFIRMATION,
        now=_now(),
    )
    assert first["ok"] is True
    p8_path = tmp_path / roadmap.FIXED_ENTRY_PATHS["p8-background-acceptance"]
    p8 = json.loads(p8_path.read_text(encoding="utf-8"))
    p8["next_action"] = "A changed but otherwise safe terminal note."
    p8_path.write_text(json.dumps(p8), encoding="utf-8")

    state = roadmap.build_state(tmp_path, now=_now())

    p8_entry = state["ledger"][0]
    assert state["status"] == "blocked"
    assert state["tamper_status"] == "tampered"
    assert p8_entry["integrity_status"] == "tampered"
    assert "terminal_evidence_changed_since_previous_state" in p8_entry["blockers"]



def test_registry_cannot_redirect_a_fixed_input_path(tmp_path: Path) -> None:
    _copy_inputs(tmp_path)
    registry_path = tmp_path / roadmap.REGISTRY_PATH
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["entries"][0]["path"] = (
        "runtime/solteria_helper_dev/conditions_shadow_acceptance.json"
    )
    registry_path.write_text(json.dumps(registry), encoding="utf-8")

    state = roadmap.build_state(tmp_path, now=_now())

    assert state["status"] == "blocked"
    assert "registry_entry_allowlist_mismatch" in state["blockers"]


@pytest.mark.parametrize("missing_field", ["path", "bindings"])
def test_invalid_registry_entry_fails_closed_and_writes_audit(
    tmp_path: Path,
    missing_field: str,
) -> None:
    _copy_contract_files(tmp_path)
    registry_path = tmp_path / roadmap.REGISTRY_PATH
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    del registry["entries"][0][missing_field]
    registry_path.write_text(json.dumps(registry), encoding="utf-8")

    state = roadmap.build_state(tmp_path, now=_now())
    result = roadmap.execute(
        tmp_path,
        dry_run=False,
        confirmation=roadmap.CONFIRMATION,
        now=_now(),
    )

    assert state["status"] == "blocked"
    assert any(
        blocker.startswith("registry_validation:entries.0")
        for blocker in state["blockers"]
    )
    assert "ledger_count_mismatch" in state["blockers"]
    assert result["status"] == "blocked"
    assert result["ok"] is False
    assert result["written_paths"] == []
    audit = json.loads(
        (tmp_path / roadmap.AUDIT_PATH).read_text(encoding="utf-8").splitlines()[-1]
    )
    assert audit["authorized"] is True
    assert audit["ok"] is False


def test_registry_semantics_are_pinned_before_the_first_state(tmp_path: Path) -> None:
    _copy_inputs(tmp_path)
    registry_path = tmp_path / roadmap.REGISTRY_PATH
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["entries"][6]["required_false_flags"].remove("runtime_actions")
    registry_path.write_text(json.dumps(registry), encoding="utf-8")

    state = roadmap.build_state(tmp_path, now=_now())

    assert state["status"] == "blocked"
    assert state["tamper_status"] == "tampered"
    assert state["schema_registry"]["status"] == "tampered"
    assert "schema_registry_v1_pin_mismatch" in state["blockers"]


@pytest.mark.parametrize(
    ("relative", "expected_blocker"),
    [
        (roadmap.REGISTRY_SCHEMA_PATH, "schema_registry_contract_pin_mismatch"),
        (roadmap.STATE_SCHEMA_PATH, "roadmap_state_schema_pin_mismatch"),
    ],
)
def test_schema_contracts_are_hash_pinned(
    tmp_path: Path,
    relative: Path,
    expected_blocker: str,
) -> None:
    _copy_inputs(tmp_path)
    schema_path = tmp_path / relative
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    schema["description"] = "unauthorized same-version mutation"
    schema_path.write_text(json.dumps(schema), encoding="utf-8")

    state = roadmap.build_state(tmp_path, now=_now())

    assert state["status"] == "blocked"
    assert expected_blocker in state["blockers"]


def test_symlinked_output_is_rejected(tmp_path: Path) -> None:
    _copy_inputs(tmp_path)
    output = tmp_path / roadmap.OUTPUT_JSON_PATH
    output.parent.mkdir(parents=True, exist_ok=True)
    target = tmp_path / "outside.json"
    target.write_text("{}", encoding="utf-8")
    try:
        output.symlink_to(target)
    except OSError:
        pytest.skip("Symlink creation is unavailable in this Windows environment")

    result = roadmap.execute(
        tmp_path,
        dry_run=False,
        confirmation=roadmap.CONFIRMATION,
        now=_now(),
    )

    assert result["status"] == "blocked"
    assert result["ok"] is False
    assert target.read_text(encoding="utf-8") == "{}"


def test_dangling_symlink_input_is_rejected(tmp_path: Path) -> None:
    dangling = tmp_path / "dangling-input"
    try:
        dangling.symlink_to(tmp_path / "outside-target.json")
    except OSError:
        pytest.skip("Symlink creation is unavailable in this Windows environment")

    path, error = roadmap._fixed_path(tmp_path, dangling.name)

    assert path is None
    assert error == "symlink_rejected"


def test_cli_has_no_caller_selected_output_path() -> None:
    with pytest.raises(SystemExit) as exc:
        roadmap.main(["--output", "outside.json"])

    assert exc.value.code == 2
