"""Generate a markdown progress diagram for a selected backlog."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

STATUS_FLOW = [
    "NEW",
    "IN_PROGRESS",
    "IN_QA",
    "IN_CI_GATE",
    "WAITING_APPROVAL",
    "RELEASED",
    "BLOCKED",
]


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Invalid YAML object in {path}")
    return data


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _state_by_task_id(state: dict[str, Any], backlog_id: str) -> dict[str, str]:
    if state.get("backlog_id") != backlog_id:
        return {}

    status_by_id: dict[str, str] = {}
    for task in state.get("tasks", []):
        if not isinstance(task, dict):
            continue
        task_id = str(task.get("id", "")).strip()
        status = str(task.get("status", "NEW")).strip()
        if not task_id:
            continue
        status_by_id[task_id] = status if status in STATUS_FLOW else "NEW"
    return status_by_id


def _percent(value: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((value / total) * 100.0, 1)


def _render_markdown(
    *,
    project_name: str,
    backlog_path: Path,
    backlog_id: str,
    state_path: Path | None,
    output_path: Path,
    total: int,
    counts: Counter,
    generated_at: str,
) -> str:
    released = counts.get("RELEASED", 0)
    in_flight = (
        counts.get("IN_PROGRESS", 0)
        + counts.get("IN_QA", 0)
        + counts.get("IN_CI_GATE", 0)
        + counts.get("WAITING_APPROVAL", 0)
    )
    new_count = counts.get("NEW", 0)
    blocked = counts.get("BLOCKED", 0)

    released_pct = _percent(released, total)
    in_flight_pct = _percent(in_flight, total)
    new_pct = _percent(new_count, total)
    blocked_pct = _percent(blocked, total)

    lines = [
        f"# Project Progress Diagram - {project_name}",
        "",
        f"Generated: {generated_at}",
        f"Backlog: {backlog_id}",
        f"Source: {backlog_path.as_posix()}",
        f"Completion: {released_pct:.1f}% ({released}/{total} RELEASED)",
        "",
        "```mermaid",
        "pie showData",
        f"    title {project_name} Progress Breakdown",
        f"    \"RELEASED\" : {released_pct:.1f}",
        f"    \"IN_FLIGHT\" : {in_flight_pct:.1f}",
        f"    \"NEW\" : {new_pct:.1f}",
        f"    \"BLOCKED\" : {blocked_pct:.1f}",
        "```",
        "",
        "## Status Split",
        "",
        "| Bucket | Tasks | Percent |",
        "|---|---|---|",
        f"| RELEASED | {released} | {released_pct:.1f}% |",
        f"| IN_FLIGHT | {in_flight} | {in_flight_pct:.1f}% |",
        f"| NEW | {new_count} | {new_pct:.1f}% |",
        f"| BLOCKED | {blocked} | {blocked_pct:.1f}% |",
        "",
        "## Raw Status Counts",
        "",
    ]

    for status in STATUS_FLOW:
        lines.append(f"- {status}: {counts.get(status, 0)}")

    lines.extend(
        [
            "",
            "## Refresh Command",
            "",
            "```bash",
            f"python scripts/ops/project_progress_diagram.py --backlog {backlog_path.as_posix()} --state {(state_path.as_posix() if state_path else 'runtime/task-state.yaml')} --output {output_path.as_posix()} --project-name {project_name}",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def generate(backlog_path: Path, state_path: Path | None, output_path: Path, project_name: str) -> dict[str, Any]:
    backlog = _load_yaml(backlog_path)
    backlog_id = str(backlog.get("backlog_id", "unknown"))

    backlog_tasks = backlog.get("tasks", [])
    if not isinstance(backlog_tasks, list):
        raise ValueError("Invalid backlog format: tasks must be a list")

    state: dict[str, Any] = {}
    if state_path is not None and state_path.exists():
        state = _load_yaml(state_path)

    status_map = _state_by_task_id(state, backlog_id)

    statuses: list[str] = []
    for task in backlog_tasks:
        if not isinstance(task, dict):
            continue
        task_id = str(task.get("id", "")).strip()
        if not task_id:
            continue
        statuses.append(status_map.get(task_id, "NEW"))

    counts: Counter = Counter(statuses)
    total = len(statuses)
    generated_at = _now_iso()

    markdown = _render_markdown(
        project_name=project_name,
        backlog_path=backlog_path,
        backlog_id=backlog_id,
        state_path=state_path,
        output_path=output_path,
        total=total,
        counts=counts,
        generated_at=generated_at,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")

    return {
        "project_name": project_name,
        "backlog_id": backlog_id,
        "total": total,
        "released": counts.get("RELEASED", 0),
        "generated_at": generated_at,
        "output": output_path.as_posix(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate project progress markdown diagram")
    parser.add_argument("--backlog", required=True, help="Path to backlog YAML")
    parser.add_argument("--state", default="runtime/task-state.yaml", help="Path to runtime task-state YAML")
    parser.add_argument("--output", required=True, help="Path to output markdown file")
    parser.add_argument("--project-name", default="Project", help="Display name in report")
    args = parser.parse_args()

    backlog_path = Path(args.backlog).resolve()
    if not backlog_path.exists():
        raise FileNotFoundError(f"Missing backlog file: {backlog_path}")

    state_arg = str(args.state).strip()
    state_path = Path(state_arg).resolve() if state_arg else None
    output_path = Path(args.output).resolve()

    report = generate(
        backlog_path=backlog_path,
        state_path=state_path,
        output_path=output_path,
        project_name=args.project_name,
    )

    print(
        "[project_progress_diagram] "
        f"{report['project_name']} backlog={report['backlog_id']} "
        f"completion={_percent(report['released'], report['total']):.1f}% "
        f"output={report['output']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())