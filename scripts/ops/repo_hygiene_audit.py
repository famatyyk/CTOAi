#!/usr/bin/env python3
"""CTOA repo hygiene audit.

Scans top-level repository entries and reports items that look like
non-product clutter in a public product repository.
Also classifies each finding by public/private visibility and package tier.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

TOP_LEVEL_ALLOWLIST = {
    ".github",
    ".vscode",
    "agents",
    "config",
    "core",
    "deploy",
    "docs",
    "mobile_console",
    "policies",
    "product",
    "prompts",
    "runner",
    "runtime",
    "schemas",
    "scoring",
    "scripts",
    "tests",
    "tools",
    "training",
    "workflows",
    "README.md",
    "CHANGELOG.md",
    "requirements.txt",
    "requirements_hybrid.txt",
    ".gitignore",
    ".luarc.json",
    "ctoa.ps1",
    "ctoa-vps.ps1",
    "archived",
    "DataAnalysisExpert",
    "labs",
    "releases",
    "templates",
}

FLAGGED_TOP_LEVEL_PREFIXES = (
    "decompiled_",
    "decrypted_",
    "readable_pack",
    "artifacts",
)

FLAGGED_TOP_LEVEL_FILES = {
    "analyze_enc3.py",
    "bulk_xxtea_decrypt.py",
    "generate_key_candidates.py",
    "hunt.py",
    "interactive_x64dbg_recovery.py",
    "readable_pack_manifest.csv",
    "readable_pack_manifest.json",
    "final_report.json",
}

LOCAL_ONLY_CANDIDATES = {
    ".ctoa-local",
    ".env",
    ".env.dev",
    "Althea.log",
    "MythibiaV2.log",
    "build",
    "dist",
    "logs",
    "metrics",
}

CORE_PUBLIC_PATHS = {
    ".github",
    ".vscode",
    "agents",
    "config",
    "core",
    "deploy",
    "docs",
    "mobile_console",
    "policies",
    "product",
    "prompts",
    "runner",
    "schemas",
    "scoring",
    "scripts",
    "tests",
    "tools",
    "training",
    "workflows",
    "README.md",
    "CHANGELOG.md",
    "requirements.txt",
    "requirements_hybrid.txt",
    ".gitignore",
}

PRO_PATHS = {
    "mobile_console",
    "deploy",
    "releases",
    "templates",
}

STUDIO_ONLY_PATHS = {
    "archived",
    "artifacts",
    "DataAnalysisExpert",
    "decompiled_lua",
    "decompiled_lua_reports",
    "decompiled_lua_stage2",
    "decrypted_xxtea",
    "labs",
    "readable_pack",
}


def classify_distribution(path: str) -> dict[str, str]:
    name = path.split("/", 1)[0]

    if name in STUDIO_ONLY_PATHS or any(name.startswith(prefix) for prefix in FLAGGED_TOP_LEVEL_PREFIXES):
        return {
            "visibility": "private",
            "package_tier": "Studio",
            "surface_action": "remove-from-public-surface",
        }

    if name in PRO_PATHS:
        return {
            "visibility": "public",
            "package_tier": "Pro",
            "surface_action": "keep-or-package-pro",
        }

    if name in CORE_PUBLIC_PATHS:
        return {
            "visibility": "public",
            "package_tier": "Core",
            "surface_action": "keep-public-core",
        }

    return {
        "visibility": "review",
        "package_tier": "Unclassified",
        "surface_action": "manual-review",
    }


def _tracked_top_level_entries() -> set[str]:
    """Return tracked top-level names so local generated files can be ignored."""
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return set()

    tracked: set[str] = set()
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        tracked.add(line.split("/", 1)[0])
    return tracked


def _scan_top_level() -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    entries = sorted(ROOT.iterdir(), key=lambda p: p.name.lower())
    tracked_top_level = _tracked_top_level_entries()

    for entry in entries:
        name = entry.name
        if name in {".git", ".venv", "__pycache__", ".pytest_cache"}:
            continue

        if name in TOP_LEVEL_ALLOWLIST:
            continue

        # Local env/log/build outputs are ignored if they are not tracked by git.
        if name in LOCAL_ONLY_CANDIDATES and name not in tracked_top_level:
            continue

        if name in FLAGGED_TOP_LEVEL_FILES:
            distribution = classify_distribution(name)
            findings.append(
                {
                    "path": name,
                    "reason": "top-level one-off or research artifact file",
                    "suggested_action": "move to private lab repo or archive path",
                    **distribution,
                }
            )
            continue

        if any(name.startswith(prefix) for prefix in FLAGGED_TOP_LEVEL_PREFIXES):
            distribution = classify_distribution(name)
            findings.append(
                {
                    "path": name,
                    "reason": "top-level artifact/data tree outside product surface",
                    "suggested_action": "move raw data outside public repo and keep only metadata",
                    **distribution,
                }
            )
            continue

        # Unknown top-level entries should be reviewed.
        distribution = classify_distribution(name)
        findings.append(
            {
                "path": name,
                "reason": "top-level entry not in product allowlist",
                "suggested_action": "classify as product content or move to archived/private storage",
                **distribution,
            }
        )

    return {
        "repo_root": str(ROOT),
        "findings": findings,
        "finding_count": len(findings),
        "summary": {
            "private_count": sum(1 for item in findings if item.get("visibility") == "private"),
            "public_count": sum(1 for item in findings if item.get("visibility") == "public"),
            "review_count": sum(1 for item in findings if item.get("visibility") == "review"),
        },
        "status": "PASS" if not findings else "REVIEW_REQUIRED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit CTOA repo hygiene.")
    parser.add_argument("--json-out", default="", help="Optional path to save JSON report.")
    parser.add_argument(
        "--fail-on-findings",
        action="store_true",
        help="Exit non-zero when findings are present.",
    )
    args = parser.parse_args()

    report = _scan_top_level()

    print(f"[repo-hygiene] status={report['status']} findings={report['finding_count']}")
    for item in report["findings"]:
        print(f"- {item['path']}: {item['reason']}")

    if args.json_out:
        out_path = Path(args.json_out)
        if not out_path.is_absolute():
            out_path = ROOT / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"[repo-hygiene] wrote {out_path}")

    if args.fail_on_findings and report["finding_count"] > 0:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
