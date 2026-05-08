from __future__ import annotations

from typing import Any, Callable, Dict, List, Set


def count_active_tasks(tasks: List[Dict[str, Any]], active_states: Set[str]) -> int:
    return sum(1 for task in tasks if task.get("status") in active_states)


def build_new_task_candidates(
    tasks: List[Dict[str, Any]],
    priority_rank: Callable[[str], int],
) -> List[Dict[str, Any]]:
    candidates = [task for task in tasks if task.get("status") == "NEW"]
    candidates.sort(key=lambda task: (priority_rank(str(task.get("priority", "P1"))), str(task.get("id", ""))))
    return candidates
