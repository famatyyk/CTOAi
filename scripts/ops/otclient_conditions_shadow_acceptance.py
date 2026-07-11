#!/usr/bin/env python3
"""Create a strict, data-only operator acceptance receipt for P9 Conditions.

The default invocation is a read-only preflight.  A persisted accepted receipt
requires the exact confirmation phrase, a fresh operational P9 report, strict
recomputation from the current inputs, and a second unchanged-input read.  This
tool never dispatches, executes, promotes, or touches an OTClient installation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

if __package__:
    from . import otclient_conditions_shadow_replay as replay
else:
    import otclient_conditions_shadow_replay as replay


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ROOT = ROOT / "runtime"
DEFAULT_DEV_DIR = RUNTIME_ROOT / "solteria_helper_dev"
DEFAULT_REPORT = DEFAULT_DEV_DIR / "conditions_shadow_replay.json"
DEFAULT_OUTPUT = DEFAULT_DEV_DIR / "conditions_shadow_acceptance.json"

SCHEMA_VERSION = "ctoa.conditions-shadow-acceptance.v1"
MODE = "data_only_operator_acceptance"
EXACT_CONFIRMATION = "accept P9 conditions shadow"
MAX_REPORT_BYTES = 256 * 1024
MAX_REPORT_AGE_MS = 30_000
ZERO_SHA256 = "0" * 64
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

REPORT_KEYS = {
    "schema_version",
    "generated_at_unix_ms",
    "mode",
    "operational_acceptance_status",
    "scenario_pack_status",
    "fixture_only_validation_passed",
    "runtime_readiness_claimed",
    "operational_trace",
    "scenario_pack",
    *replay.FALSE_FLAGS,
    "intrusive_actions_performed",
}
INPUT_HASH_KEYS = {
    "profile",
    "observation",
    "p8_proof",
    "recovery_trace",
    "recovery_proof",
}
RECEIPT_KEYS = {
    "schema_version",
    "receipt_id",
    "created_at_unix_ms",
    "mode",
    "status",
    "acceptance_granted",
    "operator_review_completed",
    "downstream_use_requires_separate_review",
    "confirmation_required",
    "confirmation_matched",
    "confirmation_sha256",
    "receipt_persisted",
    "report_sha256",
    "recomputed_report_sha256",
    "report_generated_at_unix_ms",
    "report_age_ms",
    "operational_status",
    "scenario_pack_status",
    "fixture_only_validation_passed",
    "operational_inputs_fixture",
    "canonical_operational_paths",
    "action",
    "condition",
    "spell",
    "canonical_input_sha256",
    "decision_sha256",
    "input_sha256",
    "scenario_pack_sha256",
    "blockers",
    "acceptance_basis_sha256",
    "runtime_readiness_claimed",
    *replay.FALSE_FLAGS,
    "intrusive_actions_performed",
}

BLOCKER_ORDER = (
    "report_missing",
    "report_malformed",
    "report_duplicate_keys",
    "report_oversize",
    "report_symlink_rejected",
    "report_not_regular",
    "report_not_object",
    "report_changed_during_open",
    "report_unreadable",
    "report_schema_invalid",
    "current_input_invalid",
    "report_recompute_mismatch",
    "report_future",
    "report_stale",
    "operational_status_not_ready",
    "operational_trace_not_ready",
    "operational_trace_has_blockers",
    "scenario_pack_not_passed",
    "fixture_validation_not_passed",
    "unsafe_action_contract",
    "operational_inputs_fixture",
    "raw_background_status_required",
    "noncanonical_operational_paths",
    "operator_confirmation_mismatch",
    "evidence_changed_before_write",
)
BLOCKER_RANK = {name: index for index, name in enumerate(BLOCKER_ORDER)}
REPORT_LOAD_BLOCKERS = {
    "missing": "report_missing",
    "malformed": "report_malformed",
    "duplicate_keys": "report_duplicate_keys",
    "oversize": "report_oversize",
    "symlink_rejected": "report_symlink_rejected",
    "not_regular": "report_not_regular",
    "not_object": "report_not_object",
    "changed_during_open": "report_changed_during_open",
    "unreadable": "report_unreadable",
}


@dataclass(frozen=True)
class EvidencePaths:
    report: Path = DEFAULT_REPORT
    profile: Path = replay.DEFAULT_PROFILE
    p8_proof: Path = replay.DEFAULT_P8_PROOF
    recovery_trace: Path = replay.DEFAULT_RECOVERY_TRACE
    recovery_proof: Path = replay.DEFAULT_RECOVERY_PROOF
    scenario_pack: Path = replay.DEFAULT_SCENARIO_PACK
    observation: Path | None = None


@dataclass(frozen=True)
class EvidenceBundle:
    paths: EvidencePaths
    report: replay.InputDocument
    profile: replay.InputDocument
    raw_p8: replay.InputDocument
    observation: replay.InputDocument
    p8_proof: replay.InputDocument
    recovery_trace: replay.InputDocument
    recovery_proof: replay.InputDocument
    scenario_pack: replay.InputDocument
    explicit_observation: replay.InputDocument | None


def _now_unix_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_sha256(value: Any, *, allow_zero: bool = False) -> bool:
    return bool(
        isinstance(value, str)
        and SHA256_RE.fullmatch(value)
        and (allow_zero or value != ZERO_SHA256)
    )


def _false_flags(payload: dict[str, Any]) -> bool:
    return all(payload.get(key) is False for key in replay.FALSE_FLAGS)


def _empty_ledger(payload: dict[str, Any]) -> bool:
    return payload.get("intrusive_actions_performed") == []


def _ordered_blockers(values: Iterable[str]) -> list[str]:
    unique = set(values)
    unknown = unique - set(BLOCKER_RANK)
    if unknown:
        raise ValueError(f"unknown acceptance blockers: {sorted(unknown)}")
    return sorted(unique, key=BLOCKER_RANK.__getitem__)


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left.resolve(strict=False))) == os.path.normcase(
        str(right.resolve(strict=False))
    )


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except (OSError, ValueError):
        return False


def _path_has_reparse_component(path: Path, boundary: Path) -> bool:
    absolute_path = Path(os.path.abspath(path))
    absolute_boundary = Path(os.path.abspath(boundary))
    try:
        relative = absolute_path.relative_to(absolute_boundary)
    except ValueError:
        return True
    candidates = [absolute_boundary]
    current = absolute_boundary
    for part in relative.parts:
        current /= part
        candidates.append(current)
    for candidate in candidates:
        try:
            metadata = candidate.lstat()
        except FileNotFoundError:
            continue
        file_attributes = int(getattr(metadata, "st_file_attributes", 0))
        if stat.S_ISLNK(metadata.st_mode) or (
            file_attributes & int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
        ):
            return True
    return False


def _validate_output_path(path: Path) -> Path:
    if not _same_path(path, DEFAULT_OUTPUT):
        raise ValueError(f"JSON output must equal {DEFAULT_OUTPUT}")
    if not _is_within(path, RUNTIME_ROOT):
        raise ValueError(f"JSON output must stay under {RUNTIME_ROOT}")
    if _path_has_reparse_component(path.parent, RUNTIME_ROOT.parent):
        raise ValueError("JSON output ancestors must not contain reparse points")
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return path.resolve(strict=False)
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise ValueError("JSON output must be a regular non-link file")
    return path.resolve(strict=False)


def read_evidence(paths: EvidencePaths) -> EvidenceBundle:
    report = replay.read_document(paths.report, MAX_REPORT_BYTES)
    profile = replay.read_document(paths.profile)
    raw_p8 = replay.read_document(paths.p8_proof)
    recovery_trace = replay.read_document(paths.recovery_trace)
    recovery_proof = replay.read_document(paths.recovery_proof)
    scenario_pack = replay.read_document(paths.scenario_pack, replay.MAX_SCENARIO_BYTES)
    explicit_observation = (
        replay.read_document(paths.observation) if paths.observation else None
    )
    observation = replay._select_observation_document(  # noqa: SLF001
        raw_p8, explicit_observation
    )
    p8_proof = replay.normalize_p8_proof(raw_p8, observation)
    return EvidenceBundle(
        paths=paths,
        report=report,
        profile=profile,
        raw_p8=raw_p8,
        observation=observation,
        p8_proof=p8_proof,
        recovery_trace=recovery_trace,
        recovery_proof=recovery_proof,
        scenario_pack=scenario_pack,
        explicit_observation=explicit_observation,
    )


def evidence_fingerprint(bundle: EvidenceBundle) -> tuple[tuple[str, str], ...]:
    documents = [
        bundle.report,
        bundle.profile,
        bundle.raw_p8,
        bundle.recovery_trace,
        bundle.recovery_proof,
        bundle.scenario_pack,
    ]
    if bundle.explicit_observation is not None:
        documents.append(bundle.explicit_observation)
    return tuple((document.status, document.sha256) for document in documents)


def _report_no_action_contract(payload: dict[str, Any]) -> bool:
    if set(payload) != REPORT_KEYS:
        return False
    trace = payload.get("operational_trace")
    scenario_pack = payload.get("scenario_pack")
    if not isinstance(trace, dict) or not isinstance(scenario_pack, dict):
        return False
    cases = scenario_pack.get("cases")
    return bool(
        payload.get("schema_version") == replay.REPORT_SCHEMA
        and payload.get("mode") == "offline_shadow_replay"
        and payload.get("runtime_readiness_claimed") is False
        and _false_flags(payload)
        and _empty_ledger(payload)
        and trace.get("schema_version") == replay.TRACE_SCHEMA
        and trace.get("source") == "operational"
        and trace.get("operator_review_required") is True
        and _false_flags(trace)
        and _empty_ledger(trace)
        and scenario_pack.get("fixture_only") is True
        and scenario_pack.get("operational_readiness_claimed") is False
        and _false_flags(scenario_pack)
        and _empty_ledger(scenario_pack)
        and isinstance(cases, list)
        and 1 <= len(cases) <= 128
        and all(
            isinstance(case, dict) and _false_flags(case) and _empty_ledger(case)
            for case in cases
        )
    )


def _operational_inputs_fixture(bundle: EvidenceBundle) -> bool:
    documents_and_sources = (
        (bundle.observation, "producer_source"),
        (bundle.p8_proof, "source"),
        (bundle.recovery_trace, "source"),
        (bundle.recovery_proof, "source"),
    )
    return any(
        isinstance(document.payload, dict)
        and document.payload.get(source_key) == "fixture"
        for document, source_key in documents_and_sources
    )


def _canonical_operational_paths(paths: EvidencePaths) -> bool:
    canonical_pairs = (
        (paths.report, DEFAULT_REPORT),
        (paths.profile, replay.DEFAULT_PROFILE),
        (paths.p8_proof, replay.DEFAULT_P8_PROOF),
        (paths.recovery_trace, replay.DEFAULT_RECOVERY_TRACE),
        (paths.recovery_proof, replay.DEFAULT_RECOVERY_PROOF),
        (paths.scenario_pack, replay.DEFAULT_SCENARIO_PACK),
    )
    return bool(
        paths.observation is None
        and all(_same_path(actual, expected) for actual, expected in canonical_pairs)
        and all(
            not _path_has_reparse_component(actual, ROOT)
            for actual, _ in canonical_pairs
        )
    )


def _current_inputs_loaded(bundle: EvidenceBundle) -> bool:
    documents = (
        bundle.profile,
        bundle.raw_p8,
        bundle.observation,
        bundle.p8_proof,
        bundle.recovery_trace,
        bundle.recovery_proof,
        bundle.scenario_pack,
    )
    return all(document.status == "loaded" for document in documents)


def _safe_input_hashes(trace: dict[str, Any]) -> dict[str, str]:
    raw = trace.get("input_sha256")
    if not isinstance(raw, dict) or set(raw) != INPUT_HASH_KEYS:
        return {key: ZERO_SHA256 for key in sorted(INPUT_HASH_KEYS)}
    return {
        key: value if _is_sha256(value, allow_zero=True) else ZERO_SHA256
        for key, value in raw.items()
    }


def _acceptance_basis(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": payload.get("schema_version"),
        "created_at_unix_ms": payload.get("created_at_unix_ms"),
        "status": payload.get("status"),
        "report_sha256": payload.get("report_sha256"),
        "recomputed_report_sha256": payload.get("recomputed_report_sha256"),
        "report_generated_at_unix_ms": payload.get("report_generated_at_unix_ms"),
        "canonical_input_sha256": payload.get("canonical_input_sha256"),
        "decision_sha256": payload.get("decision_sha256"),
        "input_sha256": payload.get("input_sha256"),
        "scenario_pack_sha256": payload.get("scenario_pack_sha256"),
        "confirmation_sha256": payload.get("confirmation_sha256"),
        "blockers": payload.get("blockers"),
    }


def _receipt_contract_valid(payload: dict[str, Any]) -> bool:
    if set(payload) != RECEIPT_KEYS:
        return False
    blockers = payload.get("blockers")
    input_hashes = payload.get("input_sha256")
    if not (
        payload.get("schema_version") == SCHEMA_VERSION
        and payload.get("mode") == MODE
        and isinstance(payload.get("receipt_id"), str)
        and re.fullmatch(
            r"conditions-shadow-acceptance-[0-9a-f]{16}", payload["receipt_id"]
        )
        and _is_int(payload.get("created_at_unix_ms"))
        and payload["created_at_unix_ms"] > 0
        and payload.get("status")
        in {"blocked", "ready_for_operator_review", "accepted"}
        and isinstance(payload.get("acceptance_granted"), bool)
        and isinstance(payload.get("operator_review_completed"), bool)
        and payload.get("downstream_use_requires_separate_review") is True
        and payload.get("confirmation_required") is True
        and isinstance(payload.get("confirmation_matched"), bool)
        and (
            payload.get("confirmation_sha256") is None
            or _is_sha256(payload.get("confirmation_sha256"))
        )
        and isinstance(payload.get("receipt_persisted"), bool)
        and _is_sha256(payload.get("report_sha256"), allow_zero=True)
        and _is_sha256(payload.get("recomputed_report_sha256"), allow_zero=True)
        and _is_int(payload.get("report_generated_at_unix_ms"))
        and payload["report_generated_at_unix_ms"] >= 0
        and (
            payload.get("report_age_ms") is None
            or _is_int(payload.get("report_age_ms"))
        )
        and payload.get("operational_status")
        in {
            "invalid",
            "operational_acceptance_blocked",
            "shadow_plan_ready_for_operator_review",
        }
        and payload.get("scenario_pack_status") in {"invalid", "failed", "passed"}
        and isinstance(payload.get("fixture_only_validation_passed"), bool)
        and isinstance(payload.get("operational_inputs_fixture"), bool)
        and isinstance(payload.get("canonical_operational_paths"), bool)
        and payload.get("action") == replay.ACTION
        and payload.get("condition") == replay.CONDITION
        and payload.get("spell") == replay.SPELL
        and _is_sha256(payload.get("canonical_input_sha256"), allow_zero=True)
        and _is_sha256(payload.get("decision_sha256"), allow_zero=True)
        and isinstance(input_hashes, dict)
        and set(input_hashes) == INPUT_HASH_KEYS
        and all(_is_sha256(value, allow_zero=True) for value in input_hashes.values())
        and _is_sha256(payload.get("scenario_pack_sha256"), allow_zero=True)
        and isinstance(blockers, list)
        and blockers == _ordered_blockers(blockers)
        and _is_sha256(payload.get("acceptance_basis_sha256"))
        and payload.get("runtime_readiness_claimed") is False
        and _false_flags(payload)
        and _empty_ledger(payload)
    ):
        return False
    expected_basis_sha = replay.canonical_sha256(_acceptance_basis(payload))
    if (
        payload.get("acceptance_basis_sha256") != expected_basis_sha
        or payload.get("receipt_id")
        != f"conditions-shadow-acceptance-{expected_basis_sha[:16]}"
        or (
            payload.get("report_age_ms") is not None
            and payload["report_age_ms"]
            != payload["created_at_unix_ms"] - payload["report_generated_at_unix_ms"]
        )
        or (
            payload.get("confirmation_matched") is True
            and payload.get("confirmation_sha256")
            != hashlib.sha256(EXACT_CONFIRMATION.encode("utf-8")).hexdigest()
        )
        or (
            payload.get("confirmation_matched") is False
            and payload.get("confirmation_sha256") is not None
        )
    ):
        return False

    status = payload["status"]
    accepted = status == "accepted"
    ready = status == "ready_for_operator_review"
    if accepted:
        return bool(
            blockers == []
            and payload["acceptance_granted"] is True
            and payload["operator_review_completed"] is True
            and payload["confirmation_matched"] is True
            and payload["confirmation_sha256"]
            == hashlib.sha256(EXACT_CONFIRMATION.encode("utf-8")).hexdigest()
            and payload["receipt_persisted"] is True
            and _is_int(payload["report_age_ms"])
            and 0 <= payload["report_age_ms"] <= MAX_REPORT_AGE_MS
            and payload["report_sha256"] == payload["recomputed_report_sha256"]
            and payload["report_sha256"] != ZERO_SHA256
            and payload["operational_status"] == "shadow_plan_ready_for_operator_review"
            and payload["scenario_pack_status"] == "passed"
            and payload["fixture_only_validation_passed"] is True
            and payload["operational_inputs_fixture"] is False
            and payload["canonical_operational_paths"] is True
            and payload["canonical_input_sha256"] != ZERO_SHA256
            and payload["decision_sha256"] != ZERO_SHA256
            and all(value != ZERO_SHA256 for value in input_hashes.values())
            and payload["scenario_pack_sha256"] != ZERO_SHA256
        )
    if ready:
        return bool(
            blockers == []
            and payload["acceptance_granted"] is False
            and payload["operator_review_completed"] is False
            and payload["receipt_persisted"] is False
        )
    return bool(
        blockers
        and payload["acceptance_granted"] is False
        and payload["operator_review_completed"] is False
        and payload["receipt_persisted"] is False
    )


def evaluate_acceptance(
    paths: EvidencePaths,
    *,
    confirmation: str | None = None,
    write_requested: bool = False,
    now_unix_ms: int | None = None,
    extra_blockers: Iterable[str] = (),
) -> tuple[dict[str, Any], EvidenceBundle]:
    now_ms = _now_unix_ms() if now_unix_ms is None else now_unix_ms
    if not _is_int(now_ms) or now_ms <= 0:
        raise ValueError("now_unix_ms must be a positive integer")
    bundle = read_evidence(paths)
    blockers = set(extra_blockers)
    report_payload = bundle.report.payload
    recomputed: dict[str, Any] | None = None
    recomputed_sha = ZERO_SHA256
    generated_at = 0
    report_age: int | None = None

    if bundle.report.status != "loaded" or report_payload is None:
        blockers.add(
            REPORT_LOAD_BLOCKERS.get(bundle.report.status, "report_unreadable")
        )
    else:
        if not _report_no_action_contract(report_payload):
            blockers.add("report_schema_invalid")
        raw_generated = report_payload.get("generated_at_unix_ms")
        if _is_int(raw_generated) and raw_generated > 0:
            generated_at = raw_generated
            report_age = now_ms - generated_at
            if report_age < 0:
                blockers.add("report_future")
            elif report_age > MAX_REPORT_AGE_MS:
                blockers.add("report_stale")
            recomputed = replay.build_report(
                profile_document=bundle.profile,
                raw_p8_document=bundle.raw_p8,
                recovery_trace_document=bundle.recovery_trace,
                recovery_proof_document=bundle.recovery_proof,
                scenario_document=bundle.scenario_pack,
                evaluated_at_unix_ms=generated_at,
                explicit_observation_document=bundle.explicit_observation,
            )
            recomputed_sha = replay.canonical_sha256(recomputed)
            if bundle.report.sha256 != recomputed_sha:
                blockers.add("report_recompute_mismatch")
        else:
            blockers.add("report_schema_invalid")

    if not _current_inputs_loaded(bundle):
        blockers.add("current_input_invalid")

    data = report_payload if isinstance(report_payload, dict) else {}
    trace = data.get("operational_trace")
    trace = trace if isinstance(trace, dict) else {}
    scenario_pack = data.get("scenario_pack")
    scenario_pack = scenario_pack if isinstance(scenario_pack, dict) else {}
    operational_status = data.get("operational_acceptance_status")
    if operational_status != "shadow_plan_ready_for_operator_review":
        blockers.add("operational_status_not_ready")
    if not (
        trace.get("status") == "shadow_plan_ready"
        and trace.get("decision") == "would_plan_paralyze_recovery"
        and trace.get("source") == "operational"
        and trace.get("operator_review_required") is True
    ):
        blockers.add("operational_trace_not_ready")
    if trace.get("blockers") != []:
        blockers.add("operational_trace_has_blockers")
    if (
        data.get("scenario_pack_status") != "passed"
        or scenario_pack.get("status") != "passed"
    ):
        blockers.add("scenario_pack_not_passed")
    if data.get("fixture_only_validation_passed") is not True:
        blockers.add("fixture_validation_not_passed")
    if not _report_no_action_contract(data):
        blockers.add("unsafe_action_contract")
    operational_inputs_fixture = _operational_inputs_fixture(bundle)
    if operational_inputs_fixture:
        blockers.add("operational_inputs_fixture")
    raw_p8_payload = bundle.raw_p8.payload
    if not (
        isinstance(raw_p8_payload, dict)
        and raw_p8_payload.get("schema_version") == replay.P8_BACKGROUND_SCHEMA
        and bundle.explicit_observation is None
    ):
        blockers.add("raw_background_status_required")
    canonical_operational_paths = _canonical_operational_paths(paths)
    if not canonical_operational_paths:
        blockers.add("noncanonical_operational_paths")
    confirmation_matched = confirmation == EXACT_CONFIRMATION
    if confirmation is not None and not confirmation_matched:
        blockers.add("operator_confirmation_mismatch")

    ordered_blockers = _ordered_blockers(blockers)
    accepted = bool(not ordered_blockers and confirmation_matched and write_requested)
    status = (
        "accepted"
        if accepted
        else "ready_for_operator_review"
        if not ordered_blockers
        else "blocked"
    )
    input_hashes = _safe_input_hashes(trace)
    canonical_input_sha = trace.get("canonical_input_sha256")
    if not _is_sha256(canonical_input_sha, allow_zero=True):
        canonical_input_sha = ZERO_SHA256
    decision_sha = trace.get("decision_sha256")
    if not _is_sha256(decision_sha, allow_zero=True):
        decision_sha = ZERO_SHA256
    scenario_sha = scenario_pack.get("scenario_pack_sha256")
    if not _is_sha256(scenario_sha, allow_zero=True):
        scenario_sha = ZERO_SHA256
    report_sha = (
        bundle.report.sha256
        if bundle.report.status == "loaded"
        and _is_sha256(bundle.report.sha256, allow_zero=True)
        else ZERO_SHA256
    )
    confirmation_sha = (
        hashlib.sha256(EXACT_CONFIRMATION.encode("utf-8")).hexdigest()
        if confirmation_matched
        else None
    )
    basis = {
        "schema_version": SCHEMA_VERSION,
        "created_at_unix_ms": now_ms,
        "status": status,
        "report_sha256": report_sha,
        "recomputed_report_sha256": recomputed_sha,
        "report_generated_at_unix_ms": generated_at,
        "canonical_input_sha256": canonical_input_sha,
        "decision_sha256": decision_sha,
        "input_sha256": input_hashes,
        "scenario_pack_sha256": scenario_sha,
        "confirmation_sha256": confirmation_sha,
        "blockers": ordered_blockers,
    }
    basis_sha = replay.canonical_sha256(basis)
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "receipt_id": f"conditions-shadow-acceptance-{basis_sha[:16]}",
        "created_at_unix_ms": now_ms,
        "mode": MODE,
        "status": status,
        "acceptance_granted": accepted,
        "operator_review_completed": accepted,
        "downstream_use_requires_separate_review": True,
        "confirmation_required": True,
        "confirmation_matched": confirmation_matched,
        "confirmation_sha256": confirmation_sha,
        "receipt_persisted": accepted,
        "report_sha256": report_sha,
        "recomputed_report_sha256": recomputed_sha,
        "report_generated_at_unix_ms": generated_at,
        "report_age_ms": report_age,
        "operational_status": operational_status
        if operational_status
        in {
            "operational_acceptance_blocked",
            "shadow_plan_ready_for_operator_review",
        }
        else "invalid",
        "scenario_pack_status": data.get("scenario_pack_status")
        if data.get("scenario_pack_status") in {"failed", "passed"}
        else "invalid",
        "fixture_only_validation_passed": data.get("fixture_only_validation_passed")
        is True,
        "operational_inputs_fixture": operational_inputs_fixture,
        "canonical_operational_paths": canonical_operational_paths,
        "action": replay.ACTION,
        "condition": replay.CONDITION,
        "spell": replay.SPELL,
        "canonical_input_sha256": canonical_input_sha,
        "decision_sha256": decision_sha,
        "input_sha256": input_hashes,
        "scenario_pack_sha256": scenario_sha,
        "blockers": ordered_blockers,
        "acceptance_basis_sha256": basis_sha,
        "runtime_readiness_claimed": False,
        **{key: False for key in replay.FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }
    if not _receipt_contract_valid(receipt):
        raise ValueError("internal acceptance receipt contract validation failed")
    return receipt, bundle


def write_accepted_receipt(
    path: Path,
    *,
    paths: EvidencePaths,
    confirmation: str,
) -> dict[str, Any]:
    """Revalidate canonical current evidence three times before persistence."""

    if confirmation != EXACT_CONFIRMATION:
        raise ValueError("exact operator confirmation is required for persistence")
    output = _validate_output_path(path)
    first_receipt, first_bundle = evaluate_acceptance(
        paths,
        confirmation=confirmation,
        write_requested=True,
        now_unix_ms=_now_unix_ms(),
    )
    if first_receipt["status"] != "accepted":
        return first_receipt
    second_receipt, second_bundle = evaluate_acceptance(
        paths,
        confirmation=confirmation,
        write_requested=True,
        now_unix_ms=_now_unix_ms(),
    )
    if evidence_fingerprint(first_bundle) != evidence_fingerprint(second_bundle):
        blocked_receipt, _ = evaluate_acceptance(
            paths,
            confirmation=confirmation,
            write_requested=False,
            now_unix_ms=_now_unix_ms(),
            extra_blockers=("evidence_changed_before_write",),
        )
        return blocked_receipt
    if second_receipt["status"] != "accepted":
        return second_receipt
    if not _receipt_contract_valid(second_receipt):
        raise ValueError("revalidated accepted receipt failed its internal contract")
    final_receipt, final_bundle = evaluate_acceptance(
        paths,
        confirmation=confirmation,
        write_requested=True,
        now_unix_ms=_now_unix_ms(),
    )
    if evidence_fingerprint(second_bundle) != evidence_fingerprint(final_bundle):
        blocked_receipt, _ = evaluate_acceptance(
            paths,
            confirmation=confirmation,
            write_requested=False,
            now_unix_ms=_now_unix_ms(),
            extra_blockers=("evidence_changed_before_write",),
        )
        return blocked_receipt
    if final_receipt["status"] != "accepted":
        return final_receipt
    if not _receipt_contract_valid(final_receipt):
        raise ValueError("final accepted receipt failed its internal contract")

    output.parent.mkdir(parents=True, exist_ok=True)
    output = _validate_output_path(path)
    temporary = output.with_name(f".{output.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    temporary_identity: tuple[int, int] | None = None
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        flags |= int(getattr(os, "O_BINARY", 0))
        flags |= int(getattr(os, "O_NOFOLLOW", 0))
        descriptor = os.open(temporary, flags, 0o600)
        try:
            with os.fdopen(descriptor, "wb", closefd=False) as handle:
                handle.write(replay.canonical_bytes(final_receipt) + b"\n")
                handle.flush()
                os.fsync(handle.fileno())
                opened = os.fstat(handle.fileno())
                temporary_identity = (int(opened.st_dev), int(opened.st_ino))
        finally:
            os.close(descriptor)
        current = temporary.lstat()
        current_attributes = int(getattr(current, "st_file_attributes", 0))
        if (
            stat.S_ISLNK(current.st_mode)
            or not stat.S_ISREG(current.st_mode)
            or current_attributes
            & int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
            or temporary_identity != (int(current.st_dev), int(current.st_ino))
        ):
            raise ValueError("temporary acceptance receipt identity changed")
        output = _validate_output_path(path)
        temporary.replace(output)
        temporary_identity = None
    finally:
        if temporary_identity is not None:
            try:
                current = temporary.lstat()
            except FileNotFoundError:
                pass
            else:
                if temporary_identity == (int(current.st_dev), int(current.st_ino)):
                    temporary.unlink()
    return final_receipt


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--profile", type=Path, default=replay.DEFAULT_PROFILE)
    parser.add_argument("--p8-proof", type=Path, default=replay.DEFAULT_P8_PROOF)
    parser.add_argument("--observation", type=Path)
    parser.add_argument(
        "--recovery-trace", type=Path, default=replay.DEFAULT_RECOVERY_TRACE
    )
    parser.add_argument(
        "--recovery-proof", type=Path, default=replay.DEFAULT_RECOVERY_PROOF
    )
    parser.add_argument(
        "--scenario-pack", type=Path, default=replay.DEFAULT_SCENARIO_PACK
    )
    parser.add_argument("--json-out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--confirm")
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Print preflight only; even exact confirmation cannot accept or persist.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        output = _validate_output_path(args.json_out)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    paths = EvidencePaths(
        report=args.report,
        profile=args.profile,
        p8_proof=args.p8_proof,
        recovery_trace=args.recovery_trace,
        recovery_proof=args.recovery_proof,
        scenario_pack=args.scenario_pack,
        observation=args.observation,
    )
    now_ms = _now_unix_ms()
    write_requested = bool(
        args.confirm == EXACT_CONFIRMATION and args.no_write is False
    )
    try:
        receipt, _ = evaluate_acceptance(
            paths,
            confirmation=args.confirm,
            write_requested=write_requested,
            now_unix_ms=now_ms,
        )
        if receipt["status"] == "accepted":
            receipt = write_accepted_receipt(
                output,
                paths=paths,
                confirmation=args.confirm,
            )
        if receipt["status"] == "accepted":
            print(f"[conditions-shadow-acceptance] JSON: {output}")
            print("[conditions-shadow-acceptance] Status: accepted")
        else:
            print(json.dumps(receipt, indent=2, sort_keys=True))
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0 if receipt["status"] in {"ready_for_operator_review", "accepted"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
