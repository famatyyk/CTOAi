from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OTCLIENT = ROOT / "scripts/lua/otclient"
PRESETS = OTCLIENT / "ctoa_helper_rule_presets.lua"
TARGETING = OTCLIENT / "ctoa_helper_targeting.lua"
COMBAT = OTCLIENT / "ctoa_helper_combat_runtime.lua"
MODULES = OTCLIENT / "ctoa_helper_modules.lua"
WRAPPER = ROOT / "scripts/windows/solteria_helper_test_env.ps1"


def _lua() -> str | None:
    return shutil.which("lua") or shutil.which("lua5.4") or shutil.which("lua54")


def test_rule_preset_module_is_passive_packaged_and_dependency_ordered() -> None:
    source = PRESETS.read_text(encoding="utf-8")
    modules = MODULES.read_text(encoding="utf-8")
    wrapper = WRAPPER.read_text(encoding="utf-8")

    assert 'rawget(_G, "CTOA_HELPER_RULE_PRESETS")' in source
    assert "_G.CTOA_HELPER_RULE_PRESETS = RulePresets" in source
    assert (
        'name = "ctoa_helper_rule_presets", file = "ctoa_helper_rule_presets.lua", '
        'phase = "profile", depends_on = {"ctoa_helper_targeting", '
        '"ctoa_helper_combat_runtime"}'
    ) in modules
    assert 'mods/ctoa_otclient/ctoa_helper_rule_presets.lua' in wrapper
    for forbidden in (
        "dofile(",
        "loadstring(",
        "g_game",
        "autoWalk(",
        "castSpell(",
        "useInventoryItem(",
    ):
        assert forbidden not in source
    assert "runtime_actions = false" in source
    assert "dispatch_allowed = false" in source
    assert "arms_runtime = false" in source


def test_rule_presets_round_trip_strictly_without_arming_runtime(tmp_path: Path) -> None:
    lua = _lua()
    assert lua, "Lua interpreter is required for P27.1 validation"
    probe = tmp_path / "rule_presets_probe.lua"
    probe.write_text(
        r'''
dofile(arg[1])
dofile(arg[2])
local presets = dofile(arg[3])

local tools = {
  auto_attack = true,
  spell_rotation = false,
  rune_enabled = true,
  target_rules = {{
    enabled = true, name_pattern = "demon", min_hp = 0, max_hp = 80,
    min_distance = 0, max_distance = 7, min_count = 1, max_count = 9,
    priority = 10, chase_policy = "follow",
  }},
  rotation_spells = {{
    enabled = true, words = "exori gran", use_mob_count = true,
    min_nearby = 3, max_nearby = 8, scan_range = 4,
    cooldown_ms = 2000, directional = false,
  }},
  combat_action_rules = {{
    enabled = false, kind = "rune", action_text = "sudden death rune",
    hotkey = "F5", min_count = 1, max_count = 4, cooldown_ms = 1000,
    stance_mode = "offensive", state_id = "", require_target = true,
    pvp_safe = true,
  }},
}

local payload, exportDecision = presets.exportPreset(tools, "  Demon hunt  ")
assert(exportDecision.allowed == true and exportDecision.runtime_actions == false)
assert(payload.schema_version == "ctoa-helper-rule-preset-v1")
assert(payload.name == "Demon hunt" and #payload.target_rules == 1)
assert(#payload.spell_rules == 1 and #payload.combat_action_rules == 1)

local destination = {
  auto_attack = false,
  spell_rotation = true,
  rune_enabled = false,
  rotation_preset = "smart",
  unrelated = "preserved",
}
local imported, importDecision = presets.importPreset(destination, payload)
assert(importDecision.allowed == true and importDecision.runtime_armed == false)
assert(imported.name == "Demon hunt")
assert(destination.target_rules[1].name_pattern == "demon")
assert(destination.rotation_spells[1].words == "exori gran")
assert(destination.combat_action_rules[1].hotkey == "F5")
assert(destination.auto_attack == false and destination.spell_rotation == true)
assert(destination.rune_enabled == false and destination.rotation_preset == "smart")
assert(destination.unrelated == "preserved")

payload.target_rules[1].name_pattern = "changed after import"
assert(destination.target_rules[1].name_pattern == "demon")
local again = presets.exportPreset(destination, "Demon hunt")
assert(again.target_rules[1].name_pattern == "demon")

local contract = presets.contract()
assert(contract.rejects_unknown_fields == true)
assert(contract.rejects_executable_values == true)
assert(contract.preserves_safe_boot == true)
assert(contract.mutates_only_rule_lists_on_import == true)
assert(contract.runtime_actions == false and contract.dispatch_allowed == false)
''',
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(TARGETING), str(COMBAT), str(PRESETS)],
        check=False,
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_rule_presets_fail_closed_atomically_on_untrusted_payloads(tmp_path: Path) -> None:
    lua = _lua()
    assert lua
    probe = tmp_path / "rule_presets_rejection_probe.lua"
    probe.write_text(
        r'''
dofile(arg[1])
dofile(arg[2])
local presets = dofile(arg[3])

local function validPayload()
  return {
    schema_version = "ctoa-helper-rule-preset-v1",
    name = "Strict",
    target_rules = {}, spell_rules = {}, combat_action_rules = {},
  }
end
local tools = {target_rules = {{sentinel = "target"}}, rotation_spells = {{sentinel = "spell"}}, combat_action_rules = {{sentinel = "action"}}, auto_attack = true}
local function denied(payload, expected)
  local result, decision = presets.importPreset(tools, payload)
  assert(result == nil and decision.allowed == false)
  assert(string.find(decision.reason, expected, 1, true) ~= nil)
  assert(decision.runtime_actions == false and decision.dispatch_allowed == false)
  assert(tools.target_rules[1].sentinel == "target")
  assert(tools.rotation_spells[1].sentinel == "spell")
  assert(tools.combat_action_rules[1].sentinel == "action")
  assert(tools.auto_attack == true)
end

local future = validPayload(); future.schema_version = "ctoa-helper-rule-preset-v2"
denied(future, "future_schema_version")
local unknown = validPayload(); unknown.script = "return g_game"
denied(unknown, "unknown_field")
local executable = validPayload(); executable.name = function() return "bad" end
denied(executable, "invalid_type")
local sparse = validPayload(); sparse.target_rules[2] = {}
denied(sparse, "sparse_array")
local extraRuleField = validPayload(); extraRuleField.spell_rules = {{
  enabled = false, words = "", use_mob_count = true, min_nearby = 1,
  max_nearby = 99, scan_range = 1, cooldown_ms = 2000,
  directional = false, callback = function() end,
}}
denied(extraRuleField, "unknown_field")
local nonCanonical = validPayload(); nonCanonical.target_rules = {{
  enabled = true, name_pattern = "DEMON", min_hp = 0, max_hp = 100,
  min_distance = 0, max_distance = 7, min_count = 0, max_count = 99,
  priority = 50, chase_policy = "inherit",
}}
denied(nonCanonical, "non_canonical_value")
''',
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(TARGETING), str(COMBAT), str(PRESETS)],
        check=False,
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
