"""Shared sprint validator engine for manifest-driven checks."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

import yaml

Check = dict[str, object]
QualityCheckFn = Callable[[Path, bool], Check | None]


@dataclass(slots=True)
class SprintValidatorConfig:
    sprint_id: str
    required_files: list[str]
    required_yaml_files: list[str]
    flow_file: str
    pipeline_file: str
    pipeline_validator_snippet: str
    pipeline_artifact_snippet: str
    required_task_labels: list[str]
    required_hooks: set[str] = field(default_factory=lambda: {"on_start", "on_complete", "on_fail"})
    quality_check: QualityCheckFn | None = None
    critical_checks: set[str] = field(default_factory=lambda: {"pipeline_gate", "missing_hooks", "quality_regression_tests"})


def safe_yaml_load(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def check_file_exists(root: Path, rel_path: str) -> Check:
    ok = (root / rel_path).exists()
    return {
        "id": f"file:{rel_path}",
        "ok": ok,
        "hint": "Create or restore missing sprint file" if not ok else "",
    }


def check_yaml_syntax(root: Path, yaml_files: list[str]) -> list[Check]:
    checks: list[Check] = []
    for rel in yaml_files:
        path = root / rel
        if not path.exists():
            checks.append({"id": f"syntax:{rel}", "ok": False, "hint": "File missing for syntax validation"})
            continue
        try:
            safe_yaml_load(path)
            checks.append({"id": f"syntax:{rel}", "ok": True, "hint": ""})
        except Exception as exc:  # pragma: no cover - syntax failures are data dependent
            checks.append({"id": f"syntax:{rel}", "ok": False, "hint": f"YAML parse error: {exc}"})
    return checks


def check_missing_hooks(root: Path, flow_file: str, required_hooks: set[str]) -> Check:
    flow_path = root / flow_file
    try:
        flow = safe_yaml_load(flow_path)
    except Exception as exc:
        return {"id": "missing_hooks", "ok": False, "hint": f"Cannot load flow YAML: {exc}"}

    tasks = flow.get("tasks") or []
    missing: list[str] = []
    for task_def in tasks:
        task_id = task_def.get("id", "unknown")
        for req in required_hooks:
            if req not in task_def or not task_def[req]:
                missing.append(f"{task_id}:{req}")

    return {
        "id": "missing_hooks",
        "ok": len(missing) == 0,
        "hint": f"Missing hooks: {', '.join(missing)}" if missing else "",
    }


def check_pipeline_gate(
    root: Path,
    pipeline_file: str,
    validator_snippet: str,
    artifact_snippet: str,
) -> Check:
    pipeline_path = root / pipeline_file
    if not pipeline_path.exists():
        return {"id": "pipeline_gate", "ok": False, "hint": "Pipeline file missing"}

    content = pipeline_path.read_text(encoding="utf-8")
    gate_present = validator_snippet in content
    artifact_present = artifact_snippet in content
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


def check_local_tasks(root: Path, required_task_labels: list[str]) -> Check:
    tasks_path = root / ".vscode/tasks.json"
    if not tasks_path.exists():
        return {"id": "local_tasks", "ok": False, "hint": "tasks.json missing"}

    content = tasks_path.read_text(encoding="utf-8")
    labels_present = all(label in content for label in required_task_labels)

    return {
        "id": "local_tasks",
        "ok": labels_present,
        "hint": "Add sprint validate and wave-1 tasks" if not labels_present else "",
    }


def collect_diagnostics(checks: list[Check], critical_checks: set[str]) -> dict[str, object]:
    failed = [chk for chk in checks if not chk.get("ok", False)]
    failed_ids = [str(chk.get("id")) for chk in failed]
    critical_failed = [chk_id for chk_id in failed_ids if chk_id in critical_checks]
    return {
        "failed_count": len(failed),
        "failed_ids": failed_ids,
        "critical_failed_ids": critical_failed,
    }


def build_report(root: Path, config: SprintValidatorConfig, run_tests: bool = False) -> dict[str, object]:
    checks: list[Check] = []
    for rel in config.required_files:
        checks.append(check_file_exists(root, rel))

    checks.extend(check_yaml_syntax(root, config.required_yaml_files))
    checks.append(check_missing_hooks(root, config.flow_file, config.required_hooks))
    checks.append(
        check_pipeline_gate(
            root,
            config.pipeline_file,
            config.pipeline_validator_snippet,
            config.pipeline_artifact_snippet,
        )
    )
    checks.append(check_local_tasks(root, config.required_task_labels))

    if config.quality_check:
        quality = config.quality_check(root, run_tests)
        if quality is not None:
            checks.append(quality)

    passed = sum(1 for c in checks if c.get("ok", False))
    total = len(checks)
    diagnostics = collect_diagnostics(checks, config.critical_checks)

    return {
        "status": "PASS" if passed == total else "FAIL",
        "summary": f"{passed}/{total} checks passed",
        "checks": checks,
        "diagnostics": diagnostics,
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }


def write_json_report(root: Path, json_out: str, report: dict[str, object]) -> Path:
    out_path = root / json_out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return out_path
