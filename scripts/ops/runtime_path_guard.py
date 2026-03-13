#!/usr/bin/env python3
"""Guard against runtime sprawl and duplicate agent/runtime entry paths.

Policy is read from core/runtime-freeze-policy.json.
Fails if a new risky runtime/agent file appears outside allowed runtime path
and outside legacy exceptions.
"""

from __future__ import annotations

import fnmatch
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POLICY_FILE = ROOT / "core" / "runtime-freeze-policy.json"


def _tracked_files() -> list[str]:
    out = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True)
    return [line.strip().replace("\\", "/") for line in out.splitlines() if line.strip()]


def _load_policy() -> dict:
    if not POLICY_FILE.exists():
        raise FileNotFoundError(f"Missing policy file: {POLICY_FILE}")
    with POLICY_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def _matches_any(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, p) for p in patterns)


def check() -> int:
    policy = _load_policy()
    files = _tracked_files()

    entry = policy["allowed_runtime_entrypoint"]
    agent_prefix = policy["allowed_agent_package_prefix"]
    exceptions = set(policy.get("legacy_exceptions", []))
    risky_globs = policy.get("risky_globs", [])

    if entry not in files:
        print(f"[FAIL] Missing required runtime entrypoint: {entry}")
        return 1

    bad: list[str] = []
    candidates = [f for f in files if _matches_any(f, risky_globs)]

    for f in sorted(candidates):
        if f == entry:
            continue
        if f.startswith(agent_prefix):
            continue
        if f in exceptions:
            continue
        bad.append(f)

    print("Runtime freeze guard report")
    print(f" - tracked files: {len(files)}")
    print(f" - risky candidates: {len(candidates)}")
    print(f" - legacy exceptions: {len(exceptions)}")

    if bad:
        print("\n[FAIL] New runtime/agent paths outside allowed source of truth:")
        for f in bad:
            print(f" - {f}")
        print("\nAllowed source of truth:")
        print(f" - runtime: {entry}")
        print(f" - agents package: {agent_prefix}")
        print("\nIf a path is truly legacy and temporarily accepted, add it to core/runtime-freeze-policy.json::legacy_exceptions.")
        return 1

    print("\n[OK] No new runtime/agent sprawl detected.")
    return 0


def main() -> int:
    return check()


if __name__ == "__main__":
    raise SystemExit(main())
