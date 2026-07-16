from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from scripts.ops import ctoa_helper_ui_preview as preview


ROOT = Path(__file__).resolve().parents[1]
OTCLIENT_DIR = ROOT / "scripts" / "lua" / "otclient"
UI = OTCLIENT_DIR / "ctoa_helper_ui.lua"
UI_PRIMITIVES = OTCLIENT_DIR / "ctoa_helper_ui_primitives.lua"
HUD = OTCLIENT_DIR / "ctoa_helper_hud.lua"
MODULE_STATUS = OTCLIENT_DIR / "ctoa_helper_module_status.lua"
HELPER = OTCLIENT_DIR / "ctoa_native_helper.lua"


def _lua() -> str | None:
    return shutil.which("lua") or shutil.which("lua5.4") or shutil.which("lua54")


def test_operator_states_and_rule_navigation_are_bounded_and_action_free(
    tmp_path: Path,
) -> None:
    lua = _lua()
    assert lua, "Lua interpreter is required for P22.2 validation"
    probe = tmp_path / "operator_feedback_probe.lua"
    probe.write_text(
        r'''
local primitives = dofile(arg[1])
local ui = dofile(arg[2])
local hud = dofile(arg[3])
local moduleStatus = dofile(arg[4])
assert(primitives.contract().runtime_actions == false)

assert(ui.operatorRuntimeState({enabled = false}) == "disabled")
assert(ui.operatorRuntimeState({enabled = true}) == "active")
assert(ui.operatorRuntimeState({enabled = true, stale = true}) == "stale")
assert(ui.operatorRuntimeState({enabled = true, stale = true, blocked_reason = "safe boot"}) == "blocked")
assert(ui.normalizeOperatorState("review_ready") == "active")
assert(ui.normalizeOperatorState("missing_components") == "blocked")
assert(ui.normalizeOperatorState("unknown") == "stale")

local style = {
  state_off = "#111111", state_on = "#22aa22", state_blocked = "#cc2222",
  state_stale = "#ddaa22", surface_inset = "#000000",
}
local colors = {}
for _, state in ipairs({"disabled", "blocked", "stale", "active"}) do
  local widget = {
    setColor = function(self, value) self.color = value end,
    setBackgroundColor = function(self, value) self.background = value end,
    setBorderColor = function(self, value) self.border = value end,
    setBorderWidth = function(self, value) self.border_width = value end,
    setOpacity = function(self, value) self.opacity = value end,
  }
  assert(ui.styleOperatorState(widget, state, style) == state)
  assert(widget.color == widget.border and widget.border_width == 1 and widget.opacity == 1)
  colors[widget.color] = true
end
local distinct = 0
for _ in pairs(colors) do distinct = distinct + 1 end
assert(distinct == 4)

local empty = ui.ruleEditorNavigation(0, 99, 1)
assert(empty.index == 0 and empty.count == 0 and empty.contained == true)
local first = ui.ruleEditorNavigation(16, 1, -99)
assert(first.index == 1 and first.can_previous == false and first.can_next == true)
local last = ui.ruleEditorNavigation(16, 16, 99)
assert(last.index == 16 and last.can_previous == true and last.can_next == false)
local middle = ui.ruleEditorNavigation(16, 8, 1)
assert(middle.index == 9 and middle.contained == true)

local hudText = hud.runtimeText({version = "test", runtime_state = "stale", decision = "waiting"})
assert(string.find(hudText, "STALE | waiting", 1, true) ~= nil)
local board = moduleStatus.snapshot({
  ready = {status = "ready"},
  stale = {status = "stale"},
  blocked = {status = "blocked"},
}, {"ready", "stale", "blocked"})
assert(board.status == "blocked")
assert(board.counts.ready == 1 and board.counts.stale == 1 and board.counts.blocked == 1)

local uiContract = ui.contract()
local hudContract = hud.contract()
local statusContract = moduleStatus.contract()
assert(uiContract.owns_four_state_operator_feedback == true)
assert(uiContract.owns_bounded_rule_editor_navigation == true)
assert(hudContract.owns_runtime_state_text == true)
assert(statusContract.distinguishes_stale_module_status == true)
assert(uiContract.runtime_actions == false and hudContract.runtime_actions == false)
assert(statusContract.runtime_actions == false and statusContract.dispatch_allowed == false)
''',
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(UI_PRIMITIVES), str(UI), str(HUD), str(MODULE_STATUS)],
        check=False,
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_default_and_compact_previews_remain_contained() -> None:
    source = HELPER.read_text(encoding="utf-8")
    default_window = preview.extract_window(source, compact=False)
    compact_window = preview.extract_window(source, compact=True)
    default_widgets = preview.extract_widgets(source, compact=False)
    compact_widgets = preview.extract_widgets(source, compact=True)

    assert default_window == compact_window == (0, 0, 690, 560)
    assert preview.validate(default_window, default_widgets) == []
    assert preview.validate(compact_window, compact_widgets) == []
    assert len(default_widgets) == len(compact_widgets) == 208

    default_layout = preview.extract_layout_variables(source, compact=False)
    compact_layout = preview.extract_layout_variables(source, compact=True)
    assert compact_layout["UI_LAYOUT.row_2_y"] < default_layout["UI_LAYOUT.row_2_y"]
    assert compact_layout["UI_LAYOUT.footer_y"] < default_layout["UI_LAYOUT.footer_y"]


def test_p22_feedback_wiring_has_no_gameplay_dispatch() -> None:
    ui = UI.read_text(encoding="utf-8")
    hud = HUD.read_text(encoding="utf-8")

    state_start = ui.index("function Ui.normalizeOperatorState")
    state_end = ui.index("function Ui.styleRuleCard", state_start)
    state_source = ui[state_start:state_end]
    for forbidden in ("g_game", "talk(", "attack(", "autoWalk(", "useInventoryItem"):
        assert forbidden not in state_source
        assert forbidden not in hud
