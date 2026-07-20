from __future__ import annotations

from scripts.ops import otclient_conditions_shadow_replay as documents
from scripts.ops import otclient_heal_friend_profile_change_plan as plan


NOW = 1_784_092_600_000
TARGET_ID = 268435471
TARGET_NAME = "amir to moja dziwka"


def _receipt(schema: str) -> dict:
    # Unit tests isolate plan policy; receipt contract validators are patched below.
    return {"schema_version": schema, "status": "accepted"}


def _catalog() -> dict:
    return {
        "schema_version": "ctoa.heal-friend-candidate-catalog.v1",
        "generated_at_unix_ms": NOW - 1000,
        "status": "catalog_ready",
        "blockers": [],
        "candidates": [{
            "target_id": TARGET_ID,
            "target_name": TARGET_NAME,
            "target_is_player": True,
            "target_is_self": False,
            "target_party_member": True,
            "target_visible": True,
            "target_same_floor": True,
            "distance": 1,
        }],
        **{field: False for field in plan.FALSE_FLAGS},
    }


def test_plan_is_hash_bound_and_never_applies(monkeypatch):
    monkeypatch.setattr(plan, "_receipt_ready", lambda document, *, p10: True)
    report = plan.build_plan(
        documents.document_from_payload(_catalog()),
        documents.document_from_payload(_receipt("p9")),
        documents.document_from_payload(_receipt("p10")),
        target_id=TARGET_ID,
        target_name=TARGET_NAME,
        confirmation=plan.exact_confirmation(TARGET_ID, TARGET_NAME),
        now_unix_ms=NOW,
    )
    assert report["status"] == "ready_for_operator_review"
    assert report["proposed_profile"]["whitelist"] == [
        {"target_id": TARGET_ID, "target_name": TARGET_NAME}
    ]
    assert report["required_apply_confirmation"].endswith(report["plan_sha256"])
    assert report["profile_write_allowed"] is False
    assert report["application_performed"] is False
    assert all(report[field] is False for field in plan.FALSE_FLAGS)


def test_plan_fails_closed_for_self_or_confirmation_mismatch(monkeypatch):
    monkeypatch.setattr(plan, "_receipt_ready", lambda document, *, p10: True)
    catalog = _catalog()
    catalog["candidates"][0]["target_is_self"] = True
    report = plan.build_plan(
        documents.document_from_payload(catalog),
        documents.document_from_payload(_receipt("p9")),
        documents.document_from_payload(_receipt("p10")),
        target_id=TARGET_ID,
        target_name=TARGET_NAME,
        confirmation="wrong",
        now_unix_ms=NOW,
    )
    assert report["status"] == "blocked"
    assert "candidate_guard_failed" in report["blockers"]
    assert "operator_confirmation_mismatch" in report["blockers"]


def test_receipt_validator_adapters_match_p9_and_p10_modules(monkeypatch):
    p9_doc = documents.document_from_payload({
        "status": "accepted", "acceptance_granted": True,
        "receipt_persisted": True, "operational_inputs_fixture": False,
    })
    p10_doc = documents.document_from_payload(dict(p9_doc.payload))
    monkeypatch.setattr(plan.p9_acceptance, "_receipt_contract_valid", lambda payload: True)
    monkeypatch.setattr(plan.p10_acceptance, "_receipt_contract", lambda payload: True)
    assert plan._receipt_ready(p9_doc, p10=False) is True
    assert plan._receipt_ready(p10_doc, p10=True) is True
