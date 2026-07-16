from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OTCLIENT = ROOT / "scripts/lua/otclient"
RULE_EDITORS = OTCLIENT / "ctoa_helper_ui_rule_editors.lua"
UI = OTCLIENT / "ctoa_helper_ui.lua"
MODULES = OTCLIENT / "ctoa_helper_modules.lua"
WRAPPER = ROOT / "scripts/windows/solteria_helper_test_env.ps1"


def test_rule_editors_are_one_passive_packaged_owner() -> None:
    editors = RULE_EDITORS.read_text(encoding="utf-8")
    ui = UI.read_text(encoding="utf-8")
    modules = MODULES.read_text(encoding="utf-8")
    wrapper = WRAPPER.read_text(encoding="utf-8")

    assert 'rawget(_G, "CTOA_HELPER_UI_RULE_EDITORS")' in editors
    assert "_G.CTOA_HELPER_UI_RULE_EDITORS = RuleEditors" in editors
    assert 'rawget(_G, "CTOA_HELPER_UI_RULE_EDITORS")' in ui
    assert "delegates_rule_editor_presentation = true" in ui
    assert "owns_magic_rule_editor = false" in ui
    assert "owns_target_rule_editor = false" in ui
    assert "owns_combat_action_rule_editor = false" in ui
    assert (
        'depends_on = {"ctoa_helper_ui_primitives", "ctoa_helper_ui_composition", '
        '"ctoa_helper_ui_rule_editors"}'
    ) in modules
    assert "mods/ctoa_otclient/ctoa_helper_ui_rule_editors.lua" in wrapper
    for name in (
        "addRuleEditorChrome",
        "addTargetRuleEditor",
        "addMagicRuleEditor",
        "addCombatActionRuleEditor",
    ):
        assert f"function RuleEditors.{name}" in editors
        assert f"return RuleEditors.{name}(Ui," in ui
    assert "owns_shared_editor_chrome = true" in editors
    assert "owns_target_rule_editor = true" in editors
    assert "owns_magic_rule_editor = true" in editors
    assert "owns_combat_action_rule_editor = true" in editors
    for forbidden in (
        "g_game",
        "autoWalk",
        "useInventoryItem",
        "sendActionbarSlot",
        "castSpell",
    ):
        assert forbidden not in editors


def test_shared_editor_chrome_keeps_callbacks_injected_and_action_free(
    tmp_path: Path,
) -> None:
    lua = shutil.which("lua") or shutil.which("lua5.4") or shutil.which("lua54")
    assert lua, "Lua interpreter is required for P26.3 validation"
    probe = tmp_path / "ui_rule_editors_probe.lua"
    probe.write_text(
        r"""
local editors = dofile(arg[1])
local widgets = {}
local callbacks = {}
local ui = {
  styleLabel = function() end,
  styleMiniButton = function() end,
}
local ctx = {
  ui_style = {}, align_center = 0,
  bind_click = function(widget, callback) callbacks[widget.id] = callback end,
  style_action_button = function() end,
}
local function add(kind, id, text, x, y, width, height)
  local widget = {kind = kind, id = id, text = text, x = x, y = y, width = width, height = height}
  widgets[id] = widget
  return widget
end
local previous = 0
local added = 0
local chrome = editors.addRuleEditorChrome(ui, ctx, {}, {
  add = add, panel_x = 10, panel_w = 300, row_y = 20,
  selector_id = "selector", previous_id = "previous", next_id = "next",
  on_previous = function() previous = previous + 1 end,
  actions = {{id = "add", text = "ADD", callback = function() added = added + 1 end}},
  action_y = 50,
})
assert(chrome.selector == widgets.selector and chrome.actions.add == widgets.add)
assert(widgets.selector.x == 52 and widgets.next.x + widgets.next.width == 310)
callbacks.previous()
callbacks.add()
assert(previous == 1 and added == 1)
local contract = editors.contract()
assert(contract.callbacks_injected == true and contract.mutates_profiles_directly == false)
assert(contract.runtime_actions == false and contract.dispatch_allowed == false)
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(RULE_EDITORS)],
        check=False,
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
