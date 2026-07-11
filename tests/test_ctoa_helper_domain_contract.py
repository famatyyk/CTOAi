from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
DOMAIN_CONTRACT = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_domain_contract.lua"
REGISTRY = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_modules.lua"
WRAPPER = ROOT / "scripts" / "windows" / "solteria_helper_test_env.ps1"


def test_domain_contract_covers_all_helper_lanes_with_passive_envelopes():
    source = DOMAIN_CONTRACT.read_text(encoding="utf-8")

    for lane in [
        "healing",
        "combat",
        "cavebot",
        "loot",
        "timer",
        "heal_friend",
        "conditions",
        "equipment",
        "scripting",
    ]:
        assert f'id = "{lane}"' in source

    for function_name in [
        "schemaVersion",
        "lanes",
        "lane",
        "observationEnvelope",
        "planEnvelope",
        "summaryEnvelope",
        "validateEnvelope",
        "contract",
    ]:
        assert f"function DomainContract.{function_name}" in source

    assert 'local SCHEMA_VERSION = "ctoa-helper-domain-v1"' in source
    assert "source.dispatch_allowed = false" in source
    assert "source.executes_plan = false" in source
    assert "runtime_actions = false" in source
    assert "executes_plans = false" in source
    assert "g_game" not in source
    assert "g_map" not in source
    assert "g_ui" not in source
    assert "autoWalk" not in source
    assert "castSpell" not in source
    assert "dofile" not in source


def test_domain_contract_is_in_boot_graph_and_official_package():
    registry = REGISTRY.read_text(encoding="utf-8")
    wrapper = WRAPPER.read_text(encoding="utf-8")

    assert 'name = "ctoa_helper_domain_contract"' in registry
    assert 'file = "ctoa_helper_domain_contract.lua"' in registry
    assert 'depends_on = {"ctoa_helper_runtime_core"}' in registry
    assert "ctoa_helper_domain_contract.lua" in wrapper


def test_planner_normalizes_domain_edges_without_enabling_dispatch():
    planner = (ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_planner.lua").read_text(encoding="utf-8")

    assert 'rawget(_G, "CTOA_HELPER_DOMAIN_CONTRACT")' in planner
    assert 'domainValue("planEnvelope", result.module_id, result)' in planner
    assert 'domainValue(' in planner
    assert '"observationEnvelope",' in planner
    assert 'function Planner.summaryEnvelope' in planner
    assert 'domainValue("summaryEnvelope", best.module_id, state, Planner.summary(list))' in planner
    assert 'domain_contract_version = "ctoa-helper-domain-v1"' in planner
    assert "owns_domain_plan_normalization = true" in planner
    assert "owns_observation_envelope_handoff = true" in planner
    assert "owns_summary_envelope = true" in planner
    assert "runtime_actions = false" in planner
    assert "executes_plans = false" in planner


def test_timer_uses_the_canonical_catalog_action_name():
    timer = (ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_timer_runtime.lua").read_text(encoding="utf-8")
    planner = (ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_planner.lua").read_text(encoding="utf-8")
    catalog = (ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_action_catalog.lua").read_text(encoding="utf-8")

    assert 'next_action = "plan_timer"' in timer
    assert 'plan_timer = 3' in planner
    assert 'action = "plan_timer"' in catalog
    assert "plan_timer_message" not in timer


def test_combat_and_loot_use_canonical_catalog_actions():
    combat = (ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_combat_runtime.lua").read_text(encoding="utf-8")
    loot = (ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_loot_runtime.lua").read_text(encoding="utf-8")
    catalog = (ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_action_catalog.lua").read_text(encoding="utf-8")

    assert 'action = "plan_spell"' in combat
    assert 'action = "plan_rune"' in combat
    assert "plan_rotation" not in combat
    assert 'next_action = "plan_loot"' in loot
    assert 'loot_operation = lootOperation' in loot
    for legacy_action in ["plan_scan", "plan_open", "plan_move"]:
        assert legacy_action not in loot
    assert 'action = "plan_spell"' in catalog
    assert 'action = "plan_loot"' in catalog


def test_domain_protocol_and_planner_boundary_with_real_lua(tmp_path: Path):
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for domain-contract behavior validation"
    planner_path = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_planner.lua"
    probe = tmp_path / "domain_contract_probe.lua"
    probe.write_text(
        """
local domain = dofile(arg[1])
local planner = dofile(arg[2])

local module = {
  plan = function(config, observation, context)
    assert(config.enabled == true)
    assert(observation.paralyzed == true)
    assert(context.now == 1234)
    return {next_action = "plan_paralyze_recovery", reason = "observed", detail = "exura"}
  end,
}

local plans = planner.collect({{
  id = "conditions",
  module = module,
  config = {enabled = true},
  observation = {paralyzed = true},
}}, {now = 1234})

assert(#plans == 1)
local plan = plans[1]
assert(plan.schema_version == "ctoa-helper-domain-v1")
assert(plan.kind == "plan")
assert(plan.lane == "conditions")
assert(plan.module_id == "conditions")
assert(plan.next_action == "plan_paralyze_recovery")
assert(plan.weight == 2)
assert(plan.dispatch_allowed == false)
assert(plan.executes_plan == false)
assert(plan.observation_envelope.kind == "observation")
assert(plan.observation_envelope.lane == "conditions")
assert(plan.observation_envelope.observed_at == 1234)
assert(plan.observation_envelope.payload.paralyzed == true)

local valid, errors = domain.validateEnvelope(plan, "plan")
assert(valid == true and #errors == 0)
local summary = planner.summaryEnvelope(plans)
assert(summary.schema_version == "ctoa-helper-domain-v1")
assert(summary.kind == "summary")
assert(summary.lane == "conditions")
assert(summary.state == "planned")
assert(summary.runtime_actions == false)

local unknown = domain.planEnvelope("unknown", {next_action = "hold"})
local unknownValid, unknownErrors = domain.validateEnvelope(unknown, "plan")
assert(unknownValid == false and #unknownErrors == 1 and unknownErrors[1] == "lane")
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(DOMAIN_CONTRACT), str(planner_path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
