from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "AI" / "P23_HELPER_SAFE_CONTRACT_INVENTORY.json"
DECISION = ROOT / "AI" / "P23_2_CONDITION_CORE_DECISION.json"
FIXTURE = ROOT / "tests" / "fixtures" / "ctoa_helper_safe_condition_parity_v1.json"
HELPER_ENGINE = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_rule_engine.lua"
SAFE_CONTRACT = ROOT / "tests" / "fixtures" / "lua" / "ctoa_safe_condition_contract.lua"
SAFE_HELPER = ROOT / "mods" / "ctoa_safe" / "ctoa_safe_helper.lua"
SAFE_LOADER = ROOT / "mods" / "ctoa_safe" / "ctoa_safe_loader.lua"


def _lua() -> str | None:
    return shutil.which("lua") or shutil.which("lua5.4") or shutil.which("lua54")


def _lua_literal(value: object) -> str:
    if value is None:
        return "nil"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, list):
        return "{" + ",".join(_lua_literal(item) for item in value) + "}"
    if isinstance(value, dict):
        return "{" + ",".join(
            f"[{_lua_literal(str(key))}]={_lua_literal(item)}" for key, item in value.items()
        ) + "}"
    raise TypeError(type(value))


def test_contract_inventory_preserves_product_and_evidence_boundaries() -> None:
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))

    assert inventory["status"] == "p23_2_no_share_complete"
    assert inventory["products"]["helper"]["profile_schema"] == "ctoa-helper-profile-v1"
    assert inventory["products"]["safe"]["profile_schema"] == "ctoa-safe-profile-v3"
    helper_product = inventory["products"]["helper"]
    safe_product = inventory["products"]["safe"]
    assert (
        ROOT / helper_product["source_root"] / helper_product["loader_owner"]
    ).is_file()
    assert (ROOT / safe_product["source_root"] / safe_product["loader_owner"]).is_file()
    classifications = {item["id"]: item["classification"] for item in inventory["contracts"]}
    assert classifications["numeric_condition_operators"] == "share"
    assert classifications["condition_metric_names"] == "adapt"
    assert classifications["bounded_randomization"] == "adapt"
    assert classifications["profile_schema_and_persistence"] == "reject"
    assert classifications["loader_and_lifecycle"] == "reject"
    assert classifications["mutable_runtime_state_and_dispatch"] == "reject"
    assert classifications["acceptance_evidence_and_promotion"] == "reject"

    boundaries = inventory["boundaries"]
    assert boundaries["shared_runtime_files"] == []
    assert boundaries["shared_loaders"] == []
    assert boundaries["shared_mutable_state"] == []
    assert boundaries["shared_acceptance_receipts"] == []
    assert boundaries["safe_acceptance_satisfies_helper"] is False
    assert boundaries["helper_acceptance_satisfies_safe"] is False

    parity = inventory["parity_fixture"]
    assert parity["role"] == "contract_probe_not_product_adapter"
    assert parity["runtime_randomization_parity_evaluated"] is False
    assert parity["operational_acceptance_evaluated"] is False
    assert parity["runtime_actions"] is False
    assert parity["dispatch_allowed"] is False
    assert parity["promotion_allowed"] is False


def test_no_share_decision_preserves_product_local_condition_lifecycles() -> None:
    decision = json.loads(DECISION.read_text(encoding="utf-8"))
    helper = HELPER_ENGINE.read_text(encoding="utf-8")
    safe_contract = SAFE_CONTRACT.read_text(encoding="utf-8")

    assert decision["status"] == "complete"
    assert decision["decision"] == "no_shared_runtime_core"
    assert decision["shared_contract"]["numeric_comparison_only"] is True
    assert decision["shared_contract"]["runtime_randomization_parity"] is False
    assert decision["product_adapters"]["helper"]["profile_schema"] == "ctoa-helper-profile-v1"
    assert decision["product_adapters"]["safe"]["profile_schema"] == "ctoa-safe-profile-v3"
    assert decision["product_adapters"]["helper"]["max_conditions"] == 8
    assert decision["product_adapters"]["safe"]["max_conditions"] == 4

    boundaries = decision["boundaries"]
    assert boundaries["shared_runtime_files"] == []
    assert boundaries["shared_loaders"] == []
    assert boundaries["shared_mutable_state"] == []
    assert boundaries["shared_profile_schemas"] == []
    assert boundaries["shared_acceptance_receipts"] == []
    assert boundaries["safe_release_manifest_changed"] is False
    assert boundaries["helper_release_manifest_changed"] is False
    assert boundaries["live_or_sandbox_mutation"] is False

    # The passive fixture records only Safe's comparison surface. It does not
    # import Safe runtime source or claim parity for its randomization lifecycle.
    assert "local MAX_CONDITIONS = 8" in helper
    assert "randomInteger(-spread, spread)" in helper
    assert "local MAX_CONDITIONS = 4" in safe_contract
    assert decision["product_adapters"]["safe"]["randomization_lifecycle"] == (
        "cached_effective_threshold_until_successful_action_reset"
    )
    assert decision["shared_contract"]["runtime_randomization_parity"] is False


def test_helper_and_safe_share_only_passive_condition_semantics(tmp_path: Path) -> None:
    lua = _lua()
    assert lua, "Lua interpreter is required for P23.1 parity validation"
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert fixture["operational_acceptance_evaluated"] is False
    assert fixture["runtime_actions"] is False
    assert fixture["dispatch_allowed"] is False
    assert fixture["promotion_allowed"] is False

    probe = tmp_path / "helper_safe_parity_probe.lua"
    probe.write_text(
        f'''local helper = dofile(arg[1])
local safe = dofile(arg[2])
local fixture = {_lua_literal(fixture)}
local metricMap = fixture.metric_map
for _, case in ipairs(fixture.cases) do
  local helperConditions = {{}}
  local safeConditions = {{}}
  local safeContext = {{}}
  for key, value in pairs(case.context) do
    safeContext[metricMap[key]] = value
  end
  for index, condition in ipairs(case.conditions) do
    helperConditions[index] = {{
      metric = condition.metric, operator = condition.operator, value = condition.value,
      randomization = condition.randomization or 0, hysteresis = 0,
    }}
    safeConditions[index] = {{
      metric = metricMap[condition.metric], operator = condition.operator, value = condition.value,
      randomization = condition.randomization or 0,
    }}
  end
  local random = function(_, _) return case.random_offset or 0 end
  local helperResult = helper.evaluate({{
    schema_version = "ctoa-helper-rule-v1", id = case.id, enabled = true,
    combinator = case.combinator, cooldown_ms = 0,
    action = {{type = "hold", params = {{}}}}, conditions = helperConditions,
  }}, case.context, {{}}, random)
  local safeResult = safe.evaluate({{combinator = case.combinator, conditions = safeConditions}}, safeContext, random)
  assert(helperResult.matched == case.expected, "helper mismatch " .. case.id)
  assert(safeResult.matched == case.expected, "safe mismatch " .. case.id)
  assert(helperResult.matched == safeResult.matched, "parity mismatch " .. case.id)
  assert(helperResult.dispatch_allowed == false and helperResult.executes_action == false)
  assert(safeResult.dispatch_allowed == false and safeResult.executes_action == false)
end
local helperContract = helper.contract()
local safeContract = safe.contract()
assert(helperContract.runtime_actions == false and helperContract.dispatch_allowed == false)
assert(safeContract.pure == true and safeContract.runtime_actions == false)
assert(safeContract.dispatch_allowed == false and safeContract.executes_actions == false)
''',
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(HELPER_ENGINE), str(SAFE_CONTRACT)],
        check=False,
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_safe_fixture_adapter_is_pure_and_outside_product_runtime() -> None:
    contract = SAFE_CONTRACT.read_text(encoding="utf-8")
    helper = SAFE_HELPER.read_text(encoding="utf-8")
    loader = SAFE_LOADER.read_text(encoding="utf-8")

    for forbidden in (
        "g_game",
        "g_map",
        "g_ui",
        "cycleEvent",
        "scheduleEvent",
        "talk(",
        "attack(",
        "useInventoryItem",
        "io.open",
    ):
        assert forbidden not in contract
    assert "ctoa_safe_condition_contract" not in loader
    assert "CTOA_SAFE_CONDITION_CONTRACT" not in helper
    assert SAFE_CONTRACT.parent == ROOT / "tests" / "fixtures" / "lua"
    assert not (ROOT / "mods" / "ctoa_safe" / SAFE_CONTRACT.name).exists()
    assert 'autoload: false' in (ROOT / "mods" / "ctoa_safe" / "ctoa_safe.otmod").read_text(encoding="utf-8")
    decision = json.loads(DECISION.read_text(encoding="utf-8"))
    assert decision["fixture_adapter"]["role"] == "contract_probe_not_product_adapter"
    assert decision["fixture_adapter"]["loaded_by_safe"] is False
