import importlib.util
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_module():
    module_path = PROJECT_ROOT / "scripts" / "ops" / "sprint070_validate.py"
    spec = importlib.util.spec_from_file_location("sprint070_validate", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_workspace(root: Path) -> None:
    (root / "docs/history/sprints").mkdir(parents=True, exist_ok=True)
    (root / ".vscode").mkdir(parents=True, exist_ok=True)

    (root / "docs/REPO_CLEANUP_WAVES.md").write_text(
        "# Repo Cleanup Waves\n\n## Wave 2 and Wave 3 Executed\n\n- Archive root: `_local_archive/sprint-070`\n",
        encoding="utf-8",
    )
    (root / "docs/history/sprints/SPRINT-070-PROGRESS.md").write_text(
        "# Project Progress Diagram - CTOAi\n\n## Status\n\n- Cleanup execution is complete and validated locally.\n- Repo hygiene audit currently reports no findings.\n\n## Cleanup Execution Completed\n\n- Cleanup contract: `docs/REPO_CLEANUP_WAVES.md`\n\n## Evidence\n\n- Validation report: `runtime/ci-artifacts/sprint-070-validation.json`\n- Repo hygiene audit: `runtime/ci-artifacts/repo-hygiene-audit.json`\n",
        encoding="utf-8",
    )
    (root / ".vscode/tasks.json").write_text(
        "\n".join(
            [
                "CTOA: Sprint-070 Local Archive Cleanup",
                "CTOA: Sprint-070 Cleanup Documentation Sync",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (root / ".github").mkdir(parents=True, exist_ok=True)
    (root / ".github/workflows").mkdir(parents=True, exist_ok=True)
    workflow_text = "\n".join(
        [
            "Sprint-070 cleanup contract check",
            "scripts/ops/sprint070_validate.py --run-tests --json-out runtime/ci-artifacts/sprint-070-validation.json",
        ]
    )
    (root / ".github/workflows/ctoa-pipeline.yml").write_text(workflow_text, encoding="utf-8")
    (root / ".github/workflows/pr_quality.yml").write_text(workflow_text, encoding="utf-8")
    (root / ".gitignore").write_text("_local_archive/\n", encoding="utf-8")
    (root / "tests").mkdir(parents=True, exist_ok=True)
    (root / "tests/test_repo_cleanup_waves_contract.py").write_text("def test_placeholder():\n    assert True\n", encoding="utf-8")


def test_sprint070_validator_passes_for_complete_workspace(tmp_path: Path, monkeypatch):
    module = _load_module()
    _write_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    report = module.build_report(tmp_path, run_tests=False)

    assert report["status"] == "PASS"
    assert report["summary"] == "6/6 checks passed"
    assert report["diagnostics"]["failed_ids"] == []


def test_sprint070_validator_flags_missing_task_wiring(tmp_path: Path, monkeypatch):
    module = _load_module()
    _write_workspace(tmp_path)
    (tmp_path / ".vscode/tasks.json").write_text("CTOA: Sprint-070 Local Archive Cleanup\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    report = module.build_report(tmp_path, run_tests=False)

    assert report["status"] == "FAIL"
    assert "task_wiring" in report["diagnostics"]["failed_ids"]


def test_sprint070_main_writes_json_and_returns_nonzero_for_failed_report(monkeypatch, tmp_path: Path, capsys):
    module = _load_module()
    report = {
        "status": "FAIL",
        "summary": "4/5 checks passed",
        "checks": [{"id": "task_wiring", "ok": False, "hint": "missing"}],
        "diagnostics": {"failed_ids": ["task_wiring"], "failed_count": 1, "critical_failed_ids": []},
    }
    monkeypatch.setattr(module, "build_report", lambda root, run_tests: report)
    monkeypatch.setattr(
        module.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(root=str(tmp_path), run_tests=False, json_out="runtime/ci-artifacts/sprint-070-validation.json"),
    )

    exit_code = module.main()

    assert exit_code == 1
    saved = tmp_path / "runtime/ci-artifacts/sprint-070-validation.json"
    assert saved.exists()
    out = capsys.readouterr().out
    assert "[sprint070_validate] FAIL - 4/5 checks passed" in out
    assert "[sprint070_validate] failed checks: task_wiring" in out
