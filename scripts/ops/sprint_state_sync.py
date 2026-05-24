"""Synchronize sprint runtime state after Wave-1 execution."""

from __future__ import annotations

import argparse
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Invalid YAML object in {path}")
    return data


def _save_yaml_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(payload, fh, sort_keys=False, allow_unicode=False)
        fh.flush()
        os.fsync(fh.fileno())
    tmp.replace(path)


def _init_state_from_backlog(backlog: dict[str, Any]) -> dict[str, Any]:
    tasks = backlog.get("tasks") or []
    state_tasks: list[dict[str, Any]] = []
    for task in tasks:
        if not isinstance(task, dict):
            continue
        state_tasks.append(
            {
                "id": task.get("id"),
                "title": task.get("title", ""),
                "priority": task.get("priority", "P1"),
                "type": task.get("type", "code"),
                "domain": task.get("domain", []),
                "assignees": task.get("assignees", []),
                "deliverables": task.get("deliverables", []),
                "status": "NEW",
                "ticks_in_status": 0,
                "updated_at": _now_iso(),
                "notes": [],
            }
        )

    return {
        "backlog_id": backlog.get("backlog_id", "unknown"),
        "last_tick_at": None,
        "tasks": state_tasks,
        "history": [],
    }


def synchronize_state(backlog_path: Path, state_path: Path, reason: str) -> tuple[int, int, str]:
    backlog = _load_yaml(backlog_path)
    if not backlog:
        raise FileNotFoundError(f"Missing or empty backlog: {backlog_path}")

    backlog_id = str(backlog.get("backlog_id", "unknown"))
    backlog_tasks = backlog.get("tasks") or []
    total_tasks = len([t for t in backlog_tasks if isinstance(t, dict)])

    state = _load_yaml(state_path)
    if not state or state.get("backlog_id") != backlog_id:
        state = _init_state_from_backlog(backlog)

    by_id = {
        str(task.get("id")): task
        for task in state.get("tasks", [])
        if isinstance(task, dict) and task.get("id") is not None
    }

    released = 0
    for backlog_task in backlog_tasks:
        if not isinstance(backlog_task, dict):
            continue
        task_id = str(backlog_task.get("id"))
        task = by_id.get(task_id)
        if task is None:
            task = {
                "id": backlog_task.get("id"),
                "title": backlog_task.get("title", ""),
                "priority": backlog_task.get("priority", "P1"),
                "type": backlog_task.get("type", "code"),
                "domain": backlog_task.get("domain", []),
                "assignees": backlog_task.get("assignees", []),
                "deliverables": backlog_task.get("deliverables", []),
                "status": "NEW",
                "ticks_in_status": 0,
                "updated_at": _now_iso(),
                "notes": [],
            }
            state.setdefault("tasks", []).append(task)
            by_id[task_id] = task

        task["status"] = "RELEASED"
        task["ticks_in_status"] = 0
        task["updated_at"] = _now_iso()
        task.setdefault("notes", []).append(
            {"at": _now_iso(), "reason": reason, "status": "RELEASED"}
        )
        released += 1

    state["backlog_id"] = backlog_id
    state["last_tick_at"] = _now_iso()
    state.setdefault("history", []).append(
        {
            "at": _now_iso(),
            "event": "sprint_state_sync",
            "backlog_id": backlog_id,
            "released_count": released,
            "total_tasks": total_tasks,
            "reason": reason,
        }
    )

    _save_yaml_atomic(state_path, state)
    return released, total_tasks, backlog_id


def main() -> int:
    parser = argparse.ArgumentParser(description="Synchronize sprint runtime state to RELEASED")
    parser.add_argument(
        "--backlog",
        default="workflows/backlog-sprint-052.yaml",
        help="Path to sprint backlog yaml",
    )
    parser.add_argument(
        "--state",
        default="runtime/task-state.yaml",
        help="Path to runtime task-state yaml",
    )
    parser.add_argument(
        "--reason",
        default="automatic post-wave1 state synchronization",
        help="Reason stored in task notes/history",
    )
    args = parser.parse_args()

    backlog_path = (ROOT / args.backlog).resolve()
    state_path = (ROOT / args.state).resolve()

    released, total, backlog_id = synchronize_state(backlog_path, state_path, args.reason)
    print(
        f"[sprint_state_sync] backlog={backlog_id} released={released}/{total} state={state_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
