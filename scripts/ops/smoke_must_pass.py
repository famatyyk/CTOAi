#!/usr/bin/env python3
"""Run the minimal must-pass smoke checks for Azure alerts automation."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runner import process_safety  # noqa: E402


def run_step(name: str, cmd: list[str]) -> tuple[bool, dict[str, object]]:
    print(f"\n[SMOKE] {name}")
    print(f"[CMD] {' '.join(cmd)}")
    executable = process_safety.resolve_executable(cmd[0])
    completed = process_safety.run_trusted([executable, *cmd[1:]], check=False)
    ok = completed.returncode == 0
    print(f"[RESULT] {'PASS' if ok else 'FAIL'} (exit={completed.returncode})")
    return ok, {
        "name": name,
        "command": cmd,
        "exit_code": completed.returncode,
        "status": "pass" if ok else "fail",
    }


def main() -> int:
    python_exe = process_safety.resolve_python()
    Path("runtime/alerts").mkdir(parents=True, exist_ok=True)

    steps = [
        (
            "Azure alerts focused tests",
            [python_exe, "-m", "pytest", "tests/test_azure_activity_alerts.py", "-q"],
        ),
        (
            "Azure alerts pipeline sample dry-run",
            [
                python_exe,
                "scripts/ops/azure_activity_alerts.py",
                "--ingest-mode",
                "file",
                "--source-file",
                "docs/examples/azure-activity-log-samples.json",
                "--source-format",
                "json",
                "--routes",
                "console,jsonl",
                "--output-jsonl",
                "runtime/alerts/azure-activity-alerts-smoke.jsonl",
                "--min-severity",
                "warning",
                "--dry-run",
            ],
        ),
    ]

    results: list[dict[str, object]] = []
    all_ok = True
    for name, cmd in steps:
        ok, result = run_step(name, cmd)
        results.append(result)
        all_ok = all_ok and ok

    summary = {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ok": all_ok,
        "steps": results,
    }

    out_path = Path("runtime/ci-artifacts/smoke-must-pass-summary.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\n[SMOKE] Summary")
    print(json.dumps(summary))
    print(f"[SMOKE] Report written to: {out_path}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
