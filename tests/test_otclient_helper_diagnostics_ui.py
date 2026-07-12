import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIAGNOSTICS = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_diagnostics.lua"
UI = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_ui.lua"
RECOVERY = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_recovery_runtime.lua"


def test_diagnostics_values_and_ui_adapter_keep_snapshot_formatting_out_of_shell():
    probe = r'''
local diagnostics = dofile(arg[1])
local ui = dofile(arg[2])
local recovery = dofile(arg[3])
local values = diagnostics.snapshotUiValues(
  {version = "v-test", movement = "move", magic = "magic", loot = "loot"},
  {diagnostics = true},
  {{captured_ms = 1}},
  20,
  "fallback"
)
assert(string.find(values.api, "API v-test", 1, true))
assert(string.find(values.movement, "Move: move", 1, true))
assert(string.find(values.magic_loot, "Magic: magic", 1, true))
assert(string.find(values.buffer, "Export: 1/20", 1, true))

local seen = {}
local widgets = {}
for _, name in ipairs({"tools_api_snapshot", "tools_diag_flags"}) do
  widgets[name] = {setText = function(self, text) seen[name] = text end}
end
assert(ui.updateDiagnosticsSnapshot({
  widgets = widgets,
  content_width = 320,
  fit_text = function(text) return text end,
}, values, {
  {widget = "tools_api_snapshot", text = "api"},
  {widget = "tools_diag_flags", text = "flags"},
}))
assert(seen.tools_api_snapshot == values.api)
assert(seen.tools_diag_flags == values.flags)
local vitals = recovery.readVitals({
  getHealth = function() return 80 end,
  getMaxHealth = function() return 100 end,
  getMana = function() return 40 end,
  getMaxMana = function() return 80 end,
})
assert(vitals.source == "real" and vitals.hp_percent == 80 and vitals.mana_percent == 50)
print("diagnostics-ui-adapter=passed")
'''
    completed = subprocess.run(
        ["lua", "-", str(DIAGNOSTICS), str(UI), str(RECOVERY)],
        input=probe,
        text=True,
        capture_output=True,
        check=False,
        cwd=ROOT,
    )
    assert completed.returncode == 0, completed.stderr
    assert "diagnostics-ui-adapter=passed" in completed.stdout
