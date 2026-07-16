from __future__ import annotations

import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.ops import otclient_conditions_shadow_replay as documents
from scripts.ops import otclient_equipment_candidate_catalog as candidate_catalog
from scripts.ops import otclient_equipment_capture_profile_change_plan as change_plan
from scripts.ops import otclient_equipment_consumer_parity as parity
from scripts.ops import otclient_equipment_dependency_preflight as dependency
from scripts.ops import otclient_equipment_observation_preview as observation_preview
from scripts.ops import otclient_equipment_operator_readiness as operator_readiness


ROOT = Path(__file__).resolve().parents[1]
NOW_MS = 1_783_800_000_000


def _doctor() -> dict:
    return {
        "schema_version": "ctoa.equipment-capture-profile-doctor.v1",
        "status": "blocked",
        "source": "tracked_safe_template",
        "path": "config/otclient/equipment-shadow-capture-profile.json",
        "sha256": "a" * 64,
        "configured_by_operator": False,
        "slot": "ring",
        "identifiers_present": False,
        "candidate_slot_index_valid": False,
        "no_action_contract": True,
        "blockers": [
            "local_operator_override_missing",
            "operator_confirmation_missing",
            "exact_ids_missing",
        ],
        "next_action": "Create and review the fixed local override.",
        "runtime_actions": False,
        "live_file_writes": False,
        "runtime_readiness_claimed": False,
    }


def _artifact_payloads() -> dict[str, dict]:
    doctor = _doctor()
    preview = observation_preview.build_preview(
        background=documents.document_from_payload(None, "missing"),
        generated_at_unix_ms=NOW_MS,
    )
    doctor_document = documents.document_from_payload(doctor)
    preview_document = documents.document_from_payload(preview)
    preflight = dependency.evaluate_preflight(
        dependency.EvidenceBundle(
            p8_report=documents.document_from_payload(None, "missing"),
            p9_report=documents.document_from_payload(None, "missing"),
            p9_receipt=documents.document_from_payload(None, "missing"),
            capture_doctor=doctor_document,
            observation_preview=preview_document,
        ),
        evaluated_at_unix_ms=NOW_MS,
    )
    catalog = candidate_catalog.build_catalog(
        preview_document=preview_document,
        generated_at_unix_ms=NOW_MS,
    )
    plan = change_plan.evaluate_change_plan(
        change_plan.CanonicalInputs(
            capture_doctor=doctor_document,
            observation_preview=preview_document,
        ),
        generated_at_unix_ms=NOW_MS,
    )
    readiness_inputs = {
        "capture_doctor": doctor_document,
        "observation_preview": preview_document,
        "dependency_preflight": documents.document_from_payload(preflight),
        "candidate_catalog": documents.document_from_payload(catalog),
        "change_plan": documents.document_from_payload(plan),
    }
    readiness = operator_readiness.evaluate_readiness(
        readiness_inputs,
        generated_at_unix_ms=NOW_MS,
    )
    return {
        "capture_profile_doctor": doctor,
        "observation_preview": preview,
        "dependency_preflight": preflight,
        "candidate_catalog": catalog,
        "capture_profile_change_plan": plan,
        "operator_readiness": readiness,
    }


def _write_payloads(dev_dir: Path, payloads: dict[str, dict]) -> None:
    dev_dir.mkdir(parents=True, exist_ok=True)
    for spec in parity.ARTIFACT_SPECS:
        (dev_dir / spec.filename).write_bytes(
            documents.canonical_bytes(payloads[spec.artifact_id]) + b"\n"
        )


def _consumer_sources(root: Path) -> tuple[Path, Path]:
    python_source = root / "release_evidence_pack.py"
    web_source = root / "controlCenterEvidence.ts"
    python_source.write_text(
        "\n".join(
            (
                f'P10_EQUIPMENT_CONSUMER_PARITY_SCHEMA = "{parity.PARITY_SCHEMA_VERSION}"',
                *parity.PYTHON_ARTIFACT_KEYS,
                *parity.PYTHON_PROJECTION_FIELDS,
            )
        ),
        encoding="utf-8",
    )
    web_source.write_text(
        "\n".join(
            (
                f'P10_EQUIPMENT_CONSUMER_PARITY_SCHEMA = "{parity.PARITY_SCHEMA_VERSION}"',
                *parity.WEB_ARTIFACT_KEYS,
                *parity.WEB_PROJECTION_FIELDS,
            )
        ),
        encoding="utf-8",
    )
    return python_source, web_source


def _build(tmp_path: Path, payloads: dict[str, dict] | None = None) -> dict:
    dev_dir = tmp_path / "runtime" / "solteria_helper_dev"
    _write_payloads(dev_dir, payloads or _artifact_payloads())
    python_source, web_source = _consumer_sources(tmp_path)
    return parity.build_report(
        dev_dir,
        python_consumer=python_source,
        web_consumer=web_source,
    )


def _validate(report: dict) -> None:
    schema = json.loads(
        (ROOT / "schemas/equipment-consumer-parity-report.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(report)


def test_six_artifact_chain_and_both_consumer_contracts_have_full_parity(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)

    _validate(report)
    assert report["status"] == "passed"
    assert report["artifact_count"] == 6
    assert report["blockers"] == []
    assert all(report["checks"].values())
    assert set(report["artifacts"]) == {
        "capture_profile_doctor",
        "observation_preview",
        "dependency_preflight",
        "candidate_catalog",
        "capture_profile_change_plan",
        "operator_readiness",
    }
    assert all(not row["divergences"] for row in report["artifacts"].values())
    assert report["consumer_contracts"]["python"]["contract_valid"] is True
    assert report["consumer_contracts"]["web"]["contract_valid"] is True
    assert report["runtime_actions"] is False
    assert report["eligibility_changed"] is False


def test_hash_divergence_is_detected_across_catalog_and_readiness(
    tmp_path: Path,
) -> None:
    payloads = _artifact_payloads()
    payloads["candidate_catalog"]["preview_sha256"] = "f" * 64

    report = _build(tmp_path, payloads)

    assert report["status"] == "blocked"
    assert report["checks"]["hash_parity"] is False
    assert (
        "hash:catalog.observation_preview"
        in report["artifacts"]["candidate_catalog"]["divergences"]
    )
    assert (
        "hash:readiness.candidate_catalog"
        in report["artifacts"]["operator_readiness"]["divergences"]
    )


def test_status_and_blocker_divergence_fail_closed(tmp_path: Path) -> None:
    payloads = _artifact_payloads()
    payloads["candidate_catalog"]["status"] = "catalog_ready"
    # Keep the upstream blocker list to prove status/blocker parity is independent
    # from schema validation and consumer hash binding.

    report = _build(tmp_path, payloads)

    assert report["status"] == "blocked"
    assert report["checks"]["status_parity"] is False
    assert "status_blockers" in report["artifacts"]["candidate_catalog"]["divergences"]


def test_copied_upstream_blockers_must_equal_the_source_artifact(
    tmp_path: Path,
) -> None:
    payloads = _artifact_payloads()
    payloads["candidate_catalog"]["preview_blockers"] = []

    report = _build(tmp_path, payloads)

    assert report["status"] == "blocked"
    assert report["checks"]["blockers_parity"] is False
    assert (
        "blockers:observation_preview"
        in report["artifacts"]["candidate_catalog"]["divergences"]
    )


def test_no_action_and_eligibility_mutations_are_separate_failures(
    tmp_path: Path,
) -> None:
    no_action = _artifact_payloads()
    no_action["observation_preview"]["runtime_actions"] = True
    no_action_report = _build(tmp_path / "no-action", no_action)
    assert no_action_report["checks"]["no_action_parity"] is False
    assert (
        "no_action.runtime_actions"
        in no_action_report["artifacts"]["observation_preview"]["divergences"]
    )

    eligibility = _artifact_payloads()
    eligibility["operator_readiness"]["eligibility_state"] = "changed"
    eligibility_report = _build(tmp_path / "eligibility", eligibility)
    assert eligibility_report["checks"]["eligibility_parity"] is False
    assert (
        "eligibility.eligibility_state"
        in eligibility_report["artifacts"]["operator_readiness"]["divergences"]
    )


def test_python_or_web_contract_omission_blocks_parity(tmp_path: Path) -> None:
    dev_dir = tmp_path / "runtime" / "solteria_helper_dev"
    _write_payloads(dev_dir, _artifact_payloads())
    python_source, web_source = _consumer_sources(tmp_path)
    python_source.write_text(
        python_source.read_text(encoding="utf-8").replace(
            "equipment_operator_readiness", "operator_readiness_missing"
        ),
        encoding="utf-8",
    )
    web_source.write_text(
        web_source.read_text(encoding="utf-8").replace("eligibilityState", "state"),
        encoding="utf-8",
    )

    report = parity.build_report(
        dev_dir,
        python_consumer=python_source,
        web_consumer=web_source,
    )

    assert report["status"] == "blocked"
    assert "python_consumer_contract_divergence" in report["blockers"]
    assert "web_consumer_contract_divergence" in report["blockers"]
    assert report["consumer_contracts"]["python"]["missing_artifact_tokens"] == [
        "equipment_operator_readiness"
    ]
    assert report["consumer_contracts"]["web"]["missing_projection_fields"] == [
        "eligibilityState"
    ]


def test_duplicate_keys_and_missing_artifacts_are_not_consumed(tmp_path: Path) -> None:
    dev_dir = tmp_path / "runtime" / "solteria_helper_dev"
    _write_payloads(dev_dir, _artifact_payloads())
    python_source, web_source = _consumer_sources(tmp_path)
    doctor_path = dev_dir / "equipment_capture_profile_doctor.json"
    doctor_path.write_text('{"status":"blocked","status":"ready"}', encoding="utf-8")
    (dev_dir / "equipment_candidate_catalog.json").unlink()

    report = parity.build_report(
        dev_dir,
        python_consumer=python_source,
        web_consumer=web_source,
    )

    assert report["status"] == "blocked"
    assert (
        report["artifacts"]["capture_profile_doctor"]["load_status"] == "duplicate_keys"
    )
    assert report["artifacts"]["candidate_catalog"]["load_status"] == "missing"


def test_no_write_cli_never_creates_a_report(tmp_path: Path) -> None:
    dev_dir = tmp_path / "runtime" / "solteria_helper_dev"
    _write_payloads(dev_dir, _artifact_payloads())
    python_source, web_source = _consumer_sources(tmp_path)
    output = dev_dir / parity.DEFAULT_OUTPUT.name

    exit_code = parity.main(
        [
            "--dev-dir",
            str(dev_dir),
            "--python-consumer",
            str(python_source),
            "--web-consumer",
            str(web_source),
            "--no-write",
        ]
    )

    assert exit_code == 0
    assert not output.exists()


def test_report_is_deterministic_for_the_same_inputs(tmp_path: Path) -> None:
    payloads = _artifact_payloads()
    first = _build(tmp_path / "first", payloads)
    second = _build(tmp_path / "second", copy.deepcopy(payloads))

    def portable(report: dict) -> dict:
        value = copy.deepcopy(report)
        for row in value["artifacts"].values():
            row["path"] = Path(row["path"]).name
            row["schema_path"] = Path(row["schema_path"]).name
        for consumer in value["consumer_contracts"].values():
            consumer["path"] = Path(consumer["path"]).name
        return value

    assert portable(first) == portable(second)


def test_validate_dev_runs_parity_before_independent_acceptance() -> None:
    wrapper = (ROOT / "scripts" / "windows" / "solteria_helper_test_env.ps1").read_text(
        encoding="utf-8"
    )

    parity_start = wrapper.index("Validate: P10 Python/web consumer parity")
    acceptance_start = wrapper.index(
        "Validate: P10 acceptance remains independent and fail-closed"
    )
    parity_block = wrapper[parity_start:acceptance_start]

    assert parity_start < acceptance_start
    assert "otclient_equipment_consumer_parity.py" in parity_block
    assert "equipment_consumer_parity.json" in parity_block
    assert "--allow-blocked" not in parity_block
    assert '$equipmentParityReport.status -ne "passed"' in parity_block
    assert "$equipmentParityReport.eligibility_changed -ne $false" in parity_block
    assert "$equipmentParityReport.runtime_actions -ne $false" in parity_block
    assert "$equipmentParityReport.live_file_writes -ne $false" in parity_block
