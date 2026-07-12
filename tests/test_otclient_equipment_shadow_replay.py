from __future__ import annotations

import copy
import json
from pathlib import Path

from scripts.ops import otclient_equipment_shadow_replay as replay


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "otclient_equipment_shadow_replay"
NOW_MS = 1783800000000


def _docs():
    return replay._fixture_documents()


def _no_action(payload: dict) -> None:
    assert all(payload[key] is False for key in replay.FALSE_FLAGS)
    assert payload["intrusive_actions_performed"] == []


def test_positive_ring_plan_is_deterministic_and_data_only():
    docs = _docs()
    first = replay.evaluate_shadow(
        profile=docs[0],
        snapshot=docs[1],
        p9_trace=docs[2],
        p9_receipt=docs[3],
        evaluated_at_unix_ms=NOW_MS,
        source="fixture",
    )
    second = replay.evaluate_shadow(
        profile=docs[0],
        snapshot=docs[1],
        p9_trace=docs[2],
        p9_receipt=docs[3],
        evaluated_at_unix_ms=NOW_MS,
        source="fixture",
    )
    assert first == second
    assert first["status"] == "shadow_plan_ready"
    assert first["decision"] == "would_plan_ring_swap"
    assert first["plan"]["slot"] == "ring"
    assert first["plan"]["rollback_item_id"] == first["plan"]["before_item_id"]
    assert first["rollback_simulation"] == "ready"
    _no_action(first)


def test_fixture_pack_covers_ring_only_negative_matrix():
    report = replay.run_scenario_pack(
        replay._read(replay.DEFAULT_SCENARIO_PACK, replay.MAX_SCENARIO_BYTES)
    )
    assert report["status"] == "passed"
    assert report["total_count"] == report["passed_count"] == 15
    assert report["failed_count"] == 0
    _no_action(report)
    assert all(case["deterministic"] and case["passed"] for case in report["cases"])


def test_operational_report_never_promotes_fixture_p9():
    report = replay.build_report(evaluated_at_unix_ms=NOW_MS)
    assert report["scenario_pack_status"] == "passed"
    assert report["operational_acceptance_status"] == "operational_acceptance_blocked"
    assert "p9_fixture_not_operational" in report["operational_trace"]["blockers"]
    assert report["runtime_readiness_claimed"] is False
    _no_action(report)


def test_snapshot_extra_field_is_rejected():
    docs = list(_docs())
    assert docs[1].payload is not None
    payload = copy.deepcopy(docs[1].payload)
    payload["unexpected"] = True
    docs[1] = replay.p9_replay.document_from_payload(payload)
    trace = replay.evaluate_shadow(
        profile=docs[0],
        snapshot=docs[1],
        p9_trace=docs[2],
        p9_receipt=docs[3],
        evaluated_at_unix_ms=NOW_MS,
        source="fixture",
    )
    assert trace["status"] == "operational_acceptance_blocked"
    assert "snapshot_schema_invalid" in trace["blockers"]


def test_equipment_schemas_are_closed_draft_2020_12():
    for path in (ROOT / "schemas").glob("equipment-shadow-*.schema.json"):
        schema = json.loads(path.read_text(encoding="utf-8"))
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["additionalProperties"] is False
