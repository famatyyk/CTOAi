"""Render and validate CTOA OTClient helper UI without launching the game client.

The script reads the Lua helper, extracts the widget coordinates from buildUi(),
checks whether controls fit inside the window, and writes a lightweight HTML
preview that can be opened independently from Solteria.
"""

from __future__ import annotations

import argparse
import ast
import html
import math
import operator
import re
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "scripts" / "lua" / "otclient" / "ctoa_native_helper.lua"
UI_HELPER = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_ui.lua"
OUT_DIR = ROOT / "runtime" / "otclient_ui_preview"
OUT_HTML = OUT_DIR / "ctoa_helper_preview.html"


DEFAULT_HEIGHTS = {
    "Button": 32,
    "CheckBox": 28,
    "Label": 20,
    "RuleCard": 20,
    "ToggleButton": 34,
}


@dataclass
class Widget:
    kind: str
    widget_id: str
    text: str
    x: int
    y: int
    width: int
    height: int
    section: str

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height


def clean_text(raw: str, widget_id: str) -> str:
    raw = raw.strip()
    labels = {
        "ctoaProfileName": "EK monk profile",
        "ctoaProfileSpell": "Spell | exura ico",
        "ctoaProfileSpellThreshold": "Normal heal | <= 80%",
        "ctoaProfileCriticalSpell": "Critical spell | exura med ico",
        "ctoaProfilePotionHotkey": "Potion hotkey | F1",
        "ctoaProfilePotionName": "Potion name | Health Potion",
        "ctoaProfilePotionThreshold": "Potion | <= 62%",
        "ctoaProfileSpellHeal": "Spell heal | ON",
        "ctoaProfilePotionHeal": "Potion heal | ON",
        "ctoaProfileAutoHaste": "Auto haste | OFF",
        "ctoaProfileSpellRotation": "Spell rotation | ON",
        "ctoaProfileAutoExeta": "Auto exeta | ON",
        "ctoaProfileExetaMin": "Exeta min | 2",
        "ctoaProfileRotation": "Rotation preset | smart",
        "ctoaProfileRotationInfo": "Rotation: exori gran 3+ / exori 2+ / exori min 2+",
        "ctoaProfileStatus": "Autosave: live",
        "ctoaUiHotkey": "Open hotkey | Ctrl+H",
        "ctoaUiAutoHide": "Auto hide | OFF",
        "ctoaUiHudEnabled": "HUD enabled | ON",
        "ctoaUiHudPos": "HUD position | X 22 / Y 170",
        "ctoaUiSummary": "UI only: hotkey, autoshow, HUD placement",
        "ctoaUiThemeHeader": "Theme",
        "ctoaUiThemePreset": "Theme preset | Classic",
        "ctoaUiCompactMode": "Compact mode | OFF",
        "ctoaUiWindowPos": "Window position | X 520 / Y 34",
        "ctoaUiStatus": "Autosave: live",
        "ctoaSpellHeal": "Spell Healing | ON",
        "ctoaSpellThreshold": "Normal heal | <= 80%",
        "ctoaSpellName": "Spell | exura ico",
        "ctoaCriticalSpell": "Critical heal | exura med ico",
        "ctoaPotionHeal": "Potion Healing | ON",
        "ctoaPotionThreshold": "Potion | <= 62%",
        "ctoaPotionHotkey": "Hotkey | F1",
        "ctoaPotionInfo": "Health Potion / Client hotkey",
        "ctoaPotionWarning": "Set F1 to HP potion in client hotkeys",
        "ctoaHealingSpellPriority": "1",
        "ctoaHealingPotionPriority": "2",
        "ctoaAutoHaste": "Auto Haste | OFF",
        "ctoaSpellRotation": "Spell Rotation | ON",
        "ctoaRotationListA": "AoE min mobs | 2",
        "ctoaRotationListB": "Exori Gran min | 3",
        "ctoaSingleTarget": "Single fallback | ICO",
        "ctoaAutoExeta": "Auto Exeta | ON",
        "ctoaExetaList": "Visible mobs for exeta | 2",
        "ctoaMonsterStats": "Monsters: nearby 0 / visible 0",
        "ctoaOverviewAvatarFrame": "",
        "ctoaOverviewAvatar": "EK",
        "ctoaOverviewAvatarName": "EK monk profile",
        "ctoaOverviewHpBar": "",
        "ctoaOverviewEquipSlot1": "",
        "ctoaOverviewEquipSlot2": "",
        "ctoaOverviewEquipSlot3": "",
        "ctoaOverviewEquipSlot4": "",
        "ctoaOverviewEquipSlot5": "",
        "ctoaOverviewEquipSlot6": "",
        "ctoaOverviewEquipSlot7": "",
        "ctoaOverviewEquipSlot8": "",
    }
    if widget_id in labels:
        return labels[widget_id]
    placeholder = re.match(r"ctoa([A-Za-z_]+)Placeholder(\d+)", widget_id)
    if placeholder:
        return f"{placeholder.group(1).replace('_', ' ').title()} row {placeholder.group(2)}"
    if raw.startswith('"'):
        match = re.match(r'"([^"]*)"', raw)
        if match:
            return match.group(1)
    return widget_id


def split_lua_args(arg_text: str) -> list[str]:
    args: list[str] = []
    current: list[str] = []
    depth = 0
    in_string = False
    escape = False
    for char in arg_text:
        if in_string:
            current.append(char)
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
            current.append(char)
            continue
        if char in "({[":
            depth += 1
            current.append(char)
            continue
        if char in ")}]":
            depth -= 1
            current.append(char)
            continue
        if char == "," and depth == 0:
            args.append("".join(current).strip())
            current = []
            continue
        current.append(char)
    if current:
        args.append("".join(current).strip())
    return args


_SAFE_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
}
_SAFE_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _eval_numeric_expr(expr: str) -> int:
    def visit(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.BinOp):
            op = _SAFE_BIN_OPS.get(type(node.op))
            if op is None:
                raise ValueError("unsupported operator")
            return float(op(visit(node.left), visit(node.right)))
        if isinstance(node, ast.UnaryOp):
            op = _SAFE_UNARY_OPS.get(type(node.op))
            if op is None:
                raise ValueError("unsupported unary operator")
            return float(op(visit(node.operand)))
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "floor"
            and len(node.args) == 1
            and not node.keywords
        ):
            return float(math.floor(visit(node.args[0])))
        raise ValueError("unsupported expression")

    tree = ast.parse(expr, mode="eval")
    return int(visit(tree))


def as_int(value: str | None, fallback: int, variables: dict[str, int] | None = None) -> int:
    if not value:
        return fallback
    expr = value.strip()
    if re.fullmatch(r"\d+", expr):
        return int(expr)
    if variables and expr in variables:
        return variables[expr]
    if variables:
        expanded = expr
        for name, number in sorted(variables.items(), key=lambda item: len(item[0]), reverse=True):
            expanded = re.sub(rf"\b{re.escape(name)}\b", str(number), expanded)
        expanded = expanded.replace("math.floor", "floor")
        if re.fullmatch(r"[\d\s+\-*/().floor]+", expanded):
            try:
                return _eval_numeric_expr(expanded)
            except Exception:
                return fallback
    return fallback


def section_from_args(args: list[str]) -> str:
    for arg in reversed(args):
        if arg in (
            '"healing"',
            '"heal_friend"',
            '"conditions"',
            '"cavebot"',
            '"equipment"',
            '"hunting_targeting"',
            '"hunting_target_rules"',
            '"hunting_magic"',
            '"hunting_actions"',
            '"hunting_magic_runtime"',
            '"tools_helper"',
            '"tools_pvp"',
            '"tools_timer"',
            '"tools_diag"',
            '"tools"',
            '"scripting"',
            '"profile"',
            '"ui"',
        ):
            return arg.strip('"')
        if arg == "nil":
            return "global"
    return "global"


def section_from_id(widget_id: str, fallback: str = "global") -> str:
    prefixes = (
        ("ctoaOverview", "overview"),
        ("ctoaHealFriend", "heal_friend"),
        ("ctoaheal_friend", "heal_friend"),
        ("ctoaConditions", "conditions"),
        ("ctoaconditions", "conditions"),
        ("ctoaCavebot", "cavebot"),
        ("ctoacavebot", "cavebot"),
        ("ctoaEquipment", "equipment"),
        ("ctoaequipment", "equipment"),
        ("ctoaScripting", "scripting"),
        ("ctoascripting", "scripting"),
        ("ctoaSpellRotation", "hunting_magic_runtime"),
        ("ctoaHealing", "healing"),
        ("ctoaSpell", "healing"),
        ("ctoaCritical", "healing"),
        ("ctoaPotion", "healing"),
        ("ctoaHuntingTargetRules", "hunting_target_rules"),
        ("ctoaHuntingActions", "hunting_actions"),
        ("ctoaHunting", "hunting"),
        ("ctoaRuneShooter", "hunting_magic_runtime"),
        ("ctoaMagicPriority", "hunting_magic_runtime"),
        ("ctoaRotationLockMs", "hunting_magic_runtime"),
        ("ctoaRuneHotkeyMagic", "hunting_magic_runtime"),
        ("ctoaAutoExetaMagic", "hunting_magic_runtime"),
        ("ctoaMagicRuntime", "hunting_magic_runtime"),
        ("ctoaMagicRule", "hunting_magic"),
        ("ctoaCombatAction", "hunting_actions"),
        ("ctoaRuneNameAction", "hunting_actions"),
        ("ctoaRuneHotkeyAction", "hunting_actions"),
        ("ctoaRuneMinVisibleAction", "hunting_actions"),
        ("ctoaRuneCooldownAction", "hunting_actions"),
        ("ctoaOffensiveStance", "hunting_actions"),
        ("ctoaDefensiveStance", "hunting_actions"),
        ("ctoaStanceCooldownAction", "hunting_actions"),
        ("ctoaTargetRuleEditorIgnored", "hunting_targeting"),
        ("ctoaTargetRuleEditorPriority", "hunting_targeting"),
        ("ctoaTargetRule", "hunting_target_rules"),
        ("ctoaAutoAttack", "hunting_targeting"),
        ("ctoaAutoFollowTargeting", "hunting_targeting"),
        ("ctoaHoldTargetPvp", "tools_pvp"),
        ("ctoaHoldTarget", "hunting_targeting"),
        ("ctoaAttackRange", "hunting_targeting"),
        ("ctoaTargetTimeoutHunting", "hunting_targeting"),
        ("ctoaPreferLowHp", "hunting_targeting"),
        ("ctoaMagic", "hunting"),
        ("ctoaToolsTimer", "tools_timer"),
        ("ctoaToolsDiag", "tools_diag"),
        ("ctoaTools", "tools"),
        ("ctoaAutoFollow", "tools_helper"),
        ("ctoaAutoHasteTools", "tools_helper"),
        ("ctoaAutoExetaTools", "tools_helper"),
        ("ctoaExetaMinVisible", "tools_helper"),
        ("ctoaPauseInPzTools", "tools_helper"),
        ("ctoaRunePvpSafeTools", "tools_pvp"),
        ("ctoaPauseInPzPvp", "tools_pvp"),
        ("ctoaRuneRequiresTargetPvp", "tools_pvp"),
        ("ctoaProfile", "profile"),
        ("ctoaUi", "ui"),
    )
    for prefix, section in prefixes:
        if widget_id.startswith(prefix):
            return section
    return fallback


def lua_table_field(table_source: str, field: str) -> str:
    match = re.search(rf'{field}\s*=\s*"([^"]*)"', table_source)
    return match.group(1) if match else ""


def width_from_args(fn: str, args: list[str], fallback: int, variables: dict[str, int]) -> int:
    if fn in {"addSectionBand", "addMetricCard"} and len(args) >= 7:
        return as_int(args[6], fallback, variables)
    if fn == "addSidebarCard" and len(args) >= 6:
        return as_int(args[5], fallback, variables)
    if fn == "add_priority_badge":
        return 20
    if fn in {"add_summary_strip", "add_footer_strip"} and len(args) >= 6:
        return as_int(args[5], fallback, variables)
    if fn == "addSettingRow" and len(args) >= 7:
        return as_int(args[6], fallback, variables)
    if fn in {"addToggleSettingRow", "add_toggle_setting_row"} and len(args) >= 8:
        return as_int(args[7], fallback, variables)
    if fn in {"addProfileCycleRow", "add_profile_cycle_row"} and len(args) >= 9:
        return as_int(args[8], fallback, variables)
    if fn in {"addProfileStepRow", "add_profile_step_row"} and len(args) >= 11:
        return as_int(args[10], fallback, variables)
    if fn == "addProfileRotationRow" and len(args) >= 6:
        return as_int(args[5], fallback, variables)
    if fn == "addVectorStepRow" and len(args) >= 13:
        return as_int(args[12], fallback, variables)
    if fn in {"addLabel", "addMutedLabel", "addAccentLabel", "addRuleCard"} and len(args) >= 6:
        return as_int(args[5], fallback, variables)
    if fn == "addCheck" and len(args) >= 8:
        return as_int(args[7], fallback, variables)
    if fn == "addToggleButton" and len(args) >= 9:
        return as_int(args[8], fallback, variables)
    return fallback


def extract_layout_variables(source: str, compact: bool = False) -> dict[str, int]:
    variables: dict[str, int] = {}
    layout_source = source
    if (
        'moduleValue(externalUi, "newLayout")' in source
        and "local BASE_LAYOUT = {" not in source
        and UI_HELPER.is_file()
    ):
        layout_source += "\n" + UI_HELPER.read_text(encoding="utf-8")

    # The production shell delegates layout ownership to ctoa_helper_ui.lua.
    # Compose the same base + default tables here instead of requiring geometry
    # literals to remain duplicated in the shell just for static previewing.
    selected_layout = "COMPACT_LAYOUT" if compact else "DEFAULT_LAYOUT"
    for table_name in ("BASE_LAYOUT", selected_layout, "UI_LAYOUT"):
        layout_match = re.search(
            rf"local {table_name} = \{{(?P<body>.*?)\n\}}", layout_source, re.S
        )
        if not layout_match:
            continue
        for key, value in re.findall(r"(\w+)\s*=\s*(\d+)", layout_match.group("body")):
            variables[f"UI_LAYOUT.{key}"] = int(value)

    for name, expr in re.findall(r"local\s+(\w+)\s*=\s*(UI_LAYOUT\.\w+)", source):
        if expr in variables:
            variables[name] = variables[expr]
    # buildUi uses computed local geometry; the static parser needs the same
    # values to avoid reporting false overlaps at x=0.
    variables["sx"] = variables.get("UI_LAYOUT.sidebar_x", 44)
    variables["sw"] = variables.get("UI_LAYOUT.sidebar_w", 150)
    variables["cx"] = variables.get("UI_LAYOUT.content_x", 226)
    variables["cw"] = variables.get("UI_LAYOUT.content_w", 410)
    variables["panel_x"] = variables["cx"] + 8
    variables["panel_w"] = variables["cw"] - 16
    variables["panelX"] = variables["panel_x"]
    variables["panelW"] = variables["panel_w"]
    variables["profile_gap"] = 12
    variables["profile_col_w"] = (variables["panel_w"] - variables["profile_gap"]) // 2
    variables["profile_left_x"] = variables["panel_x"]
    variables["profile_right_x"] = variables["panel_x"] + variables["profile_col_w"] + variables["profile_gap"]
    variables["profile_block_w"] = variables["panel_w"]
    variables["profile_status_w"] = variables["panel_w"] - 116
    variables["profile_save_x"] = variables["panel_x"] + variables["panel_w"] - variables.get("UI_LAYOUT.profile_save_w", 62)
    variables["tools_tab_w"] = (variables["panel_w"] - 16) // 5
    variables["hunting_tab_w"] = (variables["panel_w"] - 6) // 2
    variables["cavebotActionW"] = (variables["panel_w"] - 18) // 4
    variables["cavebotActionY1"] = variables.get("UI_LAYOUT.row_7_y", 304) + 28
    variables["cavebotActionY2"] = variables.get("UI_LAYOUT.row_7_y", 304) + 52
    variables["body_y"] = variables.get("UI_LAYOUT.content_body_y", 124)
    variables["body_h"] = variables.get("UI_LAYOUT.content_body_h", 252)
    variables["bodyY"] = variables["body_y"]
    variables["bodyH"] = variables["body_h"]
    for alias in [
        "panel_x",
        "panel_w",
        "body_y",
        "body_h",
        "profile_left_x",
        "profile_right_x",
        "profile_col_w",
        "profile_block_w",
        "profile_status_w",
        "profile_save_x",
    ]:
        variables["ctx." + alias] = variables[alias]
    for key, value in list(variables.items()):
        if key.startswith("UI_LAYOUT."):
            variables["layout." + key.split(".", 1)[1]] = value
    variables["panelTop"] = variables.get("UI_LAYOUT.inner_title_y", 64) + variables.get("UI_LAYOUT.inner_title_h", 18) + 10
    variables["panelHeight"] = (
        variables.get("UI_LAYOUT.sheet_y", 54)
        + variables.get("UI_LAYOUT.sheet_h", 422)
        - variables["panelTop"]
        - 12
    )
    return variables


def extract_window(source: str, compact: bool = False) -> tuple[int, int, int, int]:
    variables = extract_layout_variables(source, compact=compact)
    for line in source.splitlines():
        if "ctoaNativeHelperWindow" not in line:
            continue
        args = split_lua_args(line[line.find("createWidget(") + len("createWidget(") :].rstrip(")"))
        if len(args) >= 8:
            width = as_int(args[6], variables.get("UI_LAYOUT.window_w", 680), variables)
            height = as_int(args[7], variables.get("UI_LAYOUT.window_h", 500), variables)
            return 0, 0, width, height
    raise SystemExit("Could not find ctoaNativeHelperWindow declaration.")


def extract_widgets(source: str, compact: bool = False) -> list[Widget]:
    widgets: list[Widget] = []
    lines = source.splitlines()
    variables = extract_layout_variables(source, compact=compact)
    section_overrides: dict[str, str] = {}
    widgets_by_var: dict[str, Widget] = {}

    for line in lines:
        stripped = line.strip()
        section_match = re.search(r'addToSection\("([^"]+)",\s*(?:Helper\.widgets\.|)([A-Za-z0-9_]+)\)', stripped)
        if section_match:
            section_overrides[section_match.group(2)] = section_match.group(1)
            if section_match.group(2) in widgets_by_var:
                widgets_by_var[section_match.group(2)].section = section_match.group(1)
            continue
        if "createWidget(" in stripped and '"ctoaNativeHelperWindow"' not in stripped:
            var_match = re.search(r'(?:Helper\.widgets\.|local\s+)?([A-Za-z0-9_]+)\s*=\s*createWidget\(', stripped)
            widget_var = var_match.group(1) if var_match else None
            call = stripped[stripped.find("createWidget(") + len("createWidget(") :].rstrip(")")
            args = split_lua_args(call)
            if len(args) >= 8 and args[0] in ('"Button"', '"Label"') and args[1] in {"window", "parent"}:
                kind = args[0].strip('"')
                widget_id = args[2].strip('"')
                text = args[3].strip('"')
                x = as_int(args[4], 0, variables)
                y = as_int(args[5], 0, variables)
                width = as_int(args[6], 120, variables)
                height = as_int(args[7], DEFAULT_HEIGHTS.get(kind, 20), variables)
                widgets.append(
                    Widget(
                        kind=kind,
                        widget_id=widget_id,
                        text=text,
                        x=x,
                        y=y,
                        width=width,
                        height=height,
                        section=section_from_id(widget_id, section_overrides.get(widget_var or "", "global")),
                    )
                )
                if widget_var:
                    widgets_by_var[widget_var] = widgets[-1]
                    if widget_var in section_overrides:
                        widgets[-1].section = section_overrides[widget_var]
            continue

        scaffold_match = re.search(r"(?:ctx\.)?add_section_scaffold\(window,\s*\{(?P<spec>.*?)\},\s*(?P<rest>.*)\)$", stripped)
        if not scaffold_match:
            scaffold_match = re.search(r"addSectionScaffold\(window,\s*\{(?P<spec>.*?)\},\s*(?P<rest>.*)\)$", stripped)
        if scaffold_match:
            spec = scaffold_match.group("spec")
            args = split_lua_args(scaffold_match.group("rest"))
            if len(args) >= 4:
                section = lua_table_field(spec, "section")
                widget_id = lua_table_field(spec, "header_id")
                title = lua_table_field(spec, "title")
                widgets.append(
                    Widget(
                        kind="RuleCard",
                        widget_id=widget_id,
                        text=title,
                        x=as_int(args[0], 0, variables),
                        y=variables.get("UI_LAYOUT.section_y", 96),
                        width=as_int(args[2], 210, variables),
                        height=DEFAULT_HEIGHTS["RuleCard"],
                        section=section_from_id(widget_id, section or "global"),
                    )
                )
            continue

        fn_match = re.search(
            r"(?:ctx\.)?(add(?:Muted|Accent)?Label|addSidebarCard|addRuleCard|addCheck|addToggleButton|addSectionBand|addMetricCard|addSettingRow|addToggleSettingRow|addProfileCycleRow|addProfileStepRow|addProfileRotationRow|addVectorStepRow|add_priority_badge|add_summary_strip|add_footer_strip|add_toggle_setting_row|add_profile_cycle_row|add_profile_step_row)\((.*)\)$",
            stripped,
        )
        if not fn_match:
            continue
        fn = fn_match.group(1)
        args = split_lua_args(fn_match.group(2))
        if len(args) < 5 or args[0] not in {"window", "parent"}:
            continue
        widget_id = args[1].strip('"')
        kind = {
            "add_priority_badge": "Label",
            "add_summary_strip": "Label",
            "add_footer_strip": "Label",
            "addCheck": "CheckBox",
            "addToggleButton": "ToggleButton",
            "addRuleCard": "RuleCard",
            "addSidebarCard": "RuleCard",
            "addMetricCard": "RuleCard",
            "addSectionBand": "RuleCard",
            "addSettingRow": "RuleCard",
            "addToggleSettingRow": "RuleCard",
            "addProfileCycleRow": "RuleCard",
            "addProfileStepRow": "RuleCard",
            "addProfileRotationRow": "RuleCard",
            "addVectorStepRow": "RuleCard",
            "add_toggle_setting_row": "RuleCard",
            "add_profile_cycle_row": "RuleCard",
            "add_profile_step_row": "RuleCard",
        }.get(fn, "Label")
        fallback_width = {
            "CheckBox": 260,
            "ToggleButton": 360,
            "RuleCard": 210,
            "Label": 210,
        }[kind]
        if fn in {"add_summary_strip", "add_footer_strip", "add_priority_badge"}:
            text_arg = args[2]
            x_arg = args[3]
            y_arg = args[4]
        elif fn in {"addSectionBand", "addMetricCard"}:
            text_arg = args[2] if fn == "addSectionBand" else (args[2] + " | " + args[3])
            x_arg = args[4]
            y_arg = args[5]
        elif fn == "addSidebarCard":
            text_arg = args[2]
            x_arg = args[3]
            y_arg = args[4]
        elif fn == "addSettingRow":
            text_arg = args[2] + " | " + args[3]
            x_arg = args[4]
            y_arg = args[5]
        elif fn in {"addToggleSettingRow", "add_toggle_setting_row"}:
            text_arg = args[2] + " | ON/OFF"
            x_arg = args[5]
            y_arg = args[6]
        elif fn in {"addProfileCycleRow", "add_profile_cycle_row"}:
            text_arg = clean_text(widget_id, widget_id)
            x_arg = args[6]
            y_arg = args[7]
        elif fn in {"addProfileStepRow", "add_profile_step_row"}:
            text_arg = clean_text(widget_id, widget_id)
            x_arg = args[8]
            y_arg = args[9]
        elif fn == "addProfileRotationRow":
            text_arg = clean_text(widget_id, widget_id)
            x_arg = args[3]
            y_arg = args[4]
        elif fn == "addVectorStepRow":
            text_arg = clean_text(widget_id, widget_id)
            x_arg = args[10]
            y_arg = args[11]
        else:
            text_arg = args[2]
            x_arg = args[3]
            y_arg = args[4]
        explicit_section = section_from_args(args)
        fallback_section = section_overrides.get(widget_id, explicit_section)
        section = fallback_section if fallback_section != "global" else section_from_id(widget_id, fallback_section)
        widgets.append(
            Widget(
                kind=kind,
                widget_id=widget_id,
                text=clean_text(text_arg, widget_id),
                x=as_int(x_arg, 0, variables),
                y=as_int(y_arg, 0, variables),
                width=width_from_args(fn, args, fallback_width, variables),
                height=DEFAULT_HEIGHTS[kind],
                section=section,
            )
        )
        if widget_id:
            widgets_by_var[widget_id] = widgets[-1]
            if widget_id in section_overrides:
                widgets[-1].section = section_overrides[widget_id]
    for var_name, section in section_overrides.items():
        if var_name in widgets_by_var:
            widgets_by_var[var_name].section = section
    widgets.extend(extract_rendered_overview_panel(source, variables, widgets))
    widgets.extend(extract_rendered_hunting_panel(source, variables, widgets))
    widgets.extend(extract_rendered_cavebot_panel(source, variables, widgets))
    widgets.extend(extract_rendered_tools_panel(source, variables, widgets))
    widgets.extend(extract_rendered_profile_panel(source, variables, widgets))
    widgets.extend(extract_rendered_engine_panel(source, variables, widgets))
    widgets.extend(extract_toggle_content_rows(source, variables, widgets))
    widgets.extend(extract_placeholder_modules(source, variables, widgets))
    return widgets


def extract_rendered_overview_panel(source: str, variables: dict[str, int], existing: list[Widget]) -> list[Widget]:
    if 'styleUi("renderOverviewPanel"' not in source:
        return []
    existing_ids = {widget.widget_id for widget in existing}
    widgets: list[Widget] = []
    panel_x = variables.get("panel_x", 234)
    panel_w = variables.get("panel_w", 394)
    body_y = variables.get("body_y", variables.get("UI_LAYOUT.content_body_y", 124))
    row_y = {
        1: variables.get("UI_LAYOUT.row_1_y", 152),
        2: variables.get("UI_LAYOUT.row_2_y", 178),
        3: variables.get("UI_LAYOUT.row_3_y", 204),
        4: variables.get("UI_LAYOUT.row_4_y", 230),
        5: variables.get("UI_LAYOUT.row_5_y", 256),
        6: variables.get("UI_LAYOUT.row_6_y", 282),
        7: variables.get("UI_LAYOUT.row_7_y", 320),
    }
    footer_y = variables.get("UI_LAYOUT.footer_y", 398)

    def add(
        widget_id: str,
        text: str,
        x: int,
        y: int,
        width: int,
        height: int | None = None,
        kind: str = "RuleCard",
    ) -> None:
        if widget_id in existing_ids:
            return
        existing_ids.add(widget_id)
        widgets.append(
            Widget(
                kind=kind,
                widget_id=widget_id,
                text=clean_text(text, widget_id),
                x=x,
                y=y,
                width=width,
                height=height or DEFAULT_HEIGHTS[kind],
                section="overview",
            )
        )

    add("ctoaOverviewHeader", "Overview", panel_x, variables.get("UI_LAYOUT.section_y", 96), panel_w)
    add("ctoaOverviewTableHead", "Live status | Value", panel_x, body_y, panel_w)
    add("ctoaOverviewCharacter", "Character | EK monk profile", panel_x, row_y[1], panel_w)
    add("ctoaOverviewHealth", "HP / MP | 0% / 0%", panel_x, row_y[2], panel_w)
    add("ctoaOverviewTarget", "Target | none", panel_x, row_y[3], panel_w)
    add("ctoaOverviewModules", "Modules | Healing / Targeting", panel_x, row_y[4], panel_w)
    add("ctoaOverviewMagic", "Magic | Rotation / Rune", panel_x, row_y[5], panel_w)
    add("ctoaOverviewMobs", "Monsters: nearby 0 / visible 0", panel_x, row_y[6], panel_w, 18, "Label")
    add("ctoaOverviewReadinessRuntime", "Runtime: pending", panel_x, row_y[7], panel_w, 18, "Label")
    add("ctoaOverviewReadinessPrototype", "Prototype: pending", panel_x, row_y[7] + 22, panel_w, 18, "Label")
    add("ctoaOverviewNext", "Next action: idle", panel_x, footer_y, panel_w, 18, "Label")
    return widgets


def _placeholder_rows(rows_src: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for label, value in re.findall(r'\{\s*"([^"]+)"\s*,\s*"([^"]+)"(?:\s*,\s*(?:true|false))?\s*\}', rows_src):
        rows.append((label, value))
    return rows


def extract_placeholder_modules(source: str, variables: dict[str, int], existing: list[Widget]) -> list[Widget]:
    existing_ids = {widget.widget_id for widget in existing}
    widgets: list[Widget] = []
    pattern = re.compile(
        r'addPlaceholderModule\(\s*window\s*,\s*"(?P<section>[^"]+)"\s*,\s*"(?P<title>[^"]+)"\s*,\s*"(?P<subtitle>[^"]+)"\s*,\s*\{(?P<rows>.*?)\n\s*\}\s*,\s*(?P<x>panel_x)\s*,\s*(?P<y>body_y)\s*,\s*(?P<w>panel_w)\s*\)',
        re.S,
    )
    for match in pattern.finditer(source):
        section = match.group("section")
        panel_x = as_int(match.group("x"), variables.get("panel_x", 234), variables)
        body_y = as_int(match.group("y"), variables.get("body_y", 124), variables)
        panel_w = as_int(match.group("w"), variables.get("panel_w", 394), variables)
        header_id = f"ctoa{section}Header"
        if header_id not in existing_ids:
            widgets.append(
                Widget("RuleCard", header_id, match.group("title"), panel_x, variables.get("UI_LAYOUT.section_y", 96), panel_w, 20, section)
            )
        table_id = f"ctoa{section}TableHead"
        if table_id not in existing_ids:
            widgets.append(
                Widget("RuleCard", table_id, "Module | Status", panel_x, body_y, panel_w, 20, section)
            )
        for index, (label, value) in enumerate(_placeholder_rows(match.group("rows")), start=1):
            row_id = f"ctoa{section}Placeholder{index}"
            if row_id in existing_ids:
                continue
            y = variables.get(f"UI_LAYOUT.row_{index}_y", body_y + index * 26)
            widgets.append(Widget("RuleCard", row_id, f"{label} | {value}", panel_x, y, panel_w, 20, section))
        footer_id = f"ctoa{section}Footer"
        if footer_id not in existing_ids:
            widgets.append(
                Widget(
                    "RuleCard",
                    footer_id,
                    "Placeholder only: no runtime action is attached",
                    panel_x,
                    variables.get("UI_LAYOUT.footer_y", 350),
                    panel_w,
                    20,
                    section,
                )
            )
    return widgets


def extract_toggle_content_rows(source: str, variables: dict[str, int], existing: list[Widget]) -> list[Widget]:
    existing_ids = {widget.widget_id for widget in existing}
    widgets: list[Widget] = []
    pattern = re.compile(
        r"addToggleContentRows\(\s*window\s*,\s*\{(?P<rows>.*?)\n\s*\}\s*,\s*(?P<x>\w+)\s*,\s*(?P<w>\w+)\s*\)",
        re.S,
    )
    row_pattern = re.compile(
        r'\{id\s*=\s*"(?P<id>[^"]+)"\s*,\s*label\s*=\s*"(?P<label>[^"]+)".*?y\s*=\s*(?P<y>[^,]+)\s*,\s*section\s*=\s*"(?P<section>[^"]+)"\}',
        re.S,
    )
    for match in pattern.finditer(source):
        x = as_int(match.group("x"), variables.get("panel_x", 234), variables)
        width = as_int(match.group("w"), variables.get("panel_w", 394), variables)
        for row in row_pattern.finditer(match.group("rows")):
            widget_id = row.group("id")
            if widget_id in existing_ids:
                continue
            widgets.append(
                Widget(
                    kind="RuleCard",
                    widget_id=widget_id,
                    text=f"{row.group('label')} | ON/OFF",
                    x=x,
                    y=as_int(row.group("y"), variables.get("UI_LAYOUT.row_2_y", 152), variables),
                    width=width,
                    height=DEFAULT_HEIGHTS["RuleCard"],
                    section=row.group("section"),
                )
            )
    return widgets


def extract_rendered_hunting_panel(source: str, variables: dict[str, int], existing: list[Widget]) -> list[Widget]:
    if 'styleUi("renderHuntingPanel"' not in source:
        return []
    dynamic_hunting_ids = {
        "ctoaRuneMinVisibleAction",
        "ctoaRuneCooldownAction",
        "ctoaOffensiveStanceMax",
        "ctoaDefensiveStanceMin",
    }
    existing[:] = [widget for widget in existing if widget.widget_id not in dynamic_hunting_ids]
    existing_ids = {widget.widget_id for widget in existing}
    widgets: list[Widget] = []
    panel_x = variables.get("panel_x", 234)
    panel_w = variables.get("panel_w", 394)
    body_y = variables.get("body_y", variables.get("UI_LAYOUT.content_body_y", 124))
    content_y = body_y + 26
    row_y = {
        2: variables.get("UI_LAYOUT.row_2_y", 152),
        3: variables.get("UI_LAYOUT.row_3_y", 178),
        4: variables.get("UI_LAYOUT.row_4_y", 204),
        5: variables.get("UI_LAYOUT.row_5_y", 230),
        6: variables.get("UI_LAYOUT.row_6_y", 256),
        7: variables.get("UI_LAYOUT.row_7_y", 282),
    }
    footer_y = variables.get("UI_LAYOUT.footer_y", 350)

    def add(
        widget_id: str,
        text: str,
        y: int,
        section: str,
        width: int | None = None,
        kind: str = "RuleCard",
        x: int | None = None,
        height: int | None = None,
    ) -> None:
        if widget_id in existing_ids:
            return
        existing_ids.add(widget_id)
        widgets.append(
            Widget(
                kind=kind,
                widget_id=widget_id,
                text=clean_text(text, widget_id),
                x=panel_x if x is None else x,
                y=y,
                width=width or panel_w,
                height=height or DEFAULT_HEIGHTS[kind],
                section=section,
            )
        )

    add("ctoaHuntingHeader", "Hunting", variables.get("UI_LAYOUT.section_y", 96), "hunting")
    tab_gap = 4
    tab_w = (panel_w - (tab_gap * 4)) // 5
    for index, (widget_id, label) in enumerate(
        [
            ("ctoaHuntingTargetingTab", "Targeting"),
            ("ctoaHuntingTargetRulesTab", "Target Rules"),
            ("ctoaHuntingMagicTab", "Spell Rules"),
            ("ctoaHuntingActionsTab", "Actions"),
            ("ctoaHuntingMagicRuntimeTab", "Runtime"),
        ]
    ):
        x = panel_x + (tab_w + tab_gap) * index
        if widget_id not in existing_ids:
            existing_ids.add(widget_id)
            widgets.append(Widget("Button", widget_id, label, x, body_y, tab_w, 20, "hunting"))

    for widget_id, label, y, section in [
        ("ctoaHuntingTargetingSummary", "Targeting: safe defaults", content_y, "hunting_targeting"),
        ("ctoaAutoAttack", "Targeting | ON/OFF", row_y[2], "hunting_targeting"),
        ("ctoaChaseTargeting", "Chase | ON/OFF", row_y[3], "hunting_targeting"),
        ("ctoaHoldTarget", "Hold Target | ON/OFF", row_y[4], "hunting_targeting"),
        ("ctoaAttackRange", "Attack range | 1", row_y[5], "hunting_targeting"),
        ("ctoaTargetRuleEditorIgnored", "Ignored names | npc name, summon", row_y[6], "hunting_targeting"),
        ("ctoaTargetRuleEditorPriority", "Priority order | boss, elite", row_y[7], "hunting_targeting"),
        ("ctoaMonsterStats", "Comma separated | priority order is left to right", footer_y, "hunting_targeting"),
        ("ctoaHuntingTargetRulesSummary", "Ordered filters | mandatory safety guards stay outside rules", content_y, "hunting_target_rules"),
        ("ctoaTargetRuleName", "Name / blank = any", row_y[3], "hunting_target_rules"),
        ("ctoaTargetRuleHp", "HP min / max | 0% / 100%", row_y[4], "hunting_target_rules"),
        ("ctoaTargetRuleDistance", "Dist min / max | 0 / 7", row_y[5], "hunting_target_rules"),
        ("ctoaTargetRuleCount", "Mobs min / max | 0 / 99", row_y[6], "hunting_target_rules"),
        ("ctoaTargetRulesFooter", "Profile data only | lower priority number wins", footer_y + 10, "hunting_target_rules"),
        ("ctoaHuntingMagicSummary", "Magic: safe defaults", content_y, "hunting_magic"),
        ("ctoaMagicRuleWords", "Spell words | exori", row_y[3], "hunting_magic"),
        ("ctoaMagicRuleMin", "Minimum mobs | 2", row_y[4], "hunting_magic"),
        ("ctoaMagicRuleMax", "Maximum mobs | 8", row_y[5], "hunting_magic"),
        ("ctoaMagicRuleCooldown", "Cooldown | 2000 ms", row_y[6], "hunting_magic"),
        ("ctoaMagicRuleRange", "Scan range | 1 sqm", row_y[7], "hunting_magic"),
        ("ctoaMagicFooter", "Profile data only | actions remain runtime-gated", footer_y + 10, "hunting_magic"),
        ("ctoaHuntingActionsSummary", "Ordered rune / stance rules | arbitrary server words", content_y, "hunting_actions"),
        ("ctoaCombatActionText", "Rune / spell | Sudden Death Rune", row_y[3], "hunting_actions"),
        ("ctoaCombatActionCooldown", "Cooldown | 1000 ms", row_y[6], "hunting_actions"),
        ("ctoaHuntingActionsFooter", "Profile data only | global activation remains on Runtime", footer_y + 10, "hunting_actions"),
        ("ctoaHuntingMagicRuntimeSummary", "Magic: runtime gated", content_y, "hunting_magic_runtime"),
        ("ctoaSpellRotation", "Spell Rotation | ON/OFF", row_y[2], "hunting_magic_runtime"),
        ("ctoaRuneShooter", "Rune Shooter | ON/OFF", row_y[3], "hunting_magic_runtime"),
        ("ctoaAutoStanceMagic", "Auto stance | ON/OFF", row_y[4], "hunting_magic_runtime"),
        ("ctoaMagicPriority", "Priority | rotation", row_y[5], "hunting_magic_runtime"),
        ("ctoaRotationLockMs", "Spell lock | 1050 ms", row_y[6], "hunting_magic_runtime"),
        ("ctoaAutoExetaMagic", "Auto exeta | ON/OFF", row_y[7], "hunting_magic_runtime"),
        ("ctoaMagicRuntimeFooter", "Decision: waiting for runtime", footer_y, "hunting_magic_runtime"),
    ]:
        add(widget_id, label, y, section)

    actions_half_w = (panel_w - 6) // 2
    add("ctoaCombatActionPrev", "<", row_y[2], "hunting_actions", 34, "Button", height=22)
    add("ctoaCombatActionRuleEditor", "1/3 Sudden Death Rune", row_y[2], "hunting_actions", panel_w - 84, "Label", panel_x + 42)
    add("ctoaCombatActionNext", ">", row_y[2], "hunting_actions", 34, "Button", panel_x + panel_w - 34, 22)
    add("ctoaCombatActionKind", "Kind rune", row_y[4], "hunting_actions", actions_half_w, "Button", height=22)
    add("ctoaCombatActionMode", "Box F5", row_y[4], "hunting_actions", actions_half_w, "Button", panel_x + actions_half_w + 6, 22)
    add("ctoaCombatActionMin", "Min mobs | 1", row_y[5], "hunting_actions", actions_half_w)
    add("ctoaCombatActionMax", "Max mobs | 99", row_y[5], "hunting_actions", actions_half_w, x=panel_x + actions_half_w + 6)
    combat_toggle_w = (panel_w - 8) // 3
    for index, (widget_id, label) in enumerate(
        [("ctoaCombatActionEnabled", "Enabled OFF"), ("ctoaCombatActionTarget", "Target ON"), ("ctoaCombatActionPvpSafe", "PvP safe ON")]
    ):
        add(widget_id, label, row_y[7], "hunting_actions", combat_toggle_w, "Button", panel_x + index * (combat_toggle_w + 4), 22)
    combat_action_w = (panel_w - 12) // 4
    for index, (widget_id, label) in enumerate(
        [("ctoaCombatActionAdd", "+ ADD"), ("ctoaCombatActionRemove", "REMOVE"), ("ctoaCombatActionUp", "UP"), ("ctoaCombatActionDown", "DOWN")]
    ):
        add(widget_id, label, row_y[7] + 26, "hunting_actions", combat_action_w, "Button", panel_x + index * (combat_action_w + 4), 22)

    add("ctoaTargetRulePrev", "<", row_y[2], "hunting_target_rules", 34, "Button", height=22)
    add("ctoaTargetRuleEditor", "1/1 any monster", row_y[2], "hunting_target_rules", panel_w - 84, "Label", panel_x + 42)
    add("ctoaTargetRuleNext", ">", row_y[2], "hunting_target_rules", 34, "Button", panel_x + panel_w - 34, 22)
    add("ctoaTargetRulePriority", "Priority | 50", row_y[7], "hunting_target_rules", 182)
    add("ctoaTargetRuleChase", "Chase inherit", row_y[7], "hunting_target_rules", panel_w - 190, "Button", panel_x + 190, 22)
    add("ctoaTargetRuleEnabled", "Enabled ON", row_y[7] + 26, "hunting_target_rules", panel_w, "Button", height=22)
    target_action_w = (panel_w - 12) // 4
    for index, (widget_id, label) in enumerate(
        [("ctoaTargetRuleAdd", "+ ADD"), ("ctoaTargetRuleRemove", "REMOVE"), ("ctoaTargetRuleUp", "UP"), ("ctoaTargetRuleDown", "DOWN")]
    ):
        add(widget_id, label, row_y[7] + 52, "hunting_target_rules", target_action_w, "Button", panel_x + index * (target_action_w + 4), 22)

    add("ctoaMagicRulePrev", "<", row_y[2], "hunting_magic", 34, "Button", height=22)
    add("ctoaMagicRuleEditor", "1/3 exori", row_y[2], "hunting_magic", panel_w - 84, "Label", panel_x + 42)
    add("ctoaMagicRuleNext", ">", row_y[2], "hunting_magic", 34, "Button", panel_x + panel_w - 34, 22)
    toggle_w = (panel_w - 8) // 3
    for index, (widget_id, label) in enumerate(
        [("ctoaMagicRuleEnabled", "Enabled ON"), ("ctoaMagicRuleMobCount", "Mob count ON"), ("ctoaMagicRuleDirectional", "Directional OFF")]
    ):
        add(widget_id, label, row_y[7] + 26, "hunting_magic", toggle_w, "Button", panel_x + index * (toggle_w + 4), 22)
    action_w = (panel_w - 12) // 4
    for index, (widget_id, label) in enumerate(
        [("ctoaMagicRuleAdd", "+ ADD"), ("ctoaMagicRuleRemove", "REMOVE"), ("ctoaMagicRuleUp", "UP"), ("ctoaMagicRuleDown", "DOWN")]
    ):
        add(widget_id, label, row_y[7] + 52, "hunting_magic", action_w, "Button", panel_x + index * (action_w + 4), 22)

    return widgets


def extract_rendered_cavebot_panel(source: str, variables: dict[str, int], existing: list[Widget]) -> list[Widget]:
    if 'styleUi("renderCavebotPanel"' not in source:
        return []
    existing_ids = {widget.widget_id for widget in existing}
    widgets: list[Widget] = []
    panel_x = variables.get("panel_x", 234)
    panel_w = variables.get("panel_w", 394)
    body_y = variables.get("body_y", variables.get("UI_LAYOUT.content_body_y", 124))
    row_y = {
        2: variables.get("UI_LAYOUT.row_2_y", 152),
        3: variables.get("UI_LAYOUT.row_3_y", 178),
        4: variables.get("UI_LAYOUT.row_4_y", 204),
        5: variables.get("UI_LAYOUT.row_5_y", 230),
        6: variables.get("UI_LAYOUT.row_6_y", 256),
        7: variables.get("UI_LAYOUT.row_7_y", 282),
    }
    footer_y = variables.get("UI_LAYOUT.footer_y", 350)

    def add(widget_id: str, text: str, x: int, y: int, width: int, section: str = "cavebot", kind: str = "RuleCard") -> None:
        if widget_id in existing_ids:
            return
        existing_ids.add(widget_id)
        widgets.append(
            Widget(
                kind=kind,
                widget_id=widget_id,
                text=clean_text(text, widget_id),
                x=x,
                y=y,
                width=width,
                height=DEFAULT_HEIGHTS[kind],
                section=section,
            )
        )

    add("ctoaCavebotHeader", "CaveBot", panel_x, variables.get("UI_LAYOUT.section_y", 96), panel_w)
    add("ctoaCavebotTableHead", "Route | Value", panel_x, body_y, panel_w)
    for widget_id, label, row in [
        ("ctoaCavebotEnabled", "Cavebot | ON/OFF", 2),
        ("ctoaCavebotMovement", "Movement | ON/OFF", 3),
        ("ctoaCavebotDelay", "Step delay | 900 ms", 4),
        ("ctoaCavebotReach", "Reach dist | 1", 5),
        ("ctoaCavebotWpCount", "Waypoints | 0", 6),
        ("ctoaCavebotCurrent", "Current | 1", 7),
    ]:
        add(widget_id, label, panel_x, row_y[row], panel_w)

    action_w = (panel_w - 18) // 4
    action_y1 = row_y[7] + 28
    action_y2 = row_y[7] + 52
    for index, (widget_id, label) in enumerate(
        [
            ("ctoaCavebotAdd", "Add"),
            ("ctoaCavebotDelete", "Del"),
            ("ctoaCavebotUp", "Up"),
            ("ctoaCavebotDown", "Down"),
        ]
    ):
        add(widget_id, label, panel_x + (action_w + 6) * index, action_y1, action_w, kind="Button")
    for index, (widget_id, label) in enumerate(
        [
            ("ctoaCavebotPrev", "Prev"),
            ("ctoaCavebotNext", "Next"),
            ("ctoaCavebotClear", "Clear"),
            ("ctoaCavebotTestWalk", "Test"),
        ]
    ):
        add(widget_id, label, panel_x + (action_w + 6) * index, action_y2, action_w, kind="Button")
    add("ctoaCavebotStatus", "Status: idle", panel_x, footer_y + 28, panel_w)
    return widgets


def extract_rendered_tools_panel(source: str, variables: dict[str, int], existing: list[Widget]) -> list[Widget]:
    if 'styleUi("renderToolsPanel"' not in source:
        return []
    existing_ids = {widget.widget_id for widget in existing}
    widgets: list[Widget] = []
    panel_x = variables.get("panel_x", 234)
    panel_w = variables.get("panel_w", 394)
    body_y = variables.get("body_y", variables.get("UI_LAYOUT.content_body_y", 124))
    content_y = body_y + 26
    row_y = {
        2: variables.get("UI_LAYOUT.row_2_y", 152),
        3: variables.get("UI_LAYOUT.row_3_y", 178),
        4: variables.get("UI_LAYOUT.row_4_y", 204),
        5: variables.get("UI_LAYOUT.row_5_y", 230),
        6: variables.get("UI_LAYOUT.row_6_y", 256),
        7: variables.get("UI_LAYOUT.row_7_y", 282),
    }
    footer_y = variables.get("UI_LAYOUT.footer_y", 350)
    ui_value_row_w = variables.get("UI_LAYOUT.ui_value_row_w", panel_w)

    def add(widget_id: str, text: str, y: int, section: str, width: int | None = None, kind: str = "RuleCard") -> None:
        if widget_id in existing_ids:
            return
        existing_ids.add(widget_id)
        widgets.append(
            Widget(
                kind=kind,
                widget_id=widget_id,
                text=clean_text(text, widget_id),
                x=panel_x,
                y=y,
                width=width or panel_w,
                height=DEFAULT_HEIGHTS[kind],
                section=section,
            )
        )

    add("ctoaToolsHeader", "Tools", variables.get("UI_LAYOUT.section_y", 96), "tools")
    tab_w = (panel_w - 12) // 4
    for index, (widget_id, label) in enumerate(
        [
            ("ctoaToolsHelperTab", "Helper"),
            ("ctoaToolsPvpTab", "PvP"),
            ("ctoaToolsTimerTab", "Timer"),
            ("ctoaToolsDiagTab", "Diag"),
        ]
    ):
        x = panel_x + (tab_w + 4) * index
        if widget_id not in existing_ids:
            existing_ids.add(widget_id)
            widgets.append(Widget("Button", widget_id, label, x, body_y, tab_w, 20, "tools"))

    add("ctoaToolsSummary", "Tools: helper / PvP / timer / diag", content_y, "tools_helper")
    tool_rows = [
        ("ctoaChaseTools", "Chase mode | ON/OFF", row_y[2], "tools_helper"),
        ("ctoaAutoHasteTools", "Auto Haste | ON/OFF", row_y[3], "tools_helper"),
        ("ctoaAutoExetaTools", "Auto Exeta | ON/OFF", row_y[4], "tools_helper"),
        ("ctoaExetaMinVisible", "Exeta min mobs | 2", row_y[5], "tools_helper"),
        ("ctoaPauseInPzTools", "Pause in PZ | ON/OFF", row_y[6], "tools_helper"),
        ("ctoaToolsApiSnapshot", "API: pending probe", row_y[7], "tools_helper"),
        ("ctoaToolsFooter", "Support modules active only outside PZ", footer_y, "tools_helper"),
        ("ctoaRunePvpSafeTools", "Rune PvP safe | ON/OFF", row_y[2], "tools_pvp"),
        ("ctoaHoldTargetPvp", "Hold Target | ON/OFF", row_y[3], "tools_pvp"),
        ("ctoaPauseInPzPvp", "Pause in PZ | ON/OFF", row_y[4], "tools_pvp"),
        ("ctoaRuneRequiresTargetPvp", "Rune needs target | ON/OFF", row_y[5], "tools_pvp"),
        ("ctoaToolsPvpFooter", "PvP guards protect shooter and targeting", footer_y, "tools_pvp"),
        ("ctoaToolsTimerEnabled", "Timer enabled | ON/OFF", row_y[2], "tools_timer"),
        ("ctoaToolsTimerInterval", "Interval | 60s", row_y[3], "tools_timer"),
        ("ctoaToolsTimerMessage", "Message | timer", row_y[4], "tools_timer"),
        ("ctoaToolsTimerFooter", "Timer UI ready; action loop stays disabled by default", footer_y, "tools_timer"),
        ("ctoaToolsDiagCore", "API: pending probe", row_y[2], "tools_diag"),
        ("ctoaToolsDiagFlags", "Feature flags: safe", row_y[3], "tools_diag"),
        ("ctoaToolsDiagMove", "Move: pending", row_y[4], "tools_diag"),
        ("ctoaToolsDiagMagic", "Magic: pending | Loot: pending", row_y[5], "tools_diag"),
        ("ctoaToolsDiagEnabled", "Diagnostics | ON/OFF", row_y[6], "tools_diag"),
        ("ctoaToolsDiagExport", "Diagnostics buffer: empty", row_y[7], "tools_diag"),
        ("ctoaToolsDiagFooter", "Read-only diagnostics; no runtime action is triggered", footer_y, "tools_diag"),
    ]
    for row in tool_rows:
        widget_id, label, y, section = row[:4]
        width = row[4] if len(row) > 4 else None
        add(widget_id, label, y, section, width)

    for widget_id, left, right, section in [
        ("ctoaToolsPvpHead", "PvP", "Value", "tools_pvp"),
        ("ctoaToolsTimerHead", "Timer", "Value", "tools_timer"),
        ("ctoaToolsDiagHead", "Diagnostics", "Snapshot", "tools_diag"),
    ]:
        add(widget_id, f"{left} | {right}", content_y, section)

    return widgets


def extract_rendered_profile_panel(source: str, variables: dict[str, int], existing: list[Widget]) -> list[Widget]:
    if 'styleUi("renderProfilePanel"' not in source:
        return []
    existing_ids = {widget.widget_id for widget in existing}
    widgets: list[Widget] = []
    panel_x = variables.get("panel_x", 234)
    panel_w = variables.get("panel_w", 394)
    profile_gap = 12
    col_w = (panel_w - profile_gap) // 2
    right_x = panel_x + col_w + profile_gap

    def add(widget_id: str, y_key: str, section: str = "profile", x: int = panel_x, width: int = col_w, kind: str = "RuleCard") -> None:
        if widget_id in existing_ids:
            return
        existing_ids.add(widget_id)
        widgets.append(
            Widget(
                kind=kind,
                widget_id=widget_id,
                text=clean_text(widget_id, widget_id),
                x=x,
                y=variables.get(y_key, 0),
                width=width,
                height=DEFAULT_HEIGHTS[kind],
                section=section,
            )
        )

    add("ctoaProfileHeader", "UI_LAYOUT.section_y", width=panel_w)
    add("ctoaProfileSummary", "UI_LAYOUT.content_body_y", width=panel_w)
    for widget_id, row in [
        ("ctoaProfileSpell", "UI_LAYOUT.profile_row_1_y"),
        ("ctoaProfileSpellThreshold", "UI_LAYOUT.profile_row_2_y"),
        ("ctoaProfilePotionHotkey", "UI_LAYOUT.profile_row_3_y"),
        ("ctoaProfilePotionThreshold", "UI_LAYOUT.profile_row_4_y"),
        ("ctoaProfileManaHotkey", "UI_LAYOUT.profile_row_5_y"),
        ("ctoaProfileThresholdJitter", "UI_LAYOUT.profile_row_6_y"),
    ]:
        add(widget_id, row)
    for widget_id, row in [
        ("ctoaModuleHealFriend", "UI_LAYOUT.profile_row_1_y"),
        ("ctoaModuleConditions", "UI_LAYOUT.profile_row_2_y"),
        ("ctoaModuleCavebot", "UI_LAYOUT.profile_row_3_y"),
        ("ctoaModuleEquipment", "UI_LAYOUT.profile_row_4_y"),
        ("ctoaModuleHelper", "UI_LAYOUT.profile_row_5_y"),
        ("ctoaModuleScripting", "UI_LAYOUT.profile_row_6_y"),
    ]:
        add(widget_id, row, x=right_x)
    add("ctoaProfileStatus", "UI_LAYOUT.profile_footer_y", width=panel_w - variables.get("UI_LAYOUT.profile_save_w", 86) - 10)
    add(
        "ctoaProfileSave",
        "UI_LAYOUT.profile_save_y",
        x=panel_x + panel_w - variables.get("UI_LAYOUT.profile_save_w", 86),
        width=variables.get("UI_LAYOUT.profile_save_w", 86),
        kind="Button",
    )
    return widgets


def extract_rendered_engine_panel(source: str, variables: dict[str, int], existing: list[Widget]) -> list[Widget]:
    if 'styleUi("renderEnginePanel"' not in source:
        return []
    existing_ids = {widget.widget_id for widget in existing}
    widgets: list[Widget] = []
    panel_x = variables.get("panel_x", 234)
    panel_w = variables.get("panel_w", 394)
    profile_gap = 12
    col_w = (panel_w - profile_gap) // 2
    right_x = panel_x + col_w + profile_gap

    def add(widget_id: str, y_key: str, section: str = "ui", x: int = panel_x, width: int = panel_w, kind: str = "RuleCard") -> None:
        if widget_id in existing_ids:
            return
        existing_ids.add(widget_id)
        widgets.append(
            Widget(
                kind=kind,
                widget_id=widget_id,
                text=clean_text(widget_id, widget_id),
                x=x,
                y=variables.get(y_key, 0),
                width=width,
                height=DEFAULT_HEIGHTS[kind],
                section=section,
            )
        )

    add("ctoaUiRuntimeHeader", "UI_LAYOUT.section_y")
    add("ctoaUiSummary", "UI_LAYOUT.content_body_y")
    add("ctoaUiHotkey", "UI_LAYOUT.ui_runtime_row_1_y", width=col_w)
    add("ctoaUiAutoHide", "UI_LAYOUT.ui_runtime_row_1_y", x=right_x, width=col_w)
    add("ctoaUiHudEnabled", "UI_LAYOUT.ui_runtime_row_2_y")
    add("ctoaUiHudPos", "UI_LAYOUT.ui_runtime_row_3_y", width=variables.get("UI_LAYOUT.ui_value_row_w", panel_w))
    add("ctoaUiThemeHeader", "UI_LAYOUT.ui_theme_section_y")
    add("ctoaUiThemePreset", "UI_LAYOUT.ui_theme_row_1_y")
    add("ctoaUiLayoutHeader", "UI_LAYOUT.ui_layout_section_y")
    add("ctoaUiCompactMode", "UI_LAYOUT.ui_layout_row_1_y")
    add("ctoaUiWindowPos", "UI_LAYOUT.ui_layout_row_2_y", width=variables.get("UI_LAYOUT.ui_value_row_w", panel_w))
    return widgets


def validate(window: tuple[int, int, int, int], widgets: list[Widget]) -> list[str]:
    _, _, width, height = window
    issues: list[str] = []
    for widget in widgets:
        if widget.right > width - 16:
            issues.append(
                f"OVERFLOW_RIGHT {widget.widget_id}: right={widget.right}, safe={width - 16}"
            )
        if widget.bottom > height - 16:
            issues.append(
                f"OVERFLOW_BOTTOM {widget.widget_id}: bottom={widget.bottom}, safe={height - 16}"
            )
    for section in (
        "overview",
        "healing",
        "heal_friend",
        "conditions",
        "hunting",
        "hunting_targeting",
        "hunting_target_rules",
        "hunting_magic",
        "hunting_actions",
        "hunting_magic_runtime",
        "cavebot",
        "equipment",
        "tools",
        "tools_helper",
        "tools_pvp",
        "tools_timer",
        "tools_diag",
        "scripting",
        "profile",
        "ui",
    ):
        scoped = sorted((w for w in widgets if w.section == section), key=lambda w: (w.y, w.x))
        for prev, current in zip(scoped, scoped[1:]):
            horizontal_overlap = not (prev.right <= current.x or current.right <= prev.x)
            vertical_overlap = current.y < prev.bottom
            if horizontal_overlap and vertical_overlap:
                issues.append(
                    f"OVERLAP {section}: {prev.widget_id} overlaps {current.widget_id}"
                )
    for section in ("ui",):
        scoped = sorted((w for w in widgets if w.section == section), key=lambda w: (w.y, w.x))
        for prev, current in zip(scoped, scoped[1:]):
            horizontal_overlap = not (prev.right <= current.x or current.right <= prev.x)
            vertical_overlap = current.y < prev.bottom
            if horizontal_overlap and vertical_overlap:
                issues.append(
                    f"OVERLAP {section}: {prev.widget_id} overlaps {current.widget_id}"
                )
    return issues


def render_stage(width: int, height: int, widgets: list[Widget], active: str) -> str:
    section_colors = {
        "global": "#ffffff",
        "overview": "#d7b36a",
        "healing": "#d7b36a",
        "heal_friend": "#d7b36a",
        "conditions": "#d7b36a",
        "hunting": "#8fd17f",
        "hunting_targeting": "#8fd17f",
        "hunting_target_rules": "#8fd17f",
        "hunting_magic": "#8fd17f",
        "hunting_actions": "#8fd17f",
        "hunting_magic_runtime": "#8fd17f",
        "cavebot": "#8fd17f",
        "equipment": "#8fd17f",
        "tools": "#8fd17f",
        "tools_helper": "#8fd17f",
        "tools_pvp": "#8fd17f",
        "tools_timer": "#8fd17f",
        "tools_diag": "#8fd17f",
        "scripting": "#c2a2ff",
        "profile": "#7fd7ff",
        "ui": "#7fb8ff",
    }
    active_groups = {
        "overview": {"global", "overview"},
        "healing": {"global", "healing"},
        "heal_friend": {"global", "heal_friend"},
        "conditions": {"global", "conditions"},
        "hunting_targeting": {"global", "hunting", "hunting_targeting"},
        "hunting_target_rules": {"global", "hunting", "hunting_target_rules"},
        "hunting_magic": {"global", "hunting", "hunting_magic"},
        "hunting_actions": {"global", "hunting", "hunting_actions"},
        "hunting_magic_runtime": {"global", "hunting", "hunting_magic_runtime"},
        "cavebot": {"global", "cavebot"},
        "equipment": {"global", "equipment"},
        "tools_helper": {"global", "tools", "tools_helper"},
        "tools_pvp": {"global", "tools", "tools_pvp"},
        "tools_timer": {"global", "tools", "tools_timer"},
        "tools_diag": {"global", "tools", "tools_diag"},
        "scripting": {"global", "scripting"},
        "profile": {"global", "profile"},
        "ui": {"global", "ui"},
    }.get(active, {"global", active})
    blocks = []
    for widget in widgets:
        if widget.section not in active_groups:
            continue
        color = section_colors.get(widget.section, "#ffffff")
        text = widget.text
        active_class = ""
        nav_active = {
            "ctoaOverviewTab": active == "overview",
            "ctoaHealingTab": active == "healing",
            "ctoaHealFriendTab": active == "heal_friend",
            "ctoaConditionsTab": active == "conditions",
            "ctoaHuntingTab": active in {"hunting_targeting", "hunting_target_rules"},
            "ctoaMagicTab": active in {"hunting_magic", "hunting_actions", "hunting_magic_runtime"},
            "ctoaCavebotTab": active == "cavebot",
            "ctoaEquipmentTab": active == "equipment",
            "ctoaToolsTab": active.startswith("tools_"),
            "ctoaScriptingTab": active == "scripting",
            "ctoaProfileTab": active == "profile",
            "ctoaUiTab": active == "ui",
        }
        if widget.widget_id in nav_active:
            active_class = " active" if nav_active[widget.widget_id] else ""
        if widget.widget_id == "ctoaHealingTab":
            text = "[ Healing ]" if active == "healing" else "Healing"
        elif widget.widget_id == "ctoaHealFriendTab":
            text = "[ Heal Friend ]" if active == "heal_friend" else "Heal Friend"
        elif widget.widget_id == "ctoaConditionsTab":
            text = "[ Conditions ]" if active == "conditions" else "Conditions"
        elif widget.widget_id == "ctoaCavebotTab":
            text = "[ CaveBot ]" if active == "cavebot" else "CaveBot"
        elif widget.widget_id == "ctoaEquipmentTab":
            text = "[ Equipment ]" if active == "equipment" else "Equipment"
        elif widget.widget_id == "ctoaToolsTab":
            text = "[ Tools ]" if active.startswith("tools_") else "Tools"
        elif widget.widget_id == "ctoaScriptingTab":
            text = "[ Scripting ]" if active == "scripting" else "Scripting"
        elif widget.widget_id == "ctoaUiTab":
            text = "[ Settings ]" if active == "ui" else "Settings"
        elif widget.widget_id == "ctoaOverviewTab":
            text = "[ Overview ]" if active == "overview" else "Overview"
        elif widget.widget_id == "ctoaHuntingTab":
            text = "[ Targeting ]" if active in {"hunting_targeting", "hunting_target_rules"} else "Targeting"
        elif widget.widget_id == "ctoaMagicTab":
            text = "[ Magic ]" if active in {"hunting_magic", "hunting_actions", "hunting_magic_runtime"} else "Magic"
        elif widget.widget_id == "ctoaProfileTab":
            text = "[ Profile ]" if active == "profile" else "Profile"
        cls = widget.kind.lower()
        content = html.escape(text)
        extra_class = ""
        if cls == "rulecard" and widget.widget_id in {"ctoaHealingHeader", "ctoaToolsHeader"}:
            extra_class = " section-band"
        elif cls == "rulecard" and widget.widget_id == "ctoaProfileName":
            extra_class = " profile-card"
        elif cls == "rulecard" and " | " in text:
            label, value = text.split(" | ", 1)
            extra_class = " setting-row"
            content = (
                f'<span class="row-label">{html.escape(label)}</span>'
                f'<span class="row-value">{html.escape(value)}</span>'
            )
        blocks.append(
            f'<div class="widget {cls}{active_class}{extra_class}" title="{html.escape(widget.widget_id)}" '
            f'style="left:{widget.x}px;top:{widget.y}px;width:{widget.width}px;height:{widget.height}px;'
            f'border-color:{color};color:{color}">{content}</div>'
        )
    return f"""
<section>
  <h2>{active.title()}</h2>
  <div class="stage">
    <div class="title">CTOA EK Helper Options</div>
    {''.join(blocks)}
  </div>
</section>
"""


def render_html(window: tuple[int, int, int, int], widgets: list[Widget]) -> str:
    _, _, width, height = window
    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>CTOA Helper UI Preview</title>
<style>
body {{
  margin: 0;
  background: #1f1f1f;
  font-family: Verdana, sans-serif;
  color: #ddd;
}}
section {{
  margin: 20px auto 36px;
  width: {width}px;
}}
h2 {{
  margin: 0 0 8px;
  color: #d7b36a;
  font-size: 14px;
}}
.stage {{
  width: {width}px;
  height: {height}px;
  margin: 0 auto;
  position: relative;
  background:
    repeating-linear-gradient(135deg, rgba(255,255,255,.025) 0 1px, transparent 1px 5px),
    #343434;
  border: 2px solid #5a5a5a;
  box-shadow: 0 0 0 1px #181818 inset;
}}
.title {{
  position: absolute;
  left: 0;
  top: 0;
  right: 0;
  height: 22px;
  line-height: 22px;
  text-align: center;
  background: #282828;
  color: #fff;
  font-weight: 700;
  font-size: 11px;
}}
.widget {{
  position: absolute;
  box-sizing: border-box;
  overflow: hidden;
  white-space: nowrap;
  font-size: 12px;
  line-height: 20px;
  padding-left: 4px;
  text-shadow: 1px 1px 0 #111;
}}
.button, .togglebutton, .rulecard {{
  border: 1px solid;
  background: rgba(20,20,20,.45);
}}
.button.active {{
  background: rgba(80,64,28,.35);
  border-color: #9f8552 !important;
  color: #d7b36a !important;
}}
.rulecard {{
  background: rgba(37,37,37,.75);
  color: #e4e4e4 !important;
}}
.section-band {{
  text-align: center;
  background: rgba(48,48,48,.92);
  border-color: #9f8552 !important;
  color: #d7b36a !important;
  font-weight: 700;
}}
.profile-card {{
  background: rgba(34,34,34,.9);
  border-color: #5e5e5e !important;
  color: #fff !important;
}}
.setting-row {{
  padding: 0;
  background: rgba(48,56,48,.82);
  border-color: #5f8057 !important;
  color: #e4e4e4 !important;
}}
.setting-row .row-label {{
  position: absolute;
  left: 10px;
  top: 4px;
  height: 20px;
  line-height: 20px;
  color: #e4e4e4;
  font-weight: 700;
}}
.setting-row .row-value {{
  position: absolute;
  right: 10px;
  top: 4px;
  width: 108px;
  height: 20px;
  line-height: 20px;
  text-align: center;
  background: rgba(35,52,35,.95);
  border: 1px solid #446b44;
  color: #93d987;
  box-sizing: border-box;
  font-weight: 700;
}}
.checkbox::before {{
  content: "☑ ";
  color: #bdbdbd;
}}
.label {{
  font-weight: 700;
}}
.legend {{
  width: {width}px;
  margin: 0 auto;
  font-size: 12px;
  color: #aaa;
}}
</style>
</head>
<body>
{render_stage(width, height, widgets, "overview")}
{render_stage(width, height, widgets, "healing")}
{render_stage(width, height, widgets, "heal_friend")}
{render_stage(width, height, widgets, "conditions")}
{render_stage(width, height, widgets, "hunting_targeting")}
{render_stage(width, height, widgets, "hunting_target_rules")}
{render_stage(width, height, widgets, "hunting_magic")}
{render_stage(width, height, widgets, "hunting_actions")}
{render_stage(width, height, widgets, "hunting_magic_runtime")}
{render_stage(width, height, widgets, "cavebot")}
{render_stage(width, height, widgets, "equipment")}
{render_stage(width, height, widgets, "tools_helper")}
{render_stage(width, height, widgets, "tools_pvp")}
{render_stage(width, height, widgets, "tools_timer")}
{render_stage(width, height, widgets, "scripting")}
{render_stage(width, height, widgets, "profile")}
{render_stage(width, height, widgets, "ui")}
<div class="legend">White = global/sidebar, gold = overview/healing, green = combat/tools, cyan = profile, blue = engine prefs. Generated from ctoa_native_helper.lua.</div>
</body>
</html>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--helper", type=Path, default=HELPER)
    parser.add_argument("--out", type=Path, default=OUT_HTML)
    parser.add_argument(
        "--layout",
        choices=("default", "compact"),
        default="default",
        help="Render the selected production layout table.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.helper.read_text(encoding="utf-8")
    compact = args.layout == "compact"
    window = extract_window(source, compact=compact)
    widgets = extract_widgets(source, compact=compact)
    issues = validate(window, widgets)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render_html(window, widgets), encoding="utf-8")

    print(f"preview: {args.out}")
    print(f"layout: {args.layout}")
    print(f"window: x={window[0]} y={window[1]} w={window[2]} h={window[3]}")
    print(f"widgets: {len(widgets)}")
    if issues:
        print("issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print("issues: none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
