from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
LUA_DIR = ROOT / "scripts" / "lua" / "otclient"
LOADER = LUA_DIR / "ctoa_otclient_loader.lua"
OTMOD = LUA_DIR / "ctoa_otclient.otmod"
HELPER = LUA_DIR / "ctoa_native_helper.lua"


def test_otmod_uses_native_cross_fork_metadata_contract() -> None:
    source = OTMOD.read_text(encoding="utf-8")

    assert "version: 2.4.1" in source
    assert "autoload: false" in source
    assert "autoload-priority: 1000" in source
    assert "autoLoad:" not in source
    assert "autoLoadPriority:" not in source
    assert "@onLoad: CTOA_OTCLIENT.init()" in source
    assert "@onUnload: CTOA_OTCLIENT.terminate()" in source


def test_loader_has_no_focus_input_or_runtime_dispatch_surface() -> None:
    source = LOADER.read_text(encoding="utf-8")

    assert "modes.Status or modes.ModeStatus" in source
    assert "function CTOA_OTCLIENT.init()" in source
    assert "function CTOA_OTCLIENT.terminate()" in source
    assert '"/ctoa_otclient/"' in source
    for forbidden in (
        "raise()",
        "focus()",
        "g_window",
        "g_keyboard",
        "g_mouse",
        "g_game.talk",
        "g_game.move",
        "g_game.attack",
        "g_game.use",
    ):
        assert forbidden not in source


def test_native_helper_safe_start_is_hidden_and_message_mode_adaptive() -> None:
    source = HELPER.read_text(encoding="utf-8")

    assert "auto_show_window = false" in source
    assert "modes.Status or modes.ModeStatus" in source
    build_ui = source[
        source.index("buildUi = function()") : source.index("function toggleWindow")
    ]
    assert "if window.show and HELPER_CONFIG.auto_show_window ~= false then" in build_ui
    assert "elseif window.hide then" in build_ui
    init_slice = source[
        source.index("function init()") : source.index("function terminate()")
    ]
    assert "HELPER_CONFIG.auto_show_window ~= false" in init_slice


@pytest.mark.parametrize("message_mode_key", ["Status", "ModeStatus", "none"])
def test_loader_lifecycle_is_idempotent_across_message_mode_variants(
    tmp_path: Path, message_mode_key: str
) -> None:
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for cross-fork loader validation"
    workdir = tmp_path.as_posix() + "/"
    module_dir = tmp_path / "mods" / "ctoa_otclient"
    module_dir.mkdir(parents=True)
    (module_dir / "ctoa_helper_modules.lua").write_text(
        """
CTOA_HELPER_MODULES = {
  getSupportModules = function() return {} end,
  validateSupportModules = function() return true, {} end,
}
return CTOA_HELPER_MODULES
""",
        encoding="utf-8",
    )
    (module_dir / "ctoa_native_helper.lua").write_text(
        "CTOA_Helper = {handleGameStart = function() end}\n",
        encoding="utf-8",
    )
    probe = tmp_path / "loader_probe.lua"
    probe.write_text(
        f"""
local helperTerminateCount = 0
local consoleModes = {{}}
g_resources = {{
  getWorkDir = function() return {workdir!r} end,
  fileExists = function() return false end,
}}
CTOA_PROJECT_LOADER = {{isSelected = function(project) return project == "helper" end}}
modules = {{game_console = {{addText = function(_, mode) consoleModes[#consoleModes + 1] = mode or "none" end}}}}
MessageModes = {{}}
if {message_mode_key!r} ~= "none" then MessageModes[{message_mode_key!r}] = 77 end

dofile(arg[1])
assert(CTOA_OTCLIENT.version == "2.4.1")
assert(CTOA_OTCLIENT.loader_version == "2.4.1")
assert(CTOA_OTCLIENT.package_version == "v2.4.1")
assert(CTOA_OTCLIENT.loaded == false)
CTOA_OTCLIENT.init()
assert(CTOA_OTCLIENT.loaded == true and CTOA_OTCLIENT.loading == false)
CTOA_Helper.terminate = function() helperTerminateCount = helperTerminateCount + 1 end
if {message_mode_key!r} == "none" then
  assert(consoleModes[#consoleModes] == "none")
else
  assert(consoleModes[#consoleModes] == 77)
end
CTOA_OTCLIENT.terminate()
CTOA_OTCLIENT.terminate()
assert(helperTerminateCount == 1)
assert(CTOA_OTCLIENT.initialized == false)
dofile(arg[1])
assert(CTOA_OTCLIENT.loaded == false)
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(LOADER)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_loader_rejects_start_without_neutral_loader_selection(tmp_path: Path) -> None:
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for loader teardown validation"
    probe = tmp_path / "loader_pending_probe.lua"
    probe.write_text(
        """
local dofileCount = 0
g_resources = {getWorkDir = function() return "" end, fileExists = function() return false end}
local realDofile = dofile
dofile = function(path) dofileCount = dofileCount + 1; return realDofile(path) end
realDofile(arg[1])
assert(CTOA_OTCLIENT.init() == false)
assert(dofileCount == 0)
assert(CTOA_OTCLIENT.loaded == false)
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(LOADER)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_loader_prefers_native_module_resource_mount(tmp_path: Path) -> None:
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for module resource validation"
    probe = tmp_path / "loader_resource_probe.lua"
    probe.write_text(
        """
local loadedPaths = {}
g_resources = {
  getWorkDir = function() return "C:/must-not-be-used/" end,
  fileExists = function(path)
    return path == "/ctoa_otclient/ctoa_native_helper.lua" or
      path == "/ctoa_otclient/ctoa_helper_modules.lua"
  end,
}
CTOA_PROJECT_LOADER = {isSelected = function(project) return project == "helper" end}
local realDofile = dofile
dofile = function(path)
  loadedPaths[#loadedPaths + 1] = path
  if path == "/ctoa_otclient/ctoa_helper_modules.lua" then
    CTOA_HELPER_MODULES = {
      getSupportModules = function() return {} end,
      validateSupportModules = function() return true, {} end,
    }
    return CTOA_HELPER_MODULES
  end
  if path == "/ctoa_otclient/ctoa_native_helper.lua" then CTOA_Helper = {}; return CTOA_Helper end
  return realDofile(path)
end
realDofile(arg[1])
assert(CTOA_OTCLIENT.init() == true)
assert(CTOA_OTCLIENT.loaded == true)
assert(loadedPaths[1] == "/ctoa_otclient/ctoa_helper_modules.lua")
assert(loadedPaths[2] == "/ctoa_otclient/ctoa_native_helper.lua")
for _, path in ipairs(loadedPaths) do assert(not string.find(path, "C:/must-not-be-used", 1, true)) end
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(LOADER)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


@pytest.mark.parametrize("ui_variant", ["mehah", "classic"])
def test_full_manifest_load_is_passive_across_fork_ui_shapes(
    tmp_path: Path, ui_variant: str
) -> None:
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for full-manifest validation"
    probe = tmp_path / "full_manifest_probe.lua"
    probe.write_text(
        f"""
local actionCalls, eventCalls, writeCalls = 0, 0, 0
local function action() actionCalls = actionCalls + 1; return false end
local function event() eventCalls = eventCalls + 1; return {{}} end
g_game = {{talk=action, attack=action, move=action, use=action, useWith=action,
  autoWalk=action, forceWalk=action, walk=action, isOnline=function() return false end}}
g_map = {{}}
g_keyboard = {{bindKeyDown=function() end, unbindKeyDown=function() end}}
g_ui = {{loadUI=function() return nil end, createWidget=function() return nil end}}
if {ui_variant!r} == "mehah" then g_ui.setupUI = function() return nil end end
connect, disconnect = event, event
scheduleEvent, cycleEvent, addEvent, removeEvent = event, event, event, event
local realOpen, realRemove, realRename = io.open, os.remove, os.rename
io.open = function(...) writeCalls = writeCalls + 1; return nil end
os.remove = function(...) writeCalls = writeCalls + 1; return false end
os.rename = function(...) writeCalls = writeCalls + 1; return false end

local base = arg[1]
dofile(base .. "/ctoa_helper_modules.lua")
local manifest = CTOA_HELPER_MODULES.getSupportModules()
local valid, errors = CTOA_HELPER_MODULES.validateSupportModules(manifest)
assert(valid, table.concat(errors or {{}}, ";"))
for _, module in ipairs(manifest) do dofile(base .. "/" .. module.file) end
local bridge = CTOA_HELPER_RECOVERY_BRIDGE
local armed = bridge.arm({{
  session_id = "stale-session", sandbox = true,
  operator_confirmed = true, runtime_enabled = true,
}})
assert(armed == true and bridge.snapshot().armed == true)
dofile(base .. "/ctoa_native_helper.lua")

io.open, os.remove, os.rename = realOpen, realRemove, realRename
assert(#manifest == 49)
assert(actionCalls == 0, "loader-time action call")
assert(type(CTOA_Helper) == "table")
assert(CTOA_Helper.config.enabled == false)
assert(CTOA_Helper.runtime_session_armed ~= true)
assert(bridge.snapshot().armed == false, "native init retained stale bridge arm")
assert(CTOA_Helper.setEnabled(true) == false, "external enable bypassed safe boot")
assert(CTOA_Helper.config.enabled == false)
CTOA_Helper.runtime_session_armed = true
CTOA_Helper.config.enabled = true
assert(CTOA_Helper.reloadProfile() == false)
assert(CTOA_Helper.config.enabled == false)
assert(CTOA_Helper.runtime_session_armed ~= true)
assert(bridge.snapshot().armed == false)
CTOA_Helper.terminate()
assert(bridge.snapshot().armed == false)
assert(actionCalls == 0, "lifecycle action call")
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), LUA_DIR.as_posix()],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_profile_data_loader_has_no_otclient_or_filesystem_authority(
    tmp_path: Path,
) -> None:
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for data-only profile validation"
    source = HELPER.read_text(encoding="utf-8")
    start = source.index("local function loadDataOnlyLua(path)")
    end = source.index("local function loadProfile(requestedVocation)")
    loader = source[start:end].replace("local function loadDataOnlyLua", "function loadDataOnlyLua", 1)
    malicious = tmp_path / "malicious_profile.lua"
    malicious.write_text(
        'g_game.talk("unsafe")\nio.open("unsafe", "w")\nreturn {name = "unsafe"}\n',
        encoding="utf-8",
    )
    valid = tmp_path / "valid_profile.lua"
    valid.write_text('return {name = "safe", nested = {enabled = false}}\n', encoding="utf-8")
    probe = tmp_path / "data_loader_probe.lua"
    probe.write_text(
        f"""
local actionCalls, writeCalls = 0, 0
g_game = {{talk = function() actionCalls = actionCalls + 1 end}}
local realOpen = io.open
io.open = function(...) writeCalls = writeCalls + 1; return nil end
{loader}
local badOk = loadDataOnlyLua(arg[1])
assert(badOk == false)
assert(actionCalls == 0 and writeCalls == 0)
local goodOk, value = loadDataOnlyLua(arg[2])
assert(goodOk == true and value.name == "safe" and value.nested.enabled == false)
io.open = realOpen
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(malicious), str(valid)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
