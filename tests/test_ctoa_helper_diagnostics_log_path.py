from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
DIAGNOSTICS = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_diagnostics.lua"


def test_diagnostics_log_uses_otclient_workdir_not_process_cwd(tmp_path: Path):
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for diagnostics log-path validation"
    workdir = tmp_path / "sandbox-client"
    workdir.mkdir()
    probe = tmp_path / "diagnostics_log_probe.lua"
    probe.write_text(
        r'''
g_resources = {
  getWorkDir = function() return arg[2] .. "/" end,
  getUserDir = function() return arg[3] .. "/wrong-user-dir" end,
}
local diagnostics = dofile(arg[1])
assert(diagnostics.appendLog("workdir-proof", "CTOA-TEST") == true)
local expected = io.open(arg[2] .. "/ctoa_local.log", "r")
assert(expected ~= nil)
local text = expected:read("*a")
expected:close()
assert(string.find(text, "[CTOA-TEST] workdir-proof", 1, true) ~= nil)
local fallback = io.open("ctoa_local.log", "r")
assert(fallback == nil)
assert(diagnostics.contract().owns_workdir_log_path == true)
''',
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(DIAGNOSTICS), workdir.as_posix(), tmp_path.as_posix()],
        check=False,
        capture_output=True,
        text=True,
        cwd=tmp_path,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_diagnostics_owns_bounded_smoke_io_and_safe_api_calls(tmp_path: Path):
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for diagnostics smoke validation"
    probe = tmp_path / "diagnostics_smoke_probe.lua"
    probe.write_text(
        r'''
local diagnostics = dofile(arg[1])
local owner = {base = 5, add = function(self, value) return self.base + value end}
local ok, value = diagnostics.safeCall(owner, "add", 3)
assert(ok == true and value == 8)
ok, value = diagnostics.safeGlobalCall({add = function(a, b) return a + b end}, "add", 4, 6)
assert(ok == true and value == 10)
assert(diagnostics.safeCall(owner, "missing") == false)

local relative = diagnostics.smokeCommandPath("mods/ctoa_otclient/ctoa_ui_prefs.lua", nil)
assert(relative == "mods/ctoa_otclient/ctoa_smoke_command.lua")
local file = assert(io.open(arg[2], "w"))
file:write('return { action = "api_probe", confirm = true }')
file:close()
local command = diagnostics.readSmokeCommand(arg[2], io)
assert(command.action == "api_probe" and command.confirm == true)
assert(diagnostics.removeSmokeCommand(arg[2], os) == true)
assert(io.open(arg[2], "r") == nil)

local oversized = assert(io.open(arg[2], "w"))
oversized:write(string.rep("x", 4097))
oversized:close()
assert(diagnostics.readSmokeCommand(arg[2], io) == nil)
diagnostics.removeSmokeCommand(arg[2], os)
local contract = diagnostics.contract()
assert(contract.owns_safe_method_call == true)
assert(contract.owns_smoke_command_read == true)
assert(contract.bounded_smoke_command_bytes == 4096)
''',
        encoding="utf-8",
    )
    command_path = tmp_path / "ctoa_smoke_command.lua"
    completed = subprocess.run(
        [lua, str(probe), str(DIAGNOSTICS), str(command_path)],
        check=False,
        capture_output=True,
        text=True,
        cwd=tmp_path,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_diagnostics_controller_runs_passive_api_probe(tmp_path: Path):
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for diagnostics controller validation"
    probe = tmp_path / "diagnostics_controller_probe.lua"
    probe.write_text(
        r'''
local diagnostics = dofile(arg[1])
local actions = 0
local player = {
  canWalk = function(self) return true end,
  isAutoWalking = function(self) return false end,
  isInProtectionZone = function(self) return true end,
  getStates = function(self) return 7 end,
}
local target = {getName = function(self) return "Training Target" end}
local game = {
  getContainers = function() return {} end,
  getAttackingCreature = function() return target end,
  attack = function() actions = actions + 1 end,
  talk = function() actions = actions + 1 end,
}
local updated = 0
local helper = {widgets = {}, diagnostics_buffer = {}}
local controller = diagnostics.createController({
  helper = helper,
  config = {tools = {feature_flags = {diagnostics = true}, diagnostics_export_limit = 3}},
  version = "test",
  content_width = 400,
  fit_text = tostring,
  update_snapshot = function(context, values, rows)
    updated = updated + 1
    assert(type(values.api) == "string" and #rows > 0)
  end,
  get_player = function() return player end,
  get_position = function() return {x = 1, y = 2, z = 7} end,
  read_vitals = function() return {source = "probe", hp = 100, max_hp = 100, hp_percent = 100} end,
  pcall_number = function(owner, method) return owner[method](owner) end,
  online = function() return true end,
  game = game,
  map = {getTile = function() return {getFlags = function() return 0 end} end},
  ui = {}, keyboard = {}, resources = {}, runtime_core = {},
  clock_millis = function() return 100 end,
  now_ms = function() return 100 end,
  status = function(text) assert(type(text) == "string") end,
  loot_adapter_text = function() return "passive loot adapter" end,
})
assert(controller.runApiProbe("manual") == true)
assert(helper.api_probe_ran == true)
assert(type(helper.api_snapshot) == "table")
assert(#helper.diagnostics_buffer == 1)
assert(updated == 1)
assert(actions == 0)
assert(diagnostics.contract().owns_api_probe_controller == true)
''',
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(DIAGNOSTICS)],
        check=False,
        capture_output=True,
        text=True,
        cwd=tmp_path,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
