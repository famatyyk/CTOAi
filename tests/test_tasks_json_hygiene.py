import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _task_labels() -> list[str]:
    text = (PROJECT_ROOT / ".vscode" / "tasks.json").read_text(encoding="utf-8")
    return [match.group(1) for match in re.finditer(r'"label": "([^"]+)"', text)]


def test_tasks_json_keeps_current_sprint_and_shared_operators():
    labels = set(_task_labels())

    assert "CTOA: Sprint-070 Validate Cleanup Contract" in labels
    assert "CTOA: Run All Tests" in labels
    assert "CTOA: Repo Hygiene Audit" in labels
    assert "CTOA: VPS Dashboard Snapshot" in labels


def test_tasks_json_drops_ad_hoc_probe_labels():
    labels = set(_task_labels())

    assert "Copilot Probe GH" not in labels
    assert "GH Run 267039 status" not in labels
    assert "Runtime Validation Auth Community Temp Script" not in labels
    assert "CTOA: Final Freeze" not in labels
    assert "tmp-show-pwd" not in labels
