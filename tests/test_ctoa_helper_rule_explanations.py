from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OTCLIENT = ROOT / "scripts/lua/otclient"
EXPLANATIONS = OTCLIENT / "ctoa_helper_rule_explanations.lua"
TARGETING = OTCLIENT / "ctoa_helper_targeting.lua"
COMBAT = OTCLIENT / "ctoa_helper_combat_runtime.lua"
HELPER = OTCLIENT / "ctoa_native_helper.lua"
MODULES = OTCLIENT / "ctoa_helper_modules.lua"
WRAPPER = ROOT / "scripts/windows/solteria_helper_test_env.ps1"


def _lua() -> str | None:
    return shutil.which("lua") or shutil.which("lua5.4") or shutil.which("lua54")


def test_rule_explanations_are_passive_packaged_and_consumed_by_native_ui() -> None:
    source = EXPLANATIONS.read_text(encoding="utf-8")
    helper = HELPER.read_text(encoding="utf-8")
    modules = MODULES.read_text(encoding="utf-8")
    wrapper = WRAPPER.read_text(encoding="utf-8")

    assert 'rawget(_G, "CTOA_HELPER_RULE_EXPLANATIONS")' in source
    assert "_G.CTOA_HELPER_RULE_EXPLANATIONS = RuleExplanations" in source
    assert 'name = "ctoa_helper_rule_explanations"' in modules
    assert 'depends_on = {"ctoa_helper_rule_explanations"}' in modules
    assert '"ctoa_helper_targeting", "ctoa_helper_rule_explanations"' in modules
    assert 'mods/ctoa_otclient/ctoa_helper_rule_explanations.lua' in wrapper
    assert 'externalRuleExplanations, "summary", trace' in helper
    assert "Helper.last_target_rule_trace" in helper
    assert "Helper.last_spell_rule_trace" in helper
    assert "Helper.last_action_rule_trace" in helper
    for forbidden in (
        "g_game",
        "getSpectators",
        "autoWalk(",
        "castSpell(",
        "useInventoryItem(",
        "dofile(",
    ):
        assert forbidden not in source


def test_target_spell_and_action_reasons_follow_real_selection_loops(tmp_path: Path) -> None:
    lua = _lua()
    assert lua, "Lua interpreter is required for P27.2 validation"
    probe = tmp_path / "rule_explanations_probe.lua"
    probe.write_text(
        r'''
local explanations = dofile(arg[1])
local targeting = dofile(arg[2])
local combat = dofile(arg[3])

local tools = {
  target_rules = {
    {enabled = true, name_pattern = "demon", min_hp = 0, max_hp = 40, min_distance = 0, max_distance = 7, min_count = 1, max_count = 9, priority = 10, chase_policy = "follow"},
    {enabled = true, name_pattern = "demon", min_hp = 41, max_hp = 100, min_distance = 0, max_distance = 7, min_count = 1, max_count = 9, priority = 20, chase_policy = "stand"},
  },
}
local targetDecision = targeting.decision({name = "Demon", hp = 55, distance = 3, monster_count = 2, reachable = true}, tools)
assert(targetDecision.eligible == true and targetDecision.target_rule_index == 2)
assert(targetDecision.rule_explanation.status == "matched")
assert(targetDecision.rule_explanation.reason_code == "rule_matched")
assert(targetDecision.rule_explanation.selected_index == 2)
assert(targetDecision.rule_explanation.rules[1].reason_code == "hp_above_max")
assert(targetDecision.rule_explanation.rules[2].reason_code == "matched")
assert(explanations.summary(targetDecision.rule_explanation) == "Target matched r2: rule_matched")

local blockedTarget = targeting.decision({name = "Demon", hp = 55, distance = 9, monster_count = 2, reachable = true}, tools)
assert(blockedTarget.eligible == false and blockedTarget.reason == "no_target_rule")
assert(blockedTarget.rule_explanation.status == "blocked")
assert(blockedTarget.rule_explanation.rules[2].reason_code == "distance_above_max")

local spellTools = {
  rotation_interval_ms = 1000,
  last_attack_spell_ms = 0,
  attack_action_lock_until_ms = 0,
  last_spell_casts = {},
  rotation_spells = {
    {enabled = true, words = "exori", use_mob_count = true, min_nearby = 3, max_nearby = 8, scan_range = 1, cooldown_ms = 1000, directional = false},
    {enabled = true, words = "exori gran", use_mob_count = true, min_nearby = 1, max_nearby = 8, scan_range = 1, cooldown_ms = 1000, directional = false},
  },
}
local spell, spellTrace = combat.selectRotationSpell(spellTools, {adjacent = 2}, 5000)
assert(spell.words == "exori gran" and spellTrace.selected_index == 2)
assert(spellTrace.rules[1].reason_code == "count_below_min")
assert(spellTrace.rules[2].reason_code == "selected")
assert(explanations.summary(spellTrace) == "Spell matched r2: rule_selected")

spellTools.last_spell_casts["exori gran"] = 4900
local noSpell, cooldownTrace = combat.selectRotationSpell(spellTools, {adjacent = 2}, 5000)
assert(noSpell == nil and cooldownTrace.reason_code == "no_spell_rule")
assert(cooldownTrace.rules[2].reason_code == "cooldown")

local actionTools = {
  rune_enabled = true, rune_requires_target = true, last_rune_ms = 0,
  attack_action_lock_until_ms = 0,
  combat_action_rules = {
    {enabled = true, kind = "rune", action_text = "ava", hotkey = "F5", min_count = 3, max_count = 8, cooldown_ms = 1000, stance_mode = "offensive", state_id = "", require_target = true, pvp_safe = true},
    {enabled = true, kind = "rune", action_text = "sd", hotkey = "F6", min_count = 1, max_count = 2, cooldown_ms = 1000, stance_mode = "offensive", state_id = "", require_target = true, pvp_safe = true},
  },
}
local rune, runeTrace = combat.runeAction(actionTools, {target_present = true, visible = 2, now_ms = 5000, rune_target_safe = true})
assert(rune.rune_name == "sd" and rune.action_index == 2)
assert(runeTrace.rules[1].reason_code == "count_below_min")
assert(runeTrace.rules[2].reason_code == "selected")
assert(explanations.summary(runeTrace) == "Action matched r2: rule_selected")

local noRune, unsafeTrace = combat.runeAction(actionTools, {target_present = true, visible = 2, now_ms = 5000, rune_target_safe = false})
assert(noRune == nil and unsafeTrace.reason_code == "no_rune_rule")
assert(unsafeTrace.rules[2].reason_code == "pvp_unsafe")
''',
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(EXPLANATIONS), str(TARGETING), str(COMBAT)],
        check=False,
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_unknown_and_stale_observations_fail_closed_visibly(tmp_path: Path) -> None:
    lua = _lua()
    assert lua
    probe = tmp_path / "rule_explanation_freshness_probe.lua"
    probe.write_text(
        r'''
local explanations = dofile(arg[1])
local unknown = explanations.trace("spell", "rule_selected", {
  status = "matched", observation_status = "unknown", selected_index = 1,
})
assert(unknown.status == "blocked" and unknown.reason_code == "observation_unknown")
assert(explanations.summary(unknown) == "Spell blocked r1: observation_unknown")
local stale = explanations.trace("target", "rule_matched", {
  status = "matched", observation_status = "stale", selected_index = 2,
})
assert(stale.status == "blocked" and stale.reason_code == "observation_stale")
assert(explanations.summary(stale) == "Target blocked r2: observation_stale")
local contract = explanations.contract()
assert(contract.accepts_normalized_observations_only == true)
assert(contract.rescans_client == false)
assert(contract.unknown_observations_fail_closed == true)
assert(contract.stale_observations_fail_closed == true)
assert(contract.runtime_actions == false and contract.dispatch_allowed == false)
''',
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(EXPLANATIONS)],
        check=False,
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
