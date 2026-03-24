from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / "workflows"
EXPERIMENTS = ROOT / "runtime" / "experiments"
SCRIPTS_OPS = ROOT / "scripts" / "ops"
TASKS_FILE = ROOT / ".vscode" / "tasks.json"
PIPELINE_FILE = ROOT / ".github" / "workflows" / "ctoa-pipeline.yml"

START_SPRINT = 29
END_SPRINT = 40
START_CTOA_ID = 143


@dataclass
class SprintWindow:
    sprint: int
    task_ids: list[int]


def _sprint_label(sprint: int) -> str:
    return f"{sprint:03d}"


def _sprint_dir_name(sprint: int) -> str:
    return f"sprint-{_sprint_label(sprint)}"


def _backlog_path(sprint: int) -> Path:
    return WORKFLOWS / f"backlog-sprint-{_sprint_label(sprint)}.yaml"


def _flow_path(sprint: int) -> Path:
    return WORKFLOWS / f"sprint-{_sprint_label(sprint)}-delivery-flow.yaml"


def _validator_path(sprint: int) -> Path:
    return SCRIPTS_OPS / f"sprint{_sprint_label(sprint)}_validate.py"


def _experiments_dir(sprint: int) -> Path:
    return EXPERIMENTS / _sprint_dir_name(sprint)


def _window_for_sprint(sprint: int) -> SprintWindow:
    offset = sprint - START_SPRINT
    first_id = START_CTOA_ID + offset * 5
    return SprintWindow(sprint=sprint, task_ids=[first_id + i for i in range(5)])


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(payload, sort_keys=False, allow_unicode=False)
    path.write_text(text, encoding="utf-8")


def _build_backlog_payload(window: SprintWindow) -> dict:
    ctoa = window.task_ids
    return {
        "sprint": _sprint_label(window.sprint),
        "theme": "Continuous Quality + Delivery + Governance",
        "status": "PLANNING",
        "source_baseline": "v1.1.0-approved",
        "proposed_release": f"v1.{window.sprint - 27}.0",
        "items": [
            {
                "id": f"CTOA-{ctoa[0]}",
                "title": f"Sprint-{_sprint_label(window.sprint)} quality gate expansion",
                "type": "quality",
                "priority": "P1",
                "status": "READY_FOR_WAVE_1",
                "description": "Expand API and regression quality gates for current sprint scope.",
            },
            {
                "id": f"CTOA-{ctoa[1]}",
                "title": f"Sprint-{_sprint_label(window.sprint)} nightly trend automation",
                "type": "automation",
                "priority": "P1",
                "status": "READY_FOR_WAVE_1",
                "description": "Extend nightly trend evidence and verify drift visibility.",
            },
            {
                "id": f"CTOA-{ctoa[2]}",
                "title": f"Sprint-{_sprint_label(window.sprint)} dashboard ergonomics pass",
                "type": "ux",
                "priority": "P2",
                "status": "READY_FOR_WAVE_1",
                "description": "Improve operator dashboard readability in healthy and degraded modes.",
            },
            {
                "id": f"CTOA-{ctoa[3]}",
                "title": f"Sprint-{_sprint_label(window.sprint)} CI evidence hardening",
                "type": "governance",
                "priority": "P2",
                "status": "READY_FOR_WAVE_1",
                "description": "Ensure validator and nightly evidence remain fully discoverable in CI.",
            },
            {
                "id": f"CTOA-{ctoa[4]}",
                "title": f"Release pack v1.{window.sprint - 27}.0",
                "type": "governance",
                "priority": "P3",
                "status": "PENDING_WAVE_1",
                "description": "Consolidate sprint deliverables and release pack approvals.",
            },
        ],
        "slo_targets": {
            "success_rate_24h_threshold": 0.93,
            "error_budget_max_fails_per_window": 2,
            "nightly_artifact_max_age_hours": 25,
        },
    }


def _build_flow_payload(window: SprintWindow) -> dict:
    ctoa = [f"CTOA-{x}" for x in window.task_ids]
    return {
        "sprint": _sprint_label(window.sprint),
        "theme": "Continuous Quality + Delivery + Governance",
        "version": "1.0",
        "lifecycle": {
            "start": "2026-03-24",
            "target_wave1": "2026-03-27",
            "target_wave2": "2026-03-28",
        },
        "tasks": [
            {
                "id": ctoa[0],
                "title": "Quality gate expansion",
                "on_start": "read backlog scope and lock API contracts",
                "on_complete": "run focused tests and validator",
                "on_fail": "rollback sprint quality gate changes",
            },
            {
                "id": ctoa[1],
                "title": "Nightly trend automation",
                "depends_on": [ctoa[0]],
                "on_start": "review nightly artifact schema",
                "on_complete": "verify trend evidence and backward compatibility",
                "on_fail": "restore previous nightly artifact contract",
            },
            {
                "id": ctoa[2],
                "title": "Dashboard ergonomics pass",
                "depends_on": [ctoa[0]],
                "on_start": "review dashboard payload and rendering paths",
                "on_complete": "validate degraded-mode readability",
                "on_fail": "restore previous dashboard rendering",
            },
            {
                "id": ctoa[3],
                "title": "CI evidence hardening",
                "depends_on": [ctoa[0], ctoa[1]],
                "on_start": "inspect CI artifact publishing steps",
                "on_complete": "confirm evidence export in CI",
                "on_fail": "revert CI evidence changes",
            },
            {
                "id": ctoa[4],
                "title": "Release pack",
                "depends_on": [ctoa[0], ctoa[1], ctoa[2], ctoa[3]],
                "on_start": "confirm delivery status and evidence",
                "on_complete": "record wave_1 PASS and wave_2 sign-off",
                "on_fail": "hold release candidate and escalate",
            },
        ],
        "gate_policy": {
            "wave_1": "all automated checks pass",
            "wave_2": "manual STRATEGOS sign-off",
            "rollback_baseline": "v1.1.0-approved",
        },
    }


def _validator_code(sprint: int) -> str:
    sprint_label = _sprint_label(sprint)
    task_base = START_CTOA_ID + (sprint - START_SPRINT) * 5
    experiment_files = [
        f"runtime/experiments/sprint-{sprint_label}/CTOA-{task_base + i}.md" for i in range(5)
    ]
    required_files = [
        f"workflows/backlog-sprint-{sprint_label}.yaml",
        f"workflows/sprint-{sprint_label}-delivery-flow.yaml",
        f"scripts/ops/sprint{sprint_label}_validate.py",
        ".vscode/tasks.json",
        ".github/workflows/ctoa-pipeline.yml",
        *experiment_files,
    ]
    required_yaml = [
        f"workflows/backlog-sprint-{sprint_label}.yaml",
        f"workflows/sprint-{sprint_label}-delivery-flow.yaml",
    ]

    return f'''"""Sprint-{sprint_label} validator."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import yaml

REQUIRED_FILES = {required_files!r}
REQUIRED_YAML_FILES = {required_yaml!r}
REQUIRED_HOOKS = {{"on_start", "on_complete", "on_fail"}}


def _safe_yaml_load(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def check_file_exists(root: Path, rel_path: str) -> dict:
    ok = (root / rel_path).exists()
    return {{
        "id": f"file:{{rel_path}}",
        "ok": ok,
        "hint": "Create or restore missing sprint file" if not ok else "",
    }}


def check_yaml_syntax(root: Path) -> list[dict]:
    checks = []
    for rel in REQUIRED_YAML_FILES:
        path = root / rel
        if not path.exists():
            checks.append({{"id": f"syntax:{{rel}}", "ok": False, "hint": "File missing for syntax validation"}})
            continue
        try:
            _safe_yaml_load(path)
            checks.append({{"id": f"syntax:{{rel}}", "ok": True, "hint": ""}})
        except Exception as exc:
            checks.append({{"id": f"syntax:{{rel}}", "ok": False, "hint": f"YAML parse error: {{exc}}"}})
    return checks


def check_missing_hooks(root: Path) -> dict:
    flow_path = root / "workflows" / "sprint-{sprint_label}-delivery-flow.yaml"
    try:
        flow = _safe_yaml_load(flow_path)
    except Exception as exc:
        return {{"id": "missing_hooks", "ok": False, "hint": f"Cannot load flow YAML: {{exc}}"}}

    tasks = flow.get("tasks") or []
    missing: list[str] = []
    for task_def in tasks:
        task_id = task_def.get("id", "unknown")
        for req in REQUIRED_HOOKS:
            if req not in task_def or not task_def[req]:
                missing.append(f"{{task_id}}:{{req}}")

    return {{
        "id": "missing_hooks",
        "ok": len(missing) == 0,
        "hint": f"Missing hooks: {{', '.join(missing)}}" if missing else "",
    }}


def check_pipeline_gate(root: Path) -> dict:
    pipeline_path = root / ".github/workflows/ctoa-pipeline.yml"
    if not pipeline_path.exists():
        return {{"id": "pipeline_gate", "ok": False, "hint": "Pipeline file missing"}}

    content = pipeline_path.read_text(encoding="utf-8")
    gate_present = "scripts/ops/sprint{sprint_label}_validate.py" in content
    artifact_present = "runtime/ci-artifacts/sprint-{sprint_label}-validation.json" in content
    ok = gate_present and artifact_present

    hint_parts: list[str] = []
    if not gate_present:
        hint_parts.append("add sprint validator command")
    if not artifact_present:
        hint_parts.append("add sprint artifact path")

    return {{
        "id": "pipeline_gate",
        "ok": ok,
        "hint": "; ".join(hint_parts),
    }}


def check_local_tasks(root: Path) -> dict:
    tasks_path = root / ".vscode/tasks.json"
    if not tasks_path.exists():
        return {{"id": "local_tasks", "ok": False, "hint": "tasks.json missing"}}

    content = tasks_path.read_text(encoding="utf-8")
    labels_present = all(
        needle in content
        for needle in [
            "CTOA: Sprint-{sprint_label} Validate",
            "CTOA: Sprint-{sprint_label} Wave-1 Run",
        ]
    )

    return {{
        "id": "local_tasks",
        "ok": labels_present,
        "hint": "Add sprint validate and wave-1 tasks" if not labels_present else "",
    }}


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

    return {{
        "status": "PASS" if passed == total else "FAIL",
        "summary": f"{{passed}}/{{total}} checks passed",
        "checks": checks,
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }}


def main() -> int:
    parser = argparse.ArgumentParser(description="Sprint-{sprint_label} validator")
    parser.add_argument("--root", default=".", help="Workspace root directory")
    parser.add_argument("--json-out", help="Write JSON report to file")
    parser.add_argument("--run-tests", action="store_true", help="Run checks")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Root directory not found: {{root}}")

    report = validate(root)

    if args.json_out:
        out_path = root / args.json_out
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"[sprint{sprint_label}_validate] Report written to {{out_path}}")

    print(f"[sprint{sprint_label}_validate] {{report['status']}} — {{report['summary']}}")
    for chk in report["checks"]:
        mark = "OK" if chk.get("ok") else "FAIL"
        hint = f"  hint: {{chk['hint']}}" if chk.get("hint") else ""
        print(f"  [{{mark}}] {{chk['id']}}{{hint}}")

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
'''


def _write_experiment_md(path: Path, task_id: int, status: str, objective: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (
        f"# CTOA-{task_id}: {objective}\n\n"
        f"**Status:** {status}\n\n"
        "**Objective:**\n"
        f"{objective}.\n\n"
        "**Acceptance Criteria:**\n"
        "- [ ] Scope implemented\n"
        "- [ ] Focused tests PASS\n"
        "- [ ] Sprint validator PASS\n\n"
        "**Validation:**\n"
        "- Run focused tests for modified surfaces\n"
        "- Run sprint validator with --run-tests\n"
    )
    path.write_text(content, encoding="utf-8")


def _update_tasks_json() -> None:
    tasks_data = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
    tasks = tasks_data.get("tasks", [])
    existing_labels = {str(task.get("label", "")) for task in tasks if isinstance(task, dict)}

    for sprint in range(START_SPRINT, END_SPRINT + 1):
        label = _sprint_label(sprint)
        validate_label = f"CTOA: Sprint-{label} Validate"
        wave_label = f"CTOA: Sprint-{label} Wave-1 Run"
        if validate_label not in existing_labels:
            tasks.append(
                {
                    "label": validate_label,
                    "type": "shell",
                    "command": f".venv/Scripts/python.exe scripts/ops/sprint{label}_validate.py --run-tests --json-out runtime/ci-artifacts/sprint-{label}-validation.json",
                    "isBackground": False,
                    "presentation": {"reveal": "always", "panel": "dedicated"},
                }
            )
            existing_labels.add(validate_label)

        if wave_label not in existing_labels:
            tasks.append(
                {
                    "label": wave_label,
                    "dependsOrder": "sequence",
                    "dependsOn": [
                        "CTOA: Run All Tests",
                        validate_label,
                        "CTOA: Launch Pack",
                    ],
                    "isBackground": False,
                    "presentation": {"reveal": "always", "panel": "dedicated"},
                }
            )
            existing_labels.add(wave_label)

    tasks_data["tasks"] = tasks
    TASKS_FILE.write_text(json.dumps(tasks_data, indent=2), encoding="utf-8")


def _update_pipeline() -> None:
    text = PIPELINE_FILE.read_text(encoding="utf-8")
    marker = "      - name: Python linting (flake8)\n"
    if marker not in text:
        raise RuntimeError("Cannot locate pipeline insertion marker")

    steps_to_insert: list[str] = []
    for sprint in range(START_SPRINT, END_SPRINT + 1):
        label = _sprint_label(sprint)
        if f"scripts/ops/sprint{label}_validate.py" in text:
            continue
        steps_to_insert.append(
            "\n".join(
                [
                    f"      - name: Sprint-{label} delivery gate",
                    "        shell: bash",
                    "        run: |",
                    f"          python scripts/ops/sprint{label}_validate.py --run-tests --json-out runtime/ci-artifacts/sprint-{label}-validation.json",
                ]
            )
        )

    if not steps_to_insert:
        return

    insert_blob = "\n\n".join(steps_to_insert) + "\n\n"
    text = text.replace(marker, insert_blob + marker)
    PIPELINE_FILE.write_text(text, encoding="utf-8")


def bootstrap() -> None:
    for sprint in range(START_SPRINT, END_SPRINT + 1):
        window = _window_for_sprint(sprint)
        _write_yaml(_backlog_path(sprint), _build_backlog_payload(window))
        _write_yaml(_flow_path(sprint), _build_flow_payload(window))

        validator = _validator_code(sprint)
        _validator_path(sprint).write_text(validator, encoding="utf-8")

        ex_dir = _experiments_dir(sprint)
        objectives = [
            "Quality gate expansion",
            "Nightly trend automation",
            "Dashboard ergonomics pass",
            "CI evidence hardening",
            "Release pack",
        ]
        for idx, task_id in enumerate(window.task_ids):
            status = "IN_PROGRESS" if idx == 0 else ("PENDING_WAVE_1" if idx == 4 else "PLANNING")
            _write_experiment_md(
                ex_dir / f"CTOA-{task_id}.md",
                task_id=task_id,
                status=status,
                objective=objectives[idx],
            )

    _update_tasks_json()
    _update_pipeline()


def main() -> int:
    bootstrap()
    print("[bootstrap_sprints_029_040] DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
