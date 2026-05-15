import importlib.util
from pathlib import Path

import pytest


def _load_runner_module(module_name: str):
    module_path = Path(__file__).resolve().parents[1] / "runner" / "runner.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _single_task_backlog(backlog_id: str = "sprint-044") -> dict:
    return {
        "backlog_id": backlog_id,
        "rules": {"max_parallel_tasks": 1},
        "tasks": [
            {
                "id": "CTOA-224",
                "title": "Control tick and backlog parsing regression shield",
                "priority": "P1",
                "type": "quality",
                "domain": ["qa", "tests", "runner"],
                "assignees": ["code-smith", "qa-terminator"],
                "deliverables": [
                    "tests/test_runner_backlog_selection.py",
                    "tests/test_sprint044_control_tick.py",
                    "runtime/ci-artifacts/sprint-044-regression.json",
                ],
            }
        ],
    }


def test_control_tick_reaches_waiting_approval_in_expected_cycles(monkeypatch):
    monkeypatch.delenv("CTOA_BACKLOG_FILE", raising=False)
    runner = _load_runner_module("runner_control_tick_waiting_approval")

    backlog = _single_task_backlog()
    state = runner.init_state(backlog)

    for _ in range(5):
        state = runner.tick(backlog, state, invoke_agents=False)

    task = state["tasks"][0]
    assert task["status"] == "WAITING_APPROVAL"


def test_manual_approval_releases_task_after_waiting_approval(monkeypatch):
    monkeypatch.delenv("CTOA_BACKLOG_FILE", raising=False)
    runner = _load_runner_module("runner_manual_approval_release")

    backlog = _single_task_backlog()
    state = runner.init_state(backlog)

    for _ in range(5):
        state = runner.tick(backlog, state, invoke_agents=False)

    state = runner.approve_task(state, "CTOA-224")
    task = state["tasks"][0]
    assert task["status"] == "RELEASED"


def test_manual_approval_rejects_task_not_waiting(monkeypatch):
    monkeypatch.delenv("CTOA_BACKLOG_FILE", raising=False)
    runner = _load_runner_module("runner_manual_approval_reject")

    backlog = _single_task_backlog()
    state = runner.init_state(backlog)

    with pytest.raises(ValueError, match="not in WAITING_APPROVAL"):
        runner.approve_task(state, "CTOA-224")


def test_load_state_resets_when_backlog_id_changes(monkeypatch, tmp_path):
    monkeypatch.delenv("CTOA_BACKLOG_FILE", raising=False)
    runner = _load_runner_module("runner_backlog_id_reset")

    state_file = tmp_path / "task-state.yaml"
    monkeypatch.setattr(runner, "STATE_FILE", state_file)

    backlog_a = _single_task_backlog("sprint-044-a")
    backlog_b = _single_task_backlog("sprint-044-b")

    state_a = runner.init_state(backlog_a)
    state_a["tasks"][0]["status"] = "IN_PROGRESS"
    runner.save_yaml(state_file, state_a)

    loaded = runner.load_state(backlog_b)

    assert loaded["backlog_id"] == "sprint-044-b"
    assert loaded["tasks"][0]["status"] == "NEW"
