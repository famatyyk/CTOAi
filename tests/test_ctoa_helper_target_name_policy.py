from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OTCLIENT_DIR = ROOT / "scripts" / "lua" / "otclient"
TARGETING = OTCLIENT_DIR / "ctoa_helper_targeting.lua"
UI = OTCLIENT_DIR / "ctoa_helper_ui.lua"
HELPER = OTCLIENT_DIR / "ctoa_native_helper.lua"


def _lua() -> str | None:
    return shutil.which("lua") or shutil.which("lua5.4") or shutil.which("lua54")


def test_target_name_policy_is_bounded_ordered_and_action_free(tmp_path: Path) -> None:
    lua = _lua()
    assert lua, "Lua interpreter is required for target-name policy validation"
    probe = tmp_path / "target_name_policy_probe.lua"
    probe.write_text(
        r'''
local targeting = dofile(arg[1])
local parsed = targeting.parseNameList(" Demon, dragon lord;DEMON\n  cyclops  ")
assert(#parsed == 3)
assert(parsed[1] == "demon")
assert(parsed[2] == "dragon lord")
assert(parsed[3] == "cyclops")
assert(targeting.formatNameList(parsed) == "demon, dragon lord, cyclops")

local tools = {ignored_names = {"old"}, priority_names = {"rat"}}
local names, decision = targeting.updateNameList(tools, "priority_names", "dragon, demon, dragon")
assert(decision.allowed == true and decision.runtime_actions == false)
assert(#names == 2 and names[1] == "dragon" and names[2] == "demon")
assert(tools.priority_names == names)
assert(targeting.priorityRank("Demon", tools.priority_names) == 2)

local cleared, clearDecision = targeting.updateNameList(tools, "ignored_names", "")
assert(clearDecision.allowed == true and #cleared == 0 and #tools.ignored_names == 0)
local denied, deniedDecision = targeting.updateNameList(tools, "rotation_spells", "exori")
assert(denied == nil and deniedDecision.allowed == false)

local many = {}
for index = 1, 50 do many[#many + 1] = "monster " .. tostring(index) end
assert(#targeting.sanitizeNameList(many) == 32)
assert(targeting.contract().owns_editable_name_policy == true)
assert(targeting.contract().runtime_actions == false)
''',
        encoding="utf-8",
    )
    subprocess.run([lua, str(probe), str(TARGETING)], check=True, cwd=ROOT)


def test_target_name_policy_editor_is_native_autosaved_and_owned() -> None:
    ui = UI.read_text(encoding="utf-8")
    helper = HELPER.read_text(encoding="utf-8")
    targeting = TARGETING.read_text(encoding="utf-8")

    assert 'ctx.create_widget("TextEdit"' in ui
    assert '"ctoaTargetRuleEditorIgnored"' in ui
    assert '"ctoaTargetRuleEditorPriority"' in ui
    assert "editor.onTextChange" in ui
    assert "ctx.update_target_name_list(key, text)" in ui
    assert 'markProfileDirty("target_name_policy:"' in helper
    assert 'moduleValue(externalTargeting, "updateNameList"' in helper
    assert "function Targeting.updateNameList" in targeting
    assert "MAX_NAME_POLICY_ENTRIES = 32" in targeting
    assert "g_game" not in targeting
    assert "castSpell(" not in targeting
