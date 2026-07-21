from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
LUA = ROOT / "scripts" / "lua" / "otclient"
ENGINE = LUA / "ctoa_helper_runtime_module_gate.lua"
CONDITIONS = LUA / "ctoa_helper_conditions_runtime_gate.lua"
EQUIPMENT = LUA / "ctoa_helper_equipment_runtime_gate.lua"
HEAL_FRIEND = LUA / "ctoa_helper_heal_friend_runtime_gate.lua"
REGISTRY = LUA / "ctoa_helper_modules.lua"
WRAPPER = ROOT / "scripts" / "windows" / "solteria_helper_test_env.ps1"
ROADMAP = ROOT / "AI" / "FEATURE_ROADMAP.md"
THREE_PLANS = ROOT / "docs" / "roadmaps" / "CTOAI_THREE_DEVELOPMENT_PLANS_2026-07-06.md"
GATE_DOC = ROOT / "docs" / "otclient" / "HELPER_RUNTIME_MODULE_GATES_V1.md"
DEVELOPMENT_PLAN = ROOT / "docs" / "otclient" / "solteria_helper_development_plan.md"
RUNTIME_2_PLAN = ROOT / "docs" / "otclient" / "ctoai_runtime_2_execution_plan.md"
TEST_ENV_DOC = ROOT / "docs" / "otclient" / "solteria_helper_test_env.md"
MODULE_WORKPLAN = ROOT / "docs" / "otclient" / "solteria_helper_module_workplan.md"
NEXT_MODULES_PLAN = ROOT / "docs" / "otclient" / "solteria_helper_next_modules_plan.md"


def test_runtime_module_gates_are_separate_ordered_and_packaged():
    engine = ENGINE.read_text(encoding="utf-8")
    conditions = CONDITIONS.read_text(encoding="utf-8")
    equipment = EQUIPMENT.read_text(encoding="utf-8")
    heal_friend = HEAL_FRIEND.read_text(encoding="utf-8")
    registry = REGISTRY.read_text(encoding="utf-8")
    wrapper = WRAPPER.read_text(encoding="utf-8")

    assert "function RuntimeModuleGate.acceptedTrace" in engine
    assert "gate.required_false" in engine
    assert 'gate_id = "conditions_runtime_gate"' in conditions
    assert 'phase = "conditions_first"' in conditions
    assert 'allowed_actions = {"plan_paralyze_recovery"}' in conditions
    assert 'gate_id = "equipment_runtime_gate"' in equipment
    assert 'phase = "equipment_after_conditions"' in equipment
    assert 'data.conditions_gate_trace' in equipment
    assert 'allowed_actions = {"plan_ring_swap"}' in equipment
    assert 'gate_id = "heal_friend_runtime_gate"' in heal_friend
    assert 'phase = "heal_friend_after_equipment_conditions"' in heal_friend
    assert 'data.equipment_gate_trace' in heal_friend
    assert 'allowed_actions = {"plan_sio"}' in heal_friend

    for path in [ENGINE, CONDITIONS, EQUIPMENT, HEAL_FRIEND]:
        source = path.read_text(encoding="utf-8")
        assert "dispatch_allowed = false" in source
        assert "runtime_actions = false" in source
        assert "live_promotion = false" in source
        for forbidden in ["g_game.", "g_map.", "castSpell(", "sendActionbarSlot(", "useWith(", "autoWalk("]:
            assert forbidden not in source

    for name in [
        "ctoa_helper_runtime_module_gate",
        "ctoa_helper_conditions_runtime_gate",
        "ctoa_helper_equipment_runtime_gate",
        "ctoa_helper_heal_friend_runtime_gate",
    ]:
        assert f'name = "{name}"' in registry
        assert f"{name}.lua" in wrapper
        assert f"mods/ctoa_otclient/{name}.lua" in wrapper

    for action in [
        "ConditionsRuntimeGateStaticSmoke",
        "EquipmentRuntimeGateStaticSmoke",
        "HealFriendRuntimeGateStaticSmoke",
    ]:
        assert f'"{action}"' in wrapper


def test_runtime_module_gate_matrix_with_real_lua(tmp_path: Path):
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for runtime-module gate validation"
    probe = tmp_path / "runtime_module_gate_probe.lua"
    probe.write_text(
        r'''
local engine = dofile(arg[1])
local conditions = dofile(arg[2])
local equipment = dofile(arg[3])
local healFriend = dofile(arg[4])

local function has(values, needle)
  for _, value in ipairs(values or {}) do if value == needle then return true end end
  return false
end

local common = {
  manifest_current = true, module_static_gates = true,
  module_attach_smoke = true, smoke_attach_all = true,
  sandbox = true, operator_confirmed = true, runtime_disarmed = true,
  dry_run = true, online = true, player_alive = true, client_ready = true,
  protection_zone = false, outside_protection_zone = true, live_promotion = false,
  runtime_lane_states = {combat = "disabled", cavebot = "disabled"},
}
local function with(base, extra)
  local result = {}
  for key, value in pairs(base or {}) do result[key] = value end
  for key, value in pairs(extra or {}) do result[key] = value end
  return result
end

local conditionInput = with(common, {
  next_action = "plan_paralyze_recovery", evidence_id = "conditions-e1",
  recovery_bridge_trace = {
    schema_version = "ctoa.recovery-bridge-trace.v1", status = "ready",
    guard = "passed", decision = "plan_heal", dry_run = true,
    dispatch_allowed = false, runtime_actions = false,
  },
  conditions_observer_smoke = true, conditions_observation_current = true,
  observation_id = "conditions-o1",
  condition_confirmed = true, condition = "paralyze", spell = "exura",
  observed_at_ms = 1000, evaluated_at_ms = 1100,
  cooldown_ms = 1000, cooldown_elapsed_ms = 1000, retry_budget = 1,
})
local conditionTrace = conditions.evaluate(conditionInput)
assert(conditionTrace.accepted == true and conditionTrace.status == "accepted")
assert(conditionTrace.dispatch_allowed == false and conditionTrace.runtime_actions == false)
local missingRecovery = conditions.evaluate(with(conditionInput, {recovery_bridge_trace = false}))
assert(missingRecovery.status == "blocked" and has(missingRecovery.blockers, "recovery_bridge_trace_required"))
local unsupportedCondition = conditions.evaluate(with(conditionInput, {next_action = "plan_poison_recovery", condition = "poison"}))
assert(unsupportedCondition.status == "blocked" and has(unsupportedCondition.blockers, "unsupported_action"))
local unknownPz = conditions.evaluate(with(conditionInput, {outside_protection_zone = false}))
assert(unknownPz.status == "blocked" and has(unknownPz.blockers, "outside_protection_zone_required"))
local unknownPzEvidence = conditions.evaluate(with(conditionInput, {protection_zone = "unknown"}))
assert(unknownPzEvidence.status == "blocked" and has(unknownPzEvidence.blockers, "protection_zone_false_required"))
assert(conditions.evaluate(with(conditionInput, {spell = "arbitrary"})).status == "blocked")
assert(conditions.evaluate(with(conditionInput, {retry_budget = -1})).status == "blocked")
assert(conditions.evaluate(with(conditionInput, {observed_at_ms = 0 / 0})).status == "blocked")
assert(conditions.evaluate(with(conditionInput, {cooldown_elapsed_ms = 999})).status == "blocked")
local notDryRun = conditions.evaluate(with(conditionInput, {dry_run = false}))
assert(notDryRun.status == "blocked" and notDryRun.dry_run == false)

local equipmentInput = with(common, {
  next_action = "plan_ring_swap", conditions_gate_trace = conditionTrace,
  evidence_id = "equipment-e1", observation_id = "equipment-o1",
  equipment_observer_smoke = true, equipment_observation_current = true,
  inventory_unambiguous = true, free_slot_confirmed = true, rollback_supported = true,
  equipped_item_id = 3051, candidate_item_id = 3048, rollback_item_id = 3051,
  slot_name = "ring", rollback_slot_name = "ring",
  candidate_source_container_id = 2, rollback_destination_container_id = 2,
  candidate_source_slot_index = 1, rollback_destination_slot_index = 1,
  inventory_revision = "inventory-r1", rollback_inventory_revision = "inventory-r1",
  observed_at_ms = 2000, evaluated_at_ms = 2100,
  cooldown_ms = 1500, cooldown_elapsed_ms = 1500, retry_budget = 0,
})
local equipmentTrace = equipment.evaluate(equipmentInput)
assert(equipmentTrace.accepted == true and equipmentTrace.status == "accepted")
local wrongRollback = equipment.evaluate(with(equipmentInput, {rollback_item_id = 9999}))
assert(wrongRollback.status == "blocked" and has(wrongRollback.blockers, "rollback_snapshot_mismatch"))
local equipmentBeforeConditions = equipment.evaluate(with(equipmentInput, {conditions_gate_trace = false}))
assert(equipmentBeforeConditions.status == "blocked" and has(equipmentBeforeConditions.blockers, "conditions_gate_trace_required"))
local wrongConditionSchema = equipment.evaluate(with(equipmentInput, {conditions_gate_trace = with(conditionTrace, {schema_version = "wrong"})}))
assert(wrongConditionSchema.status == "blocked")
assert(equipment.evaluate(with(equipmentInput, {candidate_item_id = 3048.5})).status == "blocked")
assert(equipment.evaluate(with(equipmentInput, {candidate_item_id = 0 / 0})).status == "blocked")
assert(equipment.evaluate(with(equipmentInput, {rollback_destination_container_id = 3})).status == "blocked")
assert(equipment.evaluate(with(equipmentInput, {cooldown_elapsed_ms = 1499})).status == "blocked")

local healInput = with(common, {
  next_action = "plan_sio", conditions_gate_trace = conditionTrace,
  equipment_gate_trace = equipmentTrace, heal_friend_no_target_smoke = true,
  evidence_id = "heal-friend-e1",
  whitelist_persistence_verified = true, require_whitelist = true,
  target_is_player = true,
  target_visible = true, target_same_floor = true, target_in_range = true,
  target_is_self = false, self_id = 1,
  target_id = 77, observed_target_id = 77, current_target_id = 77,
  target_name = "friend", observed_target_name = "Friend", current_target_name = "friend",
  whitelist_revision = "whitelist-r1", persisted_whitelist_revision = "whitelist-r1",
  persisted_whitelist_names = {"Friend"}, party_member_ids = {77, 88},
  observed_target_hp_percent = 56, current_target_hp_percent = 55,
  hp_threshold = 70, spell = "exura sio",
  observed_at_ms = 3000, party_observed_at_ms = 3000, evaluated_at_ms = 3100,
  cooldown_ms = 1200, cooldown_elapsed_ms = 1200, retry_budget = 1,
})
local healTrace = healFriend.evaluate(healInput)
assert(healTrace.accepted == true and healTrace.status == "accepted")
local noEquipment = healFriend.evaluate(with(healInput, {equipment_gate_trace = false}))
assert(noEquipment.status == "blocked" and has(noEquipment.blockers, "equipment_gate_trace_required"))
local spoofed = healFriend.evaluate(with(healInput, {persisted_whitelist_names = {"someone else"}}))
assert(spoofed.status == "blocked" and has(spoofed.blockers, "persisted_whitelist_identity_missing"))
local stale = healFriend.evaluate(with(healInput, {evaluated_at_ms = 3751}))
assert(stale.status == "blocked" and has(stale.blockers, "observation_stale"))
local pz = healFriend.evaluate(with(healInput, {protection_zone = true}))
assert(pz.status == "blocked" and has(pz.blockers, "protection_zone_false_required"))
assert(healFriend.evaluate(with(healInput, {current_target_id = 78})).status == "blocked")
assert(healFriend.evaluate(with(healInput, {party_member_ids = {88}})).status == "blocked")
assert(healFriend.evaluate(with(healInput, {persisted_whitelist_revision = "stale"})).status == "blocked")
assert(healFriend.evaluate(with(healInput, {observed_at_ms = 0 / 0})).status == "blocked")
assert(healFriend.evaluate(with(healInput, {retry_budget = -1})).status == "blocked")

assert(engine.contract().default_closed == true)
assert(conditions.contract().phase == "conditions_first")
assert(equipment.contract().requires_conditions_gate == true)
assert(healFriend.contract().requires_equipment_gate == true)
''',
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(ENGINE), str(CONDITIONS), str(EQUIPMENT), str(HEAL_FRIEND)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_runtime_policy_requires_action_specific_gates_and_defers_high_risk(tmp_path: Path):
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for runtime-policy validation"
    policy = LUA / "ctoa_helper_runtime_policy.lua"
    catalog = LUA / "ctoa_helper_action_catalog.lua"
    probe = tmp_path / "runtime_policy_gate_probe.lua"
    probe.write_text(
        r'''
local policy = dofile(arg[1])
local catalog = dofile(arg[2])
local gates = {
  manifest_current = true, module_static_gates = true,
  module_attach_smoke = true, smoke_attach_all = true, live_approval = true,
}
local function with(extra)
  local result = {}
  for key, value in pairs(gates) do result[key] = value end
  for key, value in pairs(extra or {}) do result[key] = value end
  return result
end
local function has(values, needle)
  for _, value in ipairs(values or {}) do if value == needle then return true end end
  return false
end

local function acceptedTrace(gateId, action)
  local schemas = {
    conditions_runtime_gate = "ctoa.conditions-runtime-safety-gate.v1",
    equipment_runtime_gate = "ctoa.equipment-runtime-safety-gate.v1",
    heal_friend_runtime_gate = "ctoa.heal-friend-runtime-safety-gate.v1",
  }
  return {
    schema_version = schemas[gateId], evidence_id = gateId .. "-e1",
    gate_id = gateId, next_action = action, status = "accepted", accepted = true,
    guard = "passed", dry_run = true, dispatch_allowed = false,
    runtime_actions = false, live_promotion = false,
  }
end

local conditionsBlocked = policy.decision({next_action = "plan_paralyze_recovery", runtime_action = false}, gates)
assert(conditionsBlocked.status == "blocked" and has(conditionsBlocked.reasons, "conditions_runtime_gate_missing"))
assert(conditionsBlocked.runtime_action == true and conditionsBlocked.runtime_action_classified_by_policy == true)
local conditionsReady = policy.decision({next_action = "plan_paralyze_recovery", runtime_action = false}, with({conditions_runtime_gate = acceptedTrace("conditions_runtime_gate", "plan_paralyze_recovery")}))
assert(conditionsReady.status == "ready" and conditionsReady.runtime_action == true)
local booleanGate = policy.decision({next_action = "plan_paralyze_recovery"}, with({conditions_runtime_gate = true}))
assert(booleanGate.status == "blocked")
local wrongActionTrace = policy.decision({next_action = "plan_paralyze_recovery"}, with({conditions_runtime_gate = acceptedTrace("conditions_runtime_gate", "plan_poison_recovery")}))
assert(wrongActionTrace.status == "blocked")
local missingEvidenceTrace = acceptedTrace("conditions_runtime_gate", "plan_paralyze_recovery")
missingEvidenceTrace.evidence_id = ""
assert(policy.decision({next_action = "plan_paralyze_recovery"}, with({conditions_runtime_gate = missingEvidenceTrace})).status == "blocked")
local equipmentReady = policy.decision({next_action = "plan_ring_swap"}, with({equipment_runtime_gate = acceptedTrace("equipment_runtime_gate", "plan_ring_swap")}))
assert(equipmentReady.status == "ready")
local healReady = policy.decision({next_action = "plan_sio"}, with({heal_friend_runtime_gate = acceptedTrace("heal_friend_runtime_gate", "plan_sio")}))
assert(healReady.status == "ready")
local poison = policy.decision({next_action = "plan_poison_recovery", runtime_action = false}, with({conditions_runtime_gate = acceptedTrace("conditions_runtime_gate", "plan_paralyze_recovery")}))
assert(poison.status == "blocked" and has(poison.reasons, "action_not_approved_v1"))
local amulet = policy.decision({next_action = "plan_amulet_swap"}, with({equipment_runtime_gate = acceptedTrace("equipment_runtime_gate", "plan_ring_swap")}))
assert(amulet.status == "blocked" and has(amulet.reasons, "action_not_approved_v1"))

local combat = policy.decision({next_action = "plan_attack", runtime_action = false}, with({combat_runtime_gate = true}))
assert(combat.status == "blocked" and has(combat.reasons, "high_risk_deferred"))
local cavebot = policy.decision({next_action = "plan_walk", runtime_action = false}, with({cavebot_runtime_gate = true}))
assert(cavebot.status == "blocked" and has(cavebot.reasons, "high_risk_deferred"))
local unknown = policy.decision({next_action = "plan_surprise", runtime_action = false}, gates)
assert(unknown.status == "blocked" and unknown.runtime_action == true and has(unknown.reasons, "unknown_action"))

local conditionCatalog = catalog.byAction("plan_paralyze_recovery")
assert(conditionCatalog.module_safety_gate == "conditions_runtime_gate")
local equipmentCatalog = catalog.byAction("plan_ring_swap")
assert(equipmentCatalog.module_safety_gate == "equipment_runtime_gate")
local healCatalog = catalog.byAction("plan_sio")
assert(healCatalog.module_safety_gate == "heal_friend_runtime_gate")
assert(catalog.byAction("plan_poison_recovery").module_safety_gate == "none")
assert(catalog.byAction("plan_poison_recovery").phase == "deferred_module_scope")
assert(catalog.byAction("plan_amulet_swap").phase == "deferred_module_scope")
assert(catalog.byAction("plan_attack").phase == "deferred_high_risk")
assert(catalog.byAction("plan_walk").phase == "deferred_high_risk")
assert(catalog.byAction("plan_surprise").runtime_action == true)
''',
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(policy), str(catalog)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_runtime_module_sequence_is_synced_across_canonical_plans():
    roadmap = ROADMAP.read_text(encoding="utf-8")
    three_plans = THREE_PLANS.read_text(encoding="utf-8")
    gate_doc = GATE_DOC.read_text(encoding="utf-8")
    development = DEVELOPMENT_PLAN.read_text(encoding="utf-8")
    runtime_2 = RUNTIME_2_PLAN.read_text(encoding="utf-8")
    test_env = TEST_ENV_DOC.read_text(encoding="utf-8")
    module_workplan = MODULE_WORKPLAN.read_text(encoding="utf-8")
    next_modules = NEXT_MODULES_PLAN.read_text(encoding="utf-8")

    assert roadmap.index("**Conditions runtime safety gate**") < roadmap.index(
        "**Equipment runtime safety gate**"
    ) < roadmap.index("**Heal Friend runtime safety gate**")
    assert "Conditions paralyze-only gate" in three_plans
    assert gate_doc.index("1. `conditions_runtime_gate`") < gate_doc.index(
        "2. `equipment_runtime_gate`"
    ) < gate_doc.index("3. `heal_friend_runtime_gate`")
    assert "Conditions paralyze-only gate,\n  Equipment ring-only rollback gate, Heal Friend" in development
    assert "Conditions paralyze-only,\nthen Equipment ring-only rollback, then Heal Friend" in runtime_2
    assert "`conditions`, `equipment`, `heal_friend`, and `scripting`" in test_env
    assert "Conditions diagnostics and paralyze-only gate, Equipment ring-only rollback gate, Heal Friend" in module_workplan
    assert "Runtime sequence: `Conditions -> Equipment -> Heal Friend`" in next_modules
    assert "`deferred_high_risk_refactor_only`" in next_modules
