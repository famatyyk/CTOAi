from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


TRUTHY_VALUES = {"1", "true", "yes", "on"}
FALSEY_VALUES = {"0", "false", "no", "off"}


def is_truthy_env(value: str | None) -> bool:
    return str(value or "").strip().lower() in TRUTHY_VALUES


def is_falsey_env(value: str | None) -> bool:
    return str(value or "").strip().lower() in FALSEY_VALUES


def is_windows_host() -> bool:
    return os.name == "nt"


def is_production_env() -> bool:
    env = os.getenv("CTOA_ENV", "")
    return str(env).strip().lower() in {"prod", "production"}


def normalize_package_tier(value: str) -> str:
    tier = str(value or "").strip().lower()
    if tier in {"core", "pro", "studio"}:
        return tier
    return "studio"


def load_json_file(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def current_package_tier(product_manifest_file: Path, product_user_config_file: Path, default: str = "studio") -> str:
    env_tier = os.getenv("CTOA_PACKAGE_TIER", "").strip()
    if env_tier:
        return normalize_package_tier(env_tier)

    if product_user_config_file.exists():
        config = load_json_file(product_user_config_file)
        package_tier = str(config.get("package_tier", "")).strip()
        if package_tier:
            return normalize_package_tier(package_tier)

    if product_manifest_file.exists():
        manifest = load_json_file(product_manifest_file)
        return normalize_package_tier(str(manifest.get("default_package_tier", default)))

    return normalize_package_tier(default)


def mobile_console_enabled(product_manifest_file: Path, product_user_config_file: Path) -> bool:
    override = os.getenv("CTOA_CAPABILITY_MOBILE_CONSOLE", "").strip().lower()
    if override in TRUTHY_VALUES:
        return True
    if override in FALSEY_VALUES:
        return False

    default_enabled = current_package_tier(product_manifest_file, product_user_config_file) in {"pro", "studio"}
    package_tier_env = os.getenv("CTOA_PACKAGE_TIER", "").strip()
    if package_tier_env:
        return default_enabled

    if not product_user_config_file.exists():
        return default_enabled

    config = load_json_file(product_user_config_file)
    features_raw = config.get("features")
    features = features_raw if isinstance(features_raw, dict) else {}
    if "mobile_console" in features:
        return bool(features.get("mobile_console"))
    return default_enabled


def default_generated_dir(root: Path) -> Path:
    return root / "runtime" / "generated" if is_windows_host() else Path("/opt/ctoa/generated")


def default_ci_artifacts_dir(root: Path) -> Path:
    return root / "runtime" / "ci-artifacts" if is_windows_host() else Path("/opt/ctoa/runtime/ci-artifacts")
