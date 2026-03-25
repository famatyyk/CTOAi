import importlib.util
from pathlib import Path


def _load_sprint029_validate_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "ops" / "sprint029_validate.py"
    spec = importlib.util.spec_from_file_location("sprint029_validate", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sprint029_validate_passes_on_repo_root():
    sprint029_validate = _load_sprint029_validate_module()
    root = Path(__file__).resolve().parents[1]

    report = sprint029_validate.validate(root)

    assert report["status"] == "PASS"
    assert report["summary"].endswith("checks passed")
    assert all(check["ok"] for check in report["checks"])


def test_sprint029_validate_reports_expected_check_ids():
    sprint029_validate = _load_sprint029_validate_module()
    root = Path(__file__).resolve().parents[1]

    report = sprint029_validate.validate(root)
    check_ids = {check["id"] for check in report["checks"]}

    required_ids = {
        "file:workflows/backlog-sprint-029.yaml",
        "file:workflows/sprint-029-delivery-flow.yaml",
        "file:scripts/ops/sprint029_validate.py",
        "file:.vscode/tasks.json",
        "file:.github/workflows/ctoa-pipeline.yml",
        "syntax:workflows/backlog-sprint-029.yaml",
        "syntax:workflows/sprint-029-delivery-flow.yaml",
        "missing_hooks",
        "pipeline_gate",
        "local_tasks",
    }

    assert required_ids.issubset(check_ids)
