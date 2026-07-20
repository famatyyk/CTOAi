from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.ops.otclient_helper_profile_audit import audit_profile


ROOT = Path(__file__).resolve().parents[1]
LUA = ROOT / "scripts" / "lua" / "otclient"


def _run_lua(tmp_path: Path, source: str, *modules: str) -> None:
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for Helper profile validation"
    probe = tmp_path / "probe.lua"
    probe.write_text(source, encoding="utf-8")
    completed = subprocess.run(
        [lua, str(probe), *(str(LUA / module) for module in modules)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_vocation_detection_routes_promoted_and_base_vocations(tmp_path: Path):
    _run_lua(
        tmp_path,
        """
local profiles = dofile(arg[1])
local function player(id, name)
  return {getVocationId=function() return id end, getName=function() return name end}
end
assert(profiles.detect(player(1, "Ek One")) == "ek")
assert(profiles.detect(player(8, "Elite One")) == "ek")
assert(profiles.detect(player(3, "Ms One")) == "ms")
assert(profiles.detect(player(5, "Master One")) == "ms")
assert(profiles.detect(player(4, "Ed One")) == "ed")
assert(profiles.detect(player(6, "Elder One")) == "ed")
assert(profiles.detect(player(2, "Rp One")) == "rp")
assert(profiles.detect(player(7, "Royal One")) == "rp")
local candidates = profiles.candidates("ms", player(3, "Master One"))
assert(candidates[1] == "/ctoa_user_master_one_ctoa_ms_profile.lua")
assert(candidates[2] == "/ctoa_user_ms_profile.lua")
assert(candidates[5] == "mods/ctoa_otclient/ctoa_ms_profile.lua")
assert(profiles.contract().runtime_actions == false)
assert(profiles.contract().owns_data_only_pack_validation == true)
""",
        "ctoa_helper_vocation_profiles.lua",
    )


def test_vocation_pack_validation_is_bounded_data_only_and_fail_closed(tmp_path: Path):
    _run_lua(
        tmp_path,
        """
local profiles = dofile(arg[1])
for index = 2, 5 do
  local profile = dofile(arg[index])
  local decision = profiles.validatePack(profile, profile.vocation)
  assert(decision.allowed == true and decision.reason == "pack_ready")
  assert(decision.data_only == true and decision.runtime_actions == false)
  assert(decision.node_count <= decision.max_nodes)
end
local mismatch = profiles.validatePack({schema_version="ctoa-helper-profile-v1",vocation="ms",enabled=false,safe_boot_runtime_disabled=true}, "ek")
assert(mismatch.allowed == false and mismatch.reason == "pack_invalid")
local executable = profiles.validatePack({schema_version="ctoa-helper-profile-v1",vocation="ek",enabled=false,safe_boot_runtime_disabled=true,callback=function() end}, "ek")
assert(executable.allowed == false and executable.errors[1] ~= nil)
local armed = profiles.validatePack({schema_version="ctoa-helper-profile-v1",vocation="ek",enabled=true,safe_boot_runtime_disabled=true}, "ek")
assert(armed.allowed == false)
""",
        "ctoa_helper_vocation_profiles.lua",
        "ctoa_ek_profile.lua",
        "ctoa_ms_profile.lua",
        "ctoa_ed_profile.lua",
        "ctoa_rp_profile.lua",
    )


def test_vocation_deltas_replay_over_canonical_defaults_without_arming_runtime(tmp_path: Path):
    _run_lua(
        tmp_path,
        """
local profiles = dofile(arg[1])
local schema = dofile(arg[2])
local ruleEngine = dofile(arg[3])
local defaults = schema.defaultProfile()
local expected = {
  ms = {spell="exura vita", attack="exevo gran mas vis", chase=false, heal_friend=false},
  ed = {spell="exura vita", attack="exevo gran mas frigo", chase=false, heal_friend=true},
  rp = {spell="exura gran san", attack="exevo mas san", chase=true, heal_friend=false},
}
for index = 4, 6 do
  local delta = dofile(arg[index])
  local pack = profiles.validatePack(delta, delta.vocation)
  assert(pack.allowed == true)
  local migrated, plan = schema.migrate(delta, defaults, ruleEngine)
  assert(migrated ~= nil and plan.allowed == true)
  assert(migrated.enabled == false and migrated.safe_boot_runtime_disabled == true)
  assert(migrated.tools.auto_attack == false and migrated.tools.spell_rotation == false)
  assert(migrated.tools.auto_exeta == false and migrated.tools.rune_enabled == false)
  assert(migrated.tools.cavebot_enabled == false and migrated.tools.timer_enabled == false)
  assert(migrated.modules.overview == true and migrated.healing.potion_enabled == true)
  local row = expected[delta.vocation]
  assert(migrated.healing.spell == row.spell)
  assert(migrated.tools.rotation_spells[1].words == row.attack)
  assert(migrated.tools.chase == row.chase)
  assert(migrated.modules.heal_friend == row.heal_friend)
  local replayed, replayPlan = schema.migrate(migrated, defaults, ruleEngine)
  assert(replayed ~= nil and replayPlan.allowed == true)
  assert(replayed.enabled == false and replayed.tools.rotation_spells[1].words == row.attack)
end
""",
        "ctoa_helper_vocation_profiles.lua",
        "ctoa_helper_profile_schema.lua",
        "ctoa_helper_rule_engine.lua",
        "ctoa_ms_profile.lua",
        "ctoa_ed_profile.lua",
        "ctoa_rp_profile.lua",
    )


def test_shell_renders_detected_vocation_in_profile_hint():
    shell = (LUA / "ctoa_native_helper.lua").read_text(encoding="utf-8")
    assert '"Look ID: " .. string.upper(tostring(Helper.vocation_id or "unknown"))' in shell


def test_live_promotion_manifest_includes_vocation_router_and_all_profiles():
    wrapper = (ROOT / "scripts" / "windows" / "solteria_helper_test_env.ps1").read_text(
        encoding="utf-8"
    )
    package_function = wrapper.split("function Get-DevPackageFiles", 1)[1].split(
        "function Get-LiveLegacyFiles", 1
    )[0]
    for name in (
        "ctoa_helper_vocation_profiles.lua",
        "ctoa_ek_profile.lua",
        "ctoa_ms_profile.lua",
        "ctoa_ed_profile.lua",
        "ctoa_rp_profile.lua",
    ):
        assert f'mods/ctoa_otclient/{name}' in package_function


def test_ek_rotation_never_falls_back_to_single_target_in_large_pack(tmp_path: Path):
    _run_lua(
        tmp_path,
        """
local runtime = dofile(arg[1])
local spells = {
  {words="exori gran", mob_count=4, min_nearby=3, cooldown_ms=6000, last_cast_ms=9500},
  {words="exori", mob_count=4, min_nearby=2, cooldown_ms=4000, last_cast_ms=9500},
  {words="exori gran ico", mob_count=4, min_nearby=1, max_nearby=2, cooldown_ms=1000, last_cast_ms=0},
  {words="exori ico", mob_count=4, min_nearby=1, max_nearby=2, cooldown_ms=1000, last_cast_ms=0},
}
assert(runtime.rotationSpell(spells, {now_ms=10000, rotation_interval_ms=1000}) == nil)
spells[1].last_cast_ms = 0
local selected = runtime.rotationSpell(spells, {now_ms=10000, rotation_interval_ms=1000})
assert(selected.words == "exori gran")
""",
        "ctoa_helper_combat_runtime.lua",
    )


def test_ek_stance_selects_attack_for_small_pack_and_defense_for_large_pack(tmp_path: Path):
    _run_lua(
        tmp_path,
        """
local runtime = dofile(arg[1])
local cfg = {auto_stance=true, last_stance_ms=0, combat_action_rules={
 {enabled=true,kind="stance",action_text="utito tempo",min_count=1,max_count=2,cooldown_ms=1000,stance_mode="offensive",state_id="strengthened"},
 {enabled=true,kind="stance",action_text="utamo tempo",min_count=4,max_count=99,cooldown_ms=1000,stance_mode="defensive",state_id="defensive_stance"}}}
local states = {strengthened={allowed=true},defensive_stance={allowed=true}}
local attack = runtime.stanceAction(cfg, {target_present=true, nearby=2, now_ms=2000, spell_state_decisions=states})
assert(attack.stance == "offensive" and attack.spell == "utito tempo")
local defense = runtime.stanceAction(cfg, {target_present=true, nearby=4, now_ms=2000, spell_state_decisions=states})
assert(defense.stance == "defensive" and defense.spell == "utamo tempo")
assert(runtime.stanceAction(cfg, {target_present=true, nearby=3, now_ms=2000, spell_state_decisions=states}) == nil)
""",
        "ctoa_helper_combat_runtime.lua",
    )


def test_targeting_rejects_unreachable_candidate_when_required(tmp_path: Path):
    _run_lua(
        tmp_path,
        """
local targeting = dofile(arg[1])
local denied = targeting.decision({name="demon",distance=2,hp=90,reachable=false}, {require_reachable_target=true})
assert(denied.eligible == false and denied.reason == "unreachable")
local allowed = targeting.decision({name="demon",distance=2,hp=90,reachable=false}, {require_reachable_target=false})
assert(allowed.eligible == true)
""",
        "ctoa_helper_targeting.lua",
    )


def test_profile_persistence_exports_modules_vocation_and_real_workdir_path():
    source = (LUA / "ctoa_helper_profile_persistence.lua").read_text(encoding="utf-8")
    helper = (LUA / "ctoa_native_helper.lua").read_text(encoding="utf-8")
    wrapper = (ROOT / "scripts" / "windows" / "solteria_helper_test_env.ps1").read_text(encoding="utf-8")
    reporter = (LUA / "ctoa_helper_client_reporter.lua").read_text(encoding="utf-8")

    assert "modules = copyTable(cfg.modules or {})" in source
    assert "vocation = cfg.vocation" in source
    assert 'return work .. mutableFileName(kind, explicit)' in source
    assert 'work_dir_suffix = "ctoa_user_ek_profile.lua"' in source
    assert 'work_dir_suffix = "ctoa_user_ui_prefs.lua"' in source
    assert 'rawget(_G, "CTOA_HELPER_VOCATION_PROFILES")' in helper
    assert 'vocation = tostring(data.vocation or "unknown")' in reporter
    assert 'profile_name = tostring(data.profile_name or "unknown")' in reporter
    for name in [
        "ctoa_helper_vocation_profiles.lua",
        "ctoa_ek_profile.lua",
        "ctoa_ms_profile.lua",
        "ctoa_ed_profile.lua",
        "ctoa_rp_profile.lua",
    ]:
        assert name in wrapper


def test_profile_save_path_maps_packaged_resources_to_mutable_user_files(tmp_path: Path):
    _run_lua(
        tmp_path,
        r'''
local persistence = dofile(arg[1])
local path = persistence.resolveSavePath("profile", "ctoa_otclient/ctoa_ms_profile.lua", "C:/client/")
assert(path == "C:/client/ctoa_user_ms_profile.lua", path)
local userPath = persistence.resolveSavePath("profile", "user_dir/ctoa_otclient/ctoa_ed_profile.lua", "C:/client")
assert(userPath == "C:/client/ctoa_user_ed_profile.lua", userPath)
local characterPath = persistence.resolveSavePath("profile", "/ctoa_user_master_one_ctoa_ms_profile.lua", "C:/client")
assert(characterPath == "C:/client/ctoa_user_master_one_ctoa_ms_profile.lua", characterPath)
local prefsPath = persistence.resolveSavePath("ui_prefs", "mods/ctoa_otclient/ctoa_ui_prefs.lua", "C:/client")
assert(prefsPath == "C:/client/ctoa_user_ui_prefs.lua", prefsPath)
local exported = persistence.exportProfile({vocation="rp", modules={healing=true}, tools={}, healing={}}, "RP")
assert(exported.vocation == "rp" and exported.modules.healing == true)
''',
        "ctoa_helper_profile_persistence.lua",
    )


@pytest.mark.parametrize("profile_name", ["ctoa_ek_profile.lua", "ctoa_ms_profile.lua", "ctoa_ed_profile.lua", "ctoa_rp_profile.lua"])
def test_every_vocation_profile_passes_safe_migration_audit(profile_name: str):
    report = audit_profile(LUA / profile_name)
    assert report.status == "passed", [finding.reason for finding in report.findings]
