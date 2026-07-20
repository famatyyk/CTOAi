#!/usr/bin/env python3
"""Apply one approved P11 shadow profile without enabling any game action."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

if __package__:
    from . import otclient_conditions_shadow_replay as documents
    from . import otclient_equipment_capture_profile_apply as local_writer
    from . import otclient_equipment_observation_preview as writer
    from . import otclient_heal_friend_profile_change_plan as change_plan
    from . import otclient_heal_friend_shadow_replay as replay
else:  # pragma: no cover
    import otclient_conditions_shadow_replay as documents
    import otclient_equipment_capture_profile_apply as local_writer
    import otclient_equipment_observation_preview as writer
    import otclient_heal_friend_profile_change_plan as change_plan
    import otclient_heal_friend_shadow_replay as replay


ROOT = Path(__file__).resolve().parents[2]
PLAN = change_plan.OUTPUT
TARGET = ROOT / change_plan.TARGET_RELPATH
RECEIPT = change_plan.DEV_DIR / "heal_friend_profile_apply_receipt.json"
SCHEMA = "ctoa.heal-friend-profile-apply-receipt.v1"
MAX_BYTES = 256 * 1024


def _write_profile_atomic(path: Path, payload: dict[str, Any]) -> None:
    local_writer._write_local_atomic(path, payload)  # noqa: SLF001


def _plan_basis(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: payload.get(key)
        for key in (
            "schema_version",
            "target_path",
            "target_id",
            "target_name",
            "catalog_sha256",
            "p9_receipt_sha256",
            "p10_receipt_sha256",
            "proposed_profile_sha256",
            "proposed_profile",
        )
    }


def validate_application(
    plan: documents.InputDocument,
    catalog: documents.InputDocument,
    p9_receipt: documents.InputDocument,
    p10_receipt: documents.InputDocument,
    *,
    confirmation: str,
) -> list[str]:
    blockers: list[str] = []
    payload = plan.payload
    if plan.status != "loaded" or not isinstance(payload, dict):
        return ["plan_missing_or_invalid"]
    if (
        payload.get("schema_version") != change_plan.SCHEMA
        or payload.get("status") != "ready_for_operator_review"
        or payload.get("blockers") != []
        or payload.get("target_path") != change_plan.TARGET_RELPATH
        or payload.get("profile_write_allowed") is not False
        or payload.get("application_performed") is not False
        or any(payload.get(field) is not False for field in change_plan.FALSE_FLAGS)
    ):
        blockers.append("plan_contract_invalid")
    plan_sha = documents.canonical_sha256(_plan_basis(payload))
    if payload.get("plan_sha256") != plan_sha:
        blockers.append("plan_sha256_mismatch")
    required = f"zatwierdzam zastosowanie planu P11 {plan_sha}"
    if (
        confirmation != required
        or payload.get("required_apply_confirmation") != required
    ):
        blockers.append("operator_confirmation_mismatch")
    profile = payload.get("proposed_profile")
    if not replay._profile_valid(profile):  # noqa: SLF001
        blockers.append("profile_contract_invalid")
    elif payload.get("proposed_profile_sha256") != documents.canonical_sha256(profile):
        blockers.append("profile_sha256_mismatch")
    dependencies = (
        (catalog, payload.get("catalog_sha256"), "catalog_changed"),
        (p9_receipt, payload.get("p9_receipt_sha256"), "p9_receipt_changed"),
        (p10_receipt, payload.get("p10_receipt_sha256"), "p10_receipt_changed"),
    )
    for document, expected_sha, blocker in dependencies:
        if document.status != "loaded" or document.sha256 != expected_sha:
            blockers.append(blocker)
    return blockers


def apply_profile(
    plan: documents.InputDocument,
    *,
    confirmation: str,
    target: Path = TARGET,
    receipt_path: Path = RECEIPT,
) -> dict[str, Any]:
    catalog = documents.read_document(change_plan.CATALOG, MAX_BYTES)
    p9_receipt = documents.read_document(change_plan.P9_RECEIPT, MAX_BYTES)
    p10_receipt = documents.read_document(change_plan.P10_RECEIPT, MAX_BYTES)
    blockers = validate_application(
        plan, catalog, p9_receipt, p10_receipt, confirmation=confirmation
    )
    payload = plan.payload if isinstance(plan.payload, dict) else {}
    applied = not blockers
    if applied:
        _write_profile_atomic(target, payload["proposed_profile"])
    basis = {
        "schema_version": SCHEMA,
        "status": "applied" if applied else "blocked",
        "plan_sha256": payload.get("plan_sha256", documents.ZERO_SHA256),
        "plan_file_sha256": plan.sha256,
        "profile_sha256": payload.get("proposed_profile_sha256", documents.ZERO_SHA256),
        "profile_path": change_plan.TARGET_RELPATH,
        "profile_applied": applied,
        "blockers": blockers,
        "runtime_readiness_claimed": False,
        **{field: False for field in change_plan.FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }
    receipt_sha = documents.canonical_sha256(basis)
    report = {
        **basis,
        "created_at_unix_ms": int(time.time() * 1000),
        "receipt_id": f"heal-friend-profile-apply-{receipt_sha[:16]}",
        "receipt_sha256": receipt_sha,
    }
    writer._write_atomic(receipt_path, receipt_path, report)  # noqa: SLF001
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirmation", required=True)
    args = parser.parse_args(argv)
    report = apply_profile(
        documents.read_document(PLAN, MAX_BYTES), confirmation=args.confirmation
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "applied" else 1


if __name__ == "__main__":
    sys.exit(main())
