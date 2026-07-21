from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from scripts.ops import otclient_equipment_shadow_replay as replay
from scripts.ops import release_evidence_pack as evidence


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "otclient_equipment_shadow_replay"
NOW_MS = 1783800000000
P10_SCHEMA_NAMES = (
    "equipment-shadow-trace.schema.json",
    "equipment-shadow-scenario-pack.schema.json",
    "equipment-shadow-replay-report.schema.json",
)


def _schema_registry() -> Registry:
    registry = Registry()
    for name in P10_SCHEMA_NAMES:
        payload = json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))
        registry = registry.with_resource(
            payload["$id"], Resource.from_contents(payload)
        )
    return registry


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
    assert report["total_count"] == report["passed_count"] == 30
    assert report["failed_count"] == 0
    _no_action(report)
    assert all(case["deterministic"] and case["passed"] for case in report["cases"])


def test_operational_report_never_promotes_fixture_p9():
    report = replay.build_report(
        evaluated_at_unix_ms=NOW_MS,
        source="operational",
        documents=_docs(),
    )
    assert report["scenario_pack_status"] == "passed"
    assert report["operational_acceptance_status"] == "operational_acceptance_blocked"
    assert "p9_fixture_not_operational" in report["operational_trace"]["blockers"]
    assert "snapshot_fixture_not_operational" in report["operational_trace"]["blockers"]
    assert report["runtime_readiness_claimed"] is False
    _no_action(report)


def test_operational_replay_allows_only_bounded_post_snapshot_transport():
    docs = list(_docs())
    assert docs[1].payload is not None
    snapshot = copy.deepcopy(docs[1].payload)
    observed_at = snapshot["observed_at_unix_ms"]
    snapshot["producer_source"] = "otclient_guarded_adapter"
    docs[1] = replay.p9_replay.document_from_payload(snapshot)

    within_transport = replay.evaluate_shadow(
        profile=docs[0],
        snapshot=docs[1],
        p9_trace=docs[2],
        p9_receipt=docs[3],
        evaluated_at_unix_ms=(
            observed_at
            + replay.MAX_AGE_MS
            + replay.OPERATIONAL_REPLAY_TRANSPORT_ALLOWANCE_MS
        ),
        source="operational",
    )
    beyond_transport = replay.evaluate_shadow(
        profile=docs[0],
        snapshot=docs[1],
        p9_trace=docs[2],
        p9_receipt=docs[3],
        evaluated_at_unix_ms=(
            observed_at
            + replay.MAX_AGE_MS
            + replay.OPERATIONAL_REPLAY_TRANSPORT_ALLOWANCE_MS
            + 1
        ),
        source="operational",
    )

    assert "snapshot_stale" not in within_transport["blockers"]
    assert "snapshot_stale" in beyond_transport["blockers"]


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


def test_p9_unknown_keys_and_malformed_scenario_pack_fail_closed():
    docs = list(_docs())
    assert docs[2].payload is not None
    p9_trace = copy.deepcopy(docs[2].payload)
    p9_trace["unexpected"] = "dispatch"
    docs[2] = replay.p9_replay.document_from_payload(p9_trace)
    trace = replay.evaluate_shadow(
        profile=docs[0],
        snapshot=docs[1],
        p9_trace=docs[2],
        p9_receipt=docs[3],
        evaluated_at_unix_ms=NOW_MS,
        source="fixture",
    )
    assert trace["status"] == "operational_acceptance_blocked"
    assert "p9_trace_schema_invalid" in trace["blockers"]

    scenario = replay.p9_replay.document_from_payload(
        {
            "schema_version": replay.SCENARIO_SCHEMA,
            "fixture_only": True,
            "operational_readiness_claimed": False,
            "evaluated_at_unix_ms": NOW_MS,
            "scenarios": [{}],
        }
    )
    report = replay.run_scenario_pack(scenario)
    assert report["status"] == "failed"
    assert report["failed_count"] == 1


def test_release_evidence_rejects_nested_p10_tamper():
    report = replay.build_report(evaluated_at_unix_ms=NOW_MS, source="fixture")
    report["operational_trace"]["runtime_actions"] = True
    report["scenario_pack"]["cases"][0]["intrusive_actions_performed"] = ["move_item"]
    summary = evidence._equipment_shadow_summary(
        report,
        replay.DEFAULT_OUTPUT,
        now=datetime.fromtimestamp(NOW_MS / 1000, tz=timezone.utc),
    )
    assert summary["contract_valid"] is False
    assert summary["status"] == "invalid"
    assert "report.operational_trace" in summary["contract_errors"]
    assert "report.scenario_pack" in summary["contract_errors"]


def test_static_wrapper_confines_p10_evidence_to_canonical_runtime_dir():
    wrapper = (ROOT / "scripts" / "windows" / "solteria_helper_test_env.ps1").read_text(
        encoding="utf-8"
    )
    start = wrapper.index("function Invoke-EquipmentShadowReplayStaticSmoke")
    end = wrapper.index("Assert-OperatorModeAction", start)
    block = wrapper[start:end]
    assert "Assert-ExactBackgroundOutputPath" in block
    assert "equipment_shadow_replay_static_smoke.json" in block


def test_equipment_schemas_are_closed_draft_2020_12():
    for path in (ROOT / "schemas").glob("equipment-shadow-*.schema.json"):
        schema = json.loads(path.read_text(encoding="utf-8"))
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["additionalProperties"] is False


def test_strict_p10_schemas_validate_report_and_reject_nested_tamper():
    registry = _schema_registry()
    report_schema = json.loads(
        (ROOT / "schemas" / "equipment-shadow-replay-report.schema.json").read_text(
            encoding="utf-8"
        )
    )
    scenario_schema = json.loads(
        (ROOT / "schemas" / "equipment-shadow-scenario-pack.schema.json").read_text(
            encoding="utf-8"
        )
    )
    report = replay.build_report(evaluated_at_unix_ms=NOW_MS, source="fixture")
    scenario = json.loads(replay.DEFAULT_SCENARIO_PACK.read_text(encoding="utf-8"))
    report_validator = Draft202012Validator(report_schema, registry=registry)
    scenario_validator = Draft202012Validator(scenario_schema, registry=registry)
    assert not list(report_validator.iter_errors(report))
    assert not list(scenario_validator.iter_errors(scenario))

    tampered = copy.deepcopy(report)
    tampered["operational_trace"]["input_sha256"]["unexpected"] = "a" * 64
    assert list(report_validator.iter_errors(tampered))
    tampered = copy.deepcopy(report)
    tampered["operational_trace"]["plan"]["rollback_slot_index"] += 1
    assert (
        list(report_validator.iter_errors(tampered))
        or not evidence._equipment_shadow_summary(
            tampered,
            replay.DEFAULT_OUTPUT,
            now=datetime.fromtimestamp(NOW_MS / 1000, tz=timezone.utc),
        )["contract_valid"]
    )


def test_cli_separates_fixture_success_from_operational_acceptance():
    assert (
        replay.main(
            ["--no-write", "--source", "fixture", "--evaluated-at-unix-ms", str(NOW_MS)]
        )
        == 0
    )
    assert (
        replay.main(
            [
                "--no-write",
                "--source",
                "operational",
            ]
        )
        == 1
    )


def test_operational_cli_forbids_time_override_and_all_modes_fix_scenario_path(
    tmp_path,
):
    with pytest.raises(SystemExit) as exc:
        replay.main(
            [
                "--no-write",
                "--source",
                "operational",
                "--evaluated-at-unix-ms",
                str(NOW_MS),
            ]
        )
    assert exc.value.code == 2

    rogue = tmp_path / "scenarios.json"
    rogue.write_text(
        replay.DEFAULT_SCENARIO_PACK.read_text(encoding="utf-8"), encoding="utf-8"
    )
    for source in ("fixture", "operational"):
        with pytest.raises(SystemExit) as exc:
            replay.main(
                ["--no-write", "--source", source, "--scenario-pack", str(rogue)]
            )
        assert exc.value.code == 2


def test_fixture_cli_refuses_to_replace_canonical_operational_report():
    with pytest.raises(SystemExit) as exc:
        replay.main(["--source", "fixture"])
    assert exc.value.code == 2


def test_operational_cli_rejects_noncanonical_or_fixture_paths():
    with pytest.raises(SystemExit) as exc:
        replay.main(
            [
                "--no-write",
                "--source",
                "operational",
                "--snapshot",
                str(replay.DEFAULT_SNAPSHOT),
            ]
        )
    assert exc.value.code == 2

    with pytest.raises(SystemExit) as exc:
        replay.main(
            [
                "--no-write",
                "--source",
                "fixture",
                "--snapshot",
                str(replay.DEFAULT_SNAPSHOT),
            ]
        )
    assert exc.value.code == 2
