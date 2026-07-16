from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OTCLIENT_DIR = ROOT / "scripts" / "lua" / "otclient"
TARGETING = OTCLIENT_DIR / "ctoa_helper_targeting.lua"
SCHEMA = OTCLIENT_DIR / "ctoa_helper_profile_schema.lua"
PERSISTENCE = OTCLIENT_DIR / "ctoa_helper_profile_persistence.lua"
UI = OTCLIENT_DIR / "ctoa_helper_ui.lua"
HELPER = OTCLIENT_DIR / "ctoa_native_helper.lua"


def _lua() -> str | None:
    return shutil.which("lua") or shutil.which("lua5.4") or shutil.which("lua54")


def test_target_rules_are_ordered_bounded_persistent_and_action_free(tmp_path: Path) -> None:
    lua = _lua()
    assert lua, "Lua interpreter is required for target-rule validation"
    probe = tmp_path / "target_rule_editor_probe.lua"
    probe.write_text(
        r'''
local targeting = dofile(arg[1])
local schema = dofile(arg[2])
local persistence = dofile(arg[3])

local tools = {priority_names = {"demon"}, require_reachable_target = true}
local rules, replaceDecision = targeting.replaceTargetRules(tools, {
  {enabled = true, name_pattern = "demon", min_hp = 0, max_hp = 60, min_distance = 1, max_distance = 5, min_count = 2, max_count = 8, priority = 5, chase_policy = "stand"},
  {enabled = true, name_pattern = "", min_hp = 0, max_hp = 100, min_distance = 0, max_distance = 7, min_count = 0, max_count = 99, priority = 50, chase_policy = "inherit"},
})
assert(replaceDecision.allowed == true and replaceDecision.runtime_actions == false)
assert(replaceDecision.dispatch_allowed == false and #rules == 2)

local demon = {name = "Demon", hp = 55, distance = 3, monster_count = 4, reachable = true}
local rat = {name = "Rat", hp = 100, distance = 1, monster_count = 1, reachable = true}
local demonDecision = targeting.decision(demon, tools)
local ratDecision = targeting.decision(rat, tools)
assert(demonDecision.eligible == true and demonDecision.target_rule_index == 1)
assert(demonDecision.target_rule_priority == 5 and demonDecision.chase_policy == "stand")
assert(ratDecision.eligible == true and ratDecision.target_rule_index == 2)
assert(demonDecision.score < ratDecision.score)

local guarded = targeting.decision({name = "Demon familiar", hp = 20, distance = 1, monster_count = 5, reachable = true, is_familiar = true}, tools)
assert(guarded.eligible == false and guarded.reason == "friendly_summon")
local unreachable = targeting.decision({name = "Demon", hp = 20, distance = 1, monster_count = 5, reachable = false}, tools)
assert(unreachable.eligible == false and unreachable.reason == "unreachable")

tools.target_rules = {rules[1]}
local noMatch = targeting.decision(rat, tools)
assert(noMatch.eligible == false and noMatch.reason == "no_target_rule")

local index, addDecision = targeting.addTargetRule(tools, {enabled = false, name_pattern = " dragon ", priority = 20, chase_policy = "follow"})
assert(index == 2 and addDecision.allowed == true and tools.target_rules[2].name_pattern == "dragon")
local updated, updateDecision = targeting.updateTargetRule(tools, 2, {enabled = true, min_hp = 70, max_hp = 20, min_distance = 4, max_distance = 2})
assert(updateDecision.allowed == true and updated.enabled == true)
assert(updated.min_hp == 70 and updated.max_hp == 70)
assert(updated.min_distance == 4 and updated.max_distance == 4)
local moved, moveDecision = targeting.moveTargetRule(tools, 2, -1)
assert(moved == 1 and moveDecision.allowed == true and tools.target_rules[1].name_pattern == "dragon")
local nextIndex, removeDecision = targeting.removeTargetRule(tools, 1)
assert(nextIndex == 1 and removeDecision.allowed == true and #tools.target_rules == 1)

local many = {}
for i = 1, 20 do many[i] = {name_pattern = "monster " .. tostring(i)} end
local bounded = targeting.sanitizeTargetRules(many)
assert(#bounded == 16)
local denied, deniedDecision = targeting.addTargetRule({target_rules = bounded}, {})
assert(denied == nil and deniedDecision.reason == "target_rule_limit")

local exported = persistence.exportProfile({schema_version = "ctoa-helper-profile-v1", tools = tools}, "Target rules")
local serialized = schema.serializeLua(exported, "profile")
for _, key in ipairs({"target_rules", "name_pattern", "min_hp", "max_hp", "min_distance", "max_distance", "min_count", "max_count", "priority", "chase_policy"}) do
  assert(string.find(serialized, key, 1, true) ~= nil)
end
local contract = targeting.contract()
assert(contract.owns_target_rule_editor == true and contract.owns_target_rule_matching == true)
assert(contract.target_rule_limit == 16 and contract.runtime_actions == false and contract.attacks == false)
''',
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(TARGETING), str(SCHEMA), str(PERSISTENCE)],
        check=False,
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_target_rule_editor_is_native_autosaved_and_applied_to_chase() -> None:
    ui = UI.read_text(encoding="utf-8")
    helper = HELPER.read_text(encoding="utf-8")

    for widget_id in (
        "ctoaHuntingTargetRulesTab",
        "ctoaTargetRuleEditor",
        "ctoaTargetRuleName",
        "ctoaTargetRuleHp",
        "ctoaTargetRuleDistance",
        "ctoaTargetRuleCount",
        "ctoaTargetRulePriority",
        "ctoaTargetRuleChase",
        "ctoaTargetRuleEnabled",
        "ctoaTargetRuleAdd",
        "ctoaTargetRuleRemove",
        "ctoaTargetRuleUp",
        "ctoaTargetRuleDown",
    ):
        assert f'"{widget_id}' in ui
    assert "nameEdit.onTextChange" in ui
    assert 'ctx.mark_profile_dirty("target_rule_editor")' in ui
    assert "targeting_module = externalTargeting" in helper
    assert "candidate.monster_count = #candidates" in helper
    assert 'targetDecision.chase_policy == "follow"' in helper
    assert 'targetDecision.chase_policy == "stand"' in helper
    assert "g_game.attack" not in ui
    assert "applyChaseMode" not in ui


def test_rule_editors_share_chrome_and_settings_have_one_visible_owner() -> None:
    ui = UI.read_text(encoding="utf-8")

    assert "function Ui.addRuleEditorChrome" in ui
    assert ui.count("Ui.addRuleEditorChrome(ctx, window, {") == 3
    assert "owns_rule_editor_chrome = true" in ui
    assert "owns_single_settings_surface = true" in ui
    assert '{key = "ui_tab", id = "ctoaUiTab", text = "  Settings"' in ui
    assert '{key = "profile_tab", id = "ctoaProfileTab", text = "  Profile"' in ui
    assert 'title = "Settings", subtitle = "hotkey / appearance / HUD"' in ui
    assert 'title = "Profile", subtitle = "healing / modules / presets"' in ui
    assert ui.count('title = "Settings"') == 1

    settings_start = ui.index("function Ui.renderEnginePanel")
    settings_end = ui.index("function Ui.contract", settings_start)
    settings_source = ui[settings_start:settings_end]
    assert '"ctoaUiHudEnabled"' in settings_source
    assert '"ctoaUiHudPos"' in settings_source
    assert '"ctoaUiThemePreset"' in settings_source
    assert '"ctoaUiCompactMode"' in settings_source


def test_rune_and_stance_parameters_are_editable_separately_from_runtime_arming() -> None:
    ui = UI.read_text(encoding="utf-8")

    for widget_id in (
        "ctoaHuntingActionsTab",
        "ctoaCombatActionRuleEditor",
        "ctoaCombatActionText",
        "ctoaCombatActionKind",
        "ctoaCombatActionMode",
        "ctoaCombatActionMin",
        "ctoaCombatActionMax",
        "ctoaCombatActionCooldown",
        "ctoaCombatActionEnabled",
        "ctoaCombatActionTarget",
        "ctoaCombatActionPvpSafe",
        "ctoaCombatActionAdd",
        "ctoaCombatActionRemove",
        "ctoaCombatActionUp",
        "ctoaCombatActionDown",
        "ctoaAutoStanceMagic",
    ):
        assert f'"{widget_id}"' in ui
    assert 'ctx.mark_profile_dirty("combat_action_rule_editor")' in ui
    assert 'helper.setRuntimeModuleEnabled({"tools", "auto_stance"}' in ui
    actions_start = ui.index('ctx.widgets.hunting_actions_summary')
    runtime_start = ui.index('ctx.widgets.hunting_magic_runtime_summary')
    actions_source = ui[actions_start:runtime_start]
    assert "setRuntimeModuleEnabled" not in actions_source
    assert "g_game" not in actions_source
    assert "talk(" not in actions_source


def test_combat_action_rules_are_ordered_and_drive_rune_and_stance_selection(tmp_path: Path) -> None:
    lua = _lua()
    assert lua
    probe = tmp_path / "combat_action_rule_probe.lua"
    probe.write_text(
        r'''
local combat = dofile(arg[1])
local schema = dofile(arg[2])
local persistence = dofile(arg[3])
local tools = {
  rune_enabled = true, auto_stance = true, last_rune_ms = 0, last_stance_ms = 0,
  combat_action_rules = {
    {enabled = true, kind = "stance", action_text = "custom defensive", min_count = 4, max_count = 9, cooldown_ms = 2000, stance_mode = "defensive"},
    {enabled = true, kind = "rune", action_text = "Custom Rune", hotkey = "F8", min_count = 2, max_count = 5, cooldown_ms = 1000, require_target = true, pvp_safe = true},
  },
}
local stance = combat.stanceAction(tools, {target_present = true, nearby = 5, now_ms = 5000})
assert(stance and stance.kind == "stance" and stance.spell == "custom defensive" and stance.action_index == 1)
tools.combat_action_rules[1].state_id = "defensive_stance"
local guardedActive = combat.stanceAction(tools, {target_present = true, nearby = 5, now_ms = 5000, spell_state_decisions = {defensive_stance = {allowed = false, reason = "state_already_active"}}})
local guardedInactive = combat.stanceAction(tools, {target_present = true, nearby = 5, now_ms = 5000, spell_state_decisions = {defensive_stance = {allowed = true, reason = "fresh_inactive_state"}}})
assert(guardedActive == nil)
assert(guardedInactive and guardedInactive.state_id == "defensive_stance")
local descriptor = combat.dispatchDescriptor(guardedInactive, tools)
assert(descriptor.kind == "spell" and descriptor.words == "custom defensive" and descriptor.fight_mode == "defensive")
combat.recordActionSuccess(tools, guardedInactive, 5000)
assert(tools.last_stance_ms == 5000 and tools.active_stance == "defensive")
assert(tools.last_spell_state_casts.defensive_stance == 5000)
local rune = combat.runeAction(tools, {target_present = true, visible = 3, now_ms = 5000, rune_target_safe = true})
assert(rune and rune.kind == "rune" and rune.rune_name == "Custom Rune" and rune.hotkey == "F8" and rune.action_index == 2)
local blockedRune = combat.runeAction(tools, {target_present = true, visible = 6, now_ms = 5000, rune_target_safe = true})
assert(blockedRune == nil)

local index, addDecision = combat.addCombatActionRule(tools, {enabled = false, kind = "rune", action_text = "Another"})
assert(index == 3 and addDecision.allowed == true and addDecision.runtime_actions == false)
local updated, updateDecision = combat.updateCombatActionRule(tools, 3, {enabled = true, kind = "stance", stance_mode = "offensive", min_count = 3, max_count = 1})
assert(updateDecision.allowed == true and updated.kind == "stance" and updated.max_count == 3)
local moved, moveDecision = combat.moveCombatActionRule(tools, 3, -1)
assert(moved == 2 and moveDecision.allowed == true)
local nextIndex, removeDecision = combat.removeCombatActionRule(tools, 2)
assert(nextIndex == 2 and removeDecision.allowed == true and #tools.combat_action_rules == 2)
local contract = combat.contract()
assert(contract.owns_combat_action_rule_editor == true and contract.combat_action_rule_limit == 16)
assert(contract.runtime_actions == false and contract.casts == false and contract.uses_items == false)
local exported = persistence.exportProfile({schema_version = "ctoa-helper-profile-v1", tools = tools}, "Action rules")
local serialized = schema.serializeLua(exported, "profile")
for _, key in ipairs({"combat_action_rules", "kind", "action_text", "hotkey", "min_count", "max_count", "cooldown_ms", "stance_mode", "state_id", "require_target", "pvp_safe"}) do
  assert(string.find(serialized, key, 1, true) ~= nil)
end
''',
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(OTCLIENT_DIR / "ctoa_helper_combat_runtime.lua"), str(SCHEMA), str(PERSISTENCE)],
        check=False,
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
