from __future__ import annotations

import copy

from scripts.ops import otclient_conditions_shadow_replay as documents
from scripts.ops import otclient_heal_friend_operational_replay as operational
from scripts.ops import otclient_heal_friend_shadow_replay as replay


NOW = 1_784_093_100_000


def test_operational_report_is_review_only_and_no_action():
    base = replay.fixture_documents(NOW)
    observation = copy.deepcopy(base.observation.payload)
    observation["producer_source"] = "otclient_guarded_adapter"
    observation["observed_at_unix_ms"] = NOW - 1000
    observation["party_observed_at_unix_ms"] = NOW - 1000
    docs = replay.FixtureDocuments(
        base.profile,
        documents.document_from_payload(observation),
        base.p9_report,
        base.p9_receipt,
        base.p10_report,
        base.p10_receipt,
    )
    report = operational.build_report(docs, NOW)
    assert report["status"] == "passed"
    assert report["operational_acceptance_status"] == "shadow_plan_ready_for_operator_review"
    assert report["acceptance_receipt_written"] is False
    assert report["runtime_readiness_claimed"] is False
    assert all(report[field] is False for field in replay.FALSE_FLAGS)


def test_producer_document_rejects_tampered_observation():
    payload = {
        "schema_version": "ctoa.heal-friend-observation-producer.v1",
        "status": "observation_ready",
        "blockers": [],
        "observation": {"value": 1},
        "observation_sha256": "0" * 64,
        **{field: False for field in replay.FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }
    result = operational.observation_document(documents.document_from_payload(payload))
    assert result.status == "malformed"
