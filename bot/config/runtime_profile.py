"""JSON-backed client profile config with env overrides."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
_cfg_raw = Path(os.environ.get("BOT_CLIENT_CONFIG_FILE", "config/client_profiles.json"))
if not _cfg_raw.is_absolute():
    _cfg_raw = _ROOT / _cfg_raw
_CONFIG_PATH = _cfg_raw

_CACHE: dict[str, Any] | None = None
_CACHE_MTIME: float = -1.0


TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off"}


def _load_config() -> dict[str, Any]:
    global _CACHE, _CACHE_MTIME
    try:
        mtime = _CONFIG_PATH.stat().st_mtime
    except Exception:
        _CACHE = {}
        _CACHE_MTIME = -1.0
        return _CACHE

    if _CACHE is not None and mtime == _CACHE_MTIME:
        return _CACHE

    try:
        data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        _CACHE = data if isinstance(data, dict) else {}
    except Exception:
        _CACHE = {}
    _CACHE_MTIME = mtime
    return _CACHE


def active_profile_name() -> str:
    cfg = _load_config()
    from_env = os.environ.get("BOT_CLIENT_PROFILE", "").strip()
    if from_env:
        return from_env
    return str(cfg.get("default_profile", "default")).strip() or "default"


def _profile_values() -> dict[str, Any]:
    cfg = _load_config()
    vals: dict[str, Any] = {}

    defaults = cfg.get("defaults", {})
    if isinstance(defaults, dict):
        vals.update(defaults)

    profiles = cfg.get("profiles", {})
    if isinstance(profiles, dict):
        profile = profiles.get(active_profile_name(), {})
        if isinstance(profile, dict):
            vals.update(profile)

    return vals


def _raw_value(key: str, default: Any = None) -> Any:
    if key in os.environ:
        return os.environ.get(key)
    values = _profile_values()
    return values.get(key, default)


def get_str(key: str, default: str = "") -> str:
    raw = _raw_value(key, default)
    if raw is None:
        return default
    return str(raw)


def get_int(key: str, default: int = 0) -> int:
    raw = _raw_value(key, default)
    try:
        return int(raw)
    except Exception:
        return default


def get_float(key: str, default: float = 0.0) -> float:
    raw = _raw_value(key, default)
    try:
        return float(raw)
    except Exception:
        return default


def get_bool(key: str, default: bool = False) -> bool:
    raw = _raw_value(key, default)
    if isinstance(raw, bool):
        return raw
    text = str(raw).strip().lower()
    if text in TRUE_VALUES:
        return True
    if text in FALSE_VALUES:
        return False
    return default


def get_list(key: str, default: list[str] | None = None) -> list[str]:
    fallback = list(default or [])
    raw = _raw_value(key, None)
    if raw is None:
        return fallback

    if isinstance(raw, list):
        return [str(v).strip() for v in raw if str(v).strip()]

    text = str(raw).strip()
    if not text:
        return fallback
    return [v.strip() for v in text.split(",") if v.strip()]


def config_path() -> Path:
    return _CONFIG_PATH


def reload_config() -> None:
    global _CACHE, _CACHE_MTIME
    _CACHE = None
    _CACHE_MTIME = -1.0


def save_profile_values(profile: str, updates: dict[str, Any]) -> None:
    """Persist key/value updates to a profile in client_profiles JSON file.

    Env vars still have precedence at runtime, but this updates durable defaults
    for the selected profile so configuration is portable across clients.
    """
    cfg = _load_config().copy()

    profiles = cfg.get("profiles")
    if not isinstance(profiles, dict):
        profiles = {}
        cfg["profiles"] = profiles

    profile_data = profiles.get(profile)
    if not isinstance(profile_data, dict):
        profile_data = {}
        profiles[profile] = profile_data

    profile_data.update(updates)

    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    reload_config()
