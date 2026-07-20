#!/usr/bin/env python3
"""Independently review and persist the data-only P10 Equipment receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

if __package__:
    from . import otclient_conditions_shadow_replay as p9_replay
    from . import otclient_equipment_shadow_replay as replay
else:  # pragma: no cover
    import otclient_conditions_shadow_replay as p9_replay
    import otclient_equipment_shadow_replay as replay


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ROOT = ROOT / "runtime"
DEV_DIR = RUNTIME_ROOT / "solteria_helper_dev"
DEFAULT_REPORT = replay.DEFAULT_OUTPUT
DEFAULT_OUTPUT = DEV_DIR / "equipment_shadow_acceptance.json"
SCHEMA_VERSION = "ctoa.equipment-shadow-acceptance.v1"
MODE = "data_only_operator_acceptance"
EXACT_CONFIRMATION = "accept P10 equipment shadow"
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
    "report_invalid",
    "report_future",
    "report_stale",
    "current_input_invalid",
    "p9_receipt_report_mismatch",
    "report_recompute_mismatch",
    "operational_status_not_ready",
    "operational_trace_not_ready",
    "operational_trace_has_blockers",
    "scenario_pack_not_passed",
    "fixture_validation_not_passed",
    "operational_inputs_fixture",
    "noncanonical_operational_paths",
    "unsafe_action_contract",
    "operator_confirmation_mismatch",
    "evidence_changed_before_write",
)
BLOCKER_RANK = {name: index for index, name in enumerate(BLOCKER_ORDER)}


@dataclass(frozen=True)
class EvidencePaths:
    report: Path = DEFAULT_REPORT
    profile: Path = replay.DEFAULT_PROFILE
    snapshot: Path = replay.DEFAULT_OPERATIONAL_SNAPSHOT
    p9_report: Path = replay.DEFAULT_OPERATIONAL_P9_REPORT
    p9_receipt: Path = replay.DEFAULT_OPERATIONAL_P9_RECEIPT
    scenario_pack: Path = replay.DEFAULT_SCENARIO_PACK


@dataclass(frozen=True)
class EvidenceBundle:
    paths: EvidencePaths
    report: p9_replay.InputDocument
    profile: p9_replay.InputDocument
    snapshot: p9_replay.InputDocument
    raw_p9_report: p9_replay.InputDocument
    p9_trace: p9_replay.InputDocument
    p9_receipt: p9_replay.InputDocument
    scenario_pack: p9_replay.InputDocument


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_sha(value: Any, *, allow_zero: bool = False) -> bool:
    return bool(
        isinstance(value, str)
        and SHA256_RE.fullmatch(value)
        and (allow_zero or value != ZERO_SHA256)
    )


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left.resolve(strict=False))) == os.path.normcase(
        str(right.resolve(strict=False))
    )


def _path_has_reparse(path: Path, boundary: Path) -> bool:
    absolute, root = Path(os.path.abspath(path)), Path(os.path.abspath(boundary))
    try:
        relative = absolute.relative_to(root)
    except ValueError:
        return True
    current = root
    for part in relative.parts:
        current /= part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            continue
        attributes = int(getattr(metadata, "st_file_attributes", 0))
        if stat.S_ISLNK(metadata.st_mode) or attributes & int(
            getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        ):
            return True
    return False


def _canonical_paths(paths: EvidencePaths) -> bool:
    pairs = (
        (paths.report, DEFAULT_REPORT),
        (paths.profile, replay.DEFAULT_PROFILE),
        (paths.snapshot, replay.DEFAULT_OPERATIONAL_SNAPSHOT),
        (paths.p9_report, replay.DEFAULT_OPERATIONAL_P9_REPORT),
        (paths.p9_receipt, replay.DEFAULT_OPERATIONAL_P9_RECEIPT),
        (paths.scenario_pack, replay.DEFAULT_SCENARIO_PACK),
    )
    return all(_same_path(actual, expected) for actual, expected in pairs) and all(
        not _path_has_reparse(
            actual,
            RUNTIME_ROOT
            if expected.resolve(strict=False).is_relative_to(
                RUNTIME_ROOT.resolve(strict=False)
            )
            else ROOT,
        )
        for actual, expected in pairs
    )


def _validate_output(path: Path) -> Path:
    if not _same_path(path, DEFAULT_OUTPUT):
        raise ValueError(f"JSON output must equal {DEFAULT_OUTPUT}")
    if not path.resolve(strict=False).is_relative_to(
        RUNTIME_ROOT.resolve(strict=False)
    ):
        raise ValueError(f"JSON output must stay under {RUNTIME_ROOT}")
    if _path_has_reparse(path.parent, RUNTIME_ROOT):
        raise ValueError("JSON output ancestors must not contain reparse points")
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return path.resolve(strict=False)
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise ValueError("JSON output must be a regular non-link file")
    return path.resolve(strict=False)


def read_evidence(paths: EvidencePaths) -> EvidenceBundle:
    raw_p9 = p9_replay.read_document(paths.p9_report)
    return EvidenceBundle(
        paths=paths,
        report=p9_replay.read_document(paths.report, replay.MAX_SCENARIO_BYTES),
        profile=p9_replay.read_document(paths.profile),
        snapshot=p9_replay.read_document(paths.snapshot),
        raw_p9_report=raw_p9,
        p9_trace=replay._p9_trace_document(paths.p9_report),  # noqa: SLF001
        p9_receipt=p9_replay.read_document(paths.p9_receipt),
        scenario_pack=p9_replay.read_document(
            paths.scenario_pack, replay.MAX_SCENARIO_BYTES
        ),
    )


def evidence_fingerprint(bundle: EvidenceBundle) -> tuple[tuple[str, str], ...]:
    return tuple(
        (document.status, document.sha256)
        for document in (
            bundle.report,
            bundle.profile,
            bundle.snapshot,
            bundle.raw_p9_report,
            bundle.p9_receipt,
            bundle.scenario_pack,
        )
    )


def _report_no_action(payload: Any) -> bool:
    if not isinstance(payload, dict) or set(payload) != REPORT_KEYS:
        return False
    trace, pack = payload.get("operational_trace"), payload.get("scenario_pack")
    cases = pack.get("cases") if isinstance(pack, dict) else None
    values = [payload, trace, pack] + (cases if isinstance(cases, list) else [])
    return bool(
        payload.get("schema_version") == replay.REPORT_SCHEMA
        and payload.get("mode") == "offline_equipment_shadow_replay"
        and payload.get("runtime_readiness_claimed") is False
        and isinstance(trace, dict)
        and trace.get("trace_id")
        == f"equipment-shadow-{str(trace.get('decision_sha256') or '')[:16]}"
        and isinstance(trace.get("input_sha256"), dict)
        and set(trace["input_sha256"])
        == {"profile", "snapshot", "p9_trace", "p9_receipt"}
        and isinstance(pack, dict)
        and isinstance(cases, list)
        and len(cases) == 30
        and replay._is_sha256(pack.get("scenario_pack_sha256"))  # noqa: SLF001
        and pack.get("scenario_pack_sha256") != ZERO_SHA256
        and {case.get("mutation") for case in cases if isinstance(case, dict)}
        == replay.SCENARIO_MUTATIONS
        and all(
            isinstance(value, dict)
            and replay._false_flags(value)  # noqa: SLF001
            and replay._empty_ledger(value)  # noqa: SLF001
            for value in values
        )
    )


def _current_inputs_loaded(bundle: EvidenceBundle) -> bool:
    return all(
        document.status == "loaded"
        for document in (
            bundle.profile,
            bundle.snapshot,
            bundle.raw_p9_report,
            bundle.p9_trace,
            bundle.p9_receipt,
            bundle.scenario_pack,
        )
    )


def _operational_inputs_fixture(bundle: EvidenceBundle) -> bool:
    snapshot = bundle.snapshot.payload or {}
    p9_trace = bundle.p9_trace.payload or {}
    p9_receipt = bundle.p9_receipt.payload or {}
    return bool(
        snapshot.get("producer_source") != "otclient_guarded_adapter"
        or p9_trace.get("source") != "operational"
        or p9_receipt.get("operational_inputs_fixture") is not False
    )


def _ordered(values: Iterable[str]) -> list[str]:
    unknown = set(values) - set(BLOCKER_RANK)
    if unknown:
        raise ValueError(f"unknown blockers: {sorted(unknown)}")
    return sorted(set(values), key=BLOCKER_RANK.__getitem__)


def _acceptance_basis(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at_unix_ms": payload["created_at_unix_ms"],
        "status": payload["status"],
        "report_sha256": payload["report_sha256"],
        "recomputed_report_sha256": payload["recomputed_report_sha256"],
        "report_generated_at_unix_ms": payload["report_generated_at_unix_ms"],
        "report_age_ms": payload["report_age_ms"],
        "operational_status": payload["operational_status"],
        "scenario_pack_status": payload["scenario_pack_status"],
        "fixture_only_validation_passed": payload["fixture_only_validation_passed"],
        "operational_inputs_fixture": payload["operational_inputs_fixture"],
        "canonical_operational_paths": payload["canonical_operational_paths"],
        "action": payload["action"],
        "decision_sha256": payload["decision_sha256"],
        "input_sha256": payload["input_sha256"],
        "scenario_pack_sha256": payload["scenario_pack_sha256"],
        "confirmation_sha256": payload["confirmation_sha256"],
        "blockers": payload["blockers"],
    }


def _receipt_contract(payload: Any) -> bool:
    if not (
        isinstance(payload, dict)
        and set(payload) == RECEIPT_KEYS
        and payload.get("schema_version") == SCHEMA_VERSION
        and re.fullmatch(
            r"equipment-shadow-acceptance-[0-9a-f]{16}",
            str(payload.get("receipt_id") or ""),
        )
        and _is_int(payload.get("created_at_unix_ms"))
        and payload.get("mode") == MODE
        and payload.get("status")
        in {"blocked", "ready_for_operator_review", "accepted"}
        and isinstance(payload.get("acceptance_granted"), bool)
        and isinstance(payload.get("operator_review_completed"), bool)
        and payload.get("downstream_use_requires_separate_review") is True
        and payload.get("confirmation_required") is True
        and isinstance(payload.get("confirmation_matched"), bool)
        and (
            payload.get("confirmation_sha256") is None
            or _is_sha(payload.get("confirmation_sha256"))
        )
        and isinstance(payload.get("receipt_persisted"), bool)
        and _is_sha(payload.get("report_sha256"), allow_zero=True)
        and _is_sha(payload.get("recomputed_report_sha256"), allow_zero=True)
        and _is_sha(payload.get("decision_sha256"), allow_zero=True)
        and isinstance(payload.get("input_sha256"), dict)
        and set(payload["input_sha256"])
        == {"profile", "snapshot", "p9_trace", "p9_receipt"}
        and all(
            _is_sha(value, allow_zero=True)
            for value in payload["input_sha256"].values()
        )
        and _is_sha(payload.get("scenario_pack_sha256"), allow_zero=True)
        and isinstance(payload.get("blockers"), list)
        and payload["blockers"] == _ordered(payload["blockers"])
        and _is_sha(payload.get("acceptance_basis_sha256"))
        and payload.get("runtime_readiness_claimed") is False
        and replay._false_flags(payload)  # noqa: SLF001
        and replay._empty_ledger(payload)  # noqa: SLF001
    ):
        return False
    status = payload["status"]
    blockers = payload["blockers"]
    granted = payload["acceptance_granted"]
    confirmation_matched = payload["confirmation_matched"]
    expected_confirmation_sha = hashlib.sha256(EXACT_CONFIRMATION.encode()).hexdigest()
    if payload["confirmation_sha256"] != (
        expected_confirmation_sha if confirmation_matched else None
    ):
        return False
    if granted != (status == "accepted"):
        return False
    if (
        payload["operator_review_completed"] != granted
        or payload["receipt_persisted"] != granted
    ):
        return False
    if status == "blocked" and not blockers:
        return False
    if status in {"ready_for_operator_review", "accepted"} and blockers:
        return False
    if status == "accepted" and not confirmation_matched:
        return False
    generated_at = payload.get("report_generated_at_unix_ms")
    report_age = payload.get("report_age_ms")
    if generated_at is not None and not _is_int(generated_at):
        return False
    if report_age is not None and not _is_int(report_age):
        return False
    if generated_at and report_age != payload["created_at_unix_ms"] - generated_at:
        return False
    if payload.get("action") != replay.ACTION:
        return False
    if payload.get("operational_status") not in {
        "invalid",
        "operational_acceptance_blocked",
        "shadow_plan_ready_for_operator_review",
    }:
        return False
    if payload.get("scenario_pack_status") not in {"invalid", "failed", "passed"}:
        return False
    if not all(
        isinstance(payload.get(key), bool)
        for key in (
            "fixture_only_validation_passed",
            "operational_inputs_fixture",
            "canonical_operational_paths",
        )
    ):
        return False
    if status == "accepted" and not (
        payload["operational_status"] == "shadow_plan_ready_for_operator_review"
        and payload["scenario_pack_status"] == "passed"
        and payload["fixture_only_validation_passed"] is True
        and payload["operational_inputs_fixture"] is False
        and payload["canonical_operational_paths"] is True
        and payload["report_age_ms"] is not None
        and 0 <= payload["report_age_ms"] <= MAX_REPORT_AGE_MS
        and payload["report_sha256"] != ZERO_SHA256
        and payload["report_sha256"] == payload["recomputed_report_sha256"]
        and payload["decision_sha256"] != ZERO_SHA256
        and payload["scenario_pack_sha256"] != ZERO_SHA256
        and all(value != ZERO_SHA256 for value in payload["input_sha256"].values())
    ):
        return False
    basis_sha = p9_replay.canonical_sha256(_acceptance_basis(payload))
    return bool(
        payload["acceptance_basis_sha256"] == basis_sha
        and payload["receipt_id"] == f"equipment-shadow-acceptance-{basis_sha[:16]}"
    )


def evaluate_acceptance(
    paths: EvidencePaths,
    *,
    confirmation: str | None = None,
    write_requested: bool = False,
    now_unix_ms: int | None = None,
    extra_blockers: Iterable[str] = (),
) -> tuple[dict[str, Any], EvidenceBundle]:
    now_ms = now_unix_ms or int(time.time() * 1000)
    bundle = read_evidence(paths)
    blockers = set(extra_blockers)
    data = bundle.report.payload if isinstance(bundle.report.payload, dict) else {}
    generated_at = (
        data.get("generated_at_unix_ms")
        if _is_int(data.get("generated_at_unix_ms"))
        else 0
    )
    report_age = now_ms - generated_at if generated_at else None
    recomputed_sha = ZERO_SHA256
    if bundle.report.status != "loaded":
        blockers.add(
            "report_missing" if bundle.report.status == "missing" else "report_invalid"
        )
    elif not _report_no_action(data):
        blockers.add("report_invalid")
    if report_age is not None:
        if report_age < 0:
            blockers.add("report_future")
        elif report_age > MAX_REPORT_AGE_MS:
            blockers.add("report_stale")
    else:
        blockers.add("report_invalid")
    if not _current_inputs_loaded(bundle):
        blockers.add("current_input_invalid")
    p9_receipt_payload = (
        bundle.p9_receipt.payload if isinstance(bundle.p9_receipt.payload, dict) else {}
    )
    if bundle.raw_p9_report.status == "loaded" and (
        p9_receipt_payload.get("report_sha256") != bundle.raw_p9_report.sha256
        or p9_receipt_payload.get("recomputed_report_sha256")
        != bundle.raw_p9_report.sha256
    ):
        blockers.add("p9_receipt_report_mismatch")
    if generated_at and _current_inputs_loaded(bundle):
        recomputed = replay.build_report(
            evaluated_at_unix_ms=generated_at,
            source="operational",
            documents=(
                bundle.profile,
                bundle.snapshot,
                bundle.p9_trace,
                bundle.p9_receipt,
            ),
            scenario_pack_path=paths.scenario_pack,
        )
        recomputed_sha = p9_replay.canonical_sha256(recomputed)
        if bundle.report.sha256 != recomputed_sha:
            blockers.add("report_recompute_mismatch")
    trace = (
        data.get("operational_trace")
        if isinstance(data.get("operational_trace"), dict)
        else {}
    )
    pack = (
        data.get("scenario_pack") if isinstance(data.get("scenario_pack"), dict) else {}
    )
    if (
        data.get("operational_acceptance_status")
        != "shadow_plan_ready_for_operator_review"
    ):
        blockers.add("operational_status_not_ready")
    if not (
        trace.get("status") == "shadow_plan_ready"
        and trace.get("decision") == "would_plan_ring_swap"
        and trace.get("source") == "operational"
        and trace.get("rollback_simulation") == "ready"
        and trace.get("operator_review_required") is True
    ):
        blockers.add("operational_trace_not_ready")
    if trace.get("blockers") != []:
        blockers.add("operational_trace_has_blockers")
    if (
        data.get("scenario_pack_status") != "passed"
        or pack.get("status") != "passed"
        or pack.get("passed_count") != 30
        or pack.get("total_count") != 30
        or pack.get("failed_count") != 0
    ):
        blockers.add("scenario_pack_not_passed")
    if data.get("fixture_only_validation_passed") is not True:
        blockers.add("fixture_validation_not_passed")
    operational_inputs_fixture = _operational_inputs_fixture(bundle)
    if operational_inputs_fixture:
        blockers.add("operational_inputs_fixture")
    canonical_paths = _canonical_paths(paths)
    if not canonical_paths:
        blockers.add("noncanonical_operational_paths")
    if not _report_no_action(data):
        blockers.add("unsafe_action_contract")
    confirmation_matched = confirmation == EXACT_CONFIRMATION
    if confirmation is not None and not confirmation_matched:
        blockers.add("operator_confirmation_mismatch")
    ordered = _ordered(blockers)
    accepted = not ordered and confirmation_matched and write_requested
    status = (
        "accepted"
        if accepted
        else "ready_for_operator_review"
        if not ordered
        else "blocked"
    )
    input_hashes = (
        trace.get("input_sha256") if isinstance(trace.get("input_sha256"), dict) else {}
    )
    safe_hashes = {
        key: input_hashes.get(key)
        if _is_sha(input_hashes.get(key), allow_zero=True)
        else ZERO_SHA256
        for key in ("profile", "snapshot", "p9_trace", "p9_receipt")
    }
    decision_sha = (
        trace.get("decision_sha256")
        if _is_sha(trace.get("decision_sha256"), allow_zero=True)
        else ZERO_SHA256
    )
    scenario_sha = p9_replay.canonical_sha256(pack) if pack else ZERO_SHA256
    report_sha = (
        bundle.report.sha256 if bundle.report.status == "loaded" else ZERO_SHA256
    )
    confirmation_sha = (
        hashlib.sha256(EXACT_CONFIRMATION.encode()).hexdigest()
        if confirmation_matched
        else None
    )
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "receipt_id": "",
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
        "operational_status": data.get("operational_acceptance_status")
        if data.get("operational_acceptance_status")
        in {"operational_acceptance_blocked", "shadow_plan_ready_for_operator_review"}
        else "invalid",
        "scenario_pack_status": data.get("scenario_pack_status")
        if data.get("scenario_pack_status") in {"failed", "passed"}
        else "invalid",
        "fixture_only_validation_passed": data.get("fixture_only_validation_passed")
        is True,
        "operational_inputs_fixture": operational_inputs_fixture,
        "canonical_operational_paths": canonical_paths,
        "action": replay.ACTION,
        "decision_sha256": decision_sha,
        "input_sha256": safe_hashes,
        "scenario_pack_sha256": scenario_sha,
        "blockers": ordered,
        "acceptance_basis_sha256": "",
        "runtime_readiness_claimed": False,
        **{key: False for key in replay.FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }
    basis_sha = p9_replay.canonical_sha256(_acceptance_basis(receipt))
    receipt["receipt_id"] = f"equipment-shadow-acceptance-{basis_sha[:16]}"
    receipt["acceptance_basis_sha256"] = basis_sha
    if not _receipt_contract(receipt):
        raise ValueError("internal P10 receipt contract invalid")
    return receipt, bundle


def _write_atomic(path: Path, payload: dict[str, Any]) -> None:
    output = _validate_output(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        flags = (
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | int(getattr(os, "O_BINARY", 0))
            | int(getattr(os, "O_NOFOLLOW", 0))
        )
        descriptor = os.open(temporary, flags, 0o600)
        try:
            with os.fdopen(descriptor, "wb", closefd=False) as handle:
                handle.write(p9_replay.canonical_bytes(payload) + b"\n")
                handle.flush()
                os.fsync(handle.fileno())
        finally:
            os.close(descriptor)
        current = temporary.lstat()
        if stat.S_ISLNK(current.st_mode) or not stat.S_ISREG(current.st_mode):
            raise ValueError("temporary receipt identity invalid")
        _validate_output(path)
        temporary.replace(output)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def write_accepted_receipt(
    path: Path, *, paths: EvidencePaths, confirmation: str
) -> dict[str, Any]:
    if confirmation != EXACT_CONFIRMATION:
        raise ValueError("exact operator confirmation required")
    receipts: list[dict[str, Any]] = []
    bundles: list[EvidenceBundle] = []
    for _ in range(3):
        receipt, bundle = evaluate_acceptance(
            paths,
            confirmation=confirmation,
            write_requested=True,
            now_unix_ms=int(time.time() * 1000),
        )
        receipts.append(receipt)
        bundles.append(bundle)
    if any(receipt["status"] != "accepted" for receipt in receipts):
        return receipts[-1]
    if len({evidence_fingerprint(bundle) for bundle in bundles}) != 1:
        blocked, _ = evaluate_acceptance(
            paths,
            confirmation=confirmation,
            write_requested=False,
            extra_blockers=("evidence_changed_before_write",),
        )
        return blocked
    _write_atomic(path, receipts[-1])
    return receipts[-1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm")
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--json-out", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    paths = EvidencePaths()
    write_requested = args.confirm == EXACT_CONFIRMATION and not args.no_write
    try:
        receipt, _ = evaluate_acceptance(
            paths, confirmation=args.confirm, write_requested=write_requested
        )
        if receipt["status"] == "accepted":
            receipt = write_accepted_receipt(
                args.json_out, paths=paths, confirmation=args.confirm
            )
        if receipt["status"] != "accepted":
            print(json.dumps(receipt, indent=2, sort_keys=True))
        else:
            print(f"[equipment-shadow-acceptance] JSON: {args.json_out}")
            print("[equipment-shadow-acceptance] Status: accepted")
        return 0 if receipt["status"] == "accepted" else 1
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
