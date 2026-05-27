import importlib.util
import json
from pathlib import Path


def _load_runner_module(module_name: str):
    module_path = Path(__file__).resolve().parents[1] / "runner" / "runner.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_execution_summary_counts_and_eta():
    runner = _load_runner_module("runner_execution_summary_counts")

    backlog = {"backlog_id": "sprint-ctoa-315"}
    state = {
        "last_tick_at": "2026-05-25T03:40:00Z",
        "tasks": [
            {"id": "CTOA-1", "status": "IN_PROGRESS"},
            {"id": "CTOA-2", "status": "IN_CI_GATE"},
            {"id": "CTOA-3", "status": "RELEASED"},
        ],
    }

    summary = runner.build_execution_summary(backlog, state)

    assert summary["schema_version"] == "ctoa.execution_summary.v1"
    assert summary["backlog_id"] == "sprint-ctoa-315"
    assert summary["total_tasks"] == 3
    assert summary["released_count"] == 1
    assert summary["active_count"] == 2
    assert summary["waiting_approval_count"] == 0
    assert summary["blocked_count"] == 0
    assert summary["operator_status"] == "in_progress"
    assert summary["next_approval_eta_hours"] == 1
    assert summary["status_counts"]["IN_CI_GATE"] == 1
    assert summary["status_counts"]["RELEASED"] == 1


def test_build_execution_summary_blocked_has_priority_over_other_states():
    runner = _load_runner_module("runner_execution_summary_blocked")

    backlog = {"backlog_id": "sprint-ctoa-315"}
    state = {
        "last_tick_at": "2026-05-25T03:40:00Z",
        "tasks": [
            {"id": "CTOA-1", "status": "WAITING_APPROVAL"},
            {"id": "CTOA-2", "status": "BLOCKED"},
        ],
    }

    summary = runner.build_execution_summary(backlog, state)

    assert summary["operator_status"] == "needs_attention"
    assert summary["next_approval_eta_hours"] == 0


def test_build_report_includes_normalized_execution_summary_section():
    runner = _load_runner_module("runner_execution_summary_report")

    backlog = {"backlog_id": "sprint-ctoa-315"}
    state = {
        "last_tick_at": "2026-05-25T03:40:00Z",
        "tasks": [
            {"id": "CTOA-1", "status": "RELEASED", "priority": "P1", "assignees": []},
        ],
    }

    report = runner.build_report(backlog, state)

    assert "## Execution Summary (Normalized)" in report
    assert "- schema_version: ctoa.execution_summary.v1" in report
    assert "- operator_status: released" in report

def test_report_command_writes_execution_summary_artifact(tmp_path, monkeypatch, capsys):
    backlog_file = tmp_path / "backlog.yaml"
    backlog_file.write_text(
        """backlog_id: sprint-ctoa-315
rules:
  max_parallel_tasks: 1
tasks:
  - id: CTOA-1
    title: Example
    priority: P1
    assignees: []
    status: NEW
""",
        encoding="utf-8",
    )

    monkeypatch.setenv("CTOA_BACKLOG_FILE", str(backlog_file))
    runner = _load_runner_module("runner_execution_summary_artifact")

    runner.STATE_FILE = tmp_path / "task-state.yaml"
    artifact_path = tmp_path / "ci-artifacts" / "runner-execution-summary.json"
    runner.EXECUTION_SUMMARY_ARTIFACT = artifact_path

    import sys

    monkeypatch.setattr(sys, "argv", ["runner.py", "report"])
    runner.main()

    captured = capsys.readouterr().out
    assert "[report-summary]" in captured
    assert artifact_path.exists()

    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "ctoa.execution_summary.v1"
    assert payload["backlog_id"] == "sprint-ctoa-315"
    assert "status_counts" in payload
    assert isinstance(payload["status_counts"], dict)
