import importlib.util
from pathlib import Path


def _load_sprint042_validate_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "ops" / "sprint042_validate.py"
    spec = importlib.util.spec_from_file_location("sprint042_validate", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sprint042_validate_passes_on_repo_root_without_focused_regressions():
    sprint042_validate = _load_sprint042_validate_module()
    root = Path(__file__).resolve().parents[1]

    report = sprint042_validate.validate(root, run_tests=False)

    assert report["status"] == "PASS"
    assert report["summary"].endswith("checks passed")
    assert all(check["ok"] for check in report["checks"])


def test_sprint042_validate_reports_expected_base_check_ids():
    sprint042_validate = _load_sprint042_validate_module()
    root = Path(__file__).resolve().parents[1]

    report = sprint042_validate.validate(root, run_tests=False)
    check_ids = {check["id"] for check in report["checks"]}

    required_ids = {
        "file:workflows/backlog-sprint-042.yaml",
        "file:workflows/sprint-042-delivery-flow.yaml",
        "file:scripts/ops/sprint042_validate.py",
        "file:.vscode/tasks.json",
        "file:.github/workflows/ctoa-pipeline.yml",
        "syntax:workflows/backlog-sprint-042.yaml",
        "syntax:workflows/sprint-042-delivery-flow.yaml",
        "missing_hooks",
        "pipeline_gate",
        "local_tasks",
    }

    assert required_ids.issubset(check_ids)


def test_sprint042_validate_run_tests_adds_quality_regression_check(monkeypatch):
    sprint042_validate = _load_sprint042_validate_module()
    root = Path(__file__).resolve().parents[1]

    def fake_run(_cmd: list[str], cwd: Path):
        return 0, "2 passed in 0.12s\n"

    monkeypatch.setattr(sprint042_validate, "_run", fake_run)

    report = sprint042_validate.validate(root, run_tests=True)
    check_map = {check["id"]: check for check in report["checks"]}

    assert report["status"] == "PASS"
    assert "quality_regression_tests" in check_map
    assert check_map["quality_regression_tests"]["ok"] is True
    diagnostics = report.get("diagnostics", {})
    assert diagnostics.get("failed_count") == 0
    assert diagnostics.get("failed_ids") == []
