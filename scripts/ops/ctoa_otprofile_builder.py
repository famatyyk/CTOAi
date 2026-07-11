"""Build an OTClient EK helper profile from a short Polish/English request.

This is intentionally deterministic. It updates the Lua profile that the
Solteria helper loads, instead of asking a model to emit arbitrary Lua.
"""

from __future__ import annotations

import argparse
import re
import shutil
import unicodedata
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_PROFILE = REPO_ROOT / "scripts" / "lua" / "otclient" / "ctoa_ek_profile.lua"
SOLTERIA_MOD_DIR = (
    Path.home()
    / "AppData"
    / "Local"
    / "Solteria"
    / "client"
    / "mods"
    / "ctoa_otclient"
)
RUNTIME_PROFILE = SOLTERIA_MOD_DIR / "ctoa_ek_profile.lua"


def default_profile() -> dict[str, Any]:
    return {
        "schema_version": "ctoa-helper-profile-v1",
        "name": "Elite Knight Default",
        "enabled": False,
        "safe_boot_runtime_disabled": True,
        "tick_ms": 500,
        "hotkey": "Ctrl+J",
        "auto_hide_ms": 0,
        "modules": {
            "overview": True,
            "healing": True,
            "heal_friend": False,
            "conditions": False,
            "targeting": True,
            "magic": True,
            "cavebot": True,
            "equipment": False,
            "helper": True,
            "scripting": False,
            "settings": True,
            "engine": True,
        },
        "healing": {
            "spell_enabled": True,
            "potion_enabled": True,
            "spell_threshold": 80,
            "potion_threshold": 62,
            "threshold_jitter_percent": 3,
            "spell": "exura ico",
            "critical_spell": "exura med ico",
            "spell_rotation": [
                {"threshold": 85, "spell": "exura ico"},
                {"threshold": 55, "spell": "exura med ico"},
                {"threshold": 30, "spell": "exura gran ico"},
            ],
            "potion_name": "Health Potion",
            "potion_mode": "Actionbar",
            "potion_hotkey": "F1",
            "potion_actionbar_slot": "F1",
            "mana_potion_enabled": True,
            "mana_potion_threshold": 45,
            "mana_potion_name": "Mana Potion",
            "mana_potion_hotkey": "F2",
            "mana_potion_actionbar_slot": "F2",
            "mana_potion_cooldown_ms": 1000,
            "cooldown_ms": 1000,
        },
        "heal_friend": {
            "enabled": False,
            "observe_party": True,
            "sio_spell": "exura sio",
            "hp_threshold": 70,
            "cooldown_ms": 1000,
            "action_lock_ms": 1200,
            "friend_whitelist": [],
            "priority": "lowest_hp",
            "require_whitelist": True,
            "pz_safe": True,
            "runtime_enabled": False,
            "friend_scan_range": 7,
            "sample_interval_ms": 1000,
            "last_sample_ms": 0,
            "last_status": "pending",
            "observed_count": 0,
            "lowest_friend_hp": 100,
            "last_cast_ms": 0,
        },
        "conditions": {
            "enabled": False,
            "observe_states": True,
            "mana_shield": True,
            "paralyze": True,
            "poison": True,
            "burn": True,
            "electric": True,
            "bleeding": True,
            "runtime_enabled": False,
            "sample_interval_ms": 1000,
            "api_probe_enabled": True,
            "api_probe_status": "pending",
            "api_probe_count": 0,
            "last_sample_ms": 0,
            "last_status": "pending",
        },
        "equipment": {
            "enabled": False,
            "observe_slots": True,
            "ring_swap": False,
            "amulet_swap": False,
            "weapon_set": "manual",
            "pvp_gear_lock": True,
            "hp_threshold": 45,
            "sample_interval_ms": 1500,
            "api_probe_enabled": True,
            "api_probe_status": "pending",
            "api_probe_count": 0,
            "runtime_enabled": False,
            "last_sample_ms": 0,
            "last_status": "pending",
        },
        "scripting": {
            "enabled": False,
            "policy_mode": "deny_all",
            "allow_user_snippets": False,
            "allow_runtime_eval": False,
            "command_model": "none",
            "audit_log": True,
            "sandbox_required": True,
            "max_snippet_chars": 0,
            "runtime_enabled": False,
            "last_status": "blocked: no snippet execution",
        },
        "tools": {
            "auto_attack": False,
            "chase": True,
            "auto_follow": False,
            "pause_in_pz": True,
            "hold_target": False,
            "attack_range": 7,
            "target_timeout_ms": 15000,
            "retarget_delay_ms": 200,
            "log_retarget_ms": 3000,
            "block_log_ms": 3000,
            "probe_log_ms": 5000,
            "clear_target_in_pz": True,
            "block_npc_icons": True,
            "block_friendly_summons": True,
            "friendly_summon_name_fragments": [
                " familiar ",
                " summon ",
                " summoned ",
                "familiar",
                "summon",
            ],
            "ignored_names": [
                "elara goldwarden",
                "goldwarden",
                "aldren",
                "andrew",
                "brumgar",
                "hireling",
                "postman",
                "selmir",
                "taskmaster",
                "liora",
                "npc",
            ],
            "prefer_low_hp": False,
            "priority_names": ["demon", "dragon lord", "dragon", "cyclops", "dwarf"],
            "auto_haste": False,
            "haste_spell": "utani hur",
            "haste_interval_ms": 30000,
            "api_probe_enabled": True,
            "magic_api_probe_enabled": True,
            "spell_rotation": False,
            "magic_priority": "rotation",
            "rotation_interval_ms": 1050,
            "rotation_scan_range": 1,
            "recovery_action_gap_ms": 250,
            "rotation_spells": [
                {"words": "exori gran", "min_nearby": 3, "cooldown_ms": 6000},
                {"words": "exori", "min_nearby": 2, "cooldown_ms": 4000},
                {"words": "exori min", "min_nearby": 2, "cooldown_ms": 4000},
                {"words": "exori gran ico", "min_nearby": 1, "cooldown_ms": 6000},
                {"words": "exori ico", "min_nearby": 1, "cooldown_ms": 2000},
                {
                    "words": "exori hur",
                    "min_nearby": 1,
                    "cooldown_ms": 2000,
                    "max_nearby": 1,
                },
            ],
            "auto_exeta": False,
            "exeta_interval_ms": 5000,
            "exeta_min_visible": 2,
            "exeta_spells": ["exeta res", "exeta amp res"],
            "rune_enabled": False,
            "rune_name": "Sudden Death Rune",
            "rune_hotkey": "F5",
            "rune_actionbar_slot": "F5",
            "rune_min_visible": 1,
            "rune_cooldown_ms": 1000,
            "rune_pvp_safe": True,
            "rune_requires_target": True,
            "timer_enabled": False,
            "timer_interval_ms": 60000,
            "timer_message": "timer",
            "cavebot_api_probe_enabled": True,
            "cavebot_enabled": False,
            "cavebot_movement_enabled": False,
            "cavebot_step_delay_ms": 1200,
            "cavebot_reach_distance": 1,
            "cavebot_waypoints": [],
            "feature_flags": {
                "diagnostics": True,
                "experimental_cavebot": False,
                "experimental_loot": False,
                "experimental_combat": False,
            },
            "diagnostics_export_limit": 20,
            "diagnostics_sample_interval_ms": 5000,
        },
        "hud": {
            "enabled": True,
            "x": 22,
            "y": 170,
        },
    }


def normalize(text: str) -> str:
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text


def find_percent(text: str, keywords: tuple[str, ...]) -> int | None:
    for keyword in keywords:
        match = re.search(rf"{keyword}\D{{0,24}}(\d{{2,3}})\s*%?", text)
        if match:
            value = int(match.group(1))
            if 1 <= value <= 100:
                return value
    return None


def set_spell_min(profile: dict[str, Any], spell_words: str, min_nearby: int) -> None:
    for spell in profile["tools"]["rotation_spells"]:
        if spell["words"] == spell_words:
            spell["min_nearby"] = min_nearby
            return


def remove_spell(profile: dict[str, Any], spell_words: str) -> None:
    profile["tools"]["rotation_spells"] = [
        spell
        for spell in profile["tools"]["rotation_spells"]
        if spell["words"] != spell_words
    ]


def apply_request(profile: dict[str, Any], request: str) -> list[str]:
    text = normalize(request)
    changes: list[str] = []

    profile["name"] = "CTOAI EK: " + request[:48].strip()
    changes.append(f"profile name = {profile['name']}")

    spell_threshold = find_percent(text, ("heal", "leczenie", "spell", "czar"))
    if spell_threshold is not None:
        profile["healing"]["spell_threshold"] = spell_threshold
        changes.append(f"spell heal <= {spell_threshold}%")

    potion_threshold = find_percent(text, ("potion", "pot", "mikstura", "hp potion"))
    if potion_threshold is not None:
        profile["healing"]["potion_threshold"] = potion_threshold
        changes.append(f"potion <= {potion_threshold}%")

    hotkey = re.search(r"\b(f(?:1[0-2]|[1-9]))\b", text)
    if hotkey:
        profile["healing"]["potion_hotkey"] = hotkey.group(1).upper()
        changes.append(f"potion hotkey = {profile['healing']['potion_hotkey']}")

    if "ultimate health" in text or "uhp" in text:
        profile["healing"]["potion_name"] = "Ultimate Health Potion"
        changes.append("potion name = Ultimate Health Potion")
    elif "great health" in text or "ghp" in text:
        profile["healing"]["potion_name"] = "Great Health Potion"
        changes.append("potion name = Great Health Potion")
    elif "health potion" in text or "hp potion" in text:
        profile["healing"]["potion_name"] = "Health Potion"
        changes.append("potion name = Health Potion")

    if "bez potion" in text or "bez pot" in text or "wylacz potion" in text:
        profile["healing"]["potion_enabled"] = False
        changes.append("potion healing disabled")

    if "bez spell heal" in text or "wylacz spell heal" in text:
        profile["healing"]["spell_enabled"] = False
        changes.append("spell healing disabled")

    if "haste on" in text or "auto haste" in text or "utani hur" in text:
        profile["tools"]["auto_haste"] = True
        changes.append("auto haste enabled")
    if "bez haste" in text or "wylacz haste" in text:
        profile["tools"]["auto_haste"] = False
        changes.append("auto haste disabled")

    if "bez exeta" in text or "wylacz exeta" in text:
        profile["tools"]["auto_exeta"] = False
        changes.append("auto exeta disabled")
    elif "exeta" in text:
        profile["tools"]["auto_exeta"] = True
        changes.append("auto exeta enabled")

    exeta_visible = re.search(r"exeta\D{0,24}(\d+)\s*(?:visible|widoczn|ekran|mob)", text)
    if exeta_visible:
        value = max(1, int(exeta_visible.group(1)))
        profile["tools"]["exeta_min_visible"] = value
        changes.append(f"exeta min visible = {value}")

    aoe_min = re.search(r"(?:aoe|obszar|exori)\D{0,18}(?:od|>=|minimum|min)\D{0,8}(\d+)", text)
    if aoe_min:
        value = max(2, int(aoe_min.group(1)))
        set_spell_min(profile, "exori", value)
        set_spell_min(profile, "exori min", value)
        changes.append(f"exori/exori min min nearby = {value}")

    gran_min = re.search(r"exori gran(?! ico)\D{0,18}(?:od|>=|minimum|min)\D{0,8}(\d+)", text)
    if gran_min:
        value = max(2, int(gran_min.group(1)))
        set_spell_min(profile, "exori gran", value)
        changes.append(f"exori gran min nearby = {value}")

    if "bez aoe na 1" in text or "nie bij exori w 1" in text or "nie exori w 1" in text:
        set_spell_min(profile, "exori", max(2, int(profile["tools"]["rotation_spells"][1]["min_nearby"])))
        set_spell_min(profile, "exori min", max(2, int(profile["tools"]["rotation_spells"][2]["min_nearby"])))
        set_spell_min(profile, "exori gran", max(3, int(profile["tools"]["rotation_spells"][0]["min_nearby"])))
        changes.append("AoE guarded against 1 mob")

    if "bez exori hur" in text:
        remove_spell(profile, "exori hur")
        changes.append("removed exori hur")
    if "bez exori min" in text:
        remove_spell(profile, "exori min")
        changes.append("removed exori min")
    if "bez exori gran ico" in text:
        remove_spell(profile, "exori gran ico")
        changes.append("removed exori gran ico")

    if "hud off" in text or "bez hud" in text:
        profile["hud"]["enabled"] = False
        changes.append("HUD disabled")
    if "hud on" in text:
        profile["hud"]["enabled"] = True
        changes.append("HUD enabled")

    return changes


def lua_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def to_lua(value: Any, indent: int = 0) -> str:
    pad = " " * indent
    child = " " * (indent + 4)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return lua_quote(value)
    if isinstance(value, list):
        lines = ["{"]
        for item in value:
            lines.append(f"{child}{to_lua(item, indent + 4)},")
        lines.append(f"{pad}}}")
        return "\n".join(lines)
    if isinstance(value, dict):
        lines = ["{"]
        for key, item in value.items():
            lines.append(f"{child}{key} = {to_lua(item, indent + 4)},")
        lines.append(f"{pad}}}")
        return "\n".join(lines)
    raise TypeError(f"Unsupported Lua value: {type(value)!r}")


def render_profile(profile: dict[str, Any]) -> str:
    return (
        "-- ctoa_ek_profile.lua\n"
        "-- Generated by scripts/ops/ctoa_otprofile_builder.py.\n"
        "-- Edit by command, not inside helper UI code.\n\n"
        f"return {to_lua(profile)}\n"
    )


def write_profile(profile: dict[str, Any], deploy: bool) -> None:
    SOURCE_PROFILE.write_text(render_profile(profile), encoding="utf-8")
    if deploy:
        SOLTERIA_MOD_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SOURCE_PROFILE, RUNTIME_PROFILE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", "-r", required=True, help="Polish/English profile request.")
    parser.add_argument("--no-deploy", action="store_true", help="Only update repo profile.")
    parser.add_argument("--dry-run", action="store_true", help="Print generated profile without writing.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    profile = default_profile()
    changes = apply_request(profile, args.request)
    rendered = render_profile(profile)

    if args.dry_run:
        print(rendered)
    else:
        write_profile(profile, deploy=not args.no_deploy)

    print("CTOAI OT profile builder")
    for change in changes:
        print(f"- {change}")
    print(f"- repo profile: {SOURCE_PROFILE}")
    if not args.no_deploy:
        print(f"- runtime profile: {RUNTIME_PROFILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
