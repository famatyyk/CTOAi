#!/usr/bin/env python3
"""Run the P11 Heal Friend fixture pack without casting or writing evidence.

This slice is deliberately fixture-only.  It validates one exact synthetic
whitelist identity and cryptographically binds complete synthetic P9/P10
reports and receipts.  It has no operational paths, producer, acceptance
receipt, Control Center surface, or runtime output.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

if __package__:
    from . import otclient_conditions_shadow_acceptance as p9_acceptance
    from . import otclient_conditions_shadow_replay as p9
    from . import otclient_equipment_shadow_acceptance as p10_acceptance
    from . import otclient_equipment_shadow_replay as p10
else:  # pragma: no cover
    import otclient_conditions_shadow_acceptance as p9_acceptance
    import otclient_conditions_shadow_replay as p9
    import otclient_equipment_shadow_acceptance as p10_acceptance
    import otclient_equipment_shadow_replay as p10


ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "otclient_heal_friend_shadow_replay"
PROFILE_PATH = FIXTURE_DIR / "positive-profile.json"
OBSERVATION_PATH = FIXTURE_DIR / "positive-observation.json"
SCENARIO_PATH = FIXTURE_DIR / "scenarios.json"
P10_FIXTURE_DIR = ROOT / "tests" / "fixtures" / "otclient_equipment_shadow_replay"

PROFILE_SCHEMA = "ctoa.heal-friend-shadow-profile.v1"
OBSERVATION_SCHEMA = "ctoa.heal-friend-observation.v1"
TRACE_SCHEMA = "ctoa.heal-friend-shadow-trace.v1"
SCENARIO_SCHEMA = "ctoa.heal-friend-shadow-scenario-pack.v1"
REPORT_SCHEMA = "ctoa.heal-friend-shadow-replay-report.v1"
MODE = "offline_heal_friend_shadow_replay"
ACTION = "plan_sio"
SPELL = "exura sio"
ZERO_SHA256 = "0" * 64
MAX_INPUT_BYTES = 64 * 1024
MAX_SCENARIO_BYTES = 128 * 1024

FALSE_FLAGS = (
    "dispatch_allowed",
    "runtime_actions",
    "executes_plan",
    "execute_once_allowed",
    "promotion_allowed",
    "casts",
    "talks",
)

PROFILE_KEYS = {
    "schema_version",
    "mode",
    "action",
    "spell",
    "selection_policy",
    "whitelist",
    "whitelist_revision",
    "hp_threshold",
    "max_range",
    "max_observation_age_ms",
    "max_party_age_ms",
    "cooldown_required",
    "retry_budget",
    "requires_p9_acceptance",
    "requires_p10_acceptance",
    "require_party_membership",
    "prohibit_self",
    "require_visible",
    "require_same_floor",
    *FALSE_FLAGS,
}
OBSERVATION_KEYS = {
    "schema_version",
    "observation_id",
    "observed_at_unix_ms",
    "party_observed_at_unix_ms",
    "producer_source",
    "online",
    "alive",
    "protection_zone",
    "protection_zone_source",
    "self_id",
    "target_id",
    "observed_target_id",
    "current_target_id",
    "target_name",
    "observed_target_name",
    "current_target_name",
    "whitelist_revision",
    "party_member_ids",
    "target_is_player",
    "target_is_self",
    "target_visible",
    "target_same_floor",
    "distance",
    "observed_target_hp_percent",
    "current_target_hp_percent",
    "cooldown",
    "cooldown_source",
    *FALSE_FLAGS,
    "intrusive_actions_performed",
}

BLOCKER_ORDER = (
    "profile_missing",
    "profile_malformed",
    "profile_duplicate_keys",
    "profile_oversize",
    "profile_symlink_rejected",
    "profile_not_regular",
    "profile_schema_invalid",
    "observation_missing",
    "observation_malformed",
    "observation_duplicate_keys",
    "observation_oversize",
    "observation_symlink_rejected",
    "observation_not_regular",
    "observation_schema_invalid",
    "p9_report_invalid",
    "p9_report_not_ready",
    "p9_receipt_invalid",
    "p9_receipt_report_mismatch",
    "p10_report_invalid",
    "p10_report_not_ready",
    "p10_receipt_invalid",
    "p10_receipt_report_mismatch",
    "p10_predecessor_mismatch",
    "profile_action_mismatch",
    "profile_spell_mismatch",
    "profile_selection_policy_invalid",
    "profile_single_target_required",
    "profile_whitelist_revision_mismatch",
    "profile_retry_budget_nonzero",
    "profile_unsafe_contract",
    "fixture_source_required",
    "observation_future",
    "observation_stale",
    "party_observation_future",
    "party_observation_stale",
    "player_offline",
    "player_online_unknown",
    "player_dead",
    "player_life_unknown",
    "protection_zone_inside",
    "protection_zone_unknown",
    "protection_zone_source_untrusted",
    "self_identity_invalid",
    "target_id_invalid",
    "target_is_self",
    "target_not_player",
    "target_identity_mismatch",
    "target_name_not_whitelisted",
    "observation_whitelist_revision_mismatch",
    "party_membership_missing",
    "target_not_visible",
    "target_different_floor",
    "target_out_of_range",
    "target_hp_invalid",
    "target_hp_changed",
    "target_above_threshold",
    "cooldown_active",
    "cooldown_unknown",
    "cooldown_source_untrusted",
    "observation_unsafe_contract",
    "unsafe_contract",
)
BLOCKER_RANK = {name: index for index, name in enumerate(BLOCKER_ORDER)}

MUTATIONS = {
    "none",
    "profile_wrong_action",
    "profile_ranking",
    "profile_multi_target",
    "profile_revision",
    "profile_retry",
    "profile_unsafe",
    "observation_stale",
    "party_stale",
    "observation_future",
    "player_offline",
    "player_dead",
    "protection_zone",
    "target_is_self",
    "target_id_changed",
    "target_name_changed",
    "observation_revision",
    "target_not_party",
    "target_not_player",
    "target_invisible",
    "target_different_floor",
    "target_out_of_range",
    "target_hp_changed",
    "target_above_threshold",
    "cooldown_active",
    "cooldown_unknown",
    "observation_unsafe",
    "p9_report_blocked",
    "p9_receipt_tampered",
    "p10_report_blocked",
    "p10_receipt_tampered",
    "profile_wrong_spell",
    "profile_empty_whitelist",
    "profile_range_invalid",
    "profile_threshold_invalid",
    "fixture_source_invalid",
    "party_future",
    "player_online_unknown",
    "player_life_unknown",
    "protection_zone_unknown",
    "protection_zone_untrusted",
    "self_id_invalid",
    "target_id_invalid",
    "target_not_whitelisted",
    "party_duplicate",
    "target_hp_invalid",
    "cooldown_untrusted",
    "observation_ledger",
    "observation_extra",
    "observation_noncanonical_name",
    "p9_report_fixture_source",
    "p10_report_fixture_source",
    "p9_receipt_binding_tamper",
    "p10_receipt_input_tamper",
    "p10_predecessor_swap",
}


@dataclass(frozen=True)
class FixtureDocuments:
    profile: p9.InputDocument
    observation: p9.InputDocument
    p9_report: p9.InputDocument
    p9_receipt: p9.InputDocument
    p10_report: p9.InputDocument
    p10_receipt: p9.InputDocument


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_sha(value: Any, *, nonzero: bool = True) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
        and (not nonzero or value != ZERO_SHA256)
    )


def _false_flags(value: Any) -> bool:
    return isinstance(value, dict) and all(
        value.get(key) is False for key in FALSE_FLAGS
    )


def _ordered(values: Iterable[str]) -> list[str]:
    unknown = set(values) - set(BLOCKER_RANK)
    if unknown:
        raise ValueError(f"unknown P11 blockers: {sorted(unknown)}")
    return sorted(set(values), key=BLOCKER_RANK.__getitem__)


def _normalize_name(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _load_blocker(prefix: str, status: str) -> str:
    suffix = {
        "missing": "missing",
        "malformed": "malformed",
        "duplicate_keys": "duplicate_keys",
        "oversize": "oversize",
        "symlink_rejected": "symlink_rejected",
        "not_regular": "not_regular",
    }.get(status, "schema_invalid")
    return f"{prefix}_{suffix}"


def _read_fixture(path: Path, expected: Path, max_bytes: int) -> p9.InputDocument:
    """Read only one fixed tracked fixture and reject reparse ancestors."""

    if os.path.normcase(str(path.resolve(strict=False))) != os.path.normcase(
        str(expected.resolve(strict=False))
    ):
        return p9.InputDocument(None, "unreadable", ZERO_SHA256)
    root = ROOT.resolve(strict=False)
    current = root
    try:
        relative = Path(os.path.abspath(path)).relative_to(Path(os.path.abspath(root)))
    except ValueError:
        return p9.InputDocument(None, "unreadable", ZERO_SHA256)
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
    for part in relative.parts:
        current /= part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            break
        if (
            stat.S_ISLNK(metadata.st_mode)
            or int(getattr(metadata, "st_file_attributes", 0)) & reparse
        ):
            return p9.InputDocument(None, "symlink_rejected", ZERO_SHA256)
    return p9.read_document(path, max_bytes)


def _profile_valid(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) != PROFILE_KEYS:
        return False
    whitelist = value.get("whitelist")
    return bool(
        value.get("schema_version") == PROFILE_SCHEMA
        and value.get("mode") == "shadow_only"
        and isinstance(value.get("action"), str)
        and isinstance(value.get("spell"), str)
        and isinstance(value.get("selection_policy"), str)
        and isinstance(whitelist, list)
        and len(whitelist) <= 16
        and all(
            isinstance(item, dict)
            and set(item) == {"target_id", "target_name"}
            and _is_int(item.get("target_id"))
            and item["target_id"] > 0
            and isinstance(item.get("target_name"), str)
            and item["target_name"] == _normalize_name(item["target_name"])
            and bool(item["target_name"])
            for item in whitelist
        )
        and _is_sha(value.get("whitelist_revision"), nonzero=True)
        and _is_int(value.get("hp_threshold"))
        and 1 <= value["hp_threshold"] <= 100
        and value.get("max_range") == 7
        and value.get("max_observation_age_ms") == 6000
        and value.get("max_party_age_ms") == 6000
        and value.get("cooldown_required") == "ready"
        and _is_int(value.get("retry_budget"))
        and all(
            isinstance(value.get(key), bool)
            for key in (
                "requires_p9_acceptance",
                "requires_p10_acceptance",
                "require_party_membership",
                "prohibit_self",
                "require_visible",
                "require_same_floor",
                *FALSE_FLAGS,
            )
        )
    )


def _observation_valid(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) != OBSERVATION_KEYS:
        return False
    party = value.get("party_member_ids")
    return bool(
        value.get("schema_version") == OBSERVATION_SCHEMA
        and isinstance(value.get("observation_id"), str)
        and 0 < len(value["observation_id"]) <= 64
        and _is_int(value.get("observed_at_unix_ms"))
        and _is_int(value.get("party_observed_at_unix_ms"))
        and value.get("producer_source") in {"fixture", "otclient_guarded_adapter"}
        and value.get("online") in {"online", "offline", "unknown"}
        and value.get("alive") in {"alive", "dead", "unknown"}
        and value.get("protection_zone") in {"outside", "inside", "unknown"}
        and value.get("protection_zone_source")
        in {"player_method", "player_states", "unavailable"}
        and all(
            _is_int(value.get(key))
            for key in (
                "self_id",
                "target_id",
                "observed_target_id",
                "current_target_id",
                "distance",
                "observed_target_hp_percent",
                "current_target_hp_percent",
            )
        )
        and all(
            isinstance(value.get(key), str)
            and value[key] == _normalize_name(value[key])
            and bool(value[key])
            for key in ("target_name", "observed_target_name", "current_target_name")
        )
        and _is_sha(value.get("whitelist_revision"), nonzero=True)
        and isinstance(party, list)
        and len(party) <= 64
        and all(_is_int(item) for item in party)
        and len(set(party)) == len(party)
        and all(
            isinstance(value.get(key), bool)
            for key in (
                "target_is_player",
                "target_is_self",
                "target_visible",
                "target_same_floor",
                *FALSE_FLAGS,
            )
        )
        and value.get("cooldown") in {"ready", "active", "unknown"}
        and value.get("cooldown_source") in {"game_cooldown_group", "unavailable"}
        and isinstance(value.get("intrusive_actions_performed"), list)
    )


def _seal_recovery_trace(payload: dict[str, Any]) -> None:
    payload["trace_id"] = ""
    basis = {key: value for key, value in payload.items() if key != "trace_id"}
    payload["trace_id"] = f"recovery-shadow-{p9.canonical_sha256(basis)[:16]}"


def _seal_recovery_proof(payload: dict[str, Any]) -> None:
    payload["proof_id"] = ""
    basis = {key: value for key, value in payload.items() if key != "proof_id"}
    payload["proof_id"] = f"conditions-recovery-{p9.canonical_sha256(basis)[:16]}"


def _build_p9_fixture(evaluated_at: int) -> tuple[dict[str, Any], dict[str, Any]]:
    profile, observation, proof, recovery_trace, recovery_proof = (
        p9._fixture_documents()
    )  # noqa: SLF001
    assert all(
        item.payload is not None
        for item in (profile, observation, proof, recovery_trace, recovery_proof)
    )
    obs_payload = copy.deepcopy(observation.payload)
    obs_payload["producer_source"] = "otclient_guarded_adapter"
    obs_payload["observed_at_unix_ms"] = evaluated_at - 1000
    obs = p9.document_from_payload(obs_payload)
    proof_payload = copy.deepcopy(proof.payload)
    proof_payload["source"] = "background_no_screen"
    proof_payload["observed_at_unix_ms"] = evaluated_at - 1000
    proof_payload["conditions_observation_sha256"] = obs.sha256
    p8 = p9.document_from_payload(proof_payload)
    trace_payload = copy.deepcopy(recovery_trace.payload)
    trace_payload["source"] = "recovery_shadow"
    trace_payload["observed_at_unix_ms"] = evaluated_at - 1000
    _seal_recovery_trace(trace_payload)
    trace = p9.document_from_payload(trace_payload)
    recovery_payload = copy.deepcopy(recovery_proof.payload)
    recovery_payload.update(
        {
            "source": "recovery_shadow",
            "observed_at_unix_ms": evaluated_at - 1000,
            "recovery_trace_sha256": trace.sha256,
            "profile_sha256": profile.sha256,
            "observation_sha256": obs.sha256,
            "p8_proof_sha256": p8.sha256,
        }
    )
    _seal_recovery_proof(recovery_payload)
    recovery = p9.document_from_payload(recovery_payload)
    report = p9.build_report(
        profile_document=profile,
        raw_p8_document=p8,
        recovery_trace_document=trace,
        recovery_proof_document=recovery,
        scenario_document=p9.read_document(
            p9.DEFAULT_SCENARIO_PACK, p9.MAX_SCENARIO_BYTES
        ),
        evaluated_at_unix_ms=evaluated_at,
        explicit_observation_document=obs,
    )
    receipt_document = _read_fixture(
        P10_FIXTURE_DIR / "positive-p9-receipt.json",
        P10_FIXTURE_DIR / "positive-p9-receipt.json",
        MAX_INPUT_BYTES,
    )
    if not isinstance(receipt_document.payload, dict):
        raise ValueError("P9 fixture receipt unavailable")
    receipt = copy.deepcopy(receipt_document.payload)
    trace_out = report["operational_trace"]
    pack = report["scenario_pack"]
    report_sha = p9.canonical_sha256(report)
    receipt.update(
        {
            "created_at_unix_ms": evaluated_at,
            "report_sha256": report_sha,
            "recomputed_report_sha256": report_sha,
            "report_generated_at_unix_ms": report["generated_at_unix_ms"],
            "report_age_ms": evaluated_at - report["generated_at_unix_ms"],
            "canonical_input_sha256": trace_out["canonical_input_sha256"],
            "decision_sha256": trace_out["decision_sha256"],
            "input_sha256": copy.deepcopy(trace_out["input_sha256"]),
            "scenario_pack_sha256": pack["scenario_pack_sha256"],
            "operational_inputs_fixture": False,
        }
    )
    basis_sha = p9.canonical_sha256(p9_acceptance._acceptance_basis(receipt))  # noqa: SLF001
    receipt["acceptance_basis_sha256"] = basis_sha
    receipt["receipt_id"] = f"conditions-shadow-acceptance-{basis_sha[:16]}"
    if not p9_acceptance._receipt_contract_valid(receipt):  # noqa: SLF001
        raise ValueError("internal P9 fixture receipt invalid")
    return report, receipt


def _build_p10_fixture(
    evaluated_at: int, p9_report: dict[str, Any], p9_receipt: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    snapshot_document = _read_fixture(
        P10_FIXTURE_DIR / "positive-snapshot.json",
        P10_FIXTURE_DIR / "positive-snapshot.json",
        MAX_INPUT_BYTES,
    )
    if not isinstance(snapshot_document.payload, dict):
        raise ValueError("P10 fixture snapshot unavailable")
    snapshot_payload = copy.deepcopy(snapshot_document.payload)
    snapshot_payload["producer_source"] = "otclient_guarded_adapter"
    snapshot_payload["observed_at_unix_ms"] = evaluated_at - 1000
    documents = (
        p9.read_document(p10.DEFAULT_PROFILE),
        p9.document_from_payload(snapshot_payload),
        p9.document_from_payload(copy.deepcopy(p9_report["operational_trace"])),
        p9.document_from_payload(copy.deepcopy(p9_receipt)),
    )
    report = p10.build_report(
        evaluated_at_unix_ms=evaluated_at,
        source="operational",
        documents=documents,
        scenario_pack_path=p10.DEFAULT_SCENARIO_PACK,
    )
    trace = report["operational_trace"]
    pack = report["scenario_pack"]
    report_sha = p9.canonical_sha256(report)
    confirmation_sha = hashlib.sha256(
        p10_acceptance.EXACT_CONFIRMATION.encode()
    ).hexdigest()
    receipt: dict[str, Any] = {
        "schema_version": p10_acceptance.SCHEMA_VERSION,
        "receipt_id": "",
        "created_at_unix_ms": evaluated_at,
        "mode": p10_acceptance.MODE,
        "status": "accepted",
        "acceptance_granted": True,
        "operator_review_completed": True,
        "downstream_use_requires_separate_review": True,
        "confirmation_required": True,
        "confirmation_matched": True,
        "confirmation_sha256": confirmation_sha,
        "receipt_persisted": True,
        "report_sha256": report_sha,
        "recomputed_report_sha256": report_sha,
        "report_generated_at_unix_ms": report["generated_at_unix_ms"],
        "report_age_ms": evaluated_at - report["generated_at_unix_ms"],
        "operational_status": report["operational_acceptance_status"],
        "scenario_pack_status": report["scenario_pack_status"],
        "fixture_only_validation_passed": report["fixture_only_validation_passed"],
        "operational_inputs_fixture": False,
        "canonical_operational_paths": True,
        "action": p10.ACTION,
        "decision_sha256": trace["decision_sha256"],
        "input_sha256": copy.deepcopy(trace["input_sha256"]),
        "scenario_pack_sha256": p9.canonical_sha256(pack),
        "blockers": [],
        "acceptance_basis_sha256": "",
        "runtime_readiness_claimed": False,
        **{key: False for key in p10.FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }
    basis_sha = p9.canonical_sha256(p10_acceptance._acceptance_basis(receipt))  # noqa: SLF001
    receipt["acceptance_basis_sha256"] = basis_sha
    receipt["receipt_id"] = f"equipment-shadow-acceptance-{basis_sha[:16]}"
    if not p10_acceptance._receipt_contract(receipt):  # noqa: SLF001
        raise ValueError("internal P10 fixture receipt invalid")
    return report, receipt


def fixture_documents(evaluated_at: int) -> FixtureDocuments:
    p9_report, p9_receipt = _build_p9_fixture(evaluated_at)
    p10_report, p10_receipt = _build_p10_fixture(evaluated_at, p9_report, p9_receipt)
    return FixtureDocuments(
        profile=_read_fixture(PROFILE_PATH, PROFILE_PATH, MAX_INPUT_BYTES),
        observation=_read_fixture(OBSERVATION_PATH, OBSERVATION_PATH, MAX_INPUT_BYTES),
        p9_report=p9.document_from_payload(p9_report),
        p9_receipt=p9.document_from_payload(p9_receipt),
        p10_report=p9.document_from_payload(p10_report),
        p10_receipt=p9.document_from_payload(p10_receipt),
    )


def _validate_p9(
    report_doc: p9.InputDocument, receipt_doc: p9.InputDocument, blockers: set[str]
) -> None:
    report = report_doc.payload
    receipt = receipt_doc.payload
    if (
        report_doc.status != "loaded"
        or not isinstance(report, dict)
        or not p9_acceptance._report_no_action_contract(report)
    ):  # noqa: SLF001
        blockers.add("p9_report_invalid")
    elif not (
        report.get("operational_acceptance_status")
        == "shadow_plan_ready_for_operator_review"
        and isinstance(report.get("operational_trace"), dict)
        and report["operational_trace"].get("source") == "operational"
        and report["operational_trace"].get("status") == "shadow_plan_ready"
        and report["operational_trace"].get("blockers") == []
        and report.get("scenario_pack_status") == "passed"
    ):
        blockers.add("p9_report_not_ready")
    if (
        receipt_doc.status != "loaded"
        or not isinstance(receipt, dict)
        or not p9_acceptance._receipt_contract_valid(receipt)
    ):  # noqa: SLF001
        blockers.add("p9_receipt_invalid")
        return
    if not (
        receipt.get("status") == "accepted"
        and receipt.get("acceptance_granted") is True
        and receipt.get("receipt_persisted") is True
        and receipt.get("operational_inputs_fixture") is False
    ):
        blockers.add("p9_receipt_invalid")
    if not isinstance(report, dict) or not (
        receipt.get("report_sha256") == report_doc.sha256
        and receipt.get("recomputed_report_sha256") == report_doc.sha256
        and receipt.get("decision_sha256")
        == (report.get("operational_trace") or {}).get("decision_sha256")
        and receipt.get("input_sha256")
        == (report.get("operational_trace") or {}).get("input_sha256")
        and receipt.get("scenario_pack_sha256")
        == ((report.get("scenario_pack") or {}).get("scenario_pack_sha256"))
    ):
        blockers.add("p9_receipt_report_mismatch")


def _validate_p10(docs: FixtureDocuments, blockers: set[str]) -> None:
    report, receipt = docs.p10_report.payload, docs.p10_receipt.payload
    if (
        docs.p10_report.status != "loaded"
        or not isinstance(report, dict)
        or not p10_acceptance._report_no_action(report)
    ):  # noqa: SLF001
        blockers.add("p10_report_invalid")
    elif not (
        report.get("operational_acceptance_status")
        == "shadow_plan_ready_for_operator_review"
        and isinstance(report.get("operational_trace"), dict)
        and report["operational_trace"].get("source") == "operational"
        and report["operational_trace"].get("status") == "shadow_plan_ready"
        and report["operational_trace"].get("blockers") == []
        and report["operational_trace"].get("rollback_simulation") == "ready"
        and report.get("scenario_pack_status") == "passed"
    ):
        blockers.add("p10_report_not_ready")
    if (
        docs.p10_receipt.status != "loaded"
        or not isinstance(receipt, dict)
        or not p10_acceptance._receipt_contract(receipt)
    ):  # noqa: SLF001
        blockers.add("p10_receipt_invalid")
        return
    if not (
        receipt.get("status") == "accepted"
        and receipt.get("acceptance_granted") is True
        and receipt.get("receipt_persisted") is True
        and receipt.get("operational_inputs_fixture") is False
    ):
        blockers.add("p10_receipt_invalid")
    if not isinstance(report, dict) or not (
        receipt.get("report_sha256") == docs.p10_report.sha256
        and receipt.get("recomputed_report_sha256") == docs.p10_report.sha256
        and receipt.get("decision_sha256")
        == (report.get("operational_trace") or {}).get("decision_sha256")
        and receipt.get("input_sha256")
        == (report.get("operational_trace") or {}).get("input_sha256")
        and receipt.get("scenario_pack_sha256")
        == p9.canonical_sha256(report.get("scenario_pack"))
    ):
        blockers.add("p10_receipt_report_mismatch")
    trace_inputs = (report.get("operational_trace") or {}).get("input_sha256") or {}
    p9_trace = (docs.p9_report.payload or {}).get("operational_trace") or {}
    if not (
        trace_inputs.get("p9_trace") == p9.canonical_sha256(p9_trace)
        and trace_inputs.get("p9_receipt") == docs.p9_receipt.sha256
    ):
        blockers.add("p10_predecessor_mismatch")


def evaluate_shadow(
    docs: FixtureDocuments, evaluated_at: int, *, source: str = "fixture"
) -> dict[str, Any]:
    if source not in {"fixture", "operational"}:
        raise ValueError("P11 source must be fixture or operational")
    blockers: set[str] = set()
    profile, observation = docs.profile.payload, docs.observation.payload
    if docs.profile.status != "loaded":
        blockers.add(_load_blocker("profile", docs.profile.status))
    elif not _profile_valid(profile):
        blockers.add("profile_schema_invalid")
    if docs.observation.status != "loaded":
        blockers.add(_load_blocker("observation", docs.observation.status))
    elif not _observation_valid(observation):
        blockers.add("observation_schema_invalid")
    _validate_p9(docs.p9_report, docs.p9_receipt, blockers)
    _validate_p10(docs, blockers)

    if _profile_valid(profile):
        assert isinstance(profile, dict)
        if profile["action"] != ACTION:
            blockers.add("profile_action_mismatch")
        if profile["spell"] != SPELL:
            blockers.add("profile_spell_mismatch")
        if profile["selection_policy"] != "single_exact_target":
            blockers.add("profile_selection_policy_invalid")
        if len(profile["whitelist"]) != 1:
            blockers.add("profile_single_target_required")
        if profile["whitelist_revision"] != p9.canonical_sha256(profile["whitelist"]):
            blockers.add("profile_whitelist_revision_mismatch")
        if profile["retry_budget"] != 0:
            blockers.add("profile_retry_budget_nonzero")
        if not all(
            profile.get(key) is True
            for key in (
                "requires_p9_acceptance",
                "requires_p10_acceptance",
                "require_party_membership",
                "prohibit_self",
                "require_visible",
                "require_same_floor",
            )
        ) or not _false_flags(profile):
            blockers.add("profile_unsafe_contract")

    observation_age = None
    party_age = None
    if _observation_valid(observation):
        assert isinstance(observation, dict)
        observation_age = evaluated_at - observation["observed_at_unix_ms"]
        party_age = evaluated_at - observation["party_observed_at_unix_ms"]
        expected_producer = (
            "fixture" if source == "fixture" else "otclient_guarded_adapter"
        )
        if observation["producer_source"] != expected_producer:
            blockers.add("fixture_source_required")
        if observation_age < 0:
            blockers.add("observation_future")
        elif observation_age > 6000:
            blockers.add("observation_stale")
        if party_age < 0:
            blockers.add("party_observation_future")
        elif party_age > 6000:
            blockers.add("party_observation_stale")
        if observation["online"] == "offline":
            blockers.add("player_offline")
        elif observation["online"] != "online":
            blockers.add("player_online_unknown")
        if observation["alive"] == "dead":
            blockers.add("player_dead")
        elif observation["alive"] != "alive":
            blockers.add("player_life_unknown")
        if observation["protection_zone"] == "inside":
            blockers.add("protection_zone_inside")
        elif observation["protection_zone"] != "outside":
            blockers.add("protection_zone_unknown")
        elif observation["protection_zone_source"] not in {
            "player_method",
            "player_states",
        }:
            blockers.add("protection_zone_source_untrusted")
        if observation["self_id"] <= 0:
            blockers.add("self_identity_invalid")
        if observation["target_id"] <= 0:
            blockers.add("target_id_invalid")
        if (
            observation["target_is_self"]
            or observation["self_id"] == observation["target_id"]
        ):
            blockers.add("target_is_self")
        if not observation["target_is_player"]:
            blockers.add("target_not_player")
        exact_ids = {
            observation["target_id"],
            observation["observed_target_id"],
            observation["current_target_id"],
        }
        exact_names = {
            observation["target_name"],
            observation["observed_target_name"],
            observation["current_target_name"],
        }
        if len(exact_ids) != 1 or len(exact_names) != 1:
            blockers.add("target_identity_mismatch")
        if _profile_valid(profile):
            assert isinstance(profile, dict)
            target = profile["whitelist"][0] if len(profile["whitelist"]) == 1 else None
            if target is not None and (
                observation["target_id"] != target.get("target_id")
                or observation["target_name"] != target.get("target_name")
            ):
                blockers.add("target_name_not_whitelisted")
            if observation["whitelist_revision"] != profile["whitelist_revision"]:
                blockers.add("observation_whitelist_revision_mismatch")
        if observation["target_id"] not in observation["party_member_ids"]:
            blockers.add("party_membership_missing")
        if not observation["target_visible"]:
            blockers.add("target_not_visible")
        if not observation["target_same_floor"]:
            blockers.add("target_different_floor")
        max_range = profile.get("max_range", 7) if isinstance(profile, dict) else 7
        if observation["distance"] > max_range:
            blockers.add("target_out_of_range")
        hp = observation["current_target_hp_percent"]
        observed_hp = observation["observed_target_hp_percent"]
        if not (1 <= hp <= 100 and 1 <= observed_hp <= 100):
            blockers.add("target_hp_invalid")
        elif hp != observed_hp:
            blockers.add("target_hp_changed")
        threshold = profile["hp_threshold"] if _profile_valid(profile) else 100
        if hp > threshold:
            blockers.add("target_above_threshold")
        if observation["cooldown"] == "active":
            blockers.add("cooldown_active")
        elif observation["cooldown"] != "ready":
            blockers.add("cooldown_unknown")
        elif observation["cooldown_source"] != "game_cooldown_group":
            blockers.add("cooldown_source_untrusted")
        if (
            not _false_flags(observation)
            or observation.get("intrusive_actions_performed") != []
        ):
            blockers.add("observation_unsafe_contract")

    if any(
        not _false_flags(item.payload)
        for item in (docs.profile, docs.observation)
        if isinstance(item.payload, dict)
    ):
        blockers.add("unsafe_contract")
    ordered = _ordered(blockers)
    ready = not ordered
    input_hashes = {
        "profile": docs.profile.sha256,
        "observation": docs.observation.sha256,
        "p9_report": docs.p9_report.sha256,
        "p9_receipt": docs.p9_receipt.sha256,
        "p10_report": docs.p10_report.sha256,
        "p10_receipt": docs.p10_receipt.sha256,
    }
    canonical_input = p9.canonical_sha256(
        {
            "schema_version": "ctoa.heal-friend-shadow-input.v1",
            "evaluated_at_unix_ms": evaluated_at,
            "input_sha256": input_hashes,
        }
    )
    plan = None
    if ready and isinstance(profile, dict) and isinstance(observation, dict):
        plan = {
            "action": ACTION,
            "spell": SPELL,
            "target_id": observation["target_id"],
            "target_name": observation["target_name"],
            "whitelist_revision": profile["whitelist_revision"],
            "hp_percent": observation["current_target_hp_percent"],
            "hp_threshold": profile["hp_threshold"],
            "distance": observation["distance"],
            "max_range": profile["max_range"],
            "dispatch_allowed": False,
            "runtime_actions": False,
            "casts": False,
            "talks": False,
            "retry_budget": 0,
        }
    basis = {
        "schema_version": TRACE_SCHEMA,
        "source": source,
        "evaluated_at_unix_ms": evaluated_at,
        "mode": "shadow_only",
        "status": "shadow_plan_ready" if ready else "operational_acceptance_blocked",
        "decision": "would_plan_sio" if ready else "hold",
        "action": ACTION,
        "spell": SPELL,
        "input_sha256": input_hashes,
        "canonical_input_sha256": canonical_input,
        "observation_age_ms": observation_age,
        "party_observation_age_ms": party_age,
        "blockers": ordered,
        "plan": plan,
        "fixture_validation_only": source == "fixture",
        "operational_readiness_claimed": False,
        "operator_review_required": source == "operational",
        **{key: False for key in FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }
    decision_sha = p9.canonical_sha256(basis)
    return {
        **basis,
        "trace_id": f"heal-friend-shadow-{decision_sha[:16]}",
        "decision_sha256": decision_sha,
    }


def _mutate_documents(
    base: FixtureDocuments, mutation: str, evaluated_at: int
) -> FixtureDocuments:
    values = [
        copy.deepcopy(item.payload)
        for item in (
            base.profile,
            base.observation,
            base.p9_report,
            base.p9_receipt,
            base.p10_report,
            base.p10_receipt,
        )
    ]
    profile, observation, p9_report, p9_receipt, p10_report, p10_receipt = values
    assert all(isinstance(item, dict) for item in values)
    if mutation == "profile_wrong_action":
        profile["action"] = "plan_heal"
    elif mutation == "profile_ranking":
        profile["selection_policy"] = "lowest_hp"
    elif mutation == "profile_multi_target":
        profile["whitelist"].append(
            {"target_id": 515151, "target_name": "other fixture"}
        )
    elif mutation == "profile_revision":
        profile["whitelist_revision"] = "b" * 64
    elif mutation == "profile_retry":
        profile["retry_budget"] = 1
    elif mutation == "profile_unsafe":
        profile["runtime_actions"] = True
    elif mutation == "observation_stale":
        observation["observed_at_unix_ms"] = evaluated_at - 6001
    elif mutation == "party_stale":
        observation["party_observed_at_unix_ms"] = evaluated_at - 6001
    elif mutation == "observation_future":
        observation["observed_at_unix_ms"] = evaluated_at + 1
    elif mutation == "player_offline":
        observation["online"] = "offline"
    elif mutation == "player_dead":
        observation["alive"] = "dead"
    elif mutation == "protection_zone":
        observation["protection_zone"] = "inside"
    elif mutation == "target_is_self":
        observation["target_is_self"] = True
    elif mutation == "target_id_changed":
        observation["current_target_id"] = 424243
    elif mutation == "target_name_changed":
        observation["current_target_name"] = "spoofed ally"
    elif mutation == "observation_revision":
        observation["whitelist_revision"] = "b" * 64
    elif mutation == "target_not_party":
        observation["party_member_ids"] = []
    elif mutation == "target_not_player":
        observation["target_is_player"] = False
    elif mutation == "target_invisible":
        observation["target_visible"] = False
    elif mutation == "target_different_floor":
        observation["target_same_floor"] = False
    elif mutation == "target_out_of_range":
        observation["distance"] = 8
    elif mutation == "target_hp_changed":
        observation["current_target_hp_percent"] = 41
    elif mutation == "target_above_threshold":
        observation["observed_target_hp_percent"] = observation[
            "current_target_hp_percent"
        ] = 71
    elif mutation == "cooldown_active":
        observation["cooldown"] = "active"
    elif mutation == "cooldown_unknown":
        observation["cooldown"] = "unknown"
    elif mutation == "observation_unsafe":
        observation["casts"] = True
    elif mutation == "p9_report_blocked":
        p9_report["operational_acceptance_status"] = "operational_acceptance_blocked"
    elif mutation == "p9_receipt_tampered":
        p9_receipt["receipt_id"] = "conditions-shadow-acceptance-0000000000000000"
    elif mutation == "p10_report_blocked":
        p10_report["operational_acceptance_status"] = "operational_acceptance_blocked"
    elif mutation == "p10_receipt_tampered":
        p10_receipt["receipt_id"] = "equipment-shadow-acceptance-0000000000000000"
    elif mutation == "profile_wrong_spell":
        profile["spell"] = "exura gran sio"
    elif mutation == "profile_empty_whitelist":
        profile["whitelist"] = []
    elif mutation == "profile_range_invalid":
        profile["max_range"] = 8
    elif mutation == "profile_threshold_invalid":
        profile["hp_threshold"] = 0
    elif mutation == "fixture_source_invalid":
        observation["producer_source"] = "otclient_guarded_adapter"
    elif mutation == "party_future":
        observation["party_observed_at_unix_ms"] = evaluated_at + 1
    elif mutation == "player_online_unknown":
        observation["online"] = "unknown"
    elif mutation == "player_life_unknown":
        observation["alive"] = "unknown"
    elif mutation == "protection_zone_unknown":
        observation["protection_zone"] = "unknown"
    elif mutation == "protection_zone_untrusted":
        observation["protection_zone_source"] = "unavailable"
    elif mutation == "self_id_invalid":
        observation["self_id"] = 0
    elif mutation == "target_id_invalid":
        observation["target_id"] = observation["observed_target_id"] = observation[
            "current_target_id"
        ] = 0
    elif mutation == "target_not_whitelisted":
        observation["target_id"] = observation["observed_target_id"] = observation[
            "current_target_id"
        ] = 515151
        observation["target_name"] = observation["observed_target_name"] = observation[
            "current_target_name"
        ] = "other fixture"
        observation["party_member_ids"] = [515151]
    elif mutation == "party_duplicate":
        observation["party_member_ids"] = [424242, 424242]
    elif mutation == "target_hp_invalid":
        observation["observed_target_hp_percent"] = observation[
            "current_target_hp_percent"
        ] = 0
    elif mutation == "cooldown_untrusted":
        observation["cooldown_source"] = "unavailable"
    elif mutation == "observation_ledger":
        observation["intrusive_actions_performed"] = ["cast"]
    elif mutation == "observation_extra":
        observation["unexpected"] = False
    elif mutation == "observation_noncanonical_name":
        observation["target_name"] = "fixture ally "
    elif mutation == "p9_report_fixture_source":
        p9_report["operational_trace"]["source"] = "fixture"
    elif mutation == "p10_report_fixture_source":
        p10_report["operational_trace"]["source"] = "fixture"
    elif mutation == "p9_receipt_binding_tamper":
        p9_receipt["report_sha256"] = p9_receipt["recomputed_report_sha256"] = "c" * 64
        basis_sha = p9.canonical_sha256(p9_acceptance._acceptance_basis(p9_receipt))  # noqa: SLF001
        p9_receipt["acceptance_basis_sha256"] = basis_sha
        p9_receipt["receipt_id"] = f"conditions-shadow-acceptance-{basis_sha[:16]}"
    elif mutation == "p10_receipt_input_tamper":
        p10_receipt["input_sha256"]["profile"] = "c" * 64
        basis_sha = p9.canonical_sha256(p10_acceptance._acceptance_basis(p10_receipt))  # noqa: SLF001
        p10_receipt["acceptance_basis_sha256"] = basis_sha
        p10_receipt["receipt_id"] = f"equipment-shadow-acceptance-{basis_sha[:16]}"
    elif mutation == "p10_predecessor_swap":
        p10_report["operational_trace"]["input_sha256"]["p9_receipt"] = "c" * 64
    elif mutation != "none":
        raise ValueError(f"unknown mutation: {mutation}")
    return FixtureDocuments(*(p9.document_from_payload(item) for item in values))


def run_scenario_pack(document: p9.InputDocument) -> dict[str, Any]:
    payload = document.payload
    valid = bool(
        document.status == "loaded"
        and isinstance(payload, dict)
        and set(payload)
        == {
            "schema_version",
            "fixture_only",
            "operational_readiness_claimed",
            "evaluated_at_unix_ms",
            "scenarios",
        }
        and payload.get("schema_version") == SCENARIO_SCHEMA
        and payload.get("fixture_only") is True
        and payload.get("operational_readiness_claimed") is False
        and _is_int(payload.get("evaluated_at_unix_ms"))
        and payload["evaluated_at_unix_ms"] > 0
        and isinstance(payload.get("scenarios"), list)
        and len(payload["scenarios"]) == len(MUTATIONS)
    )
    if not valid:
        return _failed_report(0, document.sha256)
    names: set[str] = set()
    mutations: set[str] = set()
    for scenario in payload["scenarios"]:
        if not (
            isinstance(scenario, dict)
            and set(scenario)
            == {"name", "mutation", "expected_status", "expected_blockers"}
            and isinstance(scenario.get("name"), str)
            and scenario["name"] not in names
            and scenario.get("mutation") in MUTATIONS
            and scenario["mutation"] not in mutations
            and scenario.get("expected_status")
            in {"shadow_plan_ready", "operational_acceptance_blocked"}
            and isinstance(scenario.get("expected_blockers"), list)
            and scenario["expected_blockers"] == _ordered(scenario["expected_blockers"])
        ):
            return _failed_report(0, document.sha256)
        names.add(scenario["name"])
        mutations.add(scenario["mutation"])
    if mutations != MUTATIONS:
        return _failed_report(0, document.sha256)
    evaluated_at = payload["evaluated_at_unix_ms"]
    base = fixture_documents(evaluated_at)
    cases = []
    for scenario in payload["scenarios"]:
        docs = _mutate_documents(base, scenario["mutation"], evaluated_at)
        first = evaluate_shadow(docs, evaluated_at)
        second = evaluate_shadow(docs, evaluated_at)
        deterministic = first == second
        passed = (
            deterministic
            and first["status"] == scenario["expected_status"]
            and first["blockers"] == scenario["expected_blockers"]
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
    failed = sum(case["passed"] is not True for case in cases)
    reference_trace = evaluate_shadow(base, evaluated_at)
    return {
        "schema_version": REPORT_SCHEMA,
        "generated_at_unix_ms": evaluated_at,
        "mode": MODE,
        "source": "fixture",
        "status": "passed" if failed == 0 else "failed",
        "fixture_only": True,
        "operational_acceptance_status": "not_evaluated",
        "operational_producer_present": False,
        "acceptance_receipt_written": False,
        "operational_readiness_claimed": False,
        "runtime_readiness_claimed": False,
        "scenario_pack_status": "passed" if failed == 0 else "failed",
        "fixture_only_validation_passed": failed == 0,
        "scenario_pack_sha256": document.sha256,
        "total_count": len(cases),
        "passed_count": len(cases) - failed,
        "failed_count": failed,
        "reference_trace": reference_trace,
        "cases": cases,
        **{key: False for key in FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }


def _failed_report(total: int, scenario_sha: str) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA,
        "generated_at_unix_ms": 1,
        "mode": MODE,
        "source": "fixture",
        "status": "failed",
        "fixture_only": True,
        "operational_acceptance_status": "not_evaluated",
        "operational_producer_present": False,
        "acceptance_receipt_written": False,
        "operational_readiness_claimed": False,
        "runtime_readiness_claimed": False,
        "scenario_pack_status": "failed",
        "fixture_only_validation_passed": False,
        "scenario_pack_sha256": scenario_sha,
        "total_count": total,
        "passed_count": 0,
        "failed_count": max(1, total),
        "reference_trace": None,
        "cases": [],
        **{key: False for key in FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--evaluated-at-unix-ms", type=int, default=None)
    args = parser.parse_args(argv)
    if not args.no_write:
        parser.error("P11 fixture replay requires --no-write")
    scenario = _read_fixture(SCENARIO_PATH, SCENARIO_PATH, MAX_SCENARIO_BYTES)
    if args.evaluated_at_unix_ms is not None:
        if args.evaluated_at_unix_ms <= 0 or scenario.payload is None:
            parser.error("evaluated timestamp must be a positive integer")
        scenario.payload["evaluated_at_unix_ms"] = args.evaluated_at_unix_ms
        scenario = p9.document_from_payload(scenario.payload)
    report = run_scenario_pack(scenario)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
