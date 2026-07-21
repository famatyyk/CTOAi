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
import time
import uuid
from pathlib import Path
from typing import Any, Iterable

if __package__:
    from . import otclient_conditions_shadow_acceptance as p9_acceptance
    from . import otclient_conditions_shadow_replay as p9_replay
else:  # pragma: no cover - direct script execution
    import otclient_conditions_shadow_acceptance as p9_acceptance
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
DEFAULT_OPERATIONAL_SNAPSHOT = DEFAULT_DEV_DIR / "equipment_shadow_snapshot.json"
DEFAULT_OPERATIONAL_P9_REPORT = DEFAULT_DEV_DIR / "conditions_shadow_replay.json"
DEFAULT_OPERATIONAL_P9_RECEIPT = DEFAULT_DEV_DIR / "conditions_shadow_acceptance.json"

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
OPERATIONAL_REPLAY_TRANSPORT_ALLOWANCE_MS = 2500
FALSE_FLAGS = (
    "dispatch_allowed",
    "runtime_actions",
    "executes_plan",
    "execute_once_allowed",
    "promotion_allowed",
)
P9_TRACE_KEYS = {
    "schema_version",
    "trace_id",
    "source",
    "evaluated_at_unix_ms",
    "mode",
    "action",
    "condition",
    "spell",
    "input_sha256",
    "canonical_input_sha256",
    "observation_age_ms",
    "p8_age_ms",
    "recovery_trace_age_ms",
    "recovery_age_ms",
    "status",
    "decision",
    "blockers",
    "decision_sha256",
    "operator_review_required",
    *FALSE_FLAGS,
    "intrusive_actions_performed",
}
P9_RECEIPT_KEYS = set(p9_acceptance.RECEIPT_KEYS)

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
    "snapshot_fixture_not_operational",
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
    "player_offline",
    "player_dead",
    "protection_zone_unknown",
    "protection_zone_untrusted",
    "candidate_zero",
    "rollback_wrong_id",
    "candidate_container_negative",
    "candidate_slot_zero",
    "rollback_slot_mismatch",
    "cooldown_unknown",
    "cooldown_untrusted",
    "retry_nonzero",
    "inventory_revision_zero",
    "rollback_revision_zero",
    "snapshot_extra_key",
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
        and _is_int(payload.get("retry_budget"))
        and payload.get("retry_budget") >= 0
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
            "producer_source",
            "source_report_sha256",
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
            "candidate_source_slot_index",
            "rollback_destination_container_id",
            "rollback_destination_slot_index",
            "cooldown",
            "cooldown_source",
            *FALSE_FLAGS,
            "intrusive_actions_performed",
        }
        and payload.get("schema_version") == SNAPSHOT_SCHEMA
        and _is_int(payload.get("observed_at_unix_ms"))
        and payload.get("observed_at_unix_ms") > 0
        and isinstance(payload.get("observation_id"), str)
        and payload.get("producer_source") in {"fixture", "otclient_guarded_adapter"}
        and _is_sha256(payload.get("source_report_sha256"))
        and isinstance(payload.get("online"), bool)
        and isinstance(payload.get("alive"), bool)
        and payload.get("protection_zone") in {"outside", "inside", "unknown"}
        and isinstance(payload.get("protection_zone_source"), str)
        and _is_sha256(payload.get("inventory_revision"))
        and isinstance(payload.get("inventory_unambiguous"), bool)
        and isinstance(payload.get("slot_name"), str)
        and isinstance(payload.get("rollback_slot_name"), str)
        and _is_sha256(payload.get("rollback_inventory_revision"))
        and _false_flags(payload)
        and _empty_ledger(payload)
    )


def _p9_trace_valid(payload: Any) -> bool:
    return (
        isinstance(payload, dict)
        and set(payload) == P9_TRACE_KEYS
        and payload.get("schema_version") == P9_TRACE_SCHEMA
        and payload.get("source") in {"fixture", "operational"}
        and payload.get("status") == "shadow_plan_ready"
        and payload.get("action") == "plan_paralyze_recovery"
        and payload.get("condition") == "paralyze"
        and payload.get("spell") == "exura"
        and payload.get("decision") == "would_plan_paralyze_recovery"
        and payload.get("blockers") == []
        and _is_sha256(payload.get("decision_sha256"))
        and _false_flags(payload)
        and _empty_ledger(payload)
    )


def _p9_receipt_structurally_valid(payload: Any) -> bool:
    return (
        isinstance(payload, dict)
        and p9_acceptance._receipt_contract_valid(payload)  # noqa: SLF001
        and set(payload) == P9_RECEIPT_KEYS
        and payload.get("schema_version") == P9_RECEIPT_SCHEMA
        and payload.get("status") in {"accepted", "blocked"}
        and isinstance(payload.get("acceptance_granted"), bool)
        and isinstance(payload.get("receipt_persisted"), bool)
        and isinstance(payload.get("operational_inputs_fixture"), bool)
        and payload.get("runtime_readiness_claimed") is False
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
        snapshot_age_limit = MAX_AGE_MS + (
            OPERATIONAL_REPLAY_TRANSPORT_ALLOWANCE_MS
            if source == "operational"
            else 0
        )
        if snapshot_age < 0:
            blockers.add("snapshot_future")
        elif snapshot_age > snapshot_age_limit:
            blockers.add("snapshot_stale")
        if (
            source == "operational"
            and snapshot_payload.get("producer_source") != "otclient_guarded_adapter"
        ):
            blockers.add("snapshot_fixture_not_operational")
        if snapshot_payload["online"] is not True:
            blockers.add("player_offline")
        if snapshot_payload["alive"] is not True:
            blockers.add("player_dead")
        if snapshot_payload["protection_zone"] == "inside":
            blockers.add("protection_zone_inside")
        elif snapshot_payload["protection_zone"] == "unknown":
            blockers.add("protection_zone_unknown")
        elif snapshot_payload["protection_zone_source"] not in {
            "player_method",
            "player_states",
        }:
            blockers.add("protection_zone_source_untrusted")
        if snapshot_payload["inventory_unambiguous"] is not True:
            blockers.add("inventory_ambiguous")
        if snapshot_payload["inventory_revision"] == "0" * 64:
            blockers.add("inventory_revision_missing")
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
        if (
            not _is_int(snapshot_payload["candidate_source_slot_index"])
            or snapshot_payload["candidate_source_slot_index"] <= 0
        ):
            blockers.add("candidate_container_invalid")
        if snapshot_payload.get(
            "candidate_source_container_id"
        ) != snapshot_payload.get("rollback_destination_container_id"):
            blockers.add("rollback_container_mismatch")
        if snapshot_payload.get("candidate_source_slot_index") != snapshot_payload.get(
            "rollback_destination_slot_index"
        ):
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
    if _snapshot_valid(snapshot_payload) and not ordered:
        plan = {
            "action": ACTION,
            "slot": "ring",
            "before_item_id": snapshot_payload["equipped_item_id"],
            "candidate_item_id": snapshot_payload["candidate_item_id"],
            "rollback_item_id": snapshot_payload["rollback_item_id"],
            "source_container_id": snapshot_payload["candidate_source_container_id"],
            "source_slot_index": snapshot_payload["candidate_source_slot_index"],
            "rollback_container_id": snapshot_payload[
                "rollback_destination_container_id"
            ],
            "rollback_slot_index": snapshot_payload["rollback_destination_slot_index"],
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


def _p9_trace_document(path: Path) -> p9_replay.InputDocument:
    """Read a direct P9 trace or extract the trace from the canonical replay report."""
    document = _read(path)
    payload = document.payload
    if document.status != "loaded" or not isinstance(payload, dict):
        return document
    if payload.get("schema_version") == P9_TRACE_SCHEMA:
        return document
    if payload.get("schema_version") != "ctoa.conditions-shadow-replay-report.v1":
        return p9_replay.document_from_payload(None, "malformed")
    trace = payload.get("operational_trace")
    if not isinstance(trace, dict):
        return p9_replay.document_from_payload(None, "malformed")
    return p9_replay.document_from_payload(trace)


def _operational_documents(
    *,
    profile_path: Path = DEFAULT_PROFILE,
    snapshot_path: Path = DEFAULT_OPERATIONAL_SNAPSHOT,
    p9_trace_path: Path = DEFAULT_OPERATIONAL_P9_REPORT,
    p9_receipt_path: Path = DEFAULT_OPERATIONAL_P9_RECEIPT,
) -> tuple[p9_replay.InputDocument, ...]:
    return (
        _read(profile_path),
        _read(snapshot_path),
        _p9_trace_document(p9_trace_path),
        _read(p9_receipt_path),
    )


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left.resolve(strict=False))) == os.path.normcase(
        str(right.resolve(strict=False))
    )


def _canonical_operational_paths(
    *,
    profile_path: Path,
    snapshot_path: Path,
    p9_trace_path: Path,
    p9_receipt_path: Path,
) -> bool:
    return all(
        _same_path(actual, expected)
        for actual, expected in (
            (profile_path, DEFAULT_PROFILE),
            (snapshot_path, DEFAULT_OPERATIONAL_SNAPSHOT),
            (p9_trace_path, DEFAULT_OPERATIONAL_P9_REPORT),
            (p9_receipt_path, DEFAULT_OPERATIONAL_P9_RECEIPT),
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
        snapshot.payload["inventory_revision"] = "3" * 64
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
        receipt.payload["operator_review_completed"] = False
        receipt.payload["receipt_persisted"] = False
        receipt.payload["status"] = "blocked"
        receipt.payload["blockers"] = ["operational_status_not_ready"]
        basis_sha = p9_replay.canonical_sha256(
            p9_acceptance._acceptance_basis(receipt.payload)  # noqa: SLF001
        )
        receipt.payload["acceptance_basis_sha256"] = basis_sha
        receipt.payload["receipt_id"] = f"conditions-shadow-acceptance-{basis_sha[:16]}"
    elif mutation == "p9_tampered":
        receipt.payload["decision_sha256"] = "c" * 64
        basis_sha = p9_replay.canonical_sha256(
            p9_acceptance._acceptance_basis(receipt.payload)  # noqa: SLF001
        )
        receipt.payload["acceptance_basis_sha256"] = basis_sha
        receipt.payload["receipt_id"] = f"conditions-shadow-acceptance-{basis_sha[:16]}"
    elif mutation == "unsafe_contract":
        snapshot.payload["runtime_actions"] = True
    elif mutation == "player_offline":
        snapshot.payload["online"] = False
    elif mutation == "player_dead":
        snapshot.payload["alive"] = False
    elif mutation == "protection_zone_unknown":
        snapshot.payload["protection_zone"] = "unknown"
    elif mutation == "protection_zone_untrusted":
        snapshot.payload["protection_zone_source"] = "fixture_guess"
    elif mutation == "candidate_zero":
        snapshot.payload["candidate_item_id"] = 0
    elif mutation == "rollback_wrong_id":
        snapshot.payload["rollback_item_id"] = snapshot.payload["equipped_item_id"] + 1
    elif mutation == "candidate_container_negative":
        snapshot.payload["candidate_source_container_id"] = -1
    elif mutation == "candidate_slot_zero":
        snapshot.payload["candidate_source_slot_index"] = 0
    elif mutation == "rollback_slot_mismatch":
        snapshot.payload["rollback_destination_slot_index"] += 1
    elif mutation == "cooldown_unknown":
        snapshot.payload["cooldown"] = "unknown"
    elif mutation == "cooldown_untrusted":
        snapshot.payload["cooldown_source"] = "fixture_guess"
    elif mutation == "retry_nonzero":
        profile.payload["retry_budget"] = 1
    elif mutation == "inventory_revision_zero":
        snapshot.payload["inventory_revision"] = "0" * 64
    elif mutation == "rollback_revision_zero":
        snapshot.payload["rollback_inventory_revision"] = "0" * 64
    elif mutation == "snapshot_extra_key":
        snapshot.payload["unexpected"] = True
    elif mutation != "none":
        raise ValueError(f"unsupported scenario mutation: {mutation}")
    return tuple(
        p9_replay.document_from_payload(doc.payload)
        for doc in (profile, snapshot, trace, receipt)
    )


def _scenario_pack_valid(payload: Any) -> bool:
    if not isinstance(payload, dict) or set(payload) != {
        "schema_version",
        "fixture_only",
        "operational_readiness_claimed",
        "evaluated_at_unix_ms",
        "scenarios",
    }:
        return False
    scenarios = payload.get("scenarios")
    if not (
        payload.get("schema_version") == SCENARIO_SCHEMA
        and payload.get("fixture_only") is True
        and payload.get("operational_readiness_claimed") is False
        and _is_int(payload.get("evaluated_at_unix_ms"))
        and payload["evaluated_at_unix_ms"] > 0
        and isinstance(scenarios, list)
        and 1 <= len(scenarios) <= 128
    ):
        return False
    seen: set[str] = set()
    seen_mutations: set[str] = set()
    for scenario in scenarios:
        if not isinstance(scenario, dict) or set(scenario) != {
            "name",
            "mutation",
            "expected_status",
            "expected_blockers",
        }:
            return False
        name = scenario.get("name")
        blockers = scenario.get("expected_blockers")
        if (
            not isinstance(name, str)
            or not name
            or name in seen
            or scenario.get("mutation") not in SCENARIO_MUTATIONS
            or scenario.get("mutation") in seen_mutations
            or scenario.get("expected_status")
            not in {"shadow_plan_ready", "operational_acceptance_blocked"}
            or not isinstance(blockers, list)
            or any(item not in BLOCKER_RANK for item in blockers)
            or blockers != _ordered(blockers)
            or len(blockers) != len(set(blockers))
        ):
            return False
        seen.add(name)
        seen_mutations.add(scenario["mutation"])
    return (
        len(scenarios) == len(SCENARIO_MUTATIONS)
        and seen_mutations == SCENARIO_MUTATIONS
    )


def run_scenario_pack(document: p9_replay.InputDocument) -> dict[str, Any]:
    payload = document.payload
    if document.status != "loaded" or not _scenario_pack_valid(payload):
        return {
            "status": "failed",
            "scenario_pack_sha256": document.sha256,
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
        "scenario_pack_sha256": document.sha256,
        "total_count": len(cases),
        "passed_count": passed_count,
        "failed_count": len(cases) - passed_count,
        "cases": cases,
        **{key: False for key in FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }


def build_report(
    *,
    evaluated_at_unix_ms: int,
    source: str = "operational",
    documents: tuple[p9_replay.InputDocument, ...] | None = None,
    scenario_pack_path: Path = DEFAULT_SCENARIO_PACK,
) -> dict[str, Any]:
    if documents is None:
        documents = (
            _fixture_documents() if source == "fixture" else _operational_documents()
        )
    trace = evaluate_shadow(
        profile=documents[0],
        snapshot=documents[1],
        p9_trace=documents[2],
        p9_receipt=documents[3],
        evaluated_at_unix_ms=evaluated_at_unix_ms,
        source=source,
    )
    scenario_pack = run_scenario_pack(_read(scenario_pack_path, MAX_SCENARIO_BYTES))
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
    absolute_parent = Path(os.path.abspath(path.parent))
    boundary = Path(os.path.abspath(RUNTIME_ROOT))
    try:
        relative_parent = absolute_parent.relative_to(boundary)
    except ValueError as exc:
        raise ValueError(f"JSON output must stay under {RUNTIME_ROOT}") from exc
    candidates = [boundary]
    current = boundary
    for part in relative_parent.parts:
        current /= part
        candidates.append(current)
    for candidate in candidates:
        try:
            metadata = candidate.lstat()
        except FileNotFoundError:
            continue
        reparse_flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
        if (
            stat.S_ISLNK(metadata.st_mode)
            or int(getattr(metadata, "st_file_attributes", 0)) & reparse_flag
        ):
            raise ValueError(
                "JSON output parent must not contain a symlink or reparse point"
            )
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
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
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
        metadata = temporary.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
            raise ValueError("temporary replay identity invalid")
        _validate_output(path)
        temporary.replace(path)
        persisted = p9_replay.read_document(path)
        if (
            persisted.status != "loaded"
            or persisted.sha256 != p9_replay.canonical_sha256(payload)
        ):
            raise ValueError("persisted replay verification failed")
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
    parser.add_argument("--profile", type=Path, default=None)
    parser.add_argument("--snapshot", type=Path, default=None)
    parser.add_argument("--p9-trace", type=Path, default=None)
    parser.add_argument("--p9-receipt", type=Path, default=None)
    parser.add_argument("--scenario-pack", type=Path, default=DEFAULT_SCENARIO_PACK)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--require-operational-acceptance",
        action="store_true",
        help="return non-zero unless the real operational trace is review-ready",
    )
    parser.add_argument("--evaluated-at-unix-ms", type=int, default=None)
    args = parser.parse_args(argv)
    if not _same_path(args.scenario_pack, DEFAULT_SCENARIO_PACK):
        parser.error("scenario pack must use the fixed tracked P10 fixture path")
    if args.source == "fixture":
        if not args.no_write:
            parser.error(
                "fixture mode is no-write only and cannot replace operational evidence"
            )
        if any(
            value is not None
            for value in (args.profile, args.snapshot, args.p9_trace, args.p9_receipt)
        ):
            parser.error("fixture mode uses only the bounded repository fixture pack")
        documents = _fixture_documents()
    else:
        if args.evaluated_at_unix_ms is not None:
            parser.error(
                "operational mode uses the current wall clock and forbids time overrides"
            )
        profile_path = args.profile or DEFAULT_PROFILE
        snapshot_path = args.snapshot or DEFAULT_OPERATIONAL_SNAPSHOT
        p9_trace_path = args.p9_trace or DEFAULT_OPERATIONAL_P9_REPORT
        p9_receipt_path = args.p9_receipt or DEFAULT_OPERATIONAL_P9_RECEIPT
        if not _canonical_operational_paths(
            profile_path=profile_path,
            snapshot_path=snapshot_path,
            p9_trace_path=p9_trace_path,
            p9_receipt_path=p9_receipt_path,
        ):
            parser.error(
                "operational mode requires the canonical confined evidence paths"
            )
        documents = _operational_documents(
            profile_path=profile_path,
            snapshot_path=snapshot_path,
            p9_trace_path=p9_trace_path,
            p9_receipt_path=p9_receipt_path,
        )
    observed_times = [
        doc.payload.get("observed_at_unix_ms", 1)
        for doc in documents
        if isinstance(doc.payload, dict)
        and _is_int(doc.payload.get("observed_at_unix_ms"))
    ]
    evaluated_at = (
        args.evaluated_at_unix_ms
        or (max(observed_times) + 1000 if observed_times else int(time.time() * 1000))
        if args.source == "fixture"
        else int(time.time() * 1000)
    )
    report = build_report(
        evaluated_at_unix_ms=evaluated_at,
        source=args.source,
        documents=documents,
        scenario_pack_path=args.scenario_pack,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    if not args.no_write:
        _write_atomic(args.json_out, report)
        print(f"P10 Equipment shadow replay: {report['operational_acceptance_status']}")
    fixture_ok = report["scenario_pack_status"] == "passed"
    operational_ok = (
        report["operational_acceptance_status"]
        == "shadow_plan_ready_for_operator_review"
    )
    if args.source == "operational" or args.require_operational_acceptance:
        return 0 if fixture_ok and operational_ok else 1
    return 0 if fixture_ok else 1


if __name__ == "__main__":
    sys.exit(main())
