"""Validate Core/Pro/Studio package boundary manifests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CORE_MANIFEST = ROOT / "product" / "packages" / "core.manifest.json"
PRO_MANIFEST = ROOT / "product" / "packages" / "pro.manifest.json"
STUDIO_MANIFEST = ROOT / "product" / "packages" / "studio.manifest.json"

PRIVATE_EXCLUDES = {
    "archived/runtime/private-storage",
    "artifacts",
    "decompiled_lua",
    "decompiled_lua_reports",
    "decompiled_lua_stage2",
    "decrypted_xxtea",
    "readable_pack",
}

STUDIO_PRIVATE_INCLUDES = {
    "archived",
    "DataAnalysisExpert",
    "labs",
    "releases",
    "artifacts",
    "decompiled_lua",
    "decompiled_lua_reports",
    "decompiled_lua_stage2",
    "decrypted_xxtea",
    "readable_pack",
}

PUBLIC_CORE_PATHS = {
    "agents",
    "config",
    "core",
    "docs",
    "policies",
    "product",
    "prompts",
    "runner",
    "schemas",
    "scoring",
    "scripts/ops",
    "tests",
    "tools",
    "training",
    "workflows",
}

PRO_EXTRA_PATHS = {"mobile_console", "deploy", "releases/loader", "templates"}


def _load_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid manifest object in {path}")
    return payload


def _normalized_paths(values: Any) -> set[str]:
    if not isinstance(values, list):
        return set()
    return {str(value).strip().replace("\\", "/") for value in values if str(value).strip()}


def validate_package_boundaries(
    core_manifest: Path = CORE_MANIFEST,
    pro_manifest: Path = PRO_MANIFEST,
    studio_manifest: Path = STUDIO_MANIFEST,
) -> list[str]:
    issues: list[str] = []

    core = _load_manifest(core_manifest)
    pro = _load_manifest(pro_manifest)
    studio = _load_manifest(studio_manifest)

    core_includes = _normalized_paths(core.get("include_paths"))
    core_excludes = _normalized_paths(core.get("exclude_paths"))
    pro_includes = _normalized_paths(pro.get("include_paths"))
    pro_excludes = _normalized_paths(pro.get("exclude_paths"))
    studio_includes = _normalized_paths(studio.get("include_paths"))

    if str(core.get("tier")) != "Core":
        issues.append("core.manifest.json must declare tier=Core")
    if str(pro.get("tier")) != "Pro":
        issues.append("pro.manifest.json must declare tier=Pro")
    if str(studio.get("tier")) != "Studio":
        issues.append("studio.manifest.json must declare tier=Studio")
    if str(pro.get("extends")) != "Core":
        issues.append("pro.manifest.json must extend Core")
    if str(studio.get("visibility")) != "private":
        issues.append("studio.manifest.json must declare visibility=private")

    missing_core_paths = sorted(PUBLIC_CORE_PATHS - core_includes)
    if missing_core_paths:
        issues.append("core.manifest.json is missing public core paths: " + ", ".join(missing_core_paths))

    missing_pro_paths = sorted(PRO_EXTRA_PATHS - pro_includes)
    if missing_pro_paths:
        issues.append("pro.manifest.json is missing Pro paths: " + ", ".join(missing_pro_paths))

    missing_studio_paths = sorted(STUDIO_PRIVATE_INCLUDES - studio_includes)
    if missing_studio_paths:
        issues.append("studio.manifest.json is missing private paths: " + ", ".join(missing_studio_paths))

    if "mobile_console" in core_includes:
        issues.append("core.manifest.json must not include mobile_console")

    for path in PRIVATE_EXCLUDES:
        if path in core_includes:
            issues.append(f"core.manifest.json must not include private path: {path}")
        if path in pro_includes:
            issues.append(f"pro.manifest.json must not include private path: {path}")

    if PRIVATE_EXCLUDES - core_excludes:
        issues.append("core.manifest.json should exclude private studio paths")
    if PRIVATE_EXCLUDES - pro_excludes:
        issues.append("pro.manifest.json should exclude private studio paths")

    if core_includes & core_excludes:
        issues.append("core.manifest.json has overlapping include/exclude paths")
    if pro_includes & pro_excludes:
        issues.append("pro.manifest.json has overlapping include/exclude paths")

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Core/Pro/Studio package boundaries")
    parser.add_argument("--root", default=str(ROOT), help="Repository root")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    issues = validate_package_boundaries(
        core_manifest=root / "product" / "packages" / "core.manifest.json",
        pro_manifest=root / "product" / "packages" / "pro.manifest.json",
        studio_manifest=root / "product" / "packages" / "studio.manifest.json",
    )
    if issues:
        print("Package boundary validation failed:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("Package boundary validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
