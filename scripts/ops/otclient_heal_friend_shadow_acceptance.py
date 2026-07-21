#!/usr/bin/env python3
"""Accept one hash-bound P11 Heal Friend shadow report without casting."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from typing import Any

if __package__:
    from . import otclient_conditions_shadow_replay as documents
    from . import otclient_equipment_observation_preview as writer
    from . import otclient_heal_friend_operational_replay as operational
    from . import otclient_heal_friend_profile_apply as profile_apply
    from . import otclient_heal_friend_shadow_replay as replay
else:  # pragma: no cover
    import otclient_conditions_shadow_replay as documents
    import otclient_equipment_observation_preview as writer
    import otclient_heal_friend_operational_replay as operational
    import otclient_heal_friend_profile_apply as profile_apply
    import otclient_heal_friend_shadow_replay as replay


DEV_DIR = operational.DEV_DIR
REPORT = operational.OUTPUT
PROFILE_APPLY_RECEIPT = profile_apply.RECEIPT
OUTPUT = DEV_DIR / "heal_friend_shadow_acceptance.json"
SCHEMA = "ctoa.heal-friend-shadow-acceptance.v1"
EXACT_CONFIRMATION = "accept P11 heal friend shadow"
MAX_BYTES = 512 * 1024


def _report_no_action(payload: Any) -> bool:
    trace = payload.get("operational_trace") if isinstance(payload, dict) else None
    plan = trace.get("plan") if isinstance(trace, dict) else None
    return bool(
        isinstance(payload, dict)
        and payload.get("schema_version") == replay.REPORT_SCHEMA
        and payload.get("source") == "operational"
        and payload.get("status") == "passed"
        and payload.get("operational_acceptance_status")
        == "shadow_plan_ready_for_operator_review"
        and payload.get("acceptance_receipt_written") is False
        and payload.get("operational_readiness_claimed") is False
        and payload.get("runtime_readiness_claimed") is False
        and all(payload.get(field) is False for field in replay.FALSE_FLAGS)
        and payload.get("intrusive_actions_performed") == []
        and isinstance(trace, dict)
        and trace.get("source") == "operational"
        and trace.get("status") == "shadow_plan_ready"
        and trace.get("decision") == "would_plan_sio"
        and trace.get("blockers") == []
        and trace.get("operator_review_required") is True
        and trace.get("operational_readiness_claimed") is False
        and all(trace.get(field) is False for field in replay.FALSE_FLAGS)
        and trace.get("intrusive_actions_performed") == []
        and isinstance(plan, dict)
        and plan.get("action") == "plan_sio"
        and plan.get("spell") == "exura sio"
        and plan.get("retry_budget") == 0
        and all(
            plan.get(field) is False
            for field in ("dispatch_allowed", "runtime_actions", "casts", "talks")
        )
    )


def _profile_receipt_valid(
    document: documents.InputDocument, report: dict[str, Any]
) -> bool:
    payload = document.payload
    trace = report.get("operational_trace") or {}
    inputs = trace.get("input_sha256") or {}
    return bool(
        document.status == "loaded"
        and isinstance(payload, dict)
        and payload.get("schema_version") == profile_apply.SCHEMA
        and payload.get("status") == "applied"
        and payload.get("profile_applied") is True
        and payload.get("blockers") == []
        and payload.get("profile_sha256") == inputs.get("profile")
        and payload.get("runtime_readiness_claimed") is False
        and all(payload.get(field) is False for field in replay.FALSE_FLAGS)
        and payload.get("intrusive_actions_performed") == []
    )


def _receipt_basis(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: payload[key]
        for key in (
            "schema_version",
            "status",
            "report_sha256",
            "recomputed_report_sha256",
            "decision_sha256",
            "input_sha256",
            "profile_apply_receipt_sha256",
            "confirmation_sha256",
            "blockers",
        )
    }


def build_acceptance(*, confirmation: str, write_requested: bool) -> dict[str, Any]:
    report_doc = documents.read_document(REPORT, MAX_BYTES)
    profile_receipt = documents.read_document(PROFILE_APPLY_RECEIPT, MAX_BYTES)
    report = report_doc.payload
    blockers: list[str] = []
    if report_doc.status != "loaded" or not _report_no_action(report):
        blockers.append("report_invalid_or_not_ready")
        report = {}
    docs = operational.canonical_documents()
    generated_at = report.get("generated_at_unix_ms")
    recomputed = (
        operational.build_report(docs, generated_at)
        if isinstance(generated_at, int) and generated_at > 0
        else {}
    )
    recomputed_sha = (
        documents.canonical_sha256(recomputed) if recomputed else documents.ZERO_SHA256
    )
    if report_doc.sha256 != recomputed_sha:
        blockers.append("report_recompute_mismatch")
    if not _profile_receipt_valid(profile_receipt, report):
        blockers.append("profile_apply_receipt_invalid")
    if confirmation != EXACT_CONFIRMATION:
        blockers.append("operator_confirmation_mismatch")
    blockers = list(dict.fromkeys(blockers))
    accepted = not blockers and write_requested
    trace = report.get("operational_trace") or {}
    confirmation_sha = (
        hashlib.sha256(EXACT_CONFIRMATION.encode("utf-8")).hexdigest()
        if confirmation == EXACT_CONFIRMATION
        else None
    )
    payload = {
        "schema_version": SCHEMA,
        "status": "accepted" if accepted else "blocked",
        "acceptance_granted": accepted,
        "receipt_persisted": accepted,
        "operator_review_completed": accepted,
        "downstream_use_requires_separate_review": True,
        "report_sha256": report_doc.sha256,
        "recomputed_report_sha256": recomputed_sha,
        "decision_sha256": trace.get("decision_sha256", documents.ZERO_SHA256),
        "input_sha256": trace.get("input_sha256", {}),
        "profile_apply_receipt_sha256": profile_receipt.sha256,
        "confirmation_sha256": confirmation_sha,
        "blockers": blockers,
        "operational_inputs_fixture": False,
        "runtime_readiness_claimed": False,
        **{field: False for field in replay.FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }
    basis_sha = documents.canonical_sha256(_receipt_basis(payload))
    return {
        **payload,
        "created_at_unix_ms": int(time.time() * 1000),
        "receipt_id": f"heal-friend-shadow-acceptance-{basis_sha[:16]}",
        "acceptance_basis_sha256": basis_sha,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirmation", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    report = build_acceptance(
        confirmation=args.confirmation, write_requested=args.write
    )
    if args.write and report["status"] == "accepted":
        writer._write_atomic(OUTPUT, OUTPUT, report)  # noqa: SLF001
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "accepted" else 1


if __name__ == "__main__":
    sys.exit(main())
