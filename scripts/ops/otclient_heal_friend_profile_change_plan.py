#!/usr/bin/env python3
"""Build a hash-bound, no-action P11 exact-target shadow-profile plan."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

if __package__:
    from . import otclient_conditions_shadow_acceptance as p9_acceptance
    from . import otclient_conditions_shadow_replay as documents
    from . import otclient_equipment_observation_preview as writer
    from . import otclient_equipment_shadow_acceptance as p10_acceptance
else:  # pragma: no cover
    import otclient_conditions_shadow_acceptance as p9_acceptance
    import otclient_conditions_shadow_replay as documents
    import otclient_equipment_observation_preview as writer
    import otclient_equipment_shadow_acceptance as p10_acceptance


ROOT = Path(__file__).resolve().parents[2]
DEV_DIR = ROOT / "runtime" / "solteria_helper_dev"
CATALOG = DEV_DIR / "heal_friend_candidate_catalog.json"
P9_RECEIPT = DEV_DIR / "conditions_shadow_acceptance.json"
P10_RECEIPT = DEV_DIR / "equipment_shadow_acceptance.json"
OUTPUT = DEV_DIR / "heal_friend_profile_change_plan.json"
TARGET_RELPATH = ".ctoa-local/otclient/heal-friend-shadow-profile.json"
SCHEMA = "ctoa.heal-friend-profile-change-plan.v1"
PROFILE_SCHEMA = "ctoa.heal-friend-shadow-profile.v1"
MAX_BYTES = 256 * 1024
MAX_CATALOG_AGE_MS = 10_000
FALSE_FLAGS = (
    "dispatch_allowed",
    "runtime_actions",
    "executes_plan",
    "execute_once_allowed",
    "promotion_allowed",
    "casts",
    "talks",
)


def normalize_name(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def exact_confirmation(target_id: int, target_name: str) -> str:
    return f"zatwierdzam cel P11: id {target_id}, nazwa {target_name}"


def build_profile(target_id: int, target_name: str) -> dict[str, Any]:
    whitelist = [{"target_id": target_id, "target_name": target_name}]
    return {
        "schema_version": PROFILE_SCHEMA,
        "mode": "shadow_only",
        "action": "plan_sio",
        "spell": "exura sio",
        "selection_policy": "single_exact_target",
        "whitelist": whitelist,
        "whitelist_revision": documents.canonical_sha256(whitelist),
        "hp_threshold": 70,
        "max_range": 7,
        "max_observation_age_ms": 6000,
        "max_party_age_ms": 6000,
        "cooldown_required": "ready",
        "retry_budget": 0,
        "requires_p9_acceptance": True,
        "requires_p10_acceptance": True,
        "require_party_membership": True,
        "prohibit_self": True,
        "require_visible": True,
        "require_same_floor": True,
        **{field: False for field in FALSE_FLAGS},
    }


def _receipt_ready(document: documents.InputDocument, *, p10: bool) -> bool:
    payload = document.payload
    contract = (
        p10_acceptance._receipt_contract  # noqa: SLF001
        if p10
        else p9_acceptance._receipt_contract_valid  # noqa: SLF001
    )
    return bool(
        document.status == "loaded"
        and isinstance(payload, dict)
        and contract(payload)
        and payload.get("status") == "accepted"
        and payload.get("acceptance_granted") is True
        and payload.get("receipt_persisted") is True
        and payload.get("operational_inputs_fixture") is False
    )


def build_plan(
    catalog: documents.InputDocument,
    p9_receipt: documents.InputDocument,
    p10_receipt: documents.InputDocument,
    *,
    target_id: int,
    target_name: str,
    confirmation: str,
    now_unix_ms: int,
) -> dict[str, Any]:
    blockers: list[str] = []
    target_name = normalize_name(target_name)
    payload = catalog.payload
    if catalog.status != "loaded" or not isinstance(payload, dict):
        blockers.append("catalog_missing_or_invalid")
        payload = {}
    if payload.get("schema_version") != "ctoa.heal-friend-candidate-catalog.v1":
        blockers.append("catalog_schema_invalid")
    if payload.get("status") != "catalog_ready" or payload.get("blockers") != []:
        blockers.append("catalog_not_ready")
    age_ms = now_unix_ms - payload.get("generated_at_unix_ms", 0)
    if not isinstance(age_ms, int) or age_ms < 0 or age_ms > MAX_CATALOG_AGE_MS:
        blockers.append("catalog_stale")
    if any(payload.get(field) is not False for field in FALSE_FLAGS):
        blockers.append("catalog_unsafe")
    candidates = payload.get("candidates")
    matches = []
    if isinstance(candidates, list):
        matches = [
            item
            for item in candidates
            if isinstance(item, dict)
            and item.get("target_id") == target_id
            and normalize_name(item.get("target_name")) == target_name
        ]
    if len(matches) != 1:
        blockers.append("exact_candidate_missing_or_ambiguous")
    else:
        candidate = matches[0]
        if not (
            candidate.get("target_is_player") is True
            and candidate.get("target_is_self") is False
            and candidate.get("target_party_member") is True
            and candidate.get("target_visible") is True
            and candidate.get("target_same_floor") is True
            and isinstance(candidate.get("distance"), int)
            and 0 <= candidate["distance"] <= 7
        ):
            blockers.append("candidate_guard_failed")
    if not _receipt_ready(p9_receipt, p10=False):
        blockers.append("p9_acceptance_invalid")
    if not _receipt_ready(p10_receipt, p10=True):
        blockers.append("p10_acceptance_invalid")
    required_confirmation = exact_confirmation(target_id, target_name)
    if confirmation != required_confirmation:
        blockers.append("operator_confirmation_mismatch")

    profile = build_profile(target_id, target_name)
    profile_sha = documents.canonical_sha256(profile)
    basis = {
        "schema_version": SCHEMA,
        "target_path": TARGET_RELPATH,
        "target_id": target_id,
        "target_name": target_name,
        "catalog_sha256": catalog.sha256,
        "p9_receipt_sha256": p9_receipt.sha256,
        "p10_receipt_sha256": p10_receipt.sha256,
        "proposed_profile_sha256": profile_sha,
        "proposed_profile": profile,
    }
    plan_sha = documents.canonical_sha256(basis)
    return {
        **basis,
        "generated_at_unix_ms": now_unix_ms,
        "status": "ready_for_operator_review" if not blockers else "blocked",
        "plan_sha256": plan_sha,
        "required_apply_confirmation": f"zatwierdzam zastosowanie planu P11 {plan_sha}",
        "blockers": blockers,
        "profile_write_allowed": False,
        "application_performed": False,
        **{field: False for field in FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-id", required=True, type=int)
    parser.add_argument("--target-name", required=True)
    parser.add_argument("--confirmation", required=True)
    parser.add_argument("--allow-blocked", action="store_true")
    args = parser.parse_args(argv)
    now = int(time.time() * 1000)
    report = build_plan(
        documents.read_document(CATALOG, MAX_BYTES),
        documents.read_document(P9_RECEIPT, MAX_BYTES),
        documents.read_document(P10_RECEIPT, MAX_BYTES),
        target_id=args.target_id,
        target_name=args.target_name,
        confirmation=args.confirmation,
        now_unix_ms=now,
    )
    writer._write_atomic(OUTPUT, OUTPUT, report)  # noqa: SLF001
    print(json.dumps(report, indent=2, sort_keys=True))
    return (
        0
        if report["status"] == "ready_for_operator_review" or args.allow_blocked
        else 1
    )


if __name__ == "__main__":
    sys.exit(main())
