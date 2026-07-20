from __future__ import annotations

import json
import os
from pathlib import Path
import uuid

from jsonschema import Draft202012Validator
import pytest

from scripts.ops import otclient_conditions_shadow_replay as documents
from scripts.ops import otclient_equipment_candidate_catalog as candidate_catalog
from scripts.ops import otclient_equipment_capture_profile_change_plan as change_plan
from scripts.ops import otclient_equipment_consumer_parity as parity
from scripts.ops import otclient_equipment_dependency_preflight as dependency
from scripts.ops import otclient_equipment_observation_preview as observation_preview
from scripts.ops import otclient_equipment_operator_readiness as operator_readiness
from scripts.ops import otclient_equipment_operator_refresh_run as refresh_run


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = str(uuid.UUID("12345678-1234-4234-9234-123456789abc"))
START_MS = 1_783_800_000_000
SOURCE_MS = START_MS + 50


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
        generated_at_unix_ms=SOURCE_MS,
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
        evaluated_at_unix_ms=SOURCE_MS,
    )
    catalog = candidate_catalog.build_catalog(
        preview_document=preview_document,
        generated_at_unix_ms=SOURCE_MS,
    )
    plan = change_plan.evaluate_change_plan(
        change_plan.CanonicalInputs(
            capture_doctor=doctor_document,
            observation_preview=preview_document,
        ),
        generated_at_unix_ms=SOURCE_MS,
    )
    readiness = operator_readiness.evaluate_readiness(
        {
            "capture_doctor": doctor_document,
            "observation_preview": preview_document,
            "dependency_preflight": documents.document_from_payload(preflight),
            "candidate_catalog": documents.document_from_payload(catalog),
            "change_plan": documents.document_from_payload(plan),
        },
        generated_at_unix_ms=SOURCE_MS,
    )
    return {
        "capture_profile_doctor": doctor,
        "observation_preview": preview,
        "dependency_preflight": preflight,
        "candidate_catalog": catalog,
        "capture_profile_change_plan": plan,
        "operator_readiness": readiness,
    }


def _consumer_sources(root: Path) -> tuple[Path, Path]:
    python_source = root / "release_evidence_pack.py"
    web_source = root / "controlCenterEvidence.ts"
    python_source.write_text(
        "\n".join(
            (
                parity.PARITY_SCHEMA_VERSION,
                *parity.PYTHON_ARTIFACT_KEYS,
                *parity.PYTHON_PROJECTION_FIELDS,
            )
        ),
        encoding="utf-8",
    )
    web_source.write_text(
        "\n".join(
            (
                parity.PARITY_SCHEMA_VERSION,
                *parity.WEB_ARTIFACT_KEYS,
                *parity.WEB_PROJECTION_FIELDS,
            )
        ),
        encoding="utf-8",
    )
    return python_source, web_source


def _write_payload(path: Path, payload: dict, *, modified_at_ms: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(documents.canonical_bytes(payload) + b"\n")
    timestamp_ns = modified_at_ms * 1_000_000
    os.utime(path, ns=(timestamp_ns, timestamp_ns))


def _write_parity(dev_dir: Path, root: Path, *, modified_at_ms: int) -> dict:
    python_source, web_source = _consumer_sources(root)
    payload = parity.build_report(
        dev_dir,
        python_consumer=python_source,
        web_consumer=web_source,
    )
    assert payload["status"] == "passed"
    _write_payload(
        dev_dir / "equipment_consumer_parity.json",
        payload,
        modified_at_ms=modified_at_ms,
    )
    return payload


def _begin(tmp_path: Path) -> tuple[Path, dict[str, dict]]:
    dev_dir = tmp_path / "runtime" / "solteria_helper_dev"
    pending = refresh_run.begin_run(
        dev_dir=dev_dir,
        now_ms=START_MS,
        run_id=RUN_ID,
    )
    assert pending["stage_receipts"] == []
    return dev_dir, _artifact_payloads()


def _record_six(dev_dir: Path, payloads: dict[str, dict]) -> None:
    for index, stage in enumerate(refresh_run.STAGES[:-1], start=1):
        modified_at = START_MS + index * 100
        _write_payload(
            dev_dir / stage.filename,
            payloads[stage.stage_id],
            modified_at_ms=modified_at,
        )
        receipt = refresh_run.record_stage(
            stage.stage_id,
            RUN_ID,
            dev_dir=dev_dir,
            now_ms=modified_at + 10,
        )
        assert receipt["stage_index"] == index


def _record_parity(dev_dir: Path, root: Path, *, payload: dict | None = None) -> dict:
    modified_at = START_MS + 700
    parity_payload = payload or _write_parity(
        dev_dir,
        root,
        modified_at_ms=modified_at,
    )
    if payload is not None:
        _write_payload(
            dev_dir / "equipment_consumer_parity.json",
            payload,
            modified_at_ms=modified_at,
        )
    refresh_run.record_stage(
        "consumer_parity",
        RUN_ID,
        dev_dir=dev_dir,
        now_ms=modified_at + 10,
    )
    return parity_payload


def _complete(tmp_path: Path) -> tuple[Path, dict]:
    dev_dir, payloads = _begin(tmp_path)
    _record_six(dev_dir, payloads)
    _record_parity(dev_dir, tmp_path)
    report = refresh_run.finalize_run(
        RUN_ID,
        dev_dir=dev_dir,
        now_ms=START_MS + 800,
    )
    return dev_dir, report


def test_complete_envelope_binds_all_seven_stages_and_validates_schema(
    tmp_path: Path,
) -> None:
    dev_dir, report = _complete(tmp_path)
    schema = json.loads(
        (ROOT / "schemas" / "equipment-operator-refresh-run.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(report)

    aggregate_binding = {
        "run_id": RUN_ID,
        "started_at_unix_ms": START_MS,
        "completed_at_unix_ms": START_MS + 800,
        "stage_receipts": report["stage_receipts"],
    }
    assert report["canonical_aggregate_sha256"] == documents.canonical_sha256(
        aggregate_binding
    )
    assert report["stage_order"] == list(refresh_run.STAGE_ORDER)
    assert report["stage_count"] == 7
    assert report["mixed_run_detected"] is False
    assert report["runtime_actions"] is False
    assert report["eligibility_changed"] is False
    assert report["acceptance_granted"] is False
    assert not (dev_dir / refresh_run.PENDING.name).exists()
    persisted = json.loads(
        (dev_dir / refresh_run.OUTPUT.name).read_text(encoding="utf-8")
    )
    assert persisted == report


def test_stage_order_and_run_id_are_exact(tmp_path: Path) -> None:
    dev_dir, payloads = _begin(tmp_path)
    preview = refresh_run.STAGE_BY_ID["observation_preview"]
    _write_payload(
        dev_dir / preview.filename,
        payloads[preview.stage_id],
        modified_at_ms=START_MS + 100,
    )

    with pytest.raises(
        refresh_run.RefreshRunError, match="expected capture_profile_doctor"
    ) as order:
        refresh_run.record_stage(
            "observation_preview",
            RUN_ID,
            dev_dir=dev_dir,
            now_ms=START_MS + 110,
        )
    assert order.value.code == "stage_order_mismatch"

    with pytest.raises(refresh_run.RefreshRunError) as replay:
        refresh_run.record_stage(
            "capture_profile_doctor",
            str(uuid.uuid4()),
            dev_dir=dev_dir,
            now_ms=START_MS + 110,
        )
    assert replay.value.code == "run_id_mismatch"


def test_artifact_from_before_begin_is_rejected_as_mixed_run(tmp_path: Path) -> None:
    dev_dir, payloads = _begin(tmp_path)
    stage = refresh_run.STAGES[0]
    _write_payload(
        dev_dir / stage.filename,
        payloads[stage.stage_id],
        modified_at_ms=START_MS - 1,
    )

    with pytest.raises(refresh_run.RefreshRunError) as raised:
        refresh_run.record_stage(
            stage.stage_id,
            RUN_ID,
            dev_dir=dev_dir,
            now_ms=START_MS + 10,
        )
    assert raised.value.code == "mixed_run_detected"


def test_source_timestamp_from_before_begin_is_rejected(tmp_path: Path) -> None:
    dev_dir, payloads = _begin(tmp_path)
    doctor_stage = refresh_run.STAGES[0]
    _write_payload(
        dev_dir / doctor_stage.filename,
        payloads[doctor_stage.stage_id],
        modified_at_ms=START_MS + 100,
    )
    refresh_run.record_stage(
        doctor_stage.stage_id,
        RUN_ID,
        dev_dir=dev_dir,
        now_ms=START_MS + 110,
    )
    preview_stage = refresh_run.STAGES[1]
    payloads[preview_stage.stage_id]["generated_at_unix_ms"] = START_MS - 1
    _write_payload(
        dev_dir / preview_stage.filename,
        payloads[preview_stage.stage_id],
        modified_at_ms=START_MS + 200,
    )

    with pytest.raises(refresh_run.RefreshRunError) as raised:
        refresh_run.record_stage(
            preview_stage.stage_id,
            RUN_ID,
            dev_dir=dev_dir,
            now_ms=START_MS + 210,
        )
    assert raised.value.code == "mixed_run_detected"


def test_prior_artifact_hash_mutation_breaks_the_next_receipt(tmp_path: Path) -> None:
    dev_dir, payloads = _begin(tmp_path)
    doctor_stage = refresh_run.STAGES[0]
    doctor_path = dev_dir / doctor_stage.filename
    _write_payload(
        doctor_path, payloads[doctor_stage.stage_id], modified_at_ms=START_MS + 100
    )
    refresh_run.record_stage(
        doctor_stage.stage_id,
        RUN_ID,
        dev_dir=dev_dir,
        now_ms=START_MS + 110,
    )
    changed = dict(payloads[doctor_stage.stage_id])
    changed["next_action"] = "Changed after the signed stage receipt."
    _write_payload(doctor_path, changed, modified_at_ms=START_MS + 100)

    with pytest.raises(refresh_run.RefreshRunError) as raised:
        refresh_run.record_stage(
            "observation_preview",
            RUN_ID,
            dev_dir=dev_dir,
            now_ms=START_MS + 210,
        )
    assert raised.value.code == "hash_mismatch"


def test_parity_must_bind_exact_six_artifact_hashes(tmp_path: Path) -> None:
    dev_dir, payloads = _begin(tmp_path)
    _record_six(dev_dir, payloads)
    parity_payload = _write_parity(
        dev_dir,
        tmp_path,
        modified_at_ms=START_MS + 700,
    )
    parity_payload["artifacts"]["capture_profile_doctor"]["sha256"] = "f" * 64
    _record_parity(dev_dir, tmp_path, payload=parity_payload)

    with pytest.raises(refresh_run.RefreshRunError) as raised:
        refresh_run.finalize_run(
            RUN_ID,
            dev_dir=dev_dir,
            now_ms=START_MS + 800,
        )
    assert raised.value.code == "parity_hash_mismatch"


def test_excess_artifact_skew_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dev_dir, payloads = _begin(tmp_path)
    _record_six(dev_dir, payloads)
    _record_parity(dev_dir, tmp_path)
    monkeypatch.setattr(refresh_run, "MAX_ARTIFACT_SKEW_MS", 100)

    with pytest.raises(refresh_run.RefreshRunError) as raised:
        refresh_run.finalize_run(
            RUN_ID,
            dev_dir=dev_dir,
            now_ms=START_MS + 800,
        )
    assert raised.value.code == "artifact_skew_exceeded"


def test_stale_run_and_incomplete_stage_chain_do_not_emit_final_output(
    tmp_path: Path,
) -> None:
    dev_dir, _ = _begin(tmp_path)
    with pytest.raises(refresh_run.RefreshRunError) as incomplete:
        refresh_run.finalize_run(
            RUN_ID,
            dev_dir=dev_dir,
            now_ms=START_MS + 10,
        )
    assert incomplete.value.code == "stage_count_mismatch"

    with pytest.raises(refresh_run.RefreshRunError) as stale:
        refresh_run.finalize_run(
            RUN_ID,
            dev_dir=dev_dir,
            now_ms=START_MS + refresh_run.MAX_RUN_DURATION_MS + 1,
        )
    assert stale.value.code == "run_stale"
    assert not (dev_dir / refresh_run.OUTPUT.name).exists()


def test_duplicate_json_and_unsafe_no_action_are_rejected(tmp_path: Path) -> None:
    dev_dir, payloads = _begin(tmp_path)
    stage = refresh_run.STAGES[0]
    path = dev_dir / stage.filename
    path.write_text('{"status":"blocked","status":"ready"}', encoding="utf-8")
    timestamp_ns = (START_MS + 100) * 1_000_000
    os.utime(path, ns=(timestamp_ns, timestamp_ns))
    with pytest.raises(refresh_run.RefreshRunError) as duplicate:
        refresh_run.record_stage(
            stage.stage_id,
            RUN_ID,
            dev_dir=dev_dir,
            now_ms=START_MS + 110,
        )
    assert duplicate.value.code == "artifact_duplicate_keys"

    unsafe = payloads[stage.stage_id]
    unsafe["runtime_actions"] = True
    _write_payload(path, unsafe, modified_at_ms=START_MS + 100)
    with pytest.raises(refresh_run.RefreshRunError) as no_action:
        refresh_run.record_stage(
            stage.stage_id,
            RUN_ID,
            dev_dir=dev_dir,
            now_ms=START_MS + 110,
        )
    assert no_action.value.code == "artifact_schema_invalid"


def test_begin_preserves_old_envelope_and_refuses_parallel_run(
    tmp_path: Path,
) -> None:
    dev_dir = tmp_path / "runtime" / "solteria_helper_dev"
    dev_dir.mkdir(parents=True)
    old_output = dev_dir / refresh_run.OUTPUT.name
    old_output.write_text('{"previous":"good"}\n', encoding="utf-8")

    refresh_run.begin_run(dev_dir=dev_dir, now_ms=START_MS, run_id=RUN_ID)
    assert json.loads(old_output.read_text(encoding="utf-8")) == {"previous": "good"}
    with pytest.raises(refresh_run.RefreshRunError) as raised:
        refresh_run.begin_run(
            dev_dir=dev_dir,
            now_ms=START_MS + 1,
            run_id=str(uuid.uuid4()),
        )
    assert raised.value.code == "run_already_pending"


def test_abort_requires_exact_run_id_and_preserves_good_output(
    tmp_path: Path,
) -> None:
    dev_dir = tmp_path / "runtime" / "solteria_helper_dev"
    dev_dir.mkdir(parents=True)
    old_output = dev_dir / refresh_run.OUTPUT.name
    old_output.write_text('{"previous":"good"}\n', encoding="utf-8")
    refresh_run.begin_run(dev_dir=dev_dir, now_ms=START_MS, run_id=RUN_ID)

    with pytest.raises(refresh_run.RefreshRunError) as mismatch:
        refresh_run.abort_run(str(uuid.uuid4()), dev_dir=dev_dir)
    assert mismatch.value.code == "run_id_mismatch"
    assert (dev_dir / refresh_run.PENDING.name).is_file()
    assert json.loads(old_output.read_text(encoding="utf-8")) == {"previous": "good"}

    result = refresh_run.abort_run(RUN_ID, dev_dir=dev_dir)
    assert result["status"] == "aborted"
    assert result["pending_removed"] is True
    assert result["final_output_preserved"] is True
    assert result["runtime_actions"] is False
    assert result["eligibility_changed"] is False
    assert not (dev_dir / refresh_run.PENDING.name).exists()
    assert json.loads(old_output.read_text(encoding="utf-8")) == {"previous": "good"}

    replacement = str(uuid.uuid4())
    pending = refresh_run.begin_run(
        dev_dir=dev_dir,
        now_ms=START_MS + 1,
        run_id=replacement,
    )
    assert pending["run_id"] == replacement


def test_begin_rejects_symlinked_runtime_ancestor_without_writing_pending(
    tmp_path: Path,
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    runtime_link = tmp_path / "runtime-link"
    try:
        runtime_link.symlink_to(outside, target_is_directory=True)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"directory symlinks unavailable: {exc}")
    dev_dir = runtime_link / "solteria_helper_dev"

    with pytest.raises(refresh_run.RefreshRunError) as raised:
        refresh_run.begin_run(dev_dir=dev_dir, now_ms=START_MS, run_id=RUN_ID)
    assert raised.value.code == "runtime_root_unsafe"
    assert not (outside / "solteria_helper_dev").exists()


def test_abort_cli_cleans_only_matching_pending_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    dev_dir = tmp_path / "runtime" / "solteria_helper_dev"
    refresh_run.begin_run(dev_dir=dev_dir, now_ms=START_MS, run_id=RUN_ID)
    monkeypatch.setattr(refresh_run, "DEV_DIR", dev_dir)

    assert refresh_run.main(["--abort", "--run-id", RUN_ID]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "aborted"
    assert payload["run_id"] == RUN_ID
    assert payload["final_output_preserved"] is False
    assert not (dev_dir / refresh_run.PENDING.name).exists()
