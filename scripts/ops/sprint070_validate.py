"""Sprint-070 cleanup contract validator."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


REQUIRED_FILES = [
    "docs/REPO_CLEANUP_WAVES.md",
    "docs/history/sprints/SPRINT-070-PROGRESS.md",
]

REQUIRED_TASK_LABELS = [
    "CTOA: Sprint-070 Local Archive Cleanup",
    "CTOA: Sprint-070 Cleanup Documentation Sync",
]

REQUIRED_WORKFLOW_SNIPPETS = [
    "Sprint-070 cleanup contract check",
    "scripts/ops/sprint070_validate.py --run-tests --json-out runtime/ci-artifacts/sprint-070-validation.json",
]

REQUIRED_DOC_SNIPPETS = [
    "Wave 2 and Wave 3 Executed",
    "Cleanup Execution Completed",
    "Cleanup contract: `docs/REPO_CLEANUP_WAVES.md`",
    "Archive root",
]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _check_required_files(root: Path) -> dict[str, Any]:
    missing = [rel for rel in REQUIRED_FILES if not (root / rel).exists()]
    return {"id": "required_files", "ok": not missing, "hint": "" if not missing else f"missing files: {', '.join(missing)}"}


def _check_docs(root: Path) -> dict[str, Any]:
    cleanup_doc = _read_text(root / "docs/REPO_CLEANUP_WAVES.md")
    progress_doc = _read_text(root / "docs/history/sprints/SPRINT-070-PROGRESS.md")
    combined = f"{cleanup_doc}\n{progress_doc}"
    missing = [snippet for snippet in REQUIRED_DOC_SNIPPETS if snippet not in combined]
    return {
        "id": "docs_alignment",
        "ok": not missing,
        "hint": "" if not missing else f"missing doc snippets: {', '.join(missing)}",
    }


def _check_tasks(root: Path) -> dict[str, Any]:
    tasks_json = _read_text(root / ".vscode/tasks.json")
    missing = [label for label in REQUIRED_TASK_LABELS if label not in tasks_json]
    return {"id": "task_wiring", "ok": not missing, "hint": "" if not missing else f"missing task labels: {', '.join(missing)}"}


def _check_workflows(root: Path) -> dict[str, Any]:
    workflow_paths = [
        root / ".github/workflows/ctoa-pipeline.yml",
        root / ".github/workflows/pr_quality.yml",
    ]
    workflow_text = "\n".join(_read_text(path) for path in workflow_paths)
    missing = [snippet for snippet in REQUIRED_WORKFLOW_SNIPPETS if snippet not in workflow_text]
    return {
        "id": "workflow_wiring",
        "ok": not missing,
        "hint": "" if not missing else f"missing workflow snippets: {', '.join(missing)}",
    }


def _check_cleanup_ignore(root: Path) -> dict[str, Any]:
    gitignore = _read_text(root / ".gitignore")
    ok = "_local_archive/" in gitignore
    return {"id": "archive_ignore", "ok": ok, "hint": "" if ok else "missing _local_archive/ in .gitignore"}


def _check_quality(run_tests: bool) -> dict[str, Any]:
    test_path = Path("tests/test_repo_cleanup_waves_contract.py")
    if not run_tests:
        return {
            "id": "cleanup_regression_tests",
            "ok": test_path.exists(),
            "hint": "" if test_path.exists() else "missing tests/test_repo_cleanup_waves_contract.py",
        }

    proc = subprocess.run([sys.executable, "-m", "pytest", "tests/test_repo_cleanup_waves_contract.py", "-q"], capture_output=True, text=True)
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)
    return {"id": "cleanup_regression_tests", "ok": proc.returncode == 0, "hint": "" if proc.returncode == 0 else "pytest tests/test_repo_cleanup_waves_contract.py -q failed"}


def build_report(root: Path, run_tests: bool) -> dict[str, Any]:
    checks = [
        _check_required_files(root),
        _check_docs(root),
        _check_tasks(root),
        _check_workflows(root),
        _check_cleanup_ignore(root),
        _check_quality(run_tests),
    ]
    failed = [check["id"] for check in checks if not check.get("ok")]
    return {
        "status": "PASS" if not failed else "FAIL",
        "summary": f"{len(checks) - len(failed)}/{len(checks)} checks passed",
        "checks": checks,
        "diagnostics": {"failed_count": len(failed), "failed_ids": failed, "critical_failed_ids": []},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Sprint-070 cleanup contract validator")
    parser.add_argument("--root", default=".", help="Workspace root directory")
    parser.add_argument("--run-tests", action="store_true", help="Run cleanup contract regression test")
    parser.add_argument("--json-out", help="Write JSON report to file")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    report = build_report(root, args.run_tests)

    if args.json_out:
        out_path = (root / args.json_out).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"[sprint070_validate] Report written to {out_path}")

    print(f"[sprint070_validate] {report['status']} - {report['summary']}")
    for check in report["checks"]:
        mark = "OK" if check.get("ok") else "FAIL"
        suffix = f"  hint: {check.get('hint')}" if check.get("hint") else ""
        print(f"  [{mark}] {check['id']}{suffix}")

    failed_ids = report["diagnostics"]["failed_ids"]
    if failed_ids:
        print(f"[sprint070_validate] failed checks: {', '.join(failed_ids)}")

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
