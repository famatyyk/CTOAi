#!/usr/bin/env python3
"""Replay the P10 Equipment lane without touching an OTClient installation.

The replay is deliberately data-only.  It validates one ring-only plan, its
rollback snapshot, and a bound P9 trace/receipt.  A successful fixture replay
never authorizes inventory movement, item use, dispatch, or promotion.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any, Iterable

if __package__:
    from . import otclient_conditions_shadow_replay as p9_replay
else:  # pragma: no cover - direct script execution
    import otclient_conditions_shadow_replay as p9_replay


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ROOT = ROOT / "runtime"
DEFAULT_DEV_DIR = RUNTIME_ROOT / "solteria_helper_dev"
DEFAULT_PROFILE = ROOT / "config" / "otclient" / "equipment-shadow-profile.json"
DEFAULT_SNAPSHOT = (
    ROOT
    / "tests"
    / "fixtures"
    / "otclient_equipment_shadow_replay"
    / "positive-snapshot.json"
)
DEFAULT_P9_TRACE = (
    ROOT
    / "tests"
    / "fixtures"
    / "otclient_equipment_shadow_replay"
    / "positive-p9-trace.json"
)
DEFAULT_P9_RECEIPT = (
    ROOT
    / "tests"
    / "fixtures"
    / "otclient_equipment_shadow_replay"
    / "positive-p9-receipt.json"
)
DEFAULT_SCENARIO_PACK = (
    ROOT / "tests" / "fixtures" / "otclient_equipment_shadow_replay" / "scenarios.json"
)
DEFAULT_OUTPUT = DEFAULT_DEV_DIR / "equipment_shadow_replay.json"

PROFILE_SCHEMA = "ctoa.equipment-shadow-profile.v1"
SNAPSHOT_SCHEMA = "ctoa.equipment-shadow-snapshot.v1"
TRACE_SCHEMA = "ctoa.equipment-shadow-trace.v1"
REPORT_SCHEMA = "ctoa.equipment-shadow-replay-report.v1"
SCENARIO_SCHEMA = "ctoa.equipment-shadow-scenario-pack.v1"
P9_TRACE_SCHEMA = "ctoa.conditions-shadow-trace.v1"
P9_RECEIPT_SCHEMA = "ctoa.conditions-shadow-acceptance.v1"

MAX_INPUT_BYTES = 128 * 1024
MAX_SCENARIO_BYTES = 256 * 1024
MAX_AGE_MS = 6000
FALSE_FLAGS = (
    "dispatch_allowed",
    "runtime_actions",
    "executes_plan",
    "execute_once_allowed",
    "promotion_allowed",
)

ACTION = "plan_ring_swap"
BLOCKER_ORDER = (
    "profile_missing",
    "profile_malformed",
    "profile_duplicate_keys",
    "profile_oversize",
    "profile_symlink_rejected",
    "profile_not_regular",
    "profile_schema_invalid",
    "snapshot_missing",
    "snapshot_malformed",
    "snapshot_duplicate_keys",
    "snapshot_oversize",
    "snapshot_symlink_rejected",
    "snapshot_not_regular",
    "snapshot_schema_invalid",
    "snapshot_future",
    "snapshot_stale",
    "player_offline",
    "player_dead",
    "protection_zone_inside",
    "protection_zone_unknown",
    "protection_zone_source_untrusted",
    "inventory_ambiguous",
    "inventory_revision_missing",
    "inventory_revision_drift",
    "ring_slot_missing",
    "ring_slot_mismatch",
    "equipped_item_id_invalid",
    "candidate_item_id_invalid",
    "candidate_matches_equipped",
    "rollback_item_id_invalid",
    "rollback_snapshot_mismatch",
    "candidate_container_invalid",
    "rollback_container_mismatch",
    "cooldown_active",
    "cooldown_unknown",
    "cooldown_source_untrusted",
    "retry_budget_nonzero",
    "p9_trace_missing",
    "p9_trace_malformed",
    "p9_trace_schema_invalid",
    "p9_trace_blocked",
    "p9_trace_action_mismatch",
    "p9_trace_hash_mismatch",
    "p9_receipt_missing",
    "p9_receipt_malformed",
    "p9_receipt_schema_invalid",
    "p9_receipt_not_granted",
    "p9_receipt_trace_mismatch",
    "p9_fixture_not_operational",
    "unsafe_contract",
)
BLOCKER_RANK = {name: index for index, name in enumerate(BLOCKER_ORDER)}
SCENARIO_MUTATIONS = {
    "none",
    "inventory_ambiguous",
    "revision_drift",
    "missing_ring",
    "wrong_equipped_id",
    "wrong_candidate_id",
    "missing_rollback",
    "wrong_container",
    "stale_snapshot",
    "future_snapshot",
    "protection_zone",
    "cooldown_active",
    "p9_blocked",
    "p9_tampered",
    "unsafe_contract",
}


def _false_flags(payload: dict[str, Any]) -> bool:
    return all(payload.get(key) is False for key in FALSE_FLAGS)


def _empty_ledger(payload: dict[str, Any]) -> bool:
    return payload.get("intrusive_actions_performed") == []


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(c in "0123456789abcdef" for c in value)
    )


def _ordered(values: Iterable[str]) -> list[str]:
    return sorted(set(values), key=BLOCKER_RANK.__getitem__)


def _read(path: Path, max_bytes: int = MAX_INPUT_BYTES) -> p9_replay.InputDocument:
    return p9_replay.read_document(path, max_bytes)


def _profile_valid(payload: Any) -> bool:
    return (
        isinstance(payload, dict)
        and set(payload)
        == {
            "schema_version",
            "mode",
            "action",
            "slot",
            "max_observation_age_ms",
            "cooldown_required",
            "retry_budget",
            "requires_p9_acceptance",
            "exact_item_ids",
            "rollback_required",
            *FALSE_FLAGS,
        }
        and payload.get("schema_version") == PROFILE_SCHEMA
        and payload.get("mode") == "shadow_only"
        and payload.get("action") == ACTION
        and payload.get("slot") == "ring"
        and payload.get("max_observation_age_ms") == MAX_AGE_MS
        and payload.get("cooldown_required") == "ready"
        and payload.get("retry_budget") == 0
        and payload.get("requires_p9_acceptance") is True
        and payload.get("exact_item_ids") is True
        and payload.get("rollback_required") is True
        and _false_flags(payload)
    )


def _snapshot_valid(payload: Any) -> bool:
    return (
        isinstance(payload, dict)
        and set(payload)
        == {
            "schema_version",
            "observed_at_unix_ms",
            "observation_id",
            "online",
            "alive",
            "protection_zone",
            "protection_zone_source",
            "inventory_revision",
            "inventory_unambiguous",
            "slot_name",
            "rollback_slot_name",
            "equipped_item_id",
            "candidate_item_id",
            "rollback_item_id",
            "rollback_inventory_revision",
            "candidate_source_container_id",
            "rollback_destination_container_id",
            "cooldown",
            "cooldown_source",
            *FALSE_FLAGS,
            "intrusive_actions_performed",
        }
        and payload.get("schema_version") == SNAPSHOT_SCHEMA
        and _is_int(payload.get("observed_at_unix_ms"))
        and payload.get("observed_at_unix_ms") > 0
        and isinstance(payload.get("observation_id"), str)
        and payload.get("online") is True
        and payload.get("alive") is True
        and payload.get("protection_zone") in {"outside", "inside", "unknown"}
        and isinstance(payload.get("protection_zone_source"), str)
        and isinstance(payload.get("inventory_revision"), str)
        and payload.get("inventory_revision") != ""
        and isinstance(payload.get("inventory_unambiguous"), bool)
        and isinstance(payload.get("slot_name"), str)
        and isinstance(payload.get("rollback_slot_name"), str)
        and isinstance(payload.get("rollback_inventory_revision"), str)
        and payload.get("rollback_inventory_revision") != ""
        and _false_flags(payload)
        and _empty_ledger(payload)
    )


def _p9_trace_valid(payload: Any) -> bool:
    return (
        isinstance(payload, dict)
        and payload.get("schema_version") == P9_TRACE_SCHEMA
        and payload.get("status") == "shadow_plan_ready"
        and payload.get("action") == "plan_paralyze_recovery"
        and payload.get("decision") == "would_plan_paralyze_recovery"
        and payload.get("blockers") == []
        and _is_sha256(payload.get("decision_sha256"))
        and _false_flags(payload)
        and _empty_ledger(payload)
    )


def _p9_receipt_structurally_valid(payload: Any) -> bool:
    required = {
        "schema_version",
        "status",
        "acceptance_granted",
        "receipt_persisted",
        "decision_sha256",
        "operational_inputs_fixture",
        "runtime_readiness_claimed",
        *FALSE_FLAGS,
        "intrusive_actions_performed",
    }
    return (
        isinstance(payload, dict)
        and required <= set(payload)
        and payload.get("schema_version") == P9_RECEIPT_SCHEMA
        and _is_sha256(payload.get("decision_sha256"))
        and _false_flags(payload)
        and _empty_ledger(payload)
    )


def _p9_receipt_valid(payload: Any) -> bool:
    return (
        _p9_receipt_structurally_valid(payload)
        and payload.get("status") == "accepted"
        and payload.get("acceptance_granted") is True
        and payload.get("receipt_persisted") is True
    )


def evaluate_shadow(
    *,
    profile: p9_replay.InputDocument,
    snapshot: p9_replay.InputDocument,
    p9_trace: p9_replay.InputDocument,
    p9_receipt: p9_replay.InputDocument,
    evaluated_at_unix_ms: int,
    source: str,
) -> dict[str, Any]:
    blockers: set[str] = set()
    profile_payload, snapshot_payload = profile.payload, snapshot.payload
    trace_payload, receipt_payload = p9_trace.payload, p9_receipt.payload
    if profile.status != "loaded":
        blockers.add(f"profile_{profile.status}")
    elif not _profile_valid(profile_payload):
        blockers.add("profile_schema_invalid")
    if snapshot.status != "loaded":
        blockers.add(f"snapshot_{snapshot.status}")
    elif not _snapshot_valid(snapshot_payload):
        blockers.add("snapshot_schema_invalid")
    if p9_trace.status != "loaded":
        blockers.add(
            "p9_trace_missing" if p9_trace.status == "missing" else "p9_trace_malformed"
        )
    elif not _p9_trace_valid(trace_payload):
        blockers.add("p9_trace_schema_invalid")
    if p9_receipt.status != "loaded":
        blockers.add(
            "p9_receipt_missing"
            if p9_receipt.status == "missing"
            else "p9_receipt_malformed"
        )
    elif not _p9_receipt_structurally_valid(receipt_payload):
        blockers.add("p9_receipt_schema_invalid")

    snapshot_age = None
    if _snapshot_valid(snapshot_payload):
        snapshot_age = evaluated_at_unix_ms - snapshot_payload["observed_at_unix_ms"]
        if snapshot_age < 0:
            blockers.add("snapshot_future")
        elif snapshot_age > MAX_AGE_MS:
            blockers.add("snapshot_stale")
        if snapshot_payload["online"] is not True:
            blockers.add("player_offline")
        if snapshot_payload["alive"] is not True:
            blockers.add("player_dead")
        if snapshot_payload["protection_zone"] == "inside":
            blockers.add("protection_zone_inside")
        elif snapshot_payload["protection_zone"] == "unknown":
            blockers.add("protection_zone_unknown")
        elif snapshot_payload["protection_zone_source"] != "player_method":
            blockers.add("protection_zone_source_untrusted")
        if snapshot_payload["inventory_unambiguous"] is not True:
            blockers.add("inventory_ambiguous")
        if (
            snapshot_payload["slot_name"].lower() != "ring"
            or snapshot_payload["rollback_slot_name"].lower() != "ring"
        ):
            blockers.add("ring_slot_mismatch")
        for key in ("equipped_item_id", "candidate_item_id", "rollback_item_id"):
            value = snapshot_payload[key]
            if not _is_int(value) or value <= 0 or value > 65535:
                blockers.add(f"{key}_invalid")
        if snapshot_payload.get("equipped_item_id") == snapshot_payload.get(
            "candidate_item_id"
        ):
            blockers.add("candidate_matches_equipped")
        if snapshot_payload.get("rollback_item_id") != snapshot_payload.get(
            "equipped_item_id"
        ):
            blockers.add("rollback_snapshot_mismatch")
        for key in (
            "candidate_source_container_id",
            "rollback_destination_container_id",
        ):
            if not _is_int(snapshot_payload[key]) or snapshot_payload[key] < 0:
                blockers.add("candidate_container_invalid")
        if snapshot_payload.get(
            "candidate_source_container_id"
        ) != snapshot_payload.get("rollback_destination_container_id"):
            blockers.add("rollback_container_mismatch")
        if snapshot_payload.get("inventory_revision") != snapshot_payload.get(
            "rollback_inventory_revision"
        ):
            blockers.add("inventory_revision_drift")
        if snapshot_payload["cooldown"] == "active":
            blockers.add("cooldown_active")
        elif snapshot_payload["cooldown"] == "unknown":
            blockers.add("cooldown_unknown")
        elif snapshot_payload["cooldown_source"] != "game_cooldown_group":
            blockers.add("cooldown_source_untrusted")
    if _profile_valid(profile_payload) and profile_payload["retry_budget"] != 0:
        blockers.add("retry_budget_nonzero")
    if _p9_trace_valid(trace_payload) and _p9_receipt_structurally_valid(
        receipt_payload
    ):
        if receipt_payload["decision_sha256"] != trace_payload["decision_sha256"]:
            blockers.add("p9_receipt_trace_mismatch")
        if not _p9_receipt_valid(receipt_payload):
            blockers.add("p9_receipt_not_granted")
        if (
            source == "operational"
            and receipt_payload.get("operational_inputs_fixture") is True
        ):
            blockers.add("p9_fixture_not_operational")
        if trace_payload.get("source") != "operational" and source == "operational":
            blockers.add("p9_fixture_not_operational")
    else:
        if p9_trace.status == "loaded" and not _p9_trace_valid(trace_payload):
            blockers.add("p9_trace_blocked")
        if p9_receipt.status == "loaded" and not _p9_receipt_structurally_valid(
            receipt_payload
        ):
            blockers.add("p9_receipt_not_granted")
    unsafe = any(
        not _false_flags(payload)
        for payload in (
            profile_payload,
            snapshot_payload,
            trace_payload,
            receipt_payload,
        )
        if isinstance(payload, dict)
    )
    unsafe = unsafe or any(
        not _empty_ledger(payload)
        for payload in (snapshot_payload, trace_payload, receipt_payload)
        if isinstance(payload, dict)
    )
    if unsafe:
        blockers.add("unsafe_contract")
    ordered = _ordered(blockers)
    status = "shadow_plan_ready" if not ordered else "operational_acceptance_blocked"
    input_hashes = {
        "profile": profile.sha256,
        "snapshot": snapshot.sha256,
        "p9_trace": p9_trace.sha256,
        "p9_receipt": p9_receipt.sha256,
    }
    canonical_input_sha = p9_replay.canonical_sha256(
        {
            "schema_version": "ctoa.equipment-shadow-input.v1",
            "evaluated_at_unix_ms": evaluated_at_unix_ms,
            "input_sha256": input_hashes,
        }
    )
    plan = None
    if _snapshot_valid(snapshot_payload):
        plan = {
            "action": ACTION,
            "slot": "ring",
            "before_item_id": snapshot_payload["equipped_item_id"],
            "candidate_item_id": snapshot_payload["candidate_item_id"],
            "rollback_item_id": snapshot_payload["rollback_item_id"],
            "source_container_id": snapshot_payload["candidate_source_container_id"],
            "rollback_container_id": snapshot_payload[
                "rollback_destination_container_id"
            ],
            "inventory_revision": snapshot_payload["inventory_revision"],
            "rollback_inventory_revision": snapshot_payload[
                "rollback_inventory_revision"
            ],
            "retry_budget": 0,
            "dispatch_allowed": False,
        }
    basis = {
        "schema_version": TRACE_SCHEMA,
        "status": status,
        "decision": "would_plan_ring_swap" if not ordered else "hold",
        "action": ACTION,
        "blockers": ordered,
        "canonical_input_sha256": canonical_input_sha,
        "plan": plan,
        "rollback_simulation": "ready" if not ordered else "blocked",
        **{key: False for key in FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }
    decision_sha = p9_replay.canonical_sha256(basis)
    return {
        **basis,
        "trace_id": f"equipment-shadow-{decision_sha[:16]}",
        "source": source,
        "evaluated_at_unix_ms": evaluated_at_unix_ms,
        "input_sha256": input_hashes,
        "decision_sha256": decision_sha,
        "observation_age_ms": snapshot_age,
        "operator_review_required": True,
    }


def _fixture_documents() -> tuple[p9_replay.InputDocument, ...]:
    return tuple(
        _read(path)
        for path in (
            DEFAULT_PROFILE,
            DEFAULT_SNAPSHOT,
            DEFAULT_P9_TRACE,
            DEFAULT_P9_RECEIPT,
        )
    )


def _scenario_documents(
    mutation: str, evaluated_at: int
) -> tuple[p9_replay.InputDocument, ...]:
    docs = [
        p9_replay.document_from_payload(copy.deepcopy(doc.payload))
        for doc in _fixture_documents()
    ]
    profile, snapshot, trace, receipt = docs
    assert (
        snapshot.payload is not None
        and trace.payload is not None
        and receipt.payload is not None
    )
    if mutation == "inventory_ambiguous":
        snapshot.payload["inventory_unambiguous"] = False
    elif mutation == "revision_drift":
        snapshot.payload["inventory_revision"] = "inventory-r2"
    elif mutation == "missing_ring":
        snapshot.payload["slot_name"] = "amulet"
    elif mutation == "wrong_equipped_id":
        snapshot.payload["equipped_item_id"] = 0
    elif mutation == "wrong_candidate_id":
        snapshot.payload["candidate_item_id"] = snapshot.payload["equipped_item_id"]
    elif mutation == "missing_rollback":
        snapshot.payload["rollback_item_id"] = 0
    elif mutation == "wrong_container":
        snapshot.payload["rollback_destination_container_id"] = 3
    elif mutation == "stale_snapshot":
        snapshot.payload["observed_at_unix_ms"] = evaluated_at - MAX_AGE_MS - 1
    elif mutation == "future_snapshot":
        snapshot.payload["observed_at_unix_ms"] = evaluated_at + 1
    elif mutation == "protection_zone":
        snapshot.payload["protection_zone"] = "inside"
    elif mutation == "cooldown_active":
        snapshot.payload["cooldown"] = "active"
    elif mutation == "p9_blocked":
        receipt.payload["acceptance_granted"] = False
        receipt.payload["status"] = "blocked"
    elif mutation == "p9_tampered":
        receipt.payload["decision_sha256"] = "0" * 64
    elif mutation == "unsafe_contract":
        snapshot.payload["runtime_actions"] = True
    elif mutation != "none":
        raise ValueError(f"unsupported scenario mutation: {mutation}")
    return tuple(
        p9_replay.document_from_payload(doc.payload)
        for doc in (profile, snapshot, trace, receipt)
    )


def run_scenario_pack(document: p9_replay.InputDocument) -> dict[str, Any]:
    payload = document.payload
    if (
        document.status != "loaded"
        or not isinstance(payload, dict)
        or payload.get("schema_version") != SCENARIO_SCHEMA
        or payload.get("fixture_only") is not True
    ):
        return {
            "status": "failed",
            "total_count": 0,
            "passed_count": 0,
            "failed_count": 1,
            "cases": [],
            **{key: False for key in FALSE_FLAGS},
            "intrusive_actions_performed": [],
        }
    cases = []
    evaluated_at = payload["evaluated_at_unix_ms"]
    for scenario in payload["scenarios"]:
        docs = _scenario_documents(scenario["mutation"], evaluated_at)
        first = evaluate_shadow(
            profile=docs[0],
            snapshot=docs[1],
            p9_trace=docs[2],
            p9_receipt=docs[3],
            evaluated_at_unix_ms=evaluated_at,
            source="fixture",
        )
        second = evaluate_shadow(
            profile=docs[0],
            snapshot=docs[1],
            p9_trace=docs[2],
            p9_receipt=docs[3],
            evaluated_at_unix_ms=evaluated_at,
            source="fixture",
        )
        deterministic = (
            first["decision_sha256"] == second["decision_sha256"]
            and first["blockers"] == second["blockers"]
        )
        passed = (
            deterministic
            and first["status"] == scenario["expected_status"]
            and first["blockers"] == scenario["expected_blockers"]
            and _false_flags(first)
            and _empty_ledger(first)
        )
        cases.append(
            {
                "name": scenario["name"],
                "mutation": scenario["mutation"],
                "expected_status": scenario["expected_status"],
                "actual_status": first["status"],
                "expected_blockers": scenario["expected_blockers"],
                "blockers": first["blockers"],
                "decision_sha256": first["decision_sha256"],
                "deterministic": deterministic,
                "passed": passed,
                **{key: False for key in FALSE_FLAGS},
                "intrusive_actions_performed": [],
            }
        )
    passed_count = sum(case["passed"] is True for case in cases)
    return {
        "status": "passed" if passed_count == len(cases) else "failed",
        "total_count": len(cases),
        "passed_count": passed_count,
        "failed_count": len(cases) - passed_count,
        "cases": cases,
        **{key: False for key in FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }


def build_report(
    *, evaluated_at_unix_ms: int, source: str = "operational"
) -> dict[str, Any]:
    documents = _fixture_documents()
    trace = evaluate_shadow(
        profile=documents[0],
        snapshot=documents[1],
        p9_trace=documents[2],
        p9_receipt=documents[3],
        evaluated_at_unix_ms=evaluated_at_unix_ms,
        source=source,
    )
    scenario_pack = run_scenario_pack(_read(DEFAULT_SCENARIO_PACK, MAX_SCENARIO_BYTES))
    status = (
        "shadow_plan_ready_for_operator_review"
        if trace["status"] == "shadow_plan_ready"
        and scenario_pack["status"] == "passed"
        else "operational_acceptance_blocked"
    )
    return {
        "schema_version": REPORT_SCHEMA,
        "generated_at_unix_ms": evaluated_at_unix_ms,
        "mode": "offline_equipment_shadow_replay",
        "operational_acceptance_status": status,
        "scenario_pack_status": scenario_pack["status"],
        "fixture_only_validation_passed": scenario_pack["status"] == "passed",
        "runtime_readiness_claimed": False,
        "operational_trace": trace,
        "scenario_pack": scenario_pack,
        **{key: False for key in FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }


def _validate_output(path: Path) -> Path:
    if os.path.normcase(str(path.resolve(strict=False))) != os.path.normcase(
        str(DEFAULT_OUTPUT.resolve(strict=False))
    ):
        raise ValueError(f"JSON output must equal {DEFAULT_OUTPUT}")
    if not path.resolve(strict=False).is_relative_to(
        RUNTIME_ROOT.resolve(strict=False)
    ):
        raise ValueError(f"JSON output must stay under {RUNTIME_ROOT}")
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return path
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise ValueError("JSON output must be a regular non-symlink file")
    return path


def _write_atomic(path: Path, payload: dict[str, Any]) -> None:
    _validate_output(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        temporary.replace(path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="print the report without writing runtime evidence",
    )
    parser.add_argument(
        "--source", choices=("operational", "fixture"), default="operational"
    )
    parser.add_argument("--evaluated-at-unix-ms", type=int, default=None)
    args = parser.parse_args(argv)
    evaluated_at = (
        args.evaluated_at_unix_ms
        or max(
            doc.payload.get("observed_at_unix_ms", 1)
            for doc in _fixture_documents()
            if isinstance(doc.payload, dict)
        )
        + 1000
    )
    report = build_report(evaluated_at_unix_ms=evaluated_at, source=args.source)
    print(json.dumps(report, indent=2, sort_keys=True))
    if not args.no_write:
        _write_atomic(DEFAULT_OUTPUT, report)
        print(f"P10 Equipment shadow replay: {report['operational_acceptance_status']}")
    return 0 if report["scenario_pack_status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
