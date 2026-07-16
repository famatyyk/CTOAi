from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OTCLIENT = ROOT / "scripts/lua/otclient"
PRIMITIVES = OTCLIENT / "ctoa_helper_ui_primitives.lua"
UI = OTCLIENT / "ctoa_helper_ui.lua"
MODULES = OTCLIENT / "ctoa_helper_modules.lua"
WRAPPER = ROOT / "scripts/windows/solteria_helper_test_env.ps1"


def test_ui_uses_one_passive_primitive_owner() -> None:
    primitives = PRIMITIVES.read_text(encoding="utf-8")
    ui = UI.read_text(encoding="utf-8")
    modules = MODULES.read_text(encoding="utf-8")
    wrapper = WRAPPER.read_text(encoding="utf-8")

    assert 'rawget(_G, "CTOA_HELPER_UI_PRIMITIVES")' in primitives
    assert "_G.CTOA_HELPER_UI_PRIMITIVES = Primitives" in primitives
    assert 'rawget(_G, "CTOA_HELPER_UI_PRIMITIVES")' in ui
    assert 'depends_on = {"ctoa_helper_ui_primitives"}' in modules
    assert 'mods/ctoa_otclient/ctoa_helper_ui_primitives.lua' in wrapper
    for name in (
        "shortText",
        "fitText",
        "setWidgetText",
        "createWidget",
        "settingRowGeometry",
        "metricCardGeometry",
        "profileFieldGeometry",
        "sectionBodyGeometry",
        "mergeContext",
        "ruleEditorNavigation",
    ):
        assert f"function Primitives.{name}" in primitives
    for forbidden in ("g_game.talk", "g_game.attack", "autoWalk", "useInventoryItem"):
        assert forbidden not in primitives


def test_primitive_form_geometry_and_rule_navigation_are_bounded(tmp_path: Path) -> None:
    lua = shutil.which("lua") or shutil.which("lua5.4") or shutil.which("lua54")
    assert lua, "Lua interpreter is required for P26.1 validation"
    probe = tmp_path / "ui_primitives_probe.lua"
    probe.write_text(
        r'''
local p = dofile(arg[1])
assert(p.shortText("abcdefgh", 5) == "ab...")
assert(p.fitText("a long operator value", 24, 1.0) ~= "")
local row = p.settingRowGeometry(100, 300, {value_w = 108})
assert(row.value_x > row.name_x and row.value_width >= 92)
local card = p.metricCardGeometry(20, 300)
assert(card.label_width + card.value_width < 300)
local field = p.profileFieldGeometry(20, 216)
assert(field.prev_x < field.value_x and field.value_x < field.next_x)
local body = p.sectionBodyGeometry(20, 30, 300, 200)
assert(body.x == 18 and body.width == 304 and body.height == 200)
local merged = p.mergeContext({a = 1, b = 1}, {b = 2, c = 3})
assert(merged.a == 1 and merged.b == 2 and merged.c == 3)
local empty = p.ruleEditorNavigation(0, 99, 1)
assert(empty.index == 0 and empty.contained == true)
local low = p.ruleEditorNavigation(4, 1, -99)
assert(low.index == 1 and low.can_previous == false)
local high = p.ruleEditorNavigation(4, 4, 99)
assert(high.index == 4 and high.can_next == false)
local contract = p.contract()
assert(contract.runtime_actions == false and contract.dispatch_allowed == false)
''',
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(PRIMITIVES)],
        check=False,
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
