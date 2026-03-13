#!/usr/bin/env python3
"""Readiness checks before replacing legacy bridge runner/agents.py.

This script is intentionally read-only and reports dependencies that must be
resolved before archiving the final legacy runtime file.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PATTERNS = {
    "legacy_import_agents": re.compile(r"from\s+agents\s+import\s+execute_agent_for_task"),
    "legacy_file_reference": re.compile(r"runner/agents\.py"),
}


def tracked_files() -> list[Path]:
    out = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True)
    return [ROOT / line.strip() for line in out.splitlines() if line.strip()]


def scan() -> dict[str, list[str]]:
    findings: dict[str, list[str]] = {k: [] for k in PATTERNS}

    code_ext = {".py", ".sh", ".ps1", ".yml", ".yaml"}
    all_ext = code_ext | {".md", ".txt"}

    for file_path in tracked_files():
        ext = file_path.suffix.lower()
        if ext not in all_ext:
            continue
        try:
            text = file_path.read_text(encoding="utf-8")
        except Exception:
            continue
        rel = file_path.relative_to(ROOT).as_posix()

        # Avoid self-reporting from this helper script.
        if rel == "scripts/ops/bridge_replacement_readiness.py":
            continue

        for key, rx in PATTERNS.items():
            # Import-pattern is only meaningful in code files.
            if key == "legacy_import_agents" and ext not in code_ext:
                continue
            if rx.search(text):
                findings[key].append(rel)

    return findings


def main() -> int:
    findings = scan()

    code_files = [f for f in findings["legacy_file_reference"] if f.endswith((".py", ".sh", ".ps1", ".yml", ".yaml"))]
    doc_files = [f for f in findings["legacy_file_reference"] if f.endswith((".md", ".txt"))]
    import_blockers = [f for f in findings["legacy_import_agents"] if f != "runner/runner.py"]
    allowed_code_refs = {
        "runner/agents/executor.py",
        "archived/runtime/agents_legacy.py",
    }
    code_blockers = [f for f in code_files if f not in allowed_code_refs]

    print("Bridge replacement readiness report")
    print("---------------------------------")

    for key, files in findings.items():
        print(f"{key}: {len(files)}")
        for f in files:
            print(f" - {f}")

    print(f"legacy_import_agents_blockers: {len(import_blockers)}")
    for f in import_blockers:
        print(f" - {f}")
    print(f"legacy_file_reference_code_blockers: {len(code_blockers)}")
    for f in code_blockers:
        print(f" - {f}")

    print(f"legacy_file_reference_code: {len(code_files)}")
    for f in code_files:
        print(f" - {f}")
    print(f"legacy_file_reference_docs: {len(doc_files)}")
    for f in doc_files:
        print(f" - {f}")

    print()
    if not import_blockers and not code_blockers:
        print("READY: no legacy references detected.")
        return 0

    print("NOT READY: legacy references still exist; follow docs/BRIDGE_REPLACEMENT_PLAN_AGENTS.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
