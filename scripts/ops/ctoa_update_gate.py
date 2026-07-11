"""Mandatory launch-time update gate for public CTOA Toolkit product runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "product" / "ctoa-toolkit.manifest.json"
DEFAULT_STATE_DIR = ROOT / ".ctoa-local"
BOOTSTRAP_STATE_MAX_BYTES = 50_000


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_bootstrap_state(path: Path) -> tuple[dict | None, str | None]:
    if path.is_symlink():
        return None, "symlinked_state"
    try:
        with path.open("rb") as handle:
            raw = handle.read(BOOTSTRAP_STATE_MAX_BYTES + 1)
    except OSError:
        return None, "read_failed"
    if len(raw) > BOOTSTRAP_STATE_MAX_BYTES:
        return None, "state_too_large"
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, "invalid_json"
    if not isinstance(payload, dict):
        return None, "invalid_json_object"
    return payload, None


def _invalid_bootstrap_state(reason: str) -> tuple[int, dict]:
    return 6, {
        "ok": False,
        "status": "invalid_bootstrap_state",
        "reason": reason,
        "message": "Local bootstrap state is invalid. Re-run CTOA bootstrap before launch.",
    }


def _parse_version(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in str(value).strip().split("."))


def run_gate(state_dir: Path) -> tuple[int, dict]:
    manifest = _load_json(MANIFEST_PATH)
    state_path = state_dir / "bootstrap-state.json"

    if not state_path.exists():
        return 2, {
            "ok": False,
            "status": "bootstrap_required",
            "message": "Local bootstrap state missing. Run ctoa_product_bootstrap.py before launch.",
        }

    state, state_error = _load_bootstrap_state(state_path)
    if state_error:
        return _invalid_bootstrap_state(state_error)
    if state is None:
        return _invalid_bootstrap_state("invalid_json_object")

    required_version = _parse_version(manifest["minimum_supported_version"])
    latest_version = _parse_version(manifest["version"])
    required_schema = int(manifest["bootstrap_schema_version"])
    try:
        current_version = _parse_version(str(state.get("product_version", "0.0.0")))
        current_schema = int(state.get("bootstrap_schema_version", 0))
    except (TypeError, ValueError):
        return _invalid_bootstrap_state("invalid_version_or_schema")

    if current_schema < required_schema:
        return 3, {
            "ok": False,
            "status": "rebootstrap_required",
            "message": "Bootstrap schema changed. Re-run CTOA bootstrap before launch.",
            "local_schema": current_schema,
            "required_schema": required_schema,
        }

    if current_version < required_version:
        return 4, {
            "ok": False,
            "status": "mandatory_update_required",
            "message": "Toolkit version is below minimum supported version. Update and re-bootstrap before launch.",
            "local_version": state.get("product_version"),
            "minimum_supported_version": manifest["minimum_supported_version"],
        }

    if current_version < latest_version:
        return 5, {
            "ok": False,
            "status": "update_available",
            "message": "Toolkit update available. Update before launch to continue.",
            "local_version": state.get("product_version"),
            "latest_version": manifest["version"],
        }

    return 0, {
        "ok": True,
        "status": "launch_allowed",
        "product": manifest["product"],
        "version": manifest["version"],
        "channel": manifest["channel"],
        "package_tier": state.get("package_tier") or manifest.get("default_package_tier", "Studio"),
        "message": "Update gate passed. Launch allowed.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check mandatory CTOA Toolkit update gate")
    parser.add_argument("--state-dir", default=str(DEFAULT_STATE_DIR), help="Directory containing local toolkit state")
    args = parser.parse_args()

    code, payload = run_gate(Path(args.state_dir).resolve())
    print(json.dumps(payload, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
