from __future__ import annotations

from scripts.ops import otclient_conditions_shadow_replay as documents
from scripts.ops import otclient_heal_friend_shadow_acceptance as acceptance
from scripts.ops import otclient_heal_friend_shadow_replay as replay


def test_report_contract_accepts_current_no_action_shape():
    trace = {
        "source": "operational", "status": "shadow_plan_ready",
        "decision": "would_plan_sio", "blockers": [],
        "operator_review_required": True, "operational_readiness_claimed": False,
        "plan": {
            "action": "plan_sio", "spell": "exura sio", "retry_budget": 0,
            "dispatch_allowed": False, "runtime_actions": False,
            "casts": False, "talks": False,
        },
        **{field: False for field in replay.FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }
    report = {
        "schema_version": replay.REPORT_SCHEMA, "source": "operational",
        "status": "passed",
        "operational_acceptance_status": "shadow_plan_ready_for_operator_review",
        "acceptance_receipt_written": False,
        "operational_readiness_claimed": False, "runtime_readiness_claimed": False,
        "operational_trace": trace,
        **{field: False for field in replay.FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }
    assert acceptance._report_no_action(report) is True
    report["casts"] = True
    assert acceptance._report_no_action(report) is False


def test_profile_receipt_must_bind_profile_hash():
    report = {"operational_trace": {"input_sha256": {"profile": "a" * 64}}}
    payload = {
        "schema_version": "ctoa.heal-friend-profile-apply-receipt.v1",
        "status": "applied", "profile_applied": True, "blockers": [],
        "profile_sha256": "a" * 64, "runtime_readiness_claimed": False,
        **{field: False for field in replay.FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }
    assert acceptance._profile_receipt_valid(
        documents.document_from_payload(payload), report
    ) is True
    payload["profile_sha256"] = "b" * 64
    assert acceptance._profile_receipt_valid(
        documents.document_from_payload(payload), report
    ) is False
