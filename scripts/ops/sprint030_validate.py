"""Sprint-030 validator."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import yaml

REQUIRED_FILES = ['workflows/backlog-sprint-030.yaml', 'workflows/sprint-030-delivery-flow.yaml', 'scripts/ops/sprint030_validate.py', '.vscode/tasks.json', '.github/workflows/ctoa-pipeline.yml']
REQUIRED_YAML_FILES = ['workflows/backlog-sprint-030.yaml', 'workflows/sprint-030-delivery-flow.yaml']
REQUIRED_HOOKS = {"on_start", "on_complete", "on_fail"}


def _safe_yaml_load(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


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
    flow_path = root / "workflows" / "sprint-030-delivery-flow.yaml"
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
    gate_present = "scripts/ops/sprint030_validate.py" in content
    artifact_present = "runtime/ci-artifacts/sprint-030-validation.json" in content
    ok = gate_present and artifact_present

    hint_parts: list[str] = []
    if not gate_present:
        hint_parts.append("add sprint validator command")
    if not artifact_present:
        hint_parts.append("add sprint artifact path")

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
            "CTOA: Sprint-030 Validate",
            "CTOA: Sprint-030 Wave-1 Run",
        ]
    )

    return {
        "id": "local_tasks",
        "ok": labels_present,
        "hint": "Add sprint validate and wave-1 tasks" if not labels_present else "",
    }


def validate(root: Path) -> dict:
    checks: list[dict] = []
    for rel in REQUIRED_FILES:
        checks.append(check_file_exists(root, rel))
    checks.extend(check_yaml_syntax(root))
    checks.append(check_missing_hooks(root))
    checks.append(check_pipeline_gate(root))
    checks.append(check_local_tasks(root))

    passed = sum(1 for c in checks if c.get("ok", False))
    total = len(checks)

    return {
        "status": "PASS" if passed == total else "FAIL",
        "summary": f"{passed}/{total} checks passed",
        "checks": checks,
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Sprint-030 validator")
    parser.add_argument("--root", default=".", help="Workspace root directory")
    parser.add_argument("--json-out", help="Write JSON report to file")
    parser.add_argument("--run-tests", action="store_true", help="Run checks")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Root directory not found: {root}")

    report = validate(root)

    if args.json_out:
        out_path = root / args.json_out
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"[sprint030_validate] Report written to {out_path}")

    print(f"[sprint030_validate] {report['status']} — {report['summary']}")
    for chk in report["checks"]:
        mark = "OK" if chk.get("ok") else "FAIL"
        hint = f"  hint: {chk['hint']}" if chk.get("hint") else ""
        print(f"  [{mark}] {chk['id']}{hint}")

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
