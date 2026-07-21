from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHOOSER_DIR = ROOT / "scripts" / "lua" / "ctoa_chooser"
SAFE_DIR = ROOT / "mods" / "ctoa_safe"
HELPER_DIR = ROOT / "scripts" / "lua" / "otclient"
WRAPPER = ROOT / "scripts" / "windows" / "solteria_helper_test_env.ps1"


def test_only_neutral_project_loader_autoloads() -> None:
    chooser = (CHOOSER_DIR / "ctoa_chooser.otmod").read_text(encoding="utf-8")
    safe = (SAFE_DIR / "ctoa_safe.otmod").read_text(encoding="utf-8")
    helper = (HELPER_DIR / "ctoa_otclient.otmod").read_text(encoding="utf-8")

    assert "autoload: true" in chooser
    assert "autoload: false" in safe
    assert "autoload: false" in helper
    assert sum(source.count("autoload: true") for source in (chooser, safe, helper)) == 1
    assert "version: 2.1.0" in chooser
    chooser_loader = (CHOOSER_DIR / "ctoa_chooser_loader.lua").read_text(encoding="utf-8")
    assert 'local LOADER_VERSION = "2.1.0"' in chooser_loader
    assert "Pelny" not in chooser_loader and "Wybor nie" not in chooser_loader


def test_project_loaders_require_explicit_exclusive_selection() -> None:
    chooser = (CHOOSER_DIR / "ctoa_chooser_loader.lua").read_text(encoding="utf-8")
    safe_loader = (SAFE_DIR / "ctoa_safe_loader.lua").read_text(encoding="utf-8")
    helper_loader = (HELPER_DIR / "ctoa_otclient_loader.lua").read_text(encoding="utf-8")

    assert 'loader.isSelected("helper") == true' in helper_loader
    assert 'projectLoader.isSelected("safe") == true' in safe_loader
    assert not helper_loader.rstrip().endswith("CTOA_OTCLIENT.init()")
    assert "scheduleEvent" not in safe_loader
    assert "connect(" not in safe_loader
    assert "last_choice" not in chooser
    assert "skip_chooser" not in chooser
    assert 'terminateAllProjects("logout")' in chooser
    assert 'Loader.active_project = projectId' in chooser


def test_safe_tree_is_independent_and_safe_booted() -> None:
    files = {path.name for path in SAFE_DIR.iterdir() if path.is_file()}
    assert files == {"ctoa_safe.otmod", "ctoa_safe_loader.lua", "ctoa_safe_helper.lua"}

    source = (SAFE_DIR / "ctoa_safe_helper.lua").read_text(encoding="utf-8")
    assert "safe_boot_runtime_disabled = true" in source
    assert "if not CFG.enabled or not RT.armed then return end" in source
    assert "if not safeProjectActive() then return end" in source
    assert "function CTOA_SAFE.setEnabled(enabled)" in source
    assert 'id = "cavebot"' not in source
    assert 'id = "settings"' not in source
    assert "CTOA_HELPER_" not in source
    assert 'local PROFILE_SCHEMA = "ctoa-safe-profile-v3"' in source
    assert 'local LEGACY_PROFILE_SCHEMA = "ctoa-safe-profile-v2"' in source
    assert 'workDir .. "ctoa_safe_" .. id .. "_profile.json"' in source
    assert "mods/ctoa_otclient" not in source
    assert "ctoa_ek_profile.lua" not in source
    assert "loadfile" not in source
    assert "loadstring" not in source


def test_safe_editors_expose_spells_rotations_support_and_ranges() -> None:
    source = (SAFE_DIR / "ctoa_safe_helper.lua").read_text(encoding="utf-8")
    assert 'mkWidget("TextEdit"' in source
    for editable_id in (
        '"healAdd"',
        '"healPlus"',
        '"healMinus"',
        '"ehPotKey"',
        '"ehManaKey"',
        '"targetPlus"',
        '"targetMinus"',
        '"rotationPlus"',
        '"rotationMinus"',
        '"ecoMSSpell"',
        '"ecoParSpell"',
        '"ecoPoiSpell"',
    ):
        assert editable_id in source
    assert '"TARGETING"' in source
    assert '"SPELL ROTATION"' in source
    assert "target_rules = cleanTargets(CFG.combat.target_rules" in source
    assert "selectConfiguredTarget(C.target_rules,C.attack_range)" in source
    for action_id in ('"healEdit"', '"healUp"', '"healDown"', '"targetEdit"', '"targetUp"', '"targetDown"', '"rotationEdit"', '"rotationUp"', '"rotationDown"'):
        assert action_id in source
    assert "moveSelected(C.rotation_spells,rotations" in source
    assert "rules = cleanHealingRules(CFG.healing.rules" in source
    assert '"healKindCycle"' in source
    assert 'kind="critical"' in source and 'kind="support"' in source
    assert "state.onSelect(item,index)" in source
    assert "targets.onSelect=function(item)" in source
    assert "rotations.onSelect=function(item)" in source
    assert "list.onSelect=function(item)" in source
    assert "if not UI.loading_selection then" in source
    assert 'label = "SUPPORT"' in source
    assert '"supportPlus"' in source and '"supportEdit"' in source
    assert "cleanSupportRules(CFG.support.rules" in source
    assert "local function runSupport()" in source
    assert 'mkWidget("UIItem"' in source
    assert 'id.."Backdrop"' in source and 'setBorderColor("#8a8a8a")' in source
    assert '"Mana potion %"' in source and '"Mana random +/-"' in source
    assert '"SUPPORT RULES: SPELL / ITEM"' in source
    assert 'resource="mana"' in source or 'resource=="mana"' in source
    assert 'useInventoryItem(rule.item_id)' in source
    assert '"Require monster count"' in source
    assert 'local nearby, mana = getNearbyMonsterCount(C.attack_range), getMpPercent()' in source
    assert 'panelW - 30' in source
    assert "not sameCreature(current,target)" in source
    for exeta_id in ('"exetaPlus"', '"exetaMinus"', '"exetaEdit"', '"exetaUp"', '"exetaDown"'):
        assert exeta_id in source
    assert 'openEditPanel("combat_exeta")' in source
    assert 'spell._last_cast=now' in source
    assert '"Ctrl+Tab"' in source and '"Ctrl+Shift+Tab"' in source
    assert "clampWindowPosition" in source
    assert '"csPresetImport"' in source and '"csPresetExport"' in source
    expected_order = ['id = "healing"', 'id = "combat"', 'id = "conditions"', 'id = "support"', 'id = "timer"']
    positions = [source.index(value) for value in expected_order]
    assert positions == sorted(positions)
    assert 'pages=healing,tools,kvshooter compatibility=' in source
    assert 'fileLog("edit panel opened module=" .. tostring(moduleId))' in source
    assert "CFG.conditions.poison_spell" in source
    assert "if isPoisoned then castSpell(CC.poison_spell) end" in source
    for parity_id in (
        '"csTabhealing"',
        '"csTabtools"',
        '"csTabshooter"',
        '"csSpellSelector"',
        '"csEnableSio"',
        '"csManaTrainingItem"',
        '"csAutoExeta"',
        '"csEnableShooter"',
    ):
        assert parity_id in source
    assert 'local KINGSVALE_SETTINGS_SCHEMA = "kingsvale-helper-json-v1"' in source
    assert "function CTOA_SAFE.importKingsValeSettings(path)" in source
    assert "helperEnabled=false" in source


def test_safe_imports_kingsvale_helper_json_contract_without_arming(tmp_path: Path) -> None:
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for KingsVale adapter validation"
    settings = tmp_path / "helper.json"
    settings.write_text("{}", encoding="utf-8")
    probe = tmp_path / "safe_kingsvale_adapter_probe.lua"
    probe.write_text(
        f"""
CTOA_PROJECT_LOADER={{active_project="safe",isSelected=function(id) return id=="safe" end}}
g_resources={{getWorkDir=function() return {tmp_path.as_posix()!r}.."/" end}}
g_game={{isOnline=function() return false end}}
cycleEvent=function() return {{}} end;removeEvent=function() end
json={{
  decode=function() return {{
    spells={{{{id=118,percent=80}},{{id=120,percent=90}},{{id=0,percent=50}}}},
    potions={{{{priority=0,id=238,percent=50}},{{priority=0,id=23373,percent=86}},{{priority=0,id=0,percent=50}}}},
    shooterProfiles={{Default={{spells={{{{id=118,priority=3,creatures=2,percent=80,selfCast=false,forceCast=false}}}},runes={{{{id=3155,priority=1,creatures=1,forceCast=true}}}},autoTargetMode=5}}}},
    selectedShooterProfile="Default",autoEatFood=true,autoChangeGold=true,autoTargetEnabled=false,autoTargetMode=5,magicShooterEnabled=true,
    magicShooterOnHold=false,currentLockedTargetId=99,autoTargetHotkey="F10",autoShooterHotkey="F11",autoTargetBoth="F12",
    autoChangeProfile="boss",autoExeta=false,autoHelperEnabled="F9",helperEnabled=true,autoReconnect=true,
    training={{{{id=45,enabled=true,percent=90}}}},haste={{{{id=39,enabled=true,safecast=true}}}},
    friendhealing={{{{name="Friend One",enabled=true,percent=90}}}},gransiohealing={{{{name="Friend Two",enabled=true,percent=70}}}},
    buff={{{{id=7,enabled=true,safecast=true}}}},utamo={{{{id=44,enabled=true,percent=77}}}},
    ammoConfig={{{{id=100,enabled=true}},{{id=101,enabled=false}}}},amuletPercent=80,ringPercent=81,
    amuletConfig={{{{id=817,enabled=true,percent=89,health=false,mana=true}}}},ringConfig={{{{id=3048,enabled=true,percent=79,health=true,mana=false}}}},
  }} end,
  encode=function() return "{{}}" end,
}}
dofile(arg[1]);assert(CTOA_SAFE.init()==true)
local ok=CTOA_SAFE.importKingsValeSettings(arg[2]);assert(ok==true)
assert(CTOA_SAFE.config.enabled==false and CTOA_SAFE.config.safe_boot_runtime_disabled==true)
local ek=CTOA_SAFE.vocationUiContract("ek");assert(ek.spell_slots==3 and ek.potion_slots==3 and ek.friend_healing==false and ek.auto_exeta==true)
local monk=CTOA_SAFE.vocationUiContract("monk");assert(monk.spell_slots==3 and monk.potion_slots==3 and monk.friend_healing==true and monk.auto_exeta==true)
local rp=CTOA_SAFE.vocationUiContract("rp");assert(rp.spell_slots==3 and rp.potion_slots==3 and rp.friend_healing==false and rp.auto_exeta==true)
local ms=CTOA_SAFE.vocationUiContract("ms");assert(ms.spell_slots==2 and ms.potion_slots==2 and ms.friend_healing==true and ms.auto_exeta==false)
local ed=CTOA_SAFE.vocationUiContract("ed");assert(ed.spell_slots==3 and ed.potion_slots==3 and ed.friend_healing==true and ed.auto_exeta==false)
assert(CTOA_SAFE.config.healing.spell_slots[1].id==118)
assert(CTOA_SAFE.config.healing.potion_rules[1].item_id==238 and CTOA_SAFE.config.healing.potion_enabled==false)
assert(CTOA_SAFE.config.healing.friend_rules[1].name=="Friend One")
assert(CTOA_SAFE.config.combat.shooter_profiles.Default.spells[1].creatures==2)
assert(CTOA_SAFE.config.tools.mana_training_item_id==45 and CTOA_SAFE.config.tools.auto_eat_food==true)
local contract=CTOA_SAFE.kingsValeContract();assert(contract.schema=="kingsvale-helper-json-v1")
assert(contract.settings.helperEnabled==false and contract.safe_boot_override==true and contract.source_files_embedded==false)
for _,key in ipairs({{"spells","shooterProfiles","selectedShooterProfile","potions","autoEatFood","autoChangeGold","autoTargetMode","magicShooterOnHold","autoTargetEnabled","currentLockedTargetId","autoTargetHotkey","autoShooterHotkey","autoTargetBoth","autoChangeProfile","autoHelperEnabled","helperEnabled","autoExeta","haste","ammoConfig","magicShooterEnabled","autoReconnect","training","buff","friendhealing","gransiohealing","utamo","amuletPercent","ringPercent","amuletConfig","ringConfig"}}) do assert(contract.settings[key]~=nil,key) end
assert(contract.settings.currentLockedTargetId==0 and contract.settings.autoReconnect==true)
assert(CTOA_SAFE.terminate()==true)
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(SAFE_DIR / "ctoa_safe_helper.lua"), str(settings)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
        cwd=tmp_path,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_official_package_stages_only_the_neutral_root_loader() -> None:
    source = WRAPPER.read_text(encoding="utf-8")
    package = source.split("function Get-DevPackageFiles", 1)[1].split(
        "function Get-DevPackageSourcePath", 1
    )[0]
    assert '"ctoa_project_loader.lua"' in package
    assert '"mods/ctoa_chooser/ctoa_chooser.otmod"' in package
    assert '"mods/ctoa_chooser/ctoa_chooser_loader.lua"' in package
    assert '"mods/ctoa_safe/' not in package
    assert '\n        "ctoa_otclient_loader.lua",' not in package
    staging = source.split("function New-DevPackage", 1)[1].split(
        "function Invoke-DevValidation", 1
    )[0]
    assert '"ctoa_safe.otmod", "ctoa_safe_loader.lua", "ctoa_safe_helper.lua"' not in staging
    assert '"helper.otui", "spell.otui", "siolist.otui", "shooterPreset.otui"' not in staging
    assert r"scripts\lua\ctoa_chooser\$name" in staging
    assert "local loader = '/ctoa_project_loader.lua'" in source
    assert "CTOA_PROJECT_LOADER.init()" in source
    assert "/XD ctoa_otclient ctoa_chooser ctoa_safe" in source
    sync = source.split("function Sync-CtoaRuntimeFiles", 1)[1].split(
        "function Ensure-CtoaBootHook", 1
    )[0]
    assert "Assert-SandboxClientPath -SandboxPath $ClientDir" in sync
    assert "Remove-Item -LiteralPath $safeDir -Recurse -Force" in sync
    assert 'StageRelative "mods\\ctoa_safe\\$name"' not in sync
    fallbacks = source.split("function Get-LiveLegacyFiles", 1)[1].split(
        "function Copy-LegacyHelperUserState", 1
    )[0]
    assert '"ctoa_otclient_loader.lua"' in fallbacks
    assert '"ctoa_chooser_prefs.lua"' in fallbacks
    assert '"mods/ctoa_safe/ctoa_helper_profile_persistence.lua"' in fallbacks
    assert '"mods/ctoa_safe/ctoa_ek_profile.lua"' in fallbacks
    migration = source.split("function Copy-LegacyHelperUserState", 1)[1].split(
        "function Remove-LiveLegacyFiles", 1
    )[0]
    assert '"ctoa_user_ek_profile.lua"' in migration
    assert '"ctoa_user_ui_prefs.lua"' in migration


def test_lua_lifecycle_loads_exactly_one_project_per_login(tmp_path: Path) -> None:
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for exclusive loader validation"

    helper_dir = tmp_path / "mods" / "ctoa_otclient"
    safe_dir = tmp_path / "mods" / "ctoa_safe"
    helper_dir.mkdir(parents=True)
    safe_dir.mkdir(parents=True)
    (helper_dir / "ctoa_otclient_loader.lua").write_text(
        """
CTOA_OTCLIENT = {
  init = function()
    assert(CTOA_PROJECT_LOADER.isSelected("helper"))
    HELPER_INIT = (HELPER_INIT or 0) + 1
    return true
  end,
  terminate = function() HELPER_TERM = (HELPER_TERM or 0) + 1; return true end,
}
return CTOA_OTCLIENT
""",
        encoding="utf-8",
    )
    (safe_dir / "ctoa_safe_loader.lua").write_text(
        """
CTOA_SAFE_LOADER = {
  init = function()
    assert(CTOA_PROJECT_LOADER.isSelected("safe"))
    SAFE_INIT = (SAFE_INIT or 0) + 1
    return true
  end,
  terminate = function() SAFE_TERM = (SAFE_TERM or 0) + 1; return true end,
}
return CTOA_SAFE_LOADER
""",
        encoding="utf-8",
    )
    probe = tmp_path / "exclusive_loader_probe.lua"
    probe.write_text(
        f"""
local callbacks = nil
local scheduled = {{}}
g_resources = {{
  getWorkDir = function() return {tmp_path.as_posix()!r} .. "/" end,
  fileExists = function() return false end,
}}
g_game = {{isOnline = function() return false end}}
connect = function(_, value) callbacks = value end
disconnect = function() callbacks = nil end
scheduleEvent = function(fn) scheduled[#scheduled + 1] = fn; return fn end
removeEvent = function() end

dofile(arg[1])
assert(CTOA_PROJECT_LOADER.init() == true)
assert(HELPER_INIT == nil and SAFE_INIT == nil)
callbacks.onGameStart()
assert(CTOA_PROJECT_LOADER.online_session == true)
assert(CTOA_PROJECT_LOADER.activate("helper") == true)
assert(HELPER_INIT == 1 and SAFE_INIT == nil)
dofile(arg[1])
assert(CTOA_PROJECT_LOADER.init() == true)
assert(CTOA_PROJECT_LOADER.active_project == "helper")
assert(HELPER_INIT == 1 and SAFE_INIT == nil)
assert(CTOA_PROJECT_LOADER.activate("safe") == false)
callbacks.onGameEnd()
assert(CTOA_PROJECT_LOADER.active_project == nil)

callbacks.onGameStart()
assert(CTOA_PROJECT_LOADER.activate("safe") == true)
assert(HELPER_INIT == 1 and SAFE_INIT == 1)
assert(CTOA_PROJECT_LOADER.active_project == "safe")
callbacks.onGameEnd()
assert(CTOA_PROJECT_LOADER.active_project == nil)
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(CHOOSER_DIR / "ctoa_chooser_loader.lua")],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
        cwd=tmp_path,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_safe_cannot_arm_outside_selected_project(tmp_path: Path) -> None:
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for Safe arming validation"
    probe = tmp_path / "safe_arm_probe.lua"
    probe.write_text(
        """
CTOA_PROJECT_LOADER = {active_project = nil}
g_game = {isOnline = function() return false end}
cycleEvent = function() return {} end
removeEvent = function() end
dofile(arg[1])
assert(CTOA_SAFE.init() == true)
assert(CTOA_SAFE.config.enabled == false)
assert(CTOA_SAFE.setEnabled(true) == false)
assert(CTOA_SAFE.config.enabled == false)
CTOA_PROJECT_LOADER.active_project = "safe"
assert(CTOA_SAFE.setEnabled(true) == true)
assert(CTOA_SAFE.config.enabled == true)
assert(CTOA_SAFE.terminate() == true)
assert(CTOA_SAFE.config.enabled == false)
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(SAFE_DIR / "ctoa_safe_helper.lua")],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
        cwd=tmp_path,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_safe_enable_uses_proven_bounded_spectator_signature(tmp_path: Path) -> None:
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for Safe native API validation"
    probe = tmp_path / "safe_spectator_probe.lua"
    probe.write_text(
        """
local think = nil
local spectatorArgs = nil
local player = {
  getPosition = function() return {x = 100, y = 100, z = 7} end,
  getHealthPercent = function() return 100 end,
  getManaPercent = function() return 100 end,
}
local monster = {
  isMonster = function() return true end,
  getPosition = function() return {x = 101, y = 100, z = 7} end,
}
CTOA_PROJECT_LOADER = {active_project = "safe"}
g_game = {
  isOnline = function() return true end,
  getLocalPlayer = function() return player end,
  talk = function() end,
}
g_map = {
  getSpectatorsInRange = function(position, multiFloor, xRange, yRange)
    spectatorArgs = {position, multiFloor, xRange, yRange}
    return {monster}
  end,
  getSpectators = function() error("zero-argument fallback must not run") end,
}
cycleEvent = function(fn) think = fn; return {} end
removeEvent = function() end
dofile(arg[1])
assert(CTOA_SAFE.init() == true)
assert(CTOA_SAFE.setEnabled(true) == true)
assert(type(think) == "function")
think()
assert(type(spectatorArgs) == "table")
assert(spectatorArgs[1].x == 100 and spectatorArgs[1].z == 7)
assert(spectatorArgs[2] == false)
assert(spectatorArgs[3] == 7 and spectatorArgs[4] == 7)
assert(CTOA_SAFE.terminate() == true)
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(SAFE_DIR / "ctoa_safe_helper.lua")],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
        cwd=tmp_path,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_safe_target_dispatch_is_idempotent_for_current_creature(tmp_path: Path) -> None:
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for Safe targeting validation"
    probe = tmp_path / "safe_target_probe.lua"
    probe.write_text(
        """
local think,current,attacks=nil,nil,0
local player={getPosition=function() return {x=100,y=100,z=7} end,getHealthPercent=function() return 100 end,getManaPercent=function() return 100 end}
local monster={isMonster=function() return true end,getPosition=function() return {x=101,y=100,z=7} end,getName=function() return "Training Monk" end,getId=function() return 77 end}
CTOA_PROJECT_LOADER={active_project="safe"}
g_game={isOnline=function() return true end,getLocalPlayer=function() return player end,getAttackingCreature=function() return current end,attack=function(value) attacks=attacks+1;current=value end,talk=function() end}
g_map={getSpectatorsInRange=function() return {monster} end}
cycleEvent=function(fn) think=fn;return {} end
removeEvent=function() end
dofile(arg[1])
assert(CTOA_SAFE.init()==true)
CTOA_SAFE.config.healing.enabled=false
CTOA_SAFE.config.conditions.enabled=false
CTOA_SAFE.config.support.enabled=false
CTOA_SAFE.config.timer.enabled=false
CTOA_SAFE.config.combat.spell_rotation=false
CTOA_SAFE.config.combat.auto_exeta=false
CTOA_SAFE.config.combat.target_rules={{name="Training*",priority=5,max_distance=7,chase=true}}
assert(CTOA_SAFE.setEnabled(true)==true)
think();think()
assert(attacks==1)
assert(current==monster)
assert(CTOA_SAFE.terminate()==true)
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(SAFE_DIR / "ctoa_safe_helper.lua")],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
        cwd=tmp_path,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_safe_targeting_rejects_npcs_and_exercise_dummies(tmp_path: Path) -> None:
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for Safe NPC targeting validation"
    probe = tmp_path / "safe_npc_target_probe.lua"
    probe.write_text(
        """
local think,current,attacks,cancels=nil,nil,{},0
local player={getPosition=function() return {x=100,y=100,z=7} end,getHealthPercent=function() return 100 end,getManaPercent=function() return 100 end}
local npc={isMonster=function() return true end,isNpc=function() return false end,getType=function() return 1 end,getIcon=function() return 7 end,getPosition=function() return {x=101,y=100,z=7} end,getName=function() return "Liora" end,getId=function() return 2147483745 end}
local dummy={isMonster=function() return true end,isNpc=function() return false end,getPosition=function() return {x=101,y=101,z=7} end,getName=function() return "Exercise Dummy" end,getId=function() return 11 end}
local monster={isMonster=function() return true end,isNpc=function() return false end,isPlayer=function() return false end,isAttackable=function() return true end,getPosition=function() return {x=102,y=100,z=7} end,getName=function() return "Dragon" end,getId=function() return 12 end}
current=npc
CTOA_PROJECT_LOADER={active_project="safe"}
g_game={isOnline=function() return true end,getLocalPlayer=function() return player end,getAttackingCreature=function() return current end,cancelAttack=function() cancels=cancels+1;current=nil end,attack=function(value) attacks[#attacks+1]=value;current=value end,talk=function() end}
g_map={getSpectatorsInRange=function() return {npc,dummy,monster} end}
cycleEvent=function(fn) think=fn;return {} end
removeEvent=function() end
dofile(arg[1])
assert(CTOA_SAFE.init()==true)
CTOA_SAFE.config.healing.enabled=false
CTOA_SAFE.config.conditions.enabled=false
CTOA_SAFE.config.support.enabled=false
CTOA_SAFE.config.tools.enabled=false
CTOA_SAFE.config.timer.enabled=false
CTOA_SAFE.config.combat.spell_rotation=false
CTOA_SAFE.config.combat.auto_exeta=false
CTOA_SAFE.config.combat.target_rules={}
assert(CTOA_SAFE.setEnabled(true)==true)
think()
assert(cancels==1)
assert(#attacks==1 and attacks[1]==monster)
assert(CTOA_SAFE.terminate()==true)
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(SAFE_DIR / "ctoa_safe_helper.lua")],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
        cwd=tmp_path,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_safe_blocks_automated_spells_and_npc_greetings_in_pz(tmp_path: Path) -> None:
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for Safe PZ dispatch validation"
    probe = tmp_path / "safe_pz_dispatch_probe.lua"
    probe.write_text(
        """
local think,now,casts=nil,5000,{}
local player={getPosition=function() return {x=100,y=100,z=7} end,getHealthPercent=function() return 100 end,getManaPercent=function() return 100 end,isInProtectionZone=function() return false end,getStates=function() return 0 end,hasCondition=function() return false end}
local monster={isMonster=function() return true end,isNpc=function() return false end,isPlayer=function() return false end,getPosition=function() return {x=101,y=100,z=7} end,getName=function() return "Dragon" end}
local pzTile={getFlags=function() return 1 end,hasFlag=function(_,flag) return flag==1 or flag=="TILESTATE_PROTECTIONZONE" end}
CTOA_PROJECT_LOADER={active_project="safe"}
g_clock={millis=function() return now end}
g_game={isOnline=function() return true end,getLocalPlayer=function() return player end,talk=function(words) casts[#casts+1]=words end}
g_map={getSpectatorsInRange=function() return {monster} end,getTile=function() return pzTile end,getTiles=function() return {} end}
cycleEvent=function(fn) think=fn;return {} end
removeEvent=function() end
dofile(arg[1])
assert(CTOA_SAFE.init()==true)
local snapshot=CTOA_SAFE.environmentFamilySnapshot(7)
assert(snapshot.protection_zone==true and #snapshot.protection_zone_evidence>=1)
CTOA_SAFE.config.healing.enabled=false
CTOA_SAFE.config.conditions.enabled=false
CTOA_SAFE.config.support.enabled=false
CTOA_SAFE.config.combat.auto_attack=false
CTOA_SAFE.config.combat.auto_exeta=false
CTOA_SAFE.config.combat.rotation_interval_ms=250
CTOA_SAFE.config.combat.rotation_spells={{words="exori",use_mob_count=true,min_nearby=1,max_distance=3,cooldown_ms=250}}
CTOA_SAFE.config.tools.enabled=true
CTOA_SAFE.config.tools.auto_haste=true
CTOA_SAFE.config.tools.pz_cast=false
CTOA_SAFE.config.timer.enabled=true
CTOA_SAFE.config.timer.interval_ms=250
CTOA_SAFE.config.timer.last_ms=0
CTOA_SAFE.config.timer.message="hi"
assert(CTOA_SAFE.setEnabled(true)==true)
think()
assert(#casts==0)
assert(CTOA_SAFE.terminate()==true)
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(SAFE_DIR / "ctoa_safe_helper.lua")],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
        cwd=tmp_path,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_safe_exercise_item_targets_nearest_dummy(tmp_path: Path) -> None:
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for Safe exercise validation"
    probe = tmp_path / "safe_exercise_probe.lua"
    probe.write_text(
        """
local think,now,usedId,usedTarget=nil,5000,nil,nil
local player={getPosition=function() return {x=100,y=100,z=7} end,getHealthPercent=function() return 100 end,getManaPercent=function() return 100 end}
local creatureDummy={getName=function() return "Durable Exercise Dummy" end,getPosition=function() return {x=104,y=100,z=7} end,isMonster=function() return true end}
local itemDummy={getId=function() return 28558 end,getName=function() return "" end,getDescription=function() return "" end}
local tile={getPosition=function() return {x=101,y=100,z=7} end,getItems=function() return {itemDummy} end}
local exerciseWand={getId=function() return 35284 end,getName=function() return "Durable Exercise Wand" end}
local storeInbox={getItems=function() return {exerciseWand} end}
CTOA_PROJECT_LOADER={active_project="safe"}
g_clock={millis=function() return now end}
g_game={isOnline=function() return true end,getLocalPlayer=function() return player end,getContainers=function() return {storeInbox} end,talk=function() end,useInventoryItemWith=function(id,target) usedId=id;usedTarget=target end}
g_map={getSpectatorsInRange=function() return {creatureDummy} end,getTiles=function() return {tile} end}
cycleEvent=function(fn) think=fn;return {} end
removeEvent=function() end
dofile(arg[1])
assert(CTOA_SAFE.init()==true)
local snapshot=CTOA_SAFE.environmentFamilySnapshot(7)
assert(#snapshot.items==1 and snapshot.items[1].id==28558 and snapshot.items[1].family=="exercise_dummy")
assert(#snapshot.inventory_items==1 and snapshot.inventory_items[1].id==35284 and snapshot.inventory_items[1].family=="durable_exercise_wand")
CTOA_SAFE.config.healing.enabled=false
CTOA_SAFE.config.combat.enabled=false
CTOA_SAFE.config.conditions.enabled=false
CTOA_SAFE.config.support.enabled=false
CTOA_SAFE.config.timer.enabled=false
CTOA_SAFE.config.tools.enabled=true
CTOA_SAFE.config.tools.auto_haste=false
CTOA_SAFE.config.tools.mana_training=false
CTOA_SAFE.config.tools.exercise_training=true
CTOA_SAFE.config.tools.exercise_item_id=0
CTOA_SAFE.config.tools.exercise_interval_ms=250
assert(CTOA_SAFE.setEnabled(true)==true)
think()
assert(usedId==35284 and usedTarget==itemDummy)
assert(CTOA_SAFE.terminate()==true)
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(SAFE_DIR / "ctoa_safe_helper.lua")],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
        cwd=tmp_path,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_safe_hidden_support_cannot_dispatch_from_compatibility_profile(tmp_path: Path) -> None:
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for Safe support validation"
    probe = tmp_path / "safe_support_probe.lua"
    probe.write_text(
        """
local think,now,casts=nil,5000,{}
local player={getPosition=function() return {x=100,y=100,z=7} end,getHealthPercent=function() return 100 end,getManaPercent=function() return 100 end}
CTOA_PROJECT_LOADER={active_project="safe"}
g_clock={millis=function() return now end}
g_game={isOnline=function() return true end,getLocalPlayer=function() return player end,talk=function(words) casts[#casts+1]=words end}
g_map={getSpectatorsInRange=function() return {} end}
cycleEvent=function(fn) think=fn;return {} end
removeEvent=function() end
dofile(arg[1])
assert(CTOA_SAFE.init()==true)
assert(CTOA_SAFE.config.support.enabled==false)
CTOA_SAFE.config.healing.enabled=false
CTOA_SAFE.config.combat.enabled=false
CTOA_SAFE.config.conditions.enabled=false
CTOA_SAFE.config.timer.enabled=false
CTOA_SAFE.config.support.rules={{words="utani hur",interval_ms=1000},{words="utamo tempo",interval_ms=1000}}
assert(CTOA_SAFE.setEnabled(true)==true)
think();assert(#casts==0)
CTOA_SAFE.config.support.enabled=true
think();assert(#casts==0)
now=5500;think();assert(#casts==0)
now=6100;think();assert(#casts==0)
assert(CTOA_SAFE.terminate()==true)
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(SAFE_DIR / "ctoa_safe_helper.lua")],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
        cwd=tmp_path,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_safe_hidden_support_and_legacy_rotation_never_dispatch(tmp_path: Path) -> None:
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for Safe item/distance validation"
    probe = tmp_path / "safe_item_distance_probe.lua"
    probe.write_text(
        """
local think,now,uses,casts,lastRange=nil,5000,{}, {},nil
local player={getPosition=function() return {x=100,y=100,z=7} end,getHealthPercent=function() return 100 end,getManaPercent=function() return 40 end}
local monster={isMonster=function() return true end,getPosition=function() return {x=103,y=100,z=7} end}
CTOA_PROJECT_LOADER={active_project="safe"}
g_clock={millis=function() return now end}
g_game={isOnline=function() return true end,getLocalPlayer=function() return player end,talk=function(words) casts[#casts+1]=words end,useInventoryItemWith=function(id,target) uses[#uses+1]=id end}
g_map={getSpectatorsInRange=function(pos,multifloor,xrange,yrange) lastRange=xrange; return {monster} end}
cycleEvent=function(fn) think=fn;return {} end
removeEvent=function() end
dofile(arg[1])
assert(CTOA_SAFE.init()==true)
lastRange=nil
CTOA_SAFE.config.healing.enabled=false
CTOA_SAFE.config.conditions.enabled=false
CTOA_SAFE.config.timer.enabled=false
CTOA_SAFE.config.combat.auto_attack=false
CTOA_SAFE.config.combat.auto_exeta=false
CTOA_SAFE.config.combat.rotation_interval_ms=250
CTOA_SAFE.config.combat.rotation_spells={{words="exori",use_mob_count=true,min_nearby=1,max_distance=3,cooldown_ms=250}}
CTOA_SAFE.config.support.enabled=true
CTOA_SAFE.config.support.rules={{action="item",resource="mana",item_id=268,threshold_min=45,threshold_max=45,interval_ms=1000}}
assert(CTOA_SAFE.setEnabled(true)==true)
think();assert(#uses==0 and #casts==0 and lastRange==nil)
now=5500;think();assert(#uses==0 and #casts==0)
now=6100;think();assert(#uses==0 and #casts==0)
assert(CTOA_SAFE.terminate()==true)
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(SAFE_DIR / "ctoa_safe_helper.lua")],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
        cwd=tmp_path,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_safe_json_profile_is_validated_and_never_persists_runtime_arm(
    tmp_path: Path,
) -> None:
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for Safe profile validation"
    profile = tmp_path / "ctoa_safe_ek_profile.json"
    profile.write_text("{}", encoding="utf-8")
    probe = tmp_path / "safe_profile_probe.lua"
    probe.write_text(
        f"""
local encoded = nil
CTOA_PROJECT_LOADER = {{active_project = "safe"}}
g_resources = {{getWorkDir = function() return {tmp_path.as_posix()!r} .. "/" end}}
g_game = {{isOnline = function() return false end}}
cycleEvent = function() return {{}} end
removeEvent = function() end
json = {{
  decode = function()
    return {{
      schema_version = "ctoa-safe-profile-v2", vocation = "ek", name = "portable",
      enabled = true, safe_boot_runtime_disabled = false, cavebot = {{enabled = true}},
      healing = {{spell_threshold = 999, last_cast_ms = 123, rules = {{{{kind="critical", words="exura gran", threshold=150, cooldown_ms=1}}, {{kind="heal", words="exura", threshold=70, cooldown_ms=900}}}}}},
      combat = {{attack_range = 99, rotation_spells = {{{{words = "first", min_nearby = -2, cooldown_ms = 1}}, {{words="second", min_nearby=2, max_nearby=4, cooldown_ms=3000}}}}, target_rules={{{{name="Dragon*",priority=99,max_distance=50,chase=true}},{{name="Rat",priority=2,max_distance=3,chase=false}}}}}},
      support = {{enabled=true, rules={{{{words="utani hur",interval_ms=1}},{{words="utamo tempo",interval_ms=9999999}}}}}},
    }}
  end,
  encode = function(value) encoded = value; return "{{}}" end,
}}
dofile(arg[1])
assert(CTOA_SAFE.init() == true)
assert(CTOA_SAFE.config.enabled == false)
assert(CTOA_SAFE.config.safe_boot_runtime_disabled == true)
assert(CTOA_SAFE.config.healing.spell_threshold == 99)
assert(CTOA_SAFE.config.combat.attack_range == 10)
assert(#CTOA_SAFE.config.healing.rules == 2)
assert(CTOA_SAFE.config.healing.rules[1].words == "exura gran" and CTOA_SAFE.config.healing.rules[1].threshold == 99 and CTOA_SAFE.config.healing.rules[1].cooldown_ms == 250)
assert(CTOA_SAFE.config.healing.rules[2].words == "exura")
assert(CTOA_SAFE.config.combat.rotation_spells[1].words == "first" and CTOA_SAFE.config.combat.rotation_spells[2].words == "second")
assert(CTOA_SAFE.config.combat.target_rules[1].name == "Dragon*" and CTOA_SAFE.config.combat.target_rules[1].priority == 10 and CTOA_SAFE.config.combat.target_rules[1].max_distance == 10)
assert(CTOA_SAFE.config.combat.target_rules[2].name == "Rat")
assert(CTOA_SAFE.config.support.enabled == true and #CTOA_SAFE.config.support.rules == 2)
assert(CTOA_SAFE.config.support.rules[1].interval_ms == 250 and CTOA_SAFE.config.support.rules[2].interval_ms == 3600000)
assert(CTOA_SAFE.config.cavebot == nil)
local contract = CTOA_SAFE.profileContract()
assert(contract.schema_version == "ctoa-safe-profile-v3")
assert(contract.legacy_schema_version == "ctoa-safe-profile-v2")
assert(contract.format == "json" and contract.helper_profile_compatible == false)
assert(contract.persists_runtime_arm == false)
CTOA_SAFE.config.healing.rules[1]._last_cast = 111
CTOA_SAFE.config.combat.rotation_spells[1]._last_cast = 222
CTOA_SAFE.config.support.rules[1]._last_cast = 333
assert(CTOA_SAFE.saveProfile() == true)
assert(encoded.schema_version == "ctoa-safe-profile-v3" and #encoded.presets == 1)
local saved = encoded.presets[1]
assert(saved.enabled == nil and saved.safe_boot_runtime_disabled == nil)
assert(saved.cavebot == nil and saved.loot == nil)
assert(saved.healing.last_cast_ms == nil)
assert(saved.combat.last_rotation_ms == nil)
assert(saved.healing.rules[1].words == "exura gran" and saved.healing.rules[2].words == "exura")
assert(saved.combat.rotation_spells[1].words == "first" and saved.combat.rotation_spells[2].words == "second")
assert(saved.combat.target_rules[1].name == "Dragon*" and saved.combat.target_rules[2].name == "Rat")
assert(saved.healing.rules[1]._last_cast == nil and saved.combat.rotation_spells[1]._last_cast == nil)
assert(saved.support.rules[1].words == "utani hur" and saved.support.rules[1]._last_cast == nil)
assert(CTOA_SAFE.terminate() == true)
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(SAFE_DIR / "ctoa_safe_helper.lua")],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
        cwd=tmp_path,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_safe_v3_named_presets_export_and_strict_unknown_field_rejection(
    tmp_path: Path,
) -> None:
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for Safe v3 preset validation"
    (tmp_path / "ctoa_safe_ek_profile.json").write_text("{}", encoding="utf-8")
    probe = tmp_path / "safe_v3_preset_probe.lua"
    probe.write_text(
        f"""
local encoded=nil
CTOA_PROJECT_LOADER={{active_project="safe"}}
g_resources={{getWorkDir=function() return {tmp_path.as_posix()!r}.."/" end}}
g_game={{isOnline=function() return false end}}
cycleEvent=function() return {{}} end
removeEvent=function() end
local function preset(id,name)
  return {{id=id,name=name,hotkey="Ctrl+B",window_x=20,window_y=60,healing={{}},combat={{}},conditions={{}},support={{}},timer={{}}}}
end
json={{
  decode=function() return {{schema_version="ctoa-safe-profile-v3",vocation="ek",active_preset="default",presets={{preset("default","Default")}}}} end,
  encode=function(value) encoded=value;return "{{}}" end,
}}
dofile(arg[1])
assert(CTOA_SAFE.init()==true)
local contract=CTOA_SAFE.profileContract()
assert(contract.schema_version=="ctoa-safe-profile-v3" and contract.preset_count==1 and contract.max_presets==12)
local ok,id=CTOA_SAFE.createPreset("Boss Hunt")
assert(ok==true and id=="boss_hunt")
assert(CTOA_SAFE.config.enabled==false)
assert(CTOA_SAFE.profileContract().preset_count==2)
assert(CTOA_SAFE.selectPreset("default")==true)
assert(CTOA_SAFE.deletePreset("boss_hunt")==true)
assert(CTOA_SAFE.profileContract().preset_count==1)
local exportOk,exportPath=CTOA_SAFE.exportPreset()
assert(exportOk==true and type(exportPath)=="string")
assert(encoded.schema_version=="ctoa-safe-profile-v3")
assert(encoded.enabled==nil and encoded.safe_boot_runtime_disabled==nil)
assert(CTOA_SAFE.terminate()==true)
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(SAFE_DIR / "ctoa_safe_helper.lua")],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
        cwd=tmp_path,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_safe_exeta_rotation_is_ordered_and_per_entry_cooldown_gated(
    tmp_path: Path,
) -> None:
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for Safe Exeta validation"
    probe = tmp_path / "safe_exeta_probe.lua"
    probe.write_text(
        """
local think,now,casts=nil,120000,{}
local player={getPosition=function() return {x=100,y=100,z=7} end,getHealthPercent=function() return 100 end,getManaPercent=function() return 100 end}
local monster={isMonster=function() return true end,getPosition=function() return {x=101,y=100,z=7} end}
CTOA_PROJECT_LOADER={active_project="safe"}
g_clock={millis=function() return now end}
g_game={isOnline=function() return true end,getLocalPlayer=function() return player end,talk=function(words) casts[#casts+1]=words end}
g_map={getSpectatorsInRange=function() return {monster,monster,monster} end}
cycleEvent=function(fn) think=fn;return {} end
removeEvent=function() end
dofile(arg[1])
assert(CTOA_SAFE.init()==true)
CTOA_SAFE.config.healing.enabled=false
CTOA_SAFE.config.conditions.enabled=false
CTOA_SAFE.config.support.enabled=false
CTOA_SAFE.config.timer.enabled=false
CTOA_SAFE.config.combat.auto_attack=false
CTOA_SAFE.config.combat.spell_rotation=false
CTOA_SAFE.config.combat.exeta_interval_ms=500
CTOA_SAFE.config.combat.exeta_spells={{words="exeta res",min_nearby=2,cooldown_ms=120000},{words="exeta amp res",min_nearby=3,cooldown_ms=500}}
assert(CTOA_SAFE.setEnabled(true)==true)
think();assert(#casts==1 and casts[1]=="exeta res")
now=121000;think();assert(#casts==2 and casts[2]=="exeta amp res")
assert(CTOA_SAFE.terminate()==true)
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(SAFE_DIR / "ctoa_safe_helper.lua")],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
        cwd=tmp_path,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_safe_v3_rejects_unknown_fields_fail_closed(tmp_path: Path) -> None:
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for Safe strict schema validation"
    (tmp_path / "ctoa_safe_ek_profile.json").write_text("{}", encoding="utf-8")
    probe = tmp_path / "safe_v3_unknown_probe.lua"
    probe.write_text(
        f"""
CTOA_PROJECT_LOADER={{active_project="safe"}}
g_resources={{getWorkDir=function() return {tmp_path.as_posix()!r}.."/" end}}
g_game={{isOnline=function() return false end}}
cycleEvent=function() return {{}} end
removeEvent=function() end
json={{decode=function() return {{schema_version="ctoa-safe-profile-v3",vocation="ek",active_preset="default",presets={{{{id="default",name="Unsafe",hotkey="Alt+X",window_x=9999,window_y=9999,healing={{rules={{{{kind="spell",words="exura",threshold=80,cooldown_ms=1000,rogue=true}}}}}},combat={{rotation_spells={{}},target_rules={{}},exeta_spells={{}}}},conditions={{}},support={{rules={{}}}},timer={{}}}}}}}} end}}
dofile(arg[1])
assert(CTOA_SAFE.init()==true)
assert(CTOA_SAFE.config.enabled==false and CTOA_SAFE.config.safe_boot_runtime_disabled==true)
local contract=CTOA_SAFE.profileContract()
assert(contract.active_preset=="default" and contract.preset_count==1)
assert(CTOA_SAFE.config.hotkey=="Ctrl+B")
assert(CTOA_SAFE.terminate()==true)
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(SAFE_DIR / "ctoa_safe_helper.lua")],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
        cwd=tmp_path,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_safe_keyboard_toggle_navigation_and_window_position_persistence(
    tmp_path: Path,
) -> None:
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for Safe keyboard/UI validation"
    (tmp_path / "ctoa_safe_ek_profile.json").write_text("{}", encoding="utf-8")
    probe = tmp_path / "safe_keyboard_probe.lua"
    probe.write_text(
        f"""
local callbacks,widgets,encoded={{}},{{}},nil
CTOA_PROJECT_LOADER={{active_project="safe"}}
local root={{getWidth=function() return 800 end,getHeight=function() return 600 end}}
local function widget()
  local w={{visible=true,text="",checked=false,width=0,height=0}}
  function w:setId(id) self.id=id;widgets[id]=self end
  function w:setText(value) self.text=value end
  function w:getText() return self.text end
  function w:setWidth(value) self.width=value end
  function w:setHeight(value) self.height=value end
  function w:setPosition(value) self.position=value end
  function w:setChecked(value) self.checked=value end
  function w:isVisible() return self.visible end
  function w:show() self.visible=true end
  function w:hide() self.visible=false end
  function w:raise() end
  function w:destroy() self.destroyed=true end
  function w:setMarginLeft(value) self.marginLeft=value end;function w:setMarginTop(value) self.marginTop=value end;function w:addAnchor() end
  function w:setColor() end;function w:setBackgroundColor() end;function w:setBorderColor() end;function w:setBorderWidth() end
  function w:setDraggable() end;function w:setMovable() end;function w:setFontScale() end;function w:setImageSource() end
  return w
end
AnchorLeft=1;AnchorTop=2
g_ui={{getRootWidget=function() return root end,createWidget=function() return widget() end}}
g_keyboard={{bindKeyDown=function(key,fn) callbacks[key]=fn end,unbindKeyDown=function(key) callbacks[key]=nil end}}
g_resources={{getWorkDir=function() return {tmp_path.as_posix()!r}.."/" end}}
g_game={{isOnline=function() return false end}}
cycleEvent=function() return {{}} end;removeEvent=function() end;scheduleEvent=function(fn) fn();return {{}} end
json={{decode=function() return {{schema_version="ctoa-safe-profile-v3",vocation="ek",active_preset="default",presets={{{{id="default",name="Keyboard",hotkey="Ctrl+B",window_x=4096,window_y=4096,healing={{}},combat={{}},conditions={{}},support={{}},timer={{}}}}}}}} end,encode=function(value) encoded=value;return "{{}}" end}}
dofile(arg[1]);assert(CTOA_SAFE.init()==true)
    local win=widgets.ctoaSafeWindow;assert(win~=nil and win.marginLeft==528 and win.marginTop==0)
assert(type(callbacks["Ctrl+B"])=="function" and type(callbacks["Ctrl+Tab"])=="function" and type(callbacks["Ctrl+E"])=="function")
callbacks["Ctrl+B"]();assert(win.visible==false);callbacks["Ctrl+B"]();assert(win.visible==true)
    callbacks["Ctrl+Tab"]();callbacks["Ctrl+Space"]();assert(CTOA_SAFE.config.tools.enabled==false)
callbacks["Ctrl+E"]();assert(widgets.csEditPanel~=nil)
win.onPositionChange(win,{{x=123,y=234}});assert(CTOA_SAFE.saveProfile()==true)
assert(encoded.presets[1].window_x==123 and encoded.presets[1].window_y==234)
assert(CTOA_SAFE.terminate()==true);assert(callbacks["Ctrl+B"]==nil and callbacks["Ctrl+Tab"]==nil)
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(SAFE_DIR / "ctoa_safe_helper.lua")],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
        cwd=tmp_path,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_safe_actionbar_drop_and_healing_checkbox_update_runtime_config(
    tmp_path: Path,
) -> None:
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for Safe UI contract validation"
    probe = tmp_path / "safe_ui_item_probe.lua"
    probe.write_text(
        """
local widgets={}
CTOA_PROJECT_LOADER={active_project="safe"}
local root={getWidth=function() return 1024 end,getHeight=function() return 768 end}
local function widget(kind)
  local w={kind=kind,visible=true,checked=false,itemId=0}
  function w:setId(id) self.id=id;widgets[id]=self end
  function w:setText(value) self.text=value end
  function w:setItemId(value) self.itemId=value end
  function w:getItemId() return self.itemId end
  function w:setChecked(value) self.checked=value end
  function w:setVirtual(value) self.virtual=value end
  function w:setDraggable(value) self.draggable=value end
  function w:setFocusable(value) self.focusable=value end
  function w:setTooltip(value) self.tooltip=value end
  function w:setMarginLeft(value) self.marginLeft=value end
  function w:setMarginTop(value) self.marginTop=value end
  function w:addAnchor() end
  function w:resize(width,height) self.width=width;self.height=height end
  function w:setTextAutoResize() end
  function w:setPhantom() end
  function w:setFontScale() end
  function w:setColor() end
  function w:setBackgroundColor() end
  function w:setBorderColor() end
  function w:setBorderWidth() end
  function w:setMovable() end
  function w:show() self.visible=true end
  function w:hide() self.visible=false end
  function w:raise() end
  function w:destroy() self.destroyed=true end
  return w
end
AnchorLeft=1;AnchorTop=2
g_ui={getRootWidget=function() return root end,importStyle=function() return true end,createWidget=function(kind) return widget(kind) end}
g_game={isOnline=function() return false end}
cycleEvent=function() return {} end;removeEvent=function() end;scheduleEvent=function(fn) fn();return {} end
dofile(arg[1]);assert(CTOA_SAFE.init()==true)
local slot=widgets.csPotionItem1;assert(slot~=nil)
assert(slot.selectable==true and slot.editable==true and slot.virtual==true and slot.draggable==true and slot.focusable==true)
assert(slot.onDrop(slot,{currentDragThing=268})==true)
assert(slot.itemId==268 and CTOA_SAFE.config.healing.potion_rules[1].item_id==268)
assert(slot.onDrop(slot,{cache={itemId=237}})==true)
assert(slot.itemId==237 and CTOA_SAFE.config.healing.potion_rules[1].item_id==237)
local checkbox=widgets.csHealSpellEnabled1;assert(checkbox~=nil)
checkbox.onCheckChange(checkbox,false)
assert(CTOA_SAFE.config.healing.spell_slots[1].enabled==false)
checkbox.onCheckChange(checkbox,true)
assert(CTOA_SAFE.config.healing.spell_slots[1].enabled==true)
widgets.csTabtools.onClick()
assert(widgets.csUtamoEnable==nil and CTOA_SAFE.config.conditions.mana_shield==false)
assert(CTOA_SAFE.terminate()==true)
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(SAFE_DIR / "ctoa_safe_helper.lua")],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
        cwd=tmp_path,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_safe_runtime_dispatches_healing_runes_and_plain_items_correctly(
    tmp_path: Path,
) -> None:
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for Safe runtime dispatch validation"
    probe = tmp_path / "safe_dispatch_probe.lua"
    probe.write_text(
        """
local think,now,casts,plain,withTarget=nil,5000,{},{},{}
local player={getPosition=function() return {x=100,y=100,z=7} end,getHealthPercent=function() return 50 end,getManaPercent=function() return 100 end}
local monster={isMonster=function() return true end,isNpc=function() return false end,isPlayer=function() return false end,getPosition=function() return {x=101,y=100,z=7} end,getId=function() return 88 end,getName=function() return "Dragon" end}
CTOA_PROJECT_LOADER={active_project="safe"}
g_clock={millis=function() return now end}
g_game={
  isOnline=function() return true end,getLocalPlayer=function() return player end,
  getAttackingCreature=function() return monster end,
  talk=function(words) casts[#casts+1]=words end,
  useInventoryItem=function(id) plain[#plain+1]=id end,
  useInventoryItemWith=function(id,target) withTarget[#withTarget+1]={id=id,target=target} end,
}
g_map={getSpectatorsInRange=function() return {monster} end}
cycleEvent=function(fn) think=fn;return {} end;removeEvent=function() end
dofile(arg[1]);assert(CTOA_SAFE.init()==true)
CTOA_SAFE.config.conditions.enabled=false;CTOA_SAFE.config.support.enabled=false;CTOA_SAFE.config.timer.enabled=false;CTOA_SAFE.config.tools.enabled=false;CTOA_SAFE.config.combat.enabled=false
CTOA_SAFE.config.healing.potion_enabled=false;CTOA_SAFE.config.healing.mana_potion_enabled=false;CTOA_SAFE.config.healing.potion_rules={}
CTOA_SAFE.config.healing.spell_slots={{enabled=false,words="exura",percent=80,cooldown_ms=250}}
assert(CTOA_SAFE.setEnabled(true)==true)
think();assert(#casts==0)
CTOA_SAFE.config.healing.spell_slots[1].enabled=true;now=5500;think();assert(#casts==1 and casts[1]=="exura")

CTOA_SAFE.config.healing.enabled=false;CTOA_SAFE.config.combat.enabled=true;CTOA_SAFE.config.combat.auto_attack=false;CTOA_SAFE.config.combat.auto_exeta=false;CTOA_SAFE.config.combat.spell_rotation=true;CTOA_SAFE.config.combat.rotation_interval_ms=250
CTOA_SAFE.config.combat.shooter_profiles={Default={spells={},runes={{id=3155,priority=1,creatures=1,force_cast=true}}}};CTOA_SAFE.config.combat.selected_shooter_profile="Default"
now=7000;think();assert(#withTarget==1 and withTarget[1].id==3155 and withTarget[1].target==monster)

CTOA_SAFE.config.combat.enabled=false;CTOA_SAFE.config.tools.enabled=true;CTOA_SAFE.config.tools.auto_eat_food=true;CTOA_SAFE.config.tools.food_item_id=3577;CTOA_SAFE.config.tools.change_gold=false;CTOA_SAFE.config.tools.mana_training=false;CTOA_SAFE.config.tools.auto_haste=false;CTOA_SAFE.config.tools.exercise_training=false
now=40000;think();assert(#plain==1 and plain[1]==3577)
assert(CTOA_SAFE.terminate()==true)
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(SAFE_DIR / "ctoa_safe_helper.lua")],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
        cwd=tmp_path,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
