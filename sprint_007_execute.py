#!/usr/bin/env python3
"""Sprint-007 autonomous executor.

Uses ASCII-only console output so it works on Windows terminals with legacy
code pages (for example cp1250).
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runner.agents import execute_agent_for_task


LOG_FILE = Path("logs/sprint-007-execution.log")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

SPRINT_007_TASKS: list[dict[str, Any]] = [
    {
        "id": "CTOA-031",
        "title": "Create disk emergency runbook",
        "domain": ["documentation", "ops"],
        "deliverables": ["docs/runbook-disk-emergency.md"],
    },
    {
        "id": "CTOA-032",
        "title": "Create validation checklist",
        "domain": ["documentation", "reliability"],
        "deliverables": ["docs/VALIDATION_CHECKLIST.md"],
    },
    {
        "id": "CTOA-033",
        "title": "Verify documentation consistency",
        "domain": ["documentation", "qa"],
        "deliverables": ["docs/CONSISTENCY_REPORT.md"],
    },
    {
        "id": "CTOA-035",
        "title": "Standardize weekly KPI report layout",
        "domain": ["kpi", "automation", "metrics"],
        "deliverables": ["runner/weekly_report.py"],
    },
    {
        "id": "CTOA-036",
        "title": "Integrate health trend with weekly pipeline",
        "domain": ["kpi", "automation", "reliability"],
        "deliverables": ["runner/health_trend.py"],
    },
    {
        "id": "CTOA-039",
        "title": "Implement service/timer drift detection",
        "domain": ["reliability", "guardrails", "automation"],
        "deliverables": ["runner/drift_checker.py"],
    },
    {
        "id": "CTOA-041",
        "title": "Formalize sprint governance framework",
        "domain": ["governance"],
        "deliverables": ["docs/SPRINT_GOVERNANCE.md"],
    },
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def log_event(event_type: str, data: dict[str, Any]) -> None:
    entry = {
        "timestamp": _now_iso(),
        "event": event_type,
        "data": data,
    }
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=True) + "\n")


def execute_all_tasks() -> int:
    print("\n" + "=" * 70)
    print("CTOA SPRINT-007 AUTONOMOUS AGENT EXECUTION")
    print(f"Started: {_now_iso()}")
    print("=" * 70 + "\n")

    log_event(
        "sprint_started",
        {
            "sprint": "007",
            "tasks": len(SPRINT_007_TASKS),
            "mode": "autonomous",
        },
    )

    completed = 0
    failed = 0

    for task in SPRINT_007_TASKS:
        print(f"\n[AGENT] Executing {task['id']}: {task['title']}")
        try:
            result = execute_agent_for_task(task)
            state = str(result.get("status", "pending")).lower()

            if state in {"completed", "created"}:
                completed += 1
                status_text = "[OK] COMPLETED"
            else:
                failed += 1
                status_text = f"[!!] {state.upper()}"

            deliverables = len(result.get("deliverables", []))
            print(f"{status_text} - {deliverables} deliverables")
            log_event("task_result", {"task_id": task["id"], "result": result})
        except Exception as exc:
            failed += 1
            print(f"[!!] FAILED: {exc}")
            log_event("task_failed", {"task_id": task["id"], "error": str(exc)})

        time.sleep(1)

    total = len(SPRINT_007_TASKS)
    progress_pct = int((completed / total) * 100) if total else 0

    print("\n" + "=" * 70)
    print("SPRINT-007 EXECUTION SUMMARY")
    print(f"Total Tasks: {total}")
    print(f"Completed: {completed}")
    print(f"Failed: {failed}")
    print(f"Progress: {completed}/{total} = {progress_pct}%")
    print(f"Finished: {_now_iso()}")
    print("=" * 70 + "\n")

    log_event(
        "sprint_completed",
        {
            "completed": completed,
            "failed": failed,
            "progress_pct": progress_pct,
        },
    )

    return 0 if failed == 0 else 1


def main() -> None:
    raise SystemExit(execute_all_tasks())


if __name__ == "__main__":
    main()
