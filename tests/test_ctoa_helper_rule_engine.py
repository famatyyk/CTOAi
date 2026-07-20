from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
RULE_ENGINE = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_rule_engine.lua"
REGISTRY = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_modules.lua"
WRAPPER = ROOT / "scripts" / "windows" / "solteria_helper_test_env.ps1"


def test_rule_engine_is_pure_passive_and_exposes_generic_contract() -> None:
    source = RULE_ENGINE.read_text(encoding="utf-8")

    for metric in ("hp_percent", "mana_percent", "monster_count", "distance", "pz", "active_condition"):
        assert metric in source
    for operator in ('["<"]', '["<="]', '["="]', '["!="]', '[">="]', '[">"]'):
        assert operator in source
    for forbidden in ("g_game", "g_map", "g_ui", "autoWalk", "castSpell", "sendActionbarSlot", "dofile"):
        assert forbidden not in source
    assert "dispatch_allowed = false" in source
    assert "executes_action = false" in source
    assert "runtime_actions = false" in source


def test_rule_engine_is_in_boot_graph_and_sandbox_package() -> None:
    registry = REGISTRY.read_text(encoding="utf-8")
    wrapper = WRAPPER.read_text(encoding="utf-8")

    assert 'name = "ctoa_helper_rule_engine"' in registry
    assert 'file = "ctoa_helper_rule_engine.lua"' in registry
    assert 'depends_on = {"ctoa_helper_domain_contract"}' in registry
    assert "ctoa_helper_rule_engine.lua" in wrapper


def test_rule_engine_behavior_with_real_lua(tmp_path: Path) -> None:
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for rule-engine behavior validation"
    probe = tmp_path / "rule_engine_probe.lua"
    probe.write_text(
        r'''
local engine = dofile(arg[1])
local rule = {
  schema_version = "ctoa-helper-rule-v1",
  id = "ring-danger",
  enabled = true,
  priority = 20,
  combinator = "AND",
  cooldown_ms = 1000,
  action = {type = "equipment", params = {slot = "ring", item_id = 3051}},
  conditions = {
    {metric = "hp_percent", operator = "<=", value = 50, hysteresis = 5, randomization = 2},
    {metric = "monster_count", operator = ">=", value = 3},
    {metric = "pz", operator = "=", value = false},
  },
}

local decision = engine.evaluate(rule, {hp_percent = 49, monster_count = 4, pz = false, now_ms = 2000}, {}, function(low, high)
  assert(low == -2 and high == 2)
  return 1
end)
assert(decision.matched == true)
assert(decision.results[1].expected == 51)
assert(decision.rule.action.params.item_id == 3051)
assert(decision.dispatch_allowed == false and decision.executes_action == false)

local cooling = engine.evaluate(rule, {hp_percent = 20, monster_count = 9, pz = false, now_ms = 2500}, decision.next_state)
assert(cooling.matched == false and cooling.reason == "cooldown")

local hysteresis = engine.evaluate(rule, {hp_percent = 54, monster_count = 4, pz = false, now_ms = 4000}, decision.next_state, function() return 0 end)
assert(hysteresis.matched == true)
assert(hysteresis.results[1].expected == 55)

local orRule = {
  schema_version = "ctoa-helper-rule-v1",
  enabled = true,
  combinator = "OR",
  action = {type = "spell", params = {words = "utamo vita"}},
  conditions = {
    {metric = "mana_percent", operator = ">=", value = 80},
    {metric = "active_condition", key = "mana_shield", operator = "!=", value = true},
  },
}
local orDecision = engine.evaluate(orRule, {mana_percent = 20, active_conditions = {mana_shield = false}, now_ms = 5000}, {})
assert(orDecision.matched == true)

local invalid = engine.evaluate({enabled = true, action = {type = "shell"}, conditions = {}}, {}, {})
assert(invalid.matched == false and invalid.reason == "invalid_rule")
local legacySet, legacyPlan = engine.migrateRuleSet({
  {
    id = "legacy",
    enabled = true,
    action = {type = "hold", params = {}},
    conditions = {{metric = "hp_percent", operator = "<=", value = 25}},
  },
})
assert(legacySet.schema_version == "ctoa-helper-rule-set-v1")
assert(legacySet.rules[1].schema_version == "ctoa-helper-rule-v1")
assert(legacySet.rules[1].enabled == false)
assert(legacyPlan.reason == "migration_required" and legacyPlan.safe_disabled == true)

local currentSet, currentPlan = engine.migrateRuleSet({
  schema_version = "ctoa-helper-rule-set-v1",
  rules = {rule},
})
assert(currentSet.rules[1].enabled == true)
assert(currentPlan.reason == "schema_ready" and currentPlan.applied == false)

local futureSet, futurePlan = engine.migrateRuleSet({schema_version = "ctoa-helper-rule-set-v2", rules = {}})
assert(futureSet == nil and futurePlan.reason == "future_schema_version")
local futureRule, futureRulePlan = engine.migrate({schema_version = "ctoa-helper-rule-v2"})
assert(futureRule == nil and futureRulePlan.reason == "future_schema_version")

local tooManyRules = {schema_version = "ctoa-helper-rule-set-v1", rules = {}}
for index = 1, 33 do tooManyRules.rules[index] = rule end
local oversized, oversizedPlan = engine.migrateRuleSet(tooManyRules)
assert(oversized == nil and oversizedPlan.reason == "too_many_rules")
assert(oversizedPlan.rule_count == 33 and oversizedPlan.max_rules == 32)

local invalidSet, invalidSetPlan = engine.migrateRuleSet({
  schema_version = "ctoa-helper-rule-set-v1",
  rules = {{schema_version = "ctoa-helper-rule-v1", enabled = true, action = {type = "shell"}, conditions = {}}},
})
assert(invalidSet == nil and invalidSetPlan.reason == "rule_migration_failed")
assert(invalidSetPlan.failed_rule_index == 1)

local replaySet, replayPlan = engine.migrateRuleSet(currentSet)
assert(replaySet.schema_version == currentSet.schema_version)
assert(replaySet.rules[1].enabled == currentSet.rules[1].enabled)
assert(replayPlan.reason == "schema_ready" and replayPlan.applied == false)
local contract = engine.contract()
assert(contract.schema_version == "ctoa-helper-rule-v1")
assert(contract.rule_set_schema_version == "ctoa-helper-rule-set-v1")
assert(contract.max_conditions == 8 and contract.max_rules == 32 and contract.max_randomization == 20)
assert(contract.runtime_actions == false and contract.dispatch_allowed == false)
''',
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(RULE_ENGINE)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
