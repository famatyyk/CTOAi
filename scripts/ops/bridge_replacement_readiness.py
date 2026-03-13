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

    for file_path in tracked_files():
        if file_path.suffix.lower() not in {".py", ".md", ".yml", ".yaml", ".txt", ".sh", ".ps1"}:
            continue
        try:
            text = file_path.read_text(encoding="utf-8")
        except Exception:
            continue
        rel = file_path.relative_to(ROOT).as_posix()
        for key, rx in PATTERNS.items():
            if rx.search(text):
                findings[key].append(rel)

    return findings


def main() -> int:
    findings = scan()

    print("Bridge replacement readiness report")
    print("---------------------------------")

    for key, files in findings.items():
        print(f"{key}: {len(files)}")
        for f in files:
            print(f" - {f}")

    print()
    if not findings["legacy_import_agents"] and not findings["legacy_file_reference"]:
        print("READY: no legacy references detected.")
        return 0

    print("NOT READY: legacy references still exist; follow docs/BRIDGE_REPLACEMENT_PLAN_AGENTS.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
