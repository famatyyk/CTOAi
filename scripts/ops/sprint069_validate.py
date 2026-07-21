"""Sprint-069 kickoff validator."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runner import process_safety  # noqa: E402
from scripts.ops.sprint_kickoff_validator import (  # noqa: E402
    SprintKickoffConfig,
    build_kickoff_report,
    check_quality_regression,
)

CONFIG = SprintKickoffConfig(
    "069",
    ("CTOA-338", "CTOA-339", "CTOA-340"),
    ("delivery continuity", "CLI contract alignment"),
)
REQUIRED_FILES = list(CONFIG.required_files)
REQUIRED_TASK_LABELS = list(CONFIG.required_task_labels)
REQUIRED_WORKFLOW_SNIPPETS = list(CONFIG.required_workflow_snippets)
REQUIRED_HOOKS = {"on_start", "on_complete", "on_fail"}


def _check_quality(run_tests: bool) -> dict[str, Any]:
    return check_quality_regression(run_tests, process_safety=process_safety, path_factory=Path)


def build_report(root: Path, run_tests: bool) -> dict[str, Any]:
    return build_kickoff_report(root, CONFIG, _check_quality, run_tests)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sprint-069 kickoff validator")
    parser.add_argument("--root", default=".", help="Workspace root directory")
    parser.add_argument("--run-tests", action="store_true", help="Run response guardrail regression test")
    parser.add_argument("--json-out", help="Write JSON report to file")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    report = build_report(root, args.run_tests)
    if args.json_out:
        output_path = (root / args.json_out).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"[sprint069_validate] Report written to {output_path}")

    print(f"[sprint069_validate] {report['status']} - {report['summary']}")
    for check in report["checks"]:
        suffix = f"  hint: {check['hint']}" if check.get("hint") else ""
        print(f"  [{'OK' if check.get('ok') else 'FAIL'}] {check['id']}{suffix}")
    failed_ids = report["diagnostics"]["failed_ids"]
    if failed_ids:
        print(f"[sprint069_validate] failed checks: {', '.join(failed_ids)}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
