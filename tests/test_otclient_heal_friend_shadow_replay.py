from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from scripts.ops import otclient_conditions_shadow_acceptance as p9_acceptance
from scripts.ops import otclient_conditions_shadow_replay as documents
from scripts.ops import otclient_heal_friend_shadow_replay as replay


ROOT = Path(__file__).resolve().parents[1]
NOW_MS = 1783800000000
SCHEMA_NAMES = (
    "heal-friend-scan.schema.json",
    "heal-friend-shadow-profile.schema.json",
    "heal-friend-observation.schema.json",
    "heal-friend-shadow-trace.schema.json",
    "heal-friend-shadow-scenario-pack.schema.json",
    "heal-friend-shadow-replay-report.schema.json",
)


def _assert_closed(value: object) -> None:
    if isinstance(value, dict):
        if value.get("type") == "object" or "properties" in value:
            assert value.get("additionalProperties") is False
        for nested in value.values():
            _assert_closed(nested)
    elif isinstance(value, list):
        for nested in value:
            _assert_closed(nested)


def _registry() -> Registry:
    registry = Registry()
    for name in SCHEMA_NAMES:
        payload = json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))
        registry = registry.with_resource(payload["$id"], Resource.from_contents(payload))
        registry = registry.with_resource(
            f"https://ctoa.local/schemas/{name}", Resource.from_contents(payload)
        )
    return registry


def test_positive_fixture_is_exact_single_target_and_never_ranks_or_casts():
    docs = replay.fixture_documents(NOW_MS)
    trace = replay.evaluate_shadow(docs, NOW_MS)
    profile = docs.profile.payload

    assert profile is not None
    assert profile["selection_policy"] == "single_exact_target"
    assert len(profile["whitelist"]) == 1
    assert profile["whitelist_revision"] == documents.canonical_sha256(profile["whitelist"])
    assert trace["status"] == "shadow_plan_ready"
    assert trace["decision"] == "would_plan_sio"
    assert trace["blockers"] == []
    assert trace["plan"]["target_id"] == 424242
    assert trace["fixture_validation_only"] is True
    assert trace["operational_readiness_claimed"] is False
    assert trace["operator_review_required"] is False
    assert all(trace[key] is False for key in replay.FALSE_FLAGS)
    assert trace["intrusive_actions_performed"] == []


def test_fixture_pack_is_deterministic_and_explicitly_not_operational():
    scenario = replay._read_fixture(  # noqa: SLF001
        replay.SCENARIO_PATH, replay.SCENARIO_PATH, replay.MAX_SCENARIO_BYTES
    )
    first = replay.run_scenario_pack(scenario)
    second = replay.run_scenario_pack(scenario)

    assert first == second
    assert first["status"] == first["scenario_pack_status"] == "passed"
    assert first["total_count"] == first["passed_count"] == len(replay.MUTATIONS) == 55
    assert first["failed_count"] == 0
    assert first["fixture_only"] is True
    assert first["fixture_only_validation_passed"] is True
    assert first["operational_acceptance_status"] == "not_evaluated"
    assert first["operational_producer_present"] is False
    assert first["acceptance_receipt_written"] is False
    assert first["operational_readiness_claimed"] is False
    assert first["runtime_readiness_claimed"] is False
    assert all(first[key] is False for key in replay.FALSE_FLAGS)
    assert all(case["passed"] is True for case in first["cases"])


def test_all_p11_schemas_are_closed_and_validate_positive_artifacts():
    schemas = {}
    for name in SCHEMA_NAMES:
        schema = json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        _assert_closed(schema)
        schemas[name] = schema
    registry = _registry()
    docs = replay.fixture_documents(NOW_MS)
    trace = replay.evaluate_shadow(docs, NOW_MS)
    report = replay.run_scenario_pack(
        replay._read_fixture(replay.SCENARIO_PATH, replay.SCENARIO_PATH, replay.MAX_SCENARIO_BYTES)  # noqa: SLF001
    )
    for name, value in (
        ("heal-friend-shadow-profile.schema.json", docs.profile.payload),
        ("heal-friend-observation.schema.json", docs.observation.payload),
        ("heal-friend-shadow-trace.schema.json", trace),
        ("heal-friend-shadow-scenario-pack.schema.json", json.loads(replay.SCENARIO_PATH.read_text(encoding="utf-8"))),
        ("heal-friend-shadow-replay-report.schema.json", report),
    ):
        errors = list(Draft202012Validator(schemas[name], registry=registry).iter_errors(value))
        assert errors == [], (name, errors)


def test_predecessor_receipts_bind_full_reports_and_each_other():
    docs = replay.fixture_documents(NOW_MS)
    assert docs.p9_report.payload is not None and docs.p9_receipt.payload is not None
    assert docs.p10_report.payload is not None and docs.p10_receipt.payload is not None
    assert docs.p9_receipt.payload["report_sha256"] == docs.p9_report.sha256
    assert docs.p10_receipt.payload["report_sha256"] == docs.p10_report.sha256
    p10_inputs = docs.p10_report.payload["operational_trace"]["input_sha256"]
    assert p10_inputs["p9_trace"] == documents.canonical_sha256(
        docs.p9_report.payload["operational_trace"]
    )
    assert p10_inputs["p9_receipt"] == docs.p9_receipt.sha256

    changed_receipt = copy.deepcopy(docs.p9_receipt.payload)
    changed_receipt["input_sha256"]["profile"] = "c" * 64
    basis_sha = documents.canonical_sha256(p9_acceptance._acceptance_basis(changed_receipt))  # noqa: SLF001
    changed_receipt["acceptance_basis_sha256"] = basis_sha
    changed_receipt["receipt_id"] = f"conditions-shadow-acceptance-{basis_sha[:16]}"
    assert p9_acceptance._receipt_contract_valid(changed_receipt)  # noqa: SLF001
    changed = replay.FixtureDocuments(
        docs.profile,
        docs.observation,
        docs.p9_report,
        documents.document_from_payload(changed_receipt),
        docs.p10_report,
        docs.p10_receipt,
    )
    trace = replay.evaluate_shadow(changed, NOW_MS)
    assert "p9_receipt_report_mismatch" in trace["blockers"]
    assert "p10_predecessor_mismatch" in trace["blockers"]
    assert trace["plan"] is None


@pytest.mark.parametrize(
    ("contents", "status"),
    [
        ('{"a":1,"a":2}', "duplicate_keys"),
        ('{"a":NaN}', "malformed"),
        ('{"a":Infinity}', "malformed"),
        ("[]", "not_object"),
        ('{"a":' + "[" * 80 + "0" + "]" * 80 + "}", "malformed"),
    ],
)
def test_shared_strict_reader_rejects_malformed_fixture_json(
    tmp_path: Path, contents: str, status: str
):
    path = tmp_path / "input.json"
    path.write_text(contents, encoding="utf-8")
    assert documents.read_document(path).status == status


def test_reader_rejects_oversize_nonregular_and_symlink(tmp_path: Path):
    oversized = tmp_path / "large.json"
    oversized.write_bytes(b"{" + b" " * replay.MAX_INPUT_BYTES)
    assert documents.read_document(oversized, replay.MAX_INPUT_BYTES).status == "oversize"
    directory = tmp_path / "directory.json"
    directory.mkdir()
    assert documents.read_document(directory).status == "not_regular"
    target = tmp_path / "target.json"
    target.write_text("{}", encoding="utf-8")
    link = tmp_path / "link.json"
    try:
        os.symlink(target, link)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    assert documents.read_document(link).status == "symlink_rejected"


def test_scenario_contract_rejects_unknown_duplicate_and_unsorted_content():
    payload = json.loads(replay.SCENARIO_PATH.read_text(encoding="utf-8"))
    mutations = (
        lambda value: value["scenarios"][0].update({"mutation": "unknown"}),
        lambda value: value["scenarios"][1].update({"name": value["scenarios"][0]["name"]}),
        lambda value: value["scenarios"][1].update({"expected_blockers": ["unsafe_contract", "profile_action_mismatch"]}),
    )
    for mutate in mutations:
        changed = copy.deepcopy(payload)
        mutate(changed)
        report = replay.run_scenario_pack(documents.document_from_payload(changed))
        assert report["status"] == "failed"
        assert report["fixture_only_validation_passed"] is False
        assert report["operational_acceptance_status"] == "not_evaluated"


def test_cli_requires_no_write_rejects_path_overrides_and_creates_no_runtime_artifact():
    runtime_matches_before = sorted((ROOT / "runtime").rglob("*heal_friend_shadow*"))
    command = [sys.executable, str(ROOT / "scripts" / "ops" / "otclient_heal_friend_shadow_replay.py")]
    missing_flag = subprocess.run(command, capture_output=True, text=True, check=False)
    assert missing_flag.returncode == 2
    override = subprocess.run(
        [*command, "--no-write", "--json-out", str(ROOT / "runtime" / "p11.json")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert override.returncode == 2
    passed = subprocess.run([*command, "--no-write"], capture_output=True, text=True, check=False)
    assert passed.returncode == 0
    report = json.loads(passed.stdout)
    assert report["status"] == "passed"
    runtime_matches_after = sorted((ROOT / "runtime").rglob("*heal_friend_shadow*"))
    assert runtime_matches_after == runtime_matches_before


def test_decision_hash_changes_for_any_input_value_but_not_json_key_order():
    docs = replay.fixture_documents(NOW_MS)
    first = replay.evaluate_shadow(docs, NOW_MS)
    reordered_profile = dict(reversed(list(docs.profile.payload.items())))  # type: ignore[union-attr]
    reordered = replay.FixtureDocuments(
        documents.document_from_payload(reordered_profile),
        docs.observation,
        docs.p9_report,
        docs.p9_receipt,
        docs.p10_report,
        docs.p10_receipt,
    )
    assert replay.evaluate_shadow(reordered, NOW_MS) == first
    changed_observation = copy.deepcopy(docs.observation.payload)
    changed_observation["distance"] = 4
    changed = replay.FixtureDocuments(
        docs.profile,
        documents.document_from_payload(changed_observation),
        docs.p9_report,
        docs.p9_receipt,
        docs.p10_report,
        docs.p10_receipt,
    )
    second = replay.evaluate_shadow(changed, NOW_MS)
    assert second["canonical_input_sha256"] != first["canonical_input_sha256"]
    assert second["decision_sha256"] != first["decision_sha256"]


def test_lua_exact_target_scan_refuses_ranking_and_ambiguous_matches(tmp_path: Path):
    lua = shutil.which("lua")
    if not lua:
        pytest.skip("Lua interpreter unavailable")
    probe = tmp_path / "probe.lua"
    probe.write_text(
        r'''
local heal = dofile(arg[1])
local player = {id = 1, name = "self", hp = 100, pos = {x=0,y=0,z=7}}
local ally = {id = 42, name = "fixture ally", hp = 42, pos = {x=2,y=1,z=7}, party = true, visible = true}
local duplicate = {id = 42, name = "fixture ally", hp = 10, pos = {x=3,y=1,z=7}, party = true, visible = true}
local spectators = {ally}
local ctx = {
  getLocalPlayer = function() return player end,
  getThingPosition = function(value) return value.pos end,
  getSpectatorsInRange = function() return spectators end,
  isPlayerCreature = function(value, self) return value ~= self end,
  normalizedCreatureName = function(value) return value.name end,
  getCreatureHealthPercent = function(value) return value.hp end,
  getCreatureId = function(value) return value.id end,
  isPartyMemberCreature = function(value) return value.party end,
  canShootCreature = function(value) return value.visible end,
  distanceChebyshev = function(a,b) return math.max(math.abs(a.x-b.x), math.abs(a.y-b.y)) end,
}
local config = {observe_party=true, friend_scan_range=7, friend_target_id=42, friend_whitelist={"fixture ally"}}
local exact = heal.scanExactTarget(config, ctx)
assert(exact.status == "observed" and exact.target_id == 42 and exact.hp_percent == 42)
assert(exact.target_party_member == true and exact.target_visible == true and exact.target_same_floor == true)
assert(exact.selection_policy == "single_exact_target" and exact.ranking_applied == false)
ally.party = false
local notParty = heal.scanExactTarget(config, ctx)
assert(notParty.status == "blocked" and notParty.reason == "target_not_party_member")
ally.party = true
ally.visible = false
local notVisible = heal.scanExactTarget(config, ctx)
assert(notVisible.status == "blocked" and notVisible.reason == "target_not_visible")
ally.visible = true
config.friend_target_id = 43
local identityDrift = heal.scanExactTarget(config, ctx)
assert(identityDrift.status == "blocked" and identityDrift.reason == "exact_target_not_observed")
config.friend_target_id = 42
spectators = {ally, duplicate}
local ambiguous = heal.scanExactTarget(config, ctx)
assert(ambiguous.status == "blocked" and ambiguous.reason == "exact_target_ambiguous")
assert(ambiguous.target_id == nil and ambiguous.ranking_applied == false)
config.friend_whitelist = {"fixture ally", "other fixture"}
local multiple = heal.scanExactTarget(config, ctx)
assert(multiple.status == "blocked" and multiple.reason == "single_exact_target_required")
print("ok")
''',
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_heal_friend.lua")],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert completed.stdout.strip() == "ok"
