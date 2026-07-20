from __future__ import annotations

import copy
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.ops import otclient_conditions_shadow_acceptance as p9_acceptance
from scripts.ops import otclient_conditions_shadow_replay as documents
from scripts.ops import otclient_equipment_shadow_acceptance as acceptance
from scripts.ops import otclient_equipment_shadow_replay as replay
from scripts.ops import release_evidence_pack as evidence


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "otclient_equipment_shadow_replay"


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _accepted_p9_receipt(trace: dict, report_sha: str, now_ms: int) -> dict:
    payload = json.loads((FIXTURES / "positive-p9-receipt.json").read_text(encoding="utf-8"))
    payload.update(
        {
            "created_at_unix_ms": now_ms - 1000,
            "report_sha256": report_sha,
            "recomputed_report_sha256": report_sha,
            "report_generated_at_unix_ms": now_ms - 2000,
            "report_age_ms": 1000,
            "decision_sha256": trace["decision_sha256"],
            "operational_inputs_fixture": False,
            "canonical_operational_paths": True,
            "confirmation_sha256": hashlib.sha256(
                p9_acceptance.EXACT_CONFIRMATION.encode()
            ).hexdigest(),
        }
    )
    basis_sha = documents.canonical_sha256(p9_acceptance._acceptance_basis(payload))
    payload["acceptance_basis_sha256"] = basis_sha
    payload["receipt_id"] = f"conditions-shadow-acceptance-{basis_sha[:16]}"
    assert p9_acceptance._receipt_contract_valid(payload)
    return payload


def _fixture(tmp_path: Path, monkeypatch):
    now_ms = int(time.time() * 1000)
    dev = tmp_path / "runtime" / "solteria_helper_dev"
    report_path = dev / "equipment_shadow_replay.json"
    snapshot_path = dev / "equipment_shadow_snapshot.json"
    p9_report_path = dev / "conditions_shadow_replay.json"
    p9_receipt_path = dev / "conditions_shadow_acceptance.json"
    output_path = dev / "equipment_shadow_acceptance.json"

    trace = json.loads((FIXTURES / "positive-p9-trace.json").read_text(encoding="utf-8"))
    trace["source"] = "operational"
    p9_report = {
        "schema_version": "ctoa.conditions-shadow-replay-report.v1",
        "operational_trace": trace,
    }
    p9_report_doc = documents.document_from_payload(p9_report)
    p9_receipt = _accepted_p9_receipt(trace, p9_report_doc.sha256, now_ms)
    snapshot = json.loads((FIXTURES / "positive-snapshot.json").read_text(encoding="utf-8"))
    snapshot["observed_at_unix_ms"] = now_ms - 2000
    snapshot["producer_source"] = "otclient_guarded_adapter"
    snapshot["source_report_sha256"] = "4" * 64

    profile_doc = documents.read_document(replay.DEFAULT_PROFILE)
    snapshot_doc = documents.document_from_payload(snapshot)
    trace_doc = documents.document_from_payload(trace)
    receipt_doc = documents.document_from_payload(p9_receipt)
    report = replay.build_report(
        evaluated_at_unix_ms=now_ms - 1000,
        source="operational",
        documents=(profile_doc, snapshot_doc, trace_doc, receipt_doc),
    )
    assert report["operational_acceptance_status"] == "shadow_plan_ready_for_operator_review"
    _write(report_path, report)
    _write(snapshot_path, snapshot)
    _write(p9_report_path, p9_report)
    _write(p9_receipt_path, p9_receipt)

    monkeypatch.setattr(acceptance, "DEFAULT_REPORT", report_path)
    monkeypatch.setattr(acceptance, "DEFAULT_OUTPUT", output_path)
    monkeypatch.setattr(replay, "DEFAULT_OPERATIONAL_SNAPSHOT", snapshot_path)
    monkeypatch.setattr(replay, "DEFAULT_OPERATIONAL_P9_REPORT", p9_report_path)
    monkeypatch.setattr(replay, "DEFAULT_OPERATIONAL_P9_RECEIPT", p9_receipt_path)
    monkeypatch.setattr(acceptance, "RUNTIME_ROOT", tmp_path / "runtime")

    paths = acceptance.EvidencePaths(
        report=report_path,
        profile=replay.DEFAULT_PROFILE,
        snapshot=snapshot_path,
        p9_report=p9_report_path,
        p9_receipt=p9_receipt_path,
        scenario_pack=replay.DEFAULT_SCENARIO_PACK,
    )
    return paths, output_path, now_ms


def test_p10_acceptance_requires_separate_exact_confirmation(tmp_path: Path, monkeypatch):
    paths, _, now_ms = _fixture(tmp_path, monkeypatch)
    ready, _ = acceptance.evaluate_acceptance(paths, now_unix_ms=now_ms)
    assert ready["status"] == "ready_for_operator_review"
    assert ready["acceptance_granted"] is False
    assert ready["blockers"] == []

    wrong, _ = acceptance.evaluate_acceptance(
        paths, confirmation="accept p10", write_requested=True, now_unix_ms=now_ms
    )
    assert wrong["status"] == "blocked"
    assert "operator_confirmation_mismatch" in wrong["blockers"]

    accepted, _ = acceptance.evaluate_acceptance(
        paths,
        confirmation=acceptance.EXACT_CONFIRMATION,
        write_requested=True,
        now_unix_ms=now_ms,
    )
    assert accepted["status"] == "accepted"
    assert accepted["acceptance_granted"] is True
    assert acceptance._receipt_contract(accepted)
    assert all(accepted[key] is False for key in replay.FALSE_FLAGS)

    mutations = {
        "operational_status": "operational_acceptance_blocked",
        "scenario_pack_status": "failed",
        "fixture_only_validation_passed": False,
        "operational_inputs_fixture": True,
        "canonical_operational_paths": False,
        "report_age_ms": acceptance.MAX_REPORT_AGE_MS + 1,
    }
    for key, value in mutations.items():
        changed = copy.deepcopy(accepted)
        changed[key] = value
        if key == "report_age_ms":
            changed["report_generated_at_unix_ms"] = changed["created_at_unix_ms"] - value
        basis_sha = documents.canonical_sha256(acceptance._acceptance_basis(changed))
        changed["acceptance_basis_sha256"] = basis_sha
        changed["receipt_id"] = f"equipment-shadow-acceptance-{basis_sha[:16]}"
        assert not acceptance._receipt_contract(changed), key


def test_p10_acceptance_recomputes_and_rejects_nested_tamper(tmp_path: Path, monkeypatch):
    paths, _, now_ms = _fixture(tmp_path, monkeypatch)
    payload = json.loads(paths.report.read_text(encoding="utf-8"))
    payload["operational_trace"]["plan"]["candidate_item_id"] = 9999
    _write(paths.report, payload)

    receipt, _ = acceptance.evaluate_acceptance(paths, now_unix_ms=now_ms)
    assert receipt["status"] == "blocked"
    assert "report_recompute_mismatch" in receipt["blockers"]


def test_p10_acceptance_binds_current_p9_report_and_rejects_fixture_source(tmp_path: Path, monkeypatch):
    paths, _, now_ms = _fixture(tmp_path, monkeypatch)
    p9_report = json.loads(paths.p9_report.read_text(encoding="utf-8"))
    p9_report["operational_trace"]["source"] = "fixture"
    _write(paths.p9_report, p9_report)

    receipt, _ = acceptance.evaluate_acceptance(paths, now_unix_ms=now_ms)
    assert receipt["status"] == "blocked"
    assert "p9_receipt_report_mismatch" in receipt["blockers"]
    assert "operational_inputs_fixture" in receipt["blockers"]


def test_p10_acceptance_writer_persists_only_after_three_stable_reads(tmp_path: Path, monkeypatch):
    paths, output, _ = _fixture(tmp_path, monkeypatch)
    receipt = acceptance.write_accepted_receipt(
        output, paths=paths, confirmation=acceptance.EXACT_CONFIRMATION
    )
    assert receipt["status"] == "accepted"
    assert output.exists()
    persisted = json.loads(output.read_text(encoding="utf-8"))
    assert persisted["receipt_id"] == receipt["receipt_id"]
    assert acceptance._receipt_contract(persisted)


def test_equipment_acceptance_schema_is_closed():
    schema = json.loads(
        (ROOT / "schemas" / "equipment-shadow-acceptance.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False


def test_equipment_acceptance_schema_enforces_accepted_semantics(tmp_path: Path, monkeypatch):
    paths, _, now_ms = _fixture(tmp_path, monkeypatch)
    accepted, _ = acceptance.evaluate_acceptance(
        paths,
        confirmation=acceptance.EXACT_CONFIRMATION,
        write_requested=True,
        now_unix_ms=now_ms,
    )
    schema = json.loads(
        (ROOT / "schemas" / "equipment-shadow-acceptance.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    assert not list(validator.iter_errors(accepted))
    for key, value in {
        "operational_status": "operational_acceptance_blocked",
        "scenario_pack_status": "failed",
        "fixture_only_validation_passed": False,
        "operational_inputs_fixture": True,
        "canonical_operational_paths": False,
        "report_age_ms": acceptance.MAX_REPORT_AGE_MS + 1,
    }.items():
        changed = copy.deepcopy(accepted)
        changed[key] = value
        assert list(validator.iter_errors(changed)), key


def test_release_evidence_binds_p10_receipt_to_current_report(tmp_path: Path, monkeypatch):
    paths, output, now_ms = _fixture(tmp_path, monkeypatch)
    receipt, _ = acceptance.evaluate_acceptance(
        paths,
        confirmation=acceptance.EXACT_CONFIRMATION,
        write_requested=True,
        now_unix_ms=now_ms,
    )
    report = json.loads(paths.report.read_text(encoding="utf-8"))
    summary = evidence._equipment_shadow_acceptance_summary(
        receipt,
        output,
        report,
        now=datetime.fromtimestamp(now_ms / 1000, tz=timezone.utc),
    )
    assert summary["status"] == "accepted"
    assert summary["acceptance_granted"] is True
    assert summary["p11_predecessor_eligible"] is True

    tampered = copy.deepcopy(receipt)
    tampered["report_sha256"] = "0" * 64
    summary = evidence._equipment_shadow_acceptance_summary(
        tampered,
        output,
        report,
        now=datetime.fromtimestamp(now_ms / 1000, tz=timezone.utc),
    )
    assert summary["status"] == "invalid"
    assert summary["p11_predecessor_eligible"] is False


def test_release_evidence_accepts_fail_closed_operational_trace():
    report = replay.build_report(
        evaluated_at_unix_ms=int(time.time() * 1000),
        source="operational",
        documents=(
            documents.read_document(replay.DEFAULT_PROFILE),
            documents.document_from_payload({}),
            documents.document_from_payload({}),
            documents.document_from_payload({}),
        ),
    )
    assert report["operational_trace"]["status"] == "operational_acceptance_blocked"
    assert report["operational_trace"]["plan"] is None
    summary = evidence._equipment_shadow_summary(
        report,
        replay.DEFAULT_OUTPUT,
        now=datetime.fromtimestamp(
            report["generated_at_unix_ms"] / 1000, tz=timezone.utc
        ),
    )
    assert summary["contract_valid"] is True
    assert summary["status"] == "operational_acceptance_blocked"


def test_release_evidence_rejects_rebased_accepted_receipt_for_blocked_report(
    tmp_path: Path, monkeypatch
):
    paths, output, now_ms = _fixture(tmp_path, monkeypatch)
    receipt, _ = acceptance.evaluate_acceptance(
        paths,
        confirmation=acceptance.EXACT_CONFIRMATION,
        write_requested=True,
        now_unix_ms=now_ms,
    )
    blocked_report = replay.build_report(
        evaluated_at_unix_ms=now_ms,
        source="operational",
        documents=(
            documents.read_document(replay.DEFAULT_PROFILE),
            documents.document_from_payload({}),
            documents.document_from_payload({}),
            documents.document_from_payload({}),
        ),
    )
    blocked_sha = documents.canonical_sha256(blocked_report)
    forged = copy.deepcopy(receipt)
    forged["report_sha256"] = blocked_sha
    forged["recomputed_report_sha256"] = blocked_sha
    forged["report_generated_at_unix_ms"] = now_ms
    forged["report_age_ms"] = 0
    basis_sha = documents.canonical_sha256(acceptance._acceptance_basis(forged))
    forged["acceptance_basis_sha256"] = basis_sha
    forged["receipt_id"] = f"equipment-shadow-acceptance-{basis_sha[:16]}"
    assert acceptance._receipt_contract(forged)

    summary = evidence._equipment_shadow_acceptance_summary(
        forged,
        output,
        blocked_report,
        now=datetime.fromtimestamp(now_ms / 1000, tz=timezone.utc),
    )

    assert summary["status"] == "invalid"
    assert summary["acceptance_granted"] is False
    assert summary["p11_predecessor_eligible"] is False
