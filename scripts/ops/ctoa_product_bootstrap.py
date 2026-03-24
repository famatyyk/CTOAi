"""Bootstrap local CTOA Toolkit user configuration and local state."""

from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "product" / "ctoa-toolkit.manifest.json"
CONFIG_TEMPLATE_PATH = ROOT / "config" / "ctoa-user-config.template.json"
DEFAULT_STATE_DIR = ROOT / ".ctoa-local"


def _normalize_package_tier(value: str) -> str:
    tier = str(value or "").strip().lower()
    if tier in {"core", "pro", "studio"}:
        return tier
    return "studio"


def _tier_features(package_tier: str) -> dict[str, bool]:
    tier = _normalize_package_tier(package_tier)
    return {
        "mobile_console": tier in {"pro", "studio"},
        "sealed_agents": True,
        "dashboard": tier in {"pro", "studio"},
    }


@dataclass
class BootstrapArtifacts:
    state_dir: Path
    user_config_path: Path
    bootstrap_state_path: Path
    sqlite_path: Path


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _prompt_value(label: str, default: str) -> str:
    raw = input(f"{label} [{default}]: ").strip()
    return raw or default


def _artifacts(state_dir: Path) -> BootstrapArtifacts:
    return BootstrapArtifacts(
        state_dir=state_dir,
        user_config_path=state_dir / "user-config.json",
        bootstrap_state_path=state_dir / "bootstrap-state.json",
        sqlite_path=state_dir / "toolkit-state.db",
    )


def _ensure_db(sqlite_path: Path) -> None:
    conn = sqlite3.connect(sqlite_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bootstrap_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_name TEXT NOT NULL,
                operator_handle TEXT NOT NULL,
                deployment_mode TEXT NOT NULL,
                update_channel TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bootstrap_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_version TEXT NOT NULL,
                minimum_supported_version TEXT NOT NULL,
                bootstrap_schema_version INTEGER NOT NULL,
                configured_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def bootstrap(
    *,
    state_dir: Path,
    package_tier: str,
    profile_name: str,
    operator_handle: str,
    deployment_mode: str,
    update_channel: str,
) -> dict:
    manifest = _load_json(MANIFEST_PATH)
    template = _load_json(CONFIG_TEMPLATE_PATH)
    normalized_tier = _normalize_package_tier(package_tier or str(manifest.get("default_package_tier", "studio")))
    state_dir.mkdir(parents=True, exist_ok=True)
    files = _artifacts(state_dir)
    _ensure_db(files.sqlite_path)

    configured_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    user_config = {
        **template,
        "package_tier": normalized_tier,
        "profile_name": profile_name,
        "operator_handle": operator_handle,
        "deployment_mode": deployment_mode,
        "update_channel": update_channel,
        "features": _tier_features(normalized_tier),
        "configured_at": configured_at,
    }
    files.user_config_path.write_text(json.dumps(user_config, indent=2), encoding="utf-8")

    bootstrap_state = {
        "product": manifest["product"],
        "channel": manifest["channel"],
        "product_version": manifest["version"],
        "minimum_supported_version": manifest["minimum_supported_version"],
        "bootstrap_schema_version": int(manifest["bootstrap_schema_version"]),
        "package_tier": normalized_tier,
        "configured_at": configured_at,
        "profile_name": profile_name,
        "operator_handle": operator_handle,
        "deployment_mode": deployment_mode,
        "update_channel": update_channel,
    }
    files.bootstrap_state_path.write_text(json.dumps(bootstrap_state, indent=2), encoding="utf-8")

    conn = sqlite3.connect(files.sqlite_path)
    try:
        conn.execute("DELETE FROM bootstrap_config")
        conn.execute("DELETE FROM bootstrap_state")
        conn.execute(
            "INSERT INTO bootstrap_config (profile_name, operator_handle, deployment_mode, update_channel, created_at) VALUES (?, ?, ?, ?, ?)",
            (profile_name, operator_handle, deployment_mode, update_channel, configured_at),
        )
        conn.execute(
            "INSERT INTO bootstrap_state (product_version, minimum_supported_version, bootstrap_schema_version, configured_at) VALUES (?, ?, ?, ?)",
            (
                manifest["version"],
                manifest["minimum_supported_version"],
                int(manifest["bootstrap_schema_version"]),
                configured_at,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "ok": True,
        "state_dir": str(state_dir),
        "user_config": str(files.user_config_path),
        "bootstrap_state": str(files.bootstrap_state_path),
        "sqlite_db": str(files.sqlite_path),
        "product_version": manifest["version"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap local CTOA Toolkit configuration")
    parser.add_argument("--state-dir", default=str(DEFAULT_STATE_DIR), help="Directory for ignored local toolkit state")
    parser.add_argument("--package-tier", default="", help="Package tier: core, pro, or studio")
    parser.add_argument("--profile-name", default="default-profile", help="Local profile name")
    parser.add_argument("--operator-handle", default="operator", help="Local operator handle")
    parser.add_argument("--deployment-mode", default="self-hosted", help="Deployment mode label")
    parser.add_argument("--update-channel", default="stable", help="Update channel")
    parser.add_argument("--non-interactive", action="store_true", help="Do not prompt, use CLI/default values")
    args = parser.parse_args()

    manifest = _load_json(MANIFEST_PATH)
    package_tier = _normalize_package_tier(args.package_tier or str(manifest.get("default_package_tier", "studio")))
    profile_name = args.profile_name
    operator_handle = args.operator_handle
    deployment_mode = args.deployment_mode
    update_channel = args.update_channel

    if not args.non_interactive:
        package_tier = _normalize_package_tier(_prompt_value("Package tier", package_tier))
        profile_name = _prompt_value("Profile name", profile_name)
        operator_handle = _prompt_value("Operator handle", operator_handle)
        deployment_mode = _prompt_value("Deployment mode", deployment_mode)
        update_channel = _prompt_value("Update channel", update_channel)

    result = bootstrap(
        state_dir=Path(args.state_dir).resolve(),
        package_tier=package_tier,
        profile_name=profile_name,
        operator_handle=operator_handle,
        deployment_mode=deployment_mode,
        update_channel=update_channel,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())