from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OTCLIENT_DIR = ROOT / "scripts" / "lua" / "otclient"
COMBAT = OTCLIENT_DIR / "ctoa_helper_combat_runtime.lua"
SCHEMA = OTCLIENT_DIR / "ctoa_helper_profile_schema.lua"
PERSISTENCE = OTCLIENT_DIR / "ctoa_helper_profile_persistence.lua"
UI = OTCLIENT_DIR / "ctoa_helper_ui.lua"
HELPER = OTCLIENT_DIR / "ctoa_native_helper.lua"


def _lua() -> str | None:
    return shutil.which("lua") or shutil.which("lua5.4") or shutil.which("lua54")


def test_magic_rule_editor_is_bounded_ordered_persistent_and_action_free(
    tmp_path: Path,
) -> None:
    lua = _lua()
    assert lua, "Lua interpreter is required for magic-rule editor validation"
    probe = tmp_path / "magic_rule_editor_probe.lua"
    probe.write_text(
        r'''
local combat = dofile(arg[1])
local schema = dofile(arg[2])
local persistence = dofile(arg[3])

local many = {}
for index = 1, 20 do
  many[index] = {
    enabled = true,
    words = "  exori " .. tostring(index) .. "\n",
    use_mob_count = true,
    min_nearby = index == 1 and 30 or 1,
    max_nearby = index == 1 and 2 or 99,
    scan_range = index == 1 and 50 or 1,
    cooldown_ms = index == 1 and 10 or 2000,
    directional = index == 2,
  }
end
local tools = {}
local rules, replaceDecision = combat.replaceRotationRules(tools, many)
assert(replaceDecision.allowed == true and replaceDecision.runtime_actions == false)
assert(replaceDecision.dispatch_allowed == false and #rules == 16)
assert(rules[1].words == "exori 1" and rules[1].min_nearby == 20)
assert(rules[1].max_nearby == 20 and rules[1].scan_range == 10)
assert(rules[1].cooldown_ms == 250 and rules[2].directional == true)

local deniedIndex, limitDecision = combat.addRotationRule(tools, {words = "utito tempo"})
assert(deniedIndex == nil and limitDecision.reason == "rotation_rule_limit")

tools.rotation_spells = {
  {enabled = false, words = "exori", min_nearby = 1, max_nearby = 99, scan_range = 1, cooldown_ms = 1000},
  {enabled = true, words = "exori gran", min_nearby = 2, max_nearby = 6, scan_range = 1, cooldown_ms = 1000},
}
local index, addDecision = combat.addRotationRule(tools)
assert(index == 3 and addDecision.allowed == true)
assert(tools.rotation_spells[3].enabled == false and tools.rotation_spells[3].words == "")
local updated, updateDecision = combat.updateRotationRule(tools, 3, {
  words = "  exori min  ", enabled = true, use_mob_count = true,
  min_nearby = 4, max_nearby = 2, scan_range = 3,
  cooldown_ms = 1750, directional = true,
})
assert(updateDecision.allowed == true and updateDecision.runtime_actions == false)
assert(updated.words == "exori min" and updated.enabled == true)
assert(updated.min_nearby == 4 and updated.max_nearby == 4)
assert(updated.scan_range == 3 and updated.cooldown_ms == 1750 and updated.directional == true)

local moved, moveDecision = combat.moveRotationRule(tools, 3, -1)
assert(moved == 2 and moveDecision.allowed == true)
assert(tools.rotation_spells[2].words == "exori min")
local nextIndex, removeDecision = combat.removeRotationRule(tools, 2)
assert(nextIndex == 2 and removeDecision.allowed == true)
assert(#tools.rotation_spells == 2 and tools.rotation_spells[2].words == "exori gran")

local selected = combat.selectRotationSpell(tools, {adjacent = 3}, 5000)
assert(selected ~= nil and selected.words == "exori gran")
local state = combat.rotationRuleState(tools, 99)
assert(state.index == 2 and state.count == 2 and string.find(state.summary, "2/2", 1, true) == 1)

local exported = persistence.exportProfile({
  schema_version = "ctoa-helper-profile-v1", vocation = "ek", enabled = false,
  safe_boot_runtime_disabled = true, tools = tools,
}, "Editable EK")
assert(#exported.tools.rotation_spells == 2)
local serialized = schema.serializeLua(exported, "profile")
for _, key in ipairs({"enabled", "words", "use_mob_count", "min_nearby", "max_nearby", "scan_range", "cooldown_ms", "directional"}) do
  assert(string.find(serialized, key .. " =", 1, true) ~= nil)
end

local contract = combat.contract()
assert(contract.owns_rotation_rule_editor == true)
assert(contract.owns_rotation_rule_sanitization == true)
assert(contract.rotation_rule_limit == 16)
assert(contract.runtime_actions == false and contract.attacks == false and contract.casts == false)
''',
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(COMBAT), str(SCHEMA), str(PERSISTENCE)],
        check=False,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_magic_rule_editor_replaces_fixed_ek_rows_and_autosaves() -> None:
    ui = UI.read_text(encoding="utf-8")
    helper = HELPER.read_text(encoding="utf-8")

    for widget_id in (
        "ctoaMagicRuleEditor",
        "ctoaMagicRuleWords",
        "ctoaMagicRuleEnabled",
        "ctoaMagicRuleMobCount",
        "ctoaMagicRuleDirectional",
        "ctoaMagicRuleAdd",
        "ctoaMagicRuleRemove",
        "ctoaMagicRuleUp",
        "ctoaMagicRuleDown",
        "ctoaHuntingMagicRuntimeTab",
    ):
        assert f'"{widget_id}"' in ui
    assert "wordsEdit.onTextChange" in ui
    assert "ctx.update_magic_rule({words = text})" in ui
    assert "owns_magic_rule_editor = true" in ui
    assert 'markProfileDirty("magic_rule_update")' in helper
    assert 'markProfileDirty("magic_rule_add")' in helper
    assert 'markProfileDirty("magic_rule_remove")' in helper
    assert 'markProfileDirty("magic_rule_move")' in helper
    assert '"ctoaRotationGranMobs"' not in ui
    assert '"ctoaRotationExoriMobs"' not in ui
    assert '"ctoaRotationMinMobs"' not in ui
    assert "function Helper.getRotationMin" not in helper
    assert "function Helper.setRotationMin" not in helper
