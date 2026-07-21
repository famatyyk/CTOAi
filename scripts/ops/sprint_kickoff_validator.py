"""Shared checks for the Sprint-066+ kickoff validator CLI contracts.

The individual sprint modules intentionally remain thin entry points.  They
own their sprint-specific task ids and CLI name, while this module owns the
common file, workflow, and evidence checks.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

import yaml

Check = dict[str, Any]
QualityCheck = Callable[[bool], Check]


class ProcessSafety(Protocol):
    """The small subprocess surface used by the optional regression check."""

    @staticmethod
    def resolve_python() -> str: ...

    @staticmethod
    def run_trusted(command: list[str], **kwargs: Any) -> Any: ...


@dataclass(frozen=True, slots=True)
class SprintKickoffConfig:
    """Static contract for a sprint kickoff validator."""

    sprint_id: str
    task_ids: tuple[str, ...]
    focus_terms: tuple[str, ...] = ()

    @property
    def sprint_name(self) -> str:
        return f"sprint-{self.sprint_id}"

    @property
    def sprint_title(self) -> str:
        return f"Sprint-{self.sprint_id}"

    @property
    def sprint_document_title(self) -> str:
        return f"SPRINT-{self.sprint_id}"

    @property
    def required_files(self) -> tuple[str, ...]:
        return (
            f"workflows/backlog-{self.sprint_name}.yaml",
            f"workflows/{self.sprint_name}-delivery-flow.yaml",
            f"docs/history/sprints/{self.sprint_document_title}.md",
            f"docs/history/sprints/{self.sprint_document_title}-PROGRESS.md",
        )

    @property
    def yaml_files(self) -> tuple[str, str]:
        return self.required_files[:2]

    @property
    def required_task_labels(self) -> tuple[str, ...]:
        return (
            f"CTOA: {self.sprint_title} Validate",
            f"CTOA: {self.sprint_title} State Sync",
            f"CTOA: {self.sprint_title} Refresh Progress Diagram",
            f"CTOA: {self.sprint_title} Wave Summary UTF-8",
            f"CTOA: {self.sprint_title} Quality Snapshot",
            f"CTOA: {self.sprint_title} Wave-1 Run",
        )

    @property
    def required_workflow_snippets(self) -> tuple[str, ...]:
        return (
            f"{self.sprint_title} delivery gate",
            f"scripts/ops/sprint{self.sprint_id}_validate.py --run-tests --json-out "
            f"runtime/ci-artifacts/{self.sprint_name}-validation.json",
            f"Upload {self.sprint_title} evidence",
            f"runtime/ci-artifacts/{self.sprint_name}-validation.json",
            f"runtime/ci-artifacts/{self.sprint_name}-wave1-summary.txt",
            f"docs/history/sprints/{self.sprint_document_title}-PROGRESS.md",
        )


def safe_yaml_load(path: Path) -> Any:
    """Load YAML with one encoding policy for all kickoff validators."""
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def check_quality_regression(
    run_tests: bool,
    *,
    process_safety: ProcessSafety,
    path_factory: Callable[[str], Path] = Path,
) -> Check:
    """Check the common response-guardrail regression test on demand."""
    test_file = "tests/test_response_guardrails.py"
    if not run_tests:
        exists = path_factory(test_file).exists()
        return {
            "id": "quality_regression_tests",
            "ok": exists,
            "hint": "" if exists else f"missing {test_file}",
        }

    proc = process_safety.run_trusted(
        [process_safety.resolve_python(), "-m", "pytest", test_file, "-q"],
        capture_output=True,
        text=True,
    )
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)
    return {
        "id": "quality_regression_tests",
        "ok": proc.returncode == 0,
        "hint": "" if proc.returncode == 0 else f"pytest {test_file} -q failed",
    }


def _file_check(root: Path, config: SprintKickoffConfig) -> Check:
    missing = [rel for rel in config.required_files if not (root / rel).exists()]
    return {
        "id": "required_files",
        "ok": not missing,
        "hint": "" if not missing else f"missing files: {', '.join(missing)}",
    }


def _syntax_checks(root: Path, config: SprintKickoffConfig) -> list[Check]:
    checks: list[Check] = []
    for rel_path in config.yaml_files:
        try:
            safe_yaml_load(root / rel_path)
        except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
            checks.append({"id": f"syntax:{rel_path}", "ok": False, "hint": str(exc)})
        else:
            checks.append({"id": f"syntax:{rel_path}", "ok": True, "hint": ""})
    return checks


def _load_mapping(path: Path) -> tuple[dict[str, Any] | None, str]:
    try:
        payload = safe_yaml_load(path)
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        return None, str(exc)
    if not isinstance(payload, dict):
        return None, "YAML document must be a mapping"
    return payload, ""


def _backlog_contract_check(root: Path, config: SprintKickoffConfig) -> Check:
    backlog, error = _load_mapping(root / config.yaml_files[0])
    if backlog is None:
        return {"id": "backlog_contract", "ok": False, "hint": error}
    tasks = backlog.get("tasks", [])
    task_ids = [task.get("id") for task in tasks if isinstance(task, dict)] if isinstance(tasks, list) else []
    ok = backlog.get("backlog_id") == config.sprint_name and task_ids == list(config.task_ids)
    task_list = "/".join(task_id.removeprefix("CTOA-") for task_id in config.task_ids)
    return {
        "id": "backlog_contract",
        "ok": ok,
        "hint": "" if ok else f"backlog_id must be {config.sprint_name} and tasks must remain CTOA-{task_list} in order",
    }


def _hook_check(root: Path, config: SprintKickoffConfig) -> Check:
    flow, error = _load_mapping(root / config.yaml_files[1])
    if flow is None:
        return {"id": "missing_hooks", "ok": False, "hint": error}
    tasks = flow.get("tasks", [])
    if not isinstance(tasks, list):
        return {"id": "missing_hooks", "ok": False, "hint": "tasks must be a list"}
    required_hooks = {"on_start", "on_complete", "on_fail"}
    missing = [
        str(task.get("id", "<unknown>"))
        for task in tasks
        if not isinstance(task, dict) or not required_hooks.issubset(task)
    ]
    return {
        "id": "missing_hooks",
        "ok": not missing,
        "hint": "" if not missing else f"tasks missing hooks: {', '.join(missing)}",
    }


def _contains_check(root: Path, rel_path: str, required: tuple[str, ...], check_id: str, subject: str) -> Check:
    try:
        content = (root / rel_path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return {"id": check_id, "ok": False, "hint": f"cannot read {subject}: {exc}"}
    missing = [item for item in required if item not in content]
    return {
        "id": check_id,
        "ok": not missing,
        "hint": "" if not missing else f"missing {subject}: {', '.join(missing)}",
    }


def _pipeline_check(root: Path, config: SprintKickoffConfig) -> Check:
    return _contains_check(
        root,
        ".github/workflows/ctoa-pipeline.yml",
        config.required_workflow_snippets,
        "pipeline_gate",
        "workflow snippets",
    )


def _local_tasks_check(root: Path, config: SprintKickoffConfig) -> Check:
    return _contains_check(
        root,
        ".vscode/tasks.json",
        config.required_task_labels,
        "local_tasks",
        "task labels",
    )


def _plan_scope_check(root: Path, config: SprintKickoffConfig) -> Check | None:
    if not config.focus_terms:
        return None
    backlog, error = _load_mapping(root / config.yaml_files[0])
    if backlog is None:
        return {"id": "plan_scope", "ok": False, "hint": error}
    focus = backlog.get("focus", "")
    ok = isinstance(focus, str) and all(term in focus for term in config.focus_terms)
    terms = " + ".join(config.focus_terms)
    return {
        "id": "plan_scope",
        "ok": ok,
        "hint": "" if ok else f"focus should describe {terms}",
    }


def _state_evidence_check(root: Path, config: SprintKickoffConfig) -> Check:
    backlog, error = _load_mapping(root / config.yaml_files[0])
    progress = root / config.required_files[3]
    mission = root / config.required_files[2]
    ok = backlog is not None and backlog.get("backlog_id") == config.sprint_name and progress.exists() and mission.exists()
    return {
        "id": "state_evidence_alignment",
        "ok": ok,
        "hint": "" if ok else error or f"backlog and sprint evidence must all point at {config.sprint_name}",
    }


def _progress_alignment_check(root: Path, config: SprintKickoffConfig) -> Check | None:
    if not config.focus_terms:
        return None
    try:
        normalized = (root / config.required_files[3]).read_text(encoding="utf-8").replace("\\\\", "/")
    except (OSError, UnicodeDecodeError) as exc:
        return {"id": "progress_alignment", "ok": False, "hint": str(exc)}
    source = f"workflows/backlog-{config.sprint_name}.yaml"
    source_ok = f"Source: {source}" in normalized or ("Source: " in normalized and f"/{source}" in normalized)
    ok = f"Backlog: {config.sprint_name}" in normalized and source_ok
    return {
        "id": "progress_alignment",
        "ok": ok,
        "hint": "" if ok else f"progress doc must point at {config.sprint_name} backlog source",
    }


def build_kickoff_report(root: Path, config: SprintKickoffConfig, quality_check: QualityCheck, run_tests: bool) -> dict[str, Any]:
    """Build the stable report shape consumed by CI and local VS Code tasks."""
    checks: list[Check] = [_file_check(root, config), *_syntax_checks(root, config), _backlog_contract_check(root, config), _hook_check(root, config), _pipeline_check(root, config), _local_tasks_check(root, config)]
    for optional_check in (_plan_scope_check(root, config), _state_evidence_check(root, config), _progress_alignment_check(root, config)):
        if optional_check is not None:
            checks.append(optional_check)
    checks.append(quality_check(run_tests))

    failed = [str(check["id"]) for check in checks if not check.get("ok")]
    return {
        "status": "PASS" if not failed else "FAIL",
        "summary": f"{len(checks) - len(failed)}/{len(checks)} checks passed",
        "checks": checks,
        "diagnostics": {
            "failed_count": len(failed),
            "failed_ids": failed,
            "critical_failed_ids": [],
        },
    }
