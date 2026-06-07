"""Configurable spell rotation with profession and level awareness."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from .input_backend import is_available, press

_ROOT = Path(__file__).resolve().parents[2]
_cfg_raw = Path(os.environ.get("BOT_SPELL_ROTATION_FILE", "config/bot_spell_rotation.json"))
if not _cfg_raw.is_absolute():
    _cfg_raw = _ROOT / _cfg_raw
_CONFIG_PATH = _cfg_raw

_CONFIG_CACHE: dict[str, Any] | None = None
_CONFIG_MTIME: float = -1.0
_last_cast_ts: dict[str, float] = {}
_rotation_index: dict[str, int] = {}

_TITLE_PROFESSION_HINTS: tuple[tuple[str, str], ...] = (
    ("elder druid", "druid"),
    ("master sorcerer", "sorcerer"),
    ("royal paladin", "paladin"),
    ("elite knight", "knight"),
    ("druid", "druid"),
    ("sorcerer", "sorcerer"),
    ("paladin", "paladin"),
    ("knight", "knight"),
)


def _default_config() -> dict[str, Any]:
    return {
        "default_profession": "knight",
        "profiles": [],
        "rotations": {
            "knight": [],
            "paladin": [],
            "sorcerer": [],
            "druid": [],
        },
    }


def _load_config() -> dict[str, Any]:
    global _CONFIG_CACHE, _CONFIG_MTIME
    try:
        mtime = _CONFIG_PATH.stat().st_mtime
    except Exception:
        _CONFIG_CACHE = _default_config()
        _CONFIG_MTIME = -1.0
        return _CONFIG_CACHE

    if _CONFIG_CACHE is not None and mtime == _CONFIG_MTIME:
        return _CONFIG_CACHE

    try:
        data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            _CONFIG_CACHE = data
        else:
            _CONFIG_CACHE = _default_config()
    except Exception:
        _CONFIG_CACHE = _default_config()
    _CONFIG_MTIME = mtime
    return _CONFIG_CACHE


def _active_window_title_lower() -> str:
    title = os.environ.get("BOT_WINDOW_TITLE_ACTIVE", "").strip().lower()
    if title:
        return title

    try:
        from ..perception.window import find_tibia_window
        handle = find_tibia_window()
        if handle and handle.title:
            return str(handle.title).strip().lower()
    except Exception:
        return ""

    return ""


def _detect_profession(level: int, cfg: dict[str, Any]) -> str:
    env_prof = os.environ.get("BOT_PROFESSION", "").strip().lower()
    if env_prof:
        return env_prof

    title = _active_window_title_lower()
    profiles = cfg.get("profiles", [])
    if isinstance(profiles, list):
        for p in profiles:
            if not isinstance(p, dict):
                continue
            marker = str(p.get("window_title_contains", "")).strip().lower()
            prof = str(p.get("profession", "")).strip().lower()
            min_level = int(p.get("min_level", 1))
            max_level = int(p.get("max_level", 9999))
            if marker and prof and marker in title and min_level <= level <= max_level:
                return prof

    for marker, prof in _TITLE_PROFESSION_HINTS:
        if marker in title:
            return prof

    return str(cfg.get("default_profession", "knight")).strip().lower() or "knight"


def cast_rotation_spell(level: int, profession_override: str | None = None) -> str | None:
    """Cast next eligible spell from rotation for detected profession.

    Returns pressed key when spell was cast, else None.
    """
    if not is_available():
        return None

    cfg = _load_config()
    profession = (profession_override or _detect_profession(level, cfg)).strip().lower()
    rotations = cfg.get("rotations", {})
    spells = rotations.get(profession, []) if isinstance(rotations, dict) else []
    if not isinstance(spells, list) or not spells:
        return None

    start = _rotation_index.get(profession, 0) % len(spells)
    now = time.monotonic()

    for step in range(len(spells)):
        idx = (start + step) % len(spells)
        spell = spells[idx]
        if not isinstance(spell, dict):
            continue
        key = str(spell.get("key", "")).strip().lower()
        if not key:
            continue
        min_level = int(spell.get("min_level", 1))
        if level < min_level:
            continue
        cooldown_ms = int(spell.get("cooldown_ms", 2000))
        cooldown_s = max(0.0, cooldown_ms / 1000.0)
        spell_id = f"{profession}:{key}:{idx}"
        last = _last_cast_ts.get(spell_id, 0.0)
        if now - last < cooldown_s:
            continue

        press(key)
        _last_cast_ts[spell_id] = now
        _rotation_index[profession] = (idx + 1) % len(spells)
        return key

    return None
