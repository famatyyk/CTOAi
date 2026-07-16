from __future__ import annotations

import json

from scripts.ops import otclient_conditions_shadow_replay as documents
from scripts.ops import otclient_heal_friend_profile_apply as apply
from scripts.ops import otclient_heal_friend_profile_change_plan as change


def _profile() -> dict:
    return change.build_profile(268435471, "amir to moja dziwka")


def _plan(catalog_sha: str, p9_sha: str, p10_sha: str) -> dict:
    profile = _profile()
    payload = {
        "schema_version": change.SCHEMA,
        "target_path": change.TARGET_RELPATH,
        "target_id": 268435471,
        "target_name": "amir to moja dziwka",
        "catalog_sha256": catalog_sha,
        "p9_receipt_sha256": p9_sha,
        "p10_receipt_sha256": p10_sha,
        "proposed_profile_sha256": documents.canonical_sha256(profile),
        "proposed_profile": profile,
    }
    plan_sha = documents.canonical_sha256(payload)
    return {
        **payload,
        "status": "ready_for_operator_review",
        "blockers": [],
        "plan_sha256": plan_sha,
        "required_apply_confirmation": f"zatwierdzam zastosowanie planu P11 {plan_sha}",
        "profile_write_allowed": False,
        "application_performed": False,
        **{field: False for field in change.FALSE_FLAGS},
    }


def test_validate_application_binds_plan_confirmation_and_dependencies():
    catalog = documents.document_from_payload({"catalog": "ok"})
    p9 = documents.document_from_payload({"receipt": "p9"})
    p10 = documents.document_from_payload({"receipt": "p10"})
    payload = _plan(catalog.sha256, p9.sha256, p10.sha256)
    blockers = apply.validate_application(
        documents.document_from_payload(payload), catalog, p9, p10,
        confirmation=payload["required_apply_confirmation"],
    )
    assert blockers == []


def test_validate_application_fails_closed_for_changed_dependency():
    catalog = documents.document_from_payload({"catalog": "ok"})
    p9 = documents.document_from_payload({"receipt": "p9"})
    p10 = documents.document_from_payload({"receipt": "p10"})
    payload = _plan(catalog.sha256, p9.sha256, p10.sha256)
    changed = documents.document_from_payload({"catalog": "changed"})
    blockers = apply.validate_application(
        documents.document_from_payload(payload), changed, p9, p10,
        confirmation=payload["required_apply_confirmation"],
    )
    assert blockers == ["catalog_changed"]


def test_apply_writes_only_profile_and_receipt(monkeypatch, tmp_path):
    catalog = documents.document_from_payload({"catalog": "ok"})
    p9 = documents.document_from_payload({"receipt": "p9"})
    p10 = documents.document_from_payload({"receipt": "p10"})
    payload = _plan(catalog.sha256, p9.sha256, p10.sha256)
    inputs = iter([catalog, p9, p10])
    monkeypatch.setattr(apply.documents, "read_document", lambda path, size: next(inputs))
    target = tmp_path / "profile.json"
    receipt = tmp_path / "receipt.json"
    monkeypatch.setattr(
        apply,
        "_write_profile_atomic",
        lambda path, payload: path.write_text(json.dumps(payload), encoding="utf-8"),
    )
    monkeypatch.setattr(
        apply.writer,
        "_write_atomic",
        lambda path, expected, payload: path.write_text(json.dumps(payload), encoding="utf-8"),
    )
    report = apply.apply_profile(
        documents.document_from_payload(payload),
        confirmation=payload["required_apply_confirmation"],
        target=target,
        receipt_path=receipt,
    )
    assert report["status"] == "applied"
    assert json.loads(target.read_text(encoding="utf-8")) == _profile()
    assert json.loads(receipt.read_text(encoding="utf-8"))["profile_applied"] is True
    assert all(report[field] is False for field in change.FALSE_FLAGS)
