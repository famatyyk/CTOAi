"""Sprint-057 validator."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

REQUIRED_FILES = [
    'workflows/backlog-sprint-057.yaml',
    'workflows/sprint-057-delivery-flow.yaml',
    'docs/history/sprints/SPRINT-057.md',
    'docs/history/sprints/SPRINT-057-PROGRESS.md',
    'scripts/ops/project_progress_diagram.py',
    'scripts/ops/sprint057_validate.py',
    'scripts/ops/sprint_state_sync.py',
    'scripts/ops/wave_summary_utf8.py',
    '.vscode/tasks.json',
    '.github/workflows/ctoa-pipeline.yml',
]
REQUIRED_YAML_FILES = [
    'workflows/backlog-sprint-057.yaml',
    'workflows/sprint-057-delivery-flow.yaml',
]
REQUIRED_HOOKS = {"on_start", "on_complete", "on_fail"}
FOCUSED_REGRESSION_TEST_FILES = [
    'tests/test_response_guardrails.py',
    'tests/test_sprint029_validate.py',
    'tests/test_sprint041_dashboard_ergonomics.py',
    'tests/test_sprint041_live_dashboard_status_context_panel.py',
    'tests/test_sprint042_auth_header_navigation.py',
    'tests/test_runner_backlog_selection.py',
    'tests/test_sprint044_control_tick.py',
    'tests/test_mobile_console_intel_proxy_api.py',
]


def _safe_yaml_load(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def check_file_exists(root: Path, rel_path: str) -> dict:
    ok = (root / rel_path).exists()
    return {
        "id": f"file:{rel_path}",
        "ok": ok,
        "hint": "Create or restore missing sprint file" if not ok else "",
    }


def check_yaml_syntax(root: Path) -> list[dict]:
    checks = []
    for rel in REQUIRED_YAML_FILES:
        path = root / rel
        if not path.exists():
            checks.append({"id": f"syntax:{rel}", "ok": False, "hint": "File missing for syntax validation"})
            continue
        try:
            _safe_yaml_load(path)
            checks.append({"id": f"syntax:{rel}", "ok": True, "hint": ""})
        except Exception as exc:
            checks.append({"id": f"syntax:{rel}", "ok": False, "hint": f"YAML parse error: {exc}"})
    return checks


def check_missing_hooks(root: Path) -> dict:
    flow_path = root / "workflows" / "sprint-057-delivery-flow.yaml"
    try:
        flow = _safe_yaml_load(flow_path)
    except Exception as exc:
        return {"id": "missing_hooks", "ok": False, "hint": f"Cannot load flow YAML: {exc}"}

    tasks = flow.get("tasks") or []
    missing: list[str] = []
    for task_def in tasks:
        task_id = task_def.get("id", "unknown")
        for req in REQUIRED_HOOKS:
            if req not in task_def or not task_def[req]:
                missing.append(f"{task_id}:{req}")

    return {
        "id": "missing_hooks",
        "ok": len(missing) == 0,
        "hint": f"Missing hooks: {', '.join(missing)}" if missing else "",
    }


def check_pipeline_gate(root: Path) -> dict:
    pipeline_path = root / ".github/workflows/ctoa-pipeline.yml"
    if not pipeline_path.exists():
        return {"id": "pipeline_gate", "ok": False, "hint": "Pipeline file missing"}

    content = pipeline_path.read_text(encoding="utf-8")
    gate_present = "scripts/ops/sprint057_validate.py" in content
    artifact_present = "runtime/ci-artifacts/sprint-057-validation.json" in content
    summary_present = "runtime/ci-artifacts/sprint-057-wave1-summary.txt" in content
    ok = gate_present and artifact_present and summary_present

    hint_parts: list[str] = []
    if not gate_present:
        hint_parts.append("add sprint validator command")
    if not artifact_present:
        hint_parts.append("add sprint artifact path")
    if not summary_present:
        hint_parts.append("add utf-8 summary artifact path")

    return {
        "id": "pipeline_gate",
        "ok": ok,
        "hint": "; ".join(hint_parts),
    }


def check_local_tasks(root: Path) -> dict:
    tasks_path = root / ".vscode/tasks.json"
    if not tasks_path.exists():
        return {"id": "local_tasks", "ok": False, "hint": "tasks.json missing"}

    content = tasks_path.read_text(encoding="utf-8")
    labels_present = all(
        needle in content
        for needle in [
            "CTOA: Sprint-057 Validate",
            "CTOA: Sprint-057 Wave-1 Run",
            "CTOA: Sprint-057 Refresh Progress Diagram",
            "CTOA: Sprint-057 Quality Snapshot",
            "CTOA: Sprint-057 State Sync",
            "CTOA: Sprint-057 Wave Summary UTF-8",
        ]
    )

    return {
        "id": "local_tasks",
        "ok": labels_present,
        "hint": "Add sprint validate, wave-1, state sync, utf-8 summary, progress diagram, and quality snapshot tasks" if not labels_present else "",
    }


def check_state_evidence_alignment(root: Path) -> dict:
    sprint_doc_path = root / "docs/history/sprints/SPRINT-057.md"
    backlog_path = root / "workflows/backlog-sprint-057.yaml"
    state_path = root / "runtime/task-state.yaml"

    if not sprint_doc_path.exists() or not backlog_path.exists():
        return {
            "id": "state_evidence_alignment",
            "ok": False,
            "hint": "Missing sprint doc or backlog file for alignment check",
        }

    sprint_doc = sprint_doc_path.read_text(encoding="utf-8")
    if "Status: RELEASED" not in sprint_doc:
        return {
            "id": "state_evidence_alignment",
            "ok": True,
            "hint": "",
        }

    if not state_path.exists():
        return {
            "id": "state_evidence_alignment",
            "ok": False,
            "hint": "Sprint doc is RELEASED but runtime/task-state.yaml is missing",
        }

    backlog = _safe_yaml_load(backlog_path) or {}
    state = _safe_yaml_load(state_path) or {}

    total_tasks = len([task for task in (backlog.get("tasks") or []) if isinstance(task, dict)])
    if state.get("backlog_id") != "sprint-057":
        return {
            "id": "state_evidence_alignment",
            "ok": False,
            "hint": f"Sprint doc is RELEASED but runtime backlog_id is {state.get('backlog_id')}",
        }

    state_tasks = state.get("tasks") or []
    released_count = sum(
        1
        for task in state_tasks
        if isinstance(task, dict) and str(task.get("status", "")) == "RELEASED"
    )
    ok = total_tasks > 0 and released_count >= total_tasks

    return {
        "id": "state_evidence_alignment",
        "ok": ok,
        "hint": "" if ok else f"Sprint doc is RELEASED but runtime state is RELEASED {released_count}/{total_tasks}",
    }


def check_quality_regression_tests(root: Path) -> dict:
    python = sys.executable
    cmd = [python, "-m", "pytest", *FOCUSED_REGRESSION_TEST_FILES, "-q"]
    code, output = _run(cmd, cwd=root)
    output_tail = "\n".join(output.splitlines()[-20:])

    return {
        "id": "quality_regression_tests",
        "ok": code == 0,
        "hint": "Focused quality regression tests failed" if code != 0 else "",
        "details": {
            "command": " ".join(cmd),
            "output_tail": output_tail,
        },
    }


def _collect_diagnostics(checks: list[dict]) -> dict:
    failed = [chk for chk in checks if not chk.get("ok", False)]
    severity_order = {
        "pipeline_gate": "critical",
        "missing_hooks": "critical",
        "state_evidence_alignment": "critical",
        "quality_regression_tests": "critical",
        "local_tasks": "warning",
    }

    failed_ids = [str(chk.get("id")) for chk in failed]
    critical_failed = [
        chk_id for chk_id in failed_ids if severity_order.get(chk_id, "info") == "critical"
    ]

    return {
        "failed_count": len(failed),
        "failed_ids": failed_ids,
        "critical_failed_ids": critical_failed,
    }


def validate(root: Path, run_tests: bool) -> dict:
    checks: list[dict] = []
    for rel in REQUIRED_FILES:
        checks.append(check_file_exists(root, rel))
    checks.extend(check_yaml_syntax(root))
    checks.append(check_missing_hooks(root))
    checks.append(check_pipeline_gate(root))
    checks.append(check_local_tasks(root))
    checks.append(check_state_evidence_alignment(root))

    if run_tests:
        checks.append(check_quality_regression_tests(root))

    passed = sum(1 for c in checks if c.get("ok", False))
    total = len(checks)
    diagnostics = _collect_diagnostics(checks)

    return {
        "status": "PASS" if passed == total else "FAIL",
        "summary": f"{passed}/{total} checks passed",
        "checks": checks,
        "diagnostics": diagnostics,
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Sprint-057 validator")
    parser.add_argument("--root", default=".", help="Workspace root directory")
    parser.add_argument("--json-out", help="Write JSON report to file")
    parser.add_argument("--run-tests", action="store_true", help="Run checks")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Root directory not found: {root}")

    report = validate(root, run_tests=args.run_tests)

    if args.json_out:
        out_path = root / args.json_out
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"[sprint057_validate] Report written to {out_path}")

    print(f"[sprint057_validate] {report['status']} - {report['summary']}")
    for chk in report["checks"]:
        mark = "OK" if chk.get("ok") else "FAIL"
        hint = f"  hint: {chk['hint']}" if chk.get("hint") else ""
        print(f"  [{mark}] {chk['id']}{hint}")

    failed_ids = report.get("diagnostics", {}).get("failed_ids", [])
    if failed_ids:
        print(f"[sprint057_validate] failed checks: {', '.join(failed_ids)}")

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
