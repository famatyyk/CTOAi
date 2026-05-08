from runner.pipeline.scheduler import build_new_task_candidates, count_active_tasks


def test_count_active_tasks_counts_only_selected_states():
    tasks = [
        {"id": "A", "status": "NEW"},
        {"id": "B", "status": "IN_PROGRESS"},
        {"id": "C", "status": "IN_QA"},
        {"id": "D", "status": "BLOCKED"},
    ]
    active_states = {"IN_PROGRESS", "IN_QA", "IN_CI_GATE", "WAITING_APPROVAL"}

    assert count_active_tasks(tasks, active_states) == 2


def test_build_new_task_candidates_sorts_by_priority_then_id():
    tasks = [
        {"id": "CTOA-210", "status": "NEW", "priority": "P2"},
        {"id": "CTOA-204", "status": "NEW", "priority": "P1"},
        {"id": "CTOA-200", "status": "IN_PROGRESS", "priority": "P0"},
        {"id": "CTOA-201", "status": "NEW", "priority": "P1"},
    ]

    def rank(priority: str) -> int:
        order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
        return order.get(priority, 9)

    result = build_new_task_candidates(tasks, rank)
    ids = [task["id"] for task in result]

    assert ids == ["CTOA-201", "CTOA-204", "CTOA-210"]
