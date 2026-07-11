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
