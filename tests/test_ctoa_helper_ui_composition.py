from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OTCLIENT = ROOT / "scripts/lua/otclient"
COMPOSITION = OTCLIENT / "ctoa_helper_ui_composition.lua"
UI = OTCLIENT / "ctoa_helper_ui.lua"
MODULES = OTCLIENT / "ctoa_helper_modules.lua"
WRAPPER = ROOT / "scripts/windows/solteria_helper_test_env.ps1"


def test_composition_is_one_passive_packaged_owner() -> None:
    composition = COMPOSITION.read_text(encoding="utf-8")
    ui = UI.read_text(encoding="utf-8")
    modules = MODULES.read_text(encoding="utf-8")
    wrapper = WRAPPER.read_text(encoding="utf-8")

    assert 'rawget(_G, "CTOA_HELPER_UI_COMPOSITION")' in composition
    assert "_G.CTOA_HELPER_UI_COMPOSITION = Composition" in composition
    assert 'rawget(_G, "CTOA_HELPER_UI_COMPOSITION")' in ui
    assert 'depends_on = {"ctoa_helper_ui_primitives", "ctoa_helper_ui_composition"}' in modules
    assert 'mods/ctoa_otclient/ctoa_helper_ui_composition.lua' in wrapper
    for name in (
        "sidebarTabs",
        "sidebarGeometry",
        "huntingSubtabs",
        "subtabContentY",
        "toolsSubtabs",
        "toolsTableHeaders",
        "cavebotActionSpecs",
    ):
        assert f"function Composition.{name}" in composition
        assert f"return Composition.{name}" in ui
    for forbidden in (
        "mark_profile_dirty",
        "sync_from_ui",
        "g_game.talk",
        "g_game.attack",
        "autoWalk",
        "useInventoryItem",
    ):
        assert forbidden not in composition


def test_composition_metadata_is_contained_and_callback_transparent(tmp_path: Path) -> None:
    lua = shutil.which("lua") or shutil.which("lua5.4") or shutil.which("lua54")
    assert lua, "Lua interpreter is required for P26.2 validation"
    probe = tmp_path / "ui_composition_probe.lua"
    probe.write_text(
        r'''
local c = dofile(arg[1])
local layout = {overview_tab_y = 120, row_7_y = 320}
local tabs = c.sidebarTabs(layout)
assert(#tabs == 12 and tabs[1].target == "overview" and tabs[12].target == "profile")
local geometry = c.sidebarGeometry(layout, tabs)
assert(geometry.count == 12 and geometry.dense == true and geometry.utility_divider_y ~= nil)
local hunting = c.huntingSubtabs(20, 100, 466)
assert(#hunting == 5 and hunting[1].x == 20)
assert(hunting[5].x + hunting[5].width == 486)
local tools = c.toolsSubtabs(20, 100, 466)
assert(#tools == 4 and tools[4].x + tools[4].width <= 486)
local callback = function() return "kept" end
local width, actions = c.cavebotActionSpecs(20, 466, layout, {add = callback})
assert(width > 0 and #actions == 8 and actions[1].callback == callback)
assert(actions[8].x + width <= 486)
local contract = c.contract()
assert(contract.mutates_profiles == false)
assert(contract.runtime_actions == false and contract.dispatch_allowed == false)
''',
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(COMPOSITION)],
        check=False,
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
