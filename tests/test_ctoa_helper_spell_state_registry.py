from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OTCLIENT_DIR = ROOT / "scripts" / "lua" / "otclient"
REGISTRY = OTCLIENT_DIR / "ctoa_helper_spell_state_registry.lua"
HELPER = OTCLIENT_DIR / "ctoa_native_helper.lua"
MODULES = OTCLIENT_DIR / "ctoa_helper_modules.lua"


def _lua() -> str | None:
    return shutil.which("lua") or shutil.which("lua5.4") or shutil.which("lua54")


def test_haste_state_registry_is_observed_fresh_and_fail_closed(tmp_path: Path) -> None:
    lua = _lua()
    assert lua
    probe = tmp_path / "spell_state_registry_probe.lua"
    probe.write_text(
        r'''
local registry = dofile(arg[1])
local player = {}
local active = registry.observeHaste(player, 5000, {haste_flag = 64, read_states = function() return 64 end})
local inactive = registry.observeHaste(player, 5000, {haste_flag = 64, read_states = function() return 0 end})
local unknownFlag = registry.observeHaste(player, 5000, {read_states = function() return 0 end})
local unknownStates = registry.observeHaste(player, 5000, {haste_flag = 64, read_states = function() return nil end})
assert(active.state == "active" and active.reason == "observed_active")
assert(inactive.state == "inactive" and inactive.reason == "observed_inactive")
assert(unknownFlag.state == "unknown" and unknownFlag.reason == "haste_flag_unavailable")
assert(unknownStates.state == "unknown" and unknownStates.reason == "states_unavailable")

local tools = {auto_haste = true, haste_spell = "utani hur", haste_interval_ms = 1000, spell_state_max_age_ms = 1500, last_haste_ms = 0}
local activeDecision = registry.hasteDecision(tools, active, 5000)
local inactiveDecision = registry.hasteDecision(tools, inactive, 5000)
local staleDecision = registry.hasteDecision(tools, {state = "inactive", observed_at_ms = 1000}, 5000)
local unknownDecision = registry.hasteDecision(tools, unknownStates, 5000)
assert(activeDecision.allowed == false and activeDecision.reason == "haste_already_active")
assert(inactiveDecision.allowed == true and inactiveDecision.reason == "fresh_inactive_haste" and inactiveDecision.spell == "utani hur")
assert(inactiveDecision.dispatch_allowed == false and inactiveDecision.runtime_actions == false)
assert(staleDecision.allowed == false and staleDecision.reason == "haste_state_stale")
assert(unknownDecision.allowed == false and unknownDecision.reason == "haste_state_unknown")
tools.last_haste_ms = 4500
local cooldownDecision = registry.hasteDecision(tools, inactive, 5000)
assert(cooldownDecision.allowed == false and cooldownDecision.reason == "haste_cooldown")

local families = registry.sanitizeFamilies({
  {id = "haste", flag_names = {"Haste"}, spells = {"utani hur"}, max_age_ms = 1500, unknown_policy = "block"},
  {id = "strengthened", flag_names = {"PartyBuff"}, spells = {"utito tempo"}, max_age_ms = 1500, unknown_policy = "block"},
  {id = "defensive stance", flag_names = {}, spells = {"utamo tempo"}, unknown_policy = "bounded_cooldown", fallback_cooldown_ms = 30000},
})
assert(#families == 3 and families[3].id == "defensive_stance")
local flags = {Haste = 64, PartyBuff = 4096}
local replayActive = registry.observeAll(player, families, 10000, {state_flags = flags, read_states = function() return 64 + 4096 end})
local replayInactive = registry.observeAll(player, families, 11000, {state_flags = flags, read_states = function() return 0 end})
local activeMap = registry.decisionMap(families, replayActive, 10000, {})
local inactiveMap = registry.decisionMap(families, replayInactive, 11000, {})
local fallbackMap = registry.decisionMap(families, replayInactive, 11000, {})
local fallbackCooldownMap = registry.decisionMap(families, replayInactive, 12000, {defensive_stance = 11000})
assert(activeMap.haste.allowed == false and activeMap.haste.reason == "state_already_active")
assert(activeMap.strengthened.allowed == false and activeMap.strengthened.reason == "state_already_active")
assert(inactiveMap.haste.allowed == true and inactiveMap.haste.reason == "fresh_inactive_state")
assert(fallbackMap.defensive_stance.allowed == true and fallbackMap.defensive_stance.reason == "bounded_unknown_fallback")
assert(fallbackCooldownMap.defensive_stance.allowed == false and fallbackCooldownMap.defensive_stance.reason == "bounded_fallback_cooldown")
local repeatMap = registry.decisionMap(families, replayInactive, 11000, {})
assert(repeatMap.haste.allowed == inactiveMap.haste.allowed and repeatMap.haste.reason == inactiveMap.haste.reason)

local contract = registry.contract()
assert(contract.owns_haste_observation == true and contract.owns_haste_decision == true)
assert(contract.owns_family_observation == true and contract.owns_family_decisions == true)
assert(contract.vocation_spell_families_are_data == true and contract.bounded_unknown_fallback_is_explicit == true)
assert(contract.unknown_fails_closed == true and contract.stale_fails_closed == true)
assert(contract.runtime_actions == false and contract.casts == false and contract.scans_creatures == false)
''',
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(REGISTRY)],
        check=False,
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_helper_uses_observed_haste_state_instead_of_timer_only_casting() -> None:
    helper = HELPER.read_text(encoding="utf-8")
    modules = MODULES.read_text(encoding="utf-8")
    registry = REGISTRY.read_text(encoding="utf-8")

    assert 'rawget(_G, "CTOA_HELPER_SPELL_STATE_REGISTRY")' in helper
    assert 'moduleValue(externalSpellStateRegistry, "observeHaste"' in helper
    assert 'moduleValue(externalSpellStateRegistry, "hasteDecision"' in helper
    assert 'moduleValue(externalSpellStateRegistry, "observeAll"' in helper
    assert 'moduleValue(externalSpellStateRegistry, "decisionMap"' in helper
    assert "spell_state_decisions = spellStateDecisions" in helper
    combat_runtime = (OTCLIENT_DIR / "ctoa_helper_combat_runtime.lua").read_text(encoding="utf-8")
    assert "cfg.last_spell_state_casts[item.state_id] = current" in combat_runtime
    assert "hastePlan.allowed == true" in helper
    assert "tools.auto_haste and now - tools.last_haste_ms" not in helper
    assert 'name = "ctoa_helper_spell_state_registry"' in modules
    assert 'file = "ctoa_helper_spell_state_registry.lua"' in modules
    assert 'mode = "passive_observed_state"' in registry
    assert "castSpell(" not in registry
    assert "g_game" not in registry


def test_mehah_profile_evidence_for_haste_state_is_documented_in_source_contract() -> None:
    player_lua = Path(r"C:\otclient\modules\gamelib\player.lua").read_text(encoding="utf-8")
    lua_functions = Path(r"C:\otclient\src\client\luafunctions.cpp").read_text(encoding="utf-8")
    local_player = Path(r"C:\otclient\src\client\localplayer.cpp").read_text(encoding="utf-8")

    assert "Haste = 64" in player_lua
    assert 'bindClassMemberFunction<LocalPlayer>("getStates"' in lua_functions
    assert 'callLuaField("onStatesChange", states, oldStates)' in local_player
