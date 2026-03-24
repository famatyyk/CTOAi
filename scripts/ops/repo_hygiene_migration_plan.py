#!/usr/bin/env python3
"""Generate executable batch migration plan from repo hygiene findings."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def classify(path: str, reason: str) -> dict[str, Any]:
    lower = path.lower()

    if lower in {".env", ".env.dev", "althea.log", "mythibiav2.log"}:
        return {
            "batch": 1,
            "action": "remove-from-repo-keep-local",
            "target": "local-only (ignored)",
            "priority": "critical",
            "note": "sensitive or local runtime artifact",
        }

    if lower in {"logs", "build", "dist"}:
        return {
            "batch": 1,
            "action": "untrack-and-ignore",
            "target": "local-only (ignored)",
            "priority": "high",
            "note": "generated runtime/build output",
        }

    if lower in {
        "analyze_enc3.py",
        "bulk_xxtea_decrypt.py",
        "generate_key_candidates.py",
        "hunt.py",
        "interactive_x64dbg_recovery.py",
        "final_report.json",
        "readable_pack_manifest.csv",
        "readable_pack_manifest.json",
        "interactive_recovery_readme.md",
    }:
        return {
            "batch": 2,
            "action": "move-to-archive",
            "target": f"archived/runtime/research-tools/{path}",
            "priority": "high",
            "note": "one-off research/forensics helper",
        }

    if lower in {
        "decompiled_lua",
        "decompiled_lua_reports",
        "decompiled_lua_stage2",
        "decrypted_xxtea",
        "readable_pack",
        "artifacts",
    }:
        return {
            "batch": 3,
            "action": "move-to-private-storage",
            "target": f"private-lab-storage/{path}",
            "priority": "critical",
            "note": "raw artifact/data tree not suitable for public product repo",
        }

    if lower.startswith("sprint-") or lower.startswith("sprint_") or lower == "stage_5_closure.md":
        return {
            "batch": 4,
            "action": "move-to-docs-history",
            "target": f"docs/history/sprints/{path}",
            "priority": "medium",
            "note": "historical sprint docs should be grouped under docs/history",
        }

    if lower in {"test_agents_all.py", "test_captured_key.py", "test_local.py", "test_xxtea.py"}:
        return {
            "batch": 5,
            "action": "move-to-tests-legacy",
            "target": f"tests/legacy/{path}",
            "priority": "medium",
            "note": "top-level tests should live under tests/",
        }

    if lower in {"ctoa-loader.spec", "ctoa-loader-hotfix-20260321-135431.spec"}:
        return {
            "batch": 6,
            "action": "move-to-loader-specs",
            "target": f"releases/loader/specs/{path}",
            "priority": "medium",
            "note": "loader build specs belong to loader release area",
        }

    if lower == ".luarc.json":
        return {
            "batch": 6,
            "action": "keep-and-allowlist",
            "target": ".luarc.json",
            "priority": "low",
            "note": "editor/lua tooling config can stay if intentional",
        }

    if lower in {"archived", "releases", "templates", "dataanalysisexpert", "labs"}:
        return {
            "batch": 6,
            "action": "review-structure",
            "target": path,
            "priority": "medium",
            "note": "directory needs explicit product vs internal classification",
        }

    return {
        "batch": 6,
        "action": "manual-review",
        "target": path,
        "priority": "medium",
        "note": f"unmapped finding reason: {reason}",
    }


def load_findings(input_path: Path) -> list[dict[str, Any]]:
    data = json.loads(input_path.read_text(encoding="utf-8"))
    return data.get("findings", [])


def build_plan(findings: list[dict[str, Any]]) -> dict[str, Any]:
    planned: list[dict[str, Any]] = []
    for i, item in enumerate(findings, start=1):
        path = item.get("path", "")
        reason = item.get("reason", "")
        rule = classify(path, reason)
        planned.append(
            {
                "id": f"MIG-{i:03d}",
                "path": path,
                "reason": reason,
                "visibility": item.get("visibility", "review"),
                "package_tier": item.get("package_tier", "Unclassified"),
                "surface_action": item.get("surface_action", "manual-review"),
                "batch": rule["batch"],
                "action": rule["action"],
                "target": rule["target"],
                "priority": rule["priority"],
                "note": rule["note"],
            }
        )

    batches: dict[int, list[dict[str, Any]]] = {}
    for entry in planned:
        batches.setdefault(entry["batch"], []).append(entry)

    return {
        "status": "READY",
        "finding_count": len(findings),
        "batch_count": len(batches),
        "batches": {
            str(k): {
                "count": len(v),
                "items": sorted(v, key=lambda x: (x["priority"], x["path"])),
            }
            for k, v in sorted(batches.items(), key=lambda x: x[0])
        },
    }


def write_markdown(plan: dict[str, Any], path: Path) -> None:
    lines: list[str] = []
    lines.append("# Repo Migration Batch Plan")
    lines.append("")
    lines.append(f"Findings: {plan['finding_count']}")
    lines.append(f"Batches: {plan['batch_count']}")
    lines.append("")

    for batch_id, payload in plan["batches"].items():
        lines.append(f"## Batch {batch_id} ({payload['count']} items)")
        lines.append("")
        lines.append("| ID | Path | Visibility | Tier | Action | Target | Priority |")
        lines.append("|---|---|---|---|---|---|---|")
        for item in payload["items"]:
            lines.append(
                f"| {item['id']} | {item['path']} | {item['visibility']} | {item['package_tier']} | {item['action']} | {item['target']} | {item['priority']} |"
            )
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate migration batches from hygiene findings")
    parser.add_argument(
        "--input",
        default="runtime/repo-hygiene/latest.json",
        help="Path to hygiene findings JSON",
    )
    parser.add_argument(
        "--json-out",
        default="runtime/repo-hygiene/migration-plan.json",
        help="Path to migration plan JSON",
    )
    parser.add_argument(
        "--md-out",
        default="docs/REPO_MIGRATION_BATCH_PLAN.md",
        help="Path to migration plan markdown",
    )
    args = parser.parse_args()

    input_path = ROOT / args.input
    findings = load_findings(input_path)
    plan = build_plan(findings)

    json_out = ROOT / args.json_out
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(plan, indent=2), encoding="utf-8")

    md_out = ROOT / args.md_out
    write_markdown(plan, md_out)

    print(
        f"[repo-migration-plan] status={plan['status']} findings={plan['finding_count']} batches={plan['batch_count']}"
    )
    print(f"[repo-migration-plan] wrote {json_out}")
    print(f"[repo-migration-plan] wrote {md_out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
