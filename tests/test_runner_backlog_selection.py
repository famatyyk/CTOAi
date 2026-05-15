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


def test_runner_uses_env_backlog_file_for_selection(monkeypatch, tmp_path):
    backlog = tmp_path / "backlog-env.yaml"
    backlog.write_text(
        """backlog_id: sprint-env\nrules:\n  max_parallel_tasks: 1\ntasks: []\n""",
        encoding="utf-8",
    )

    monkeypatch.setenv("CTOA_BACKLOG_FILE", str(backlog))
    runner = _load_runner_module("runner_env_backlog_selection")

    assert runner.BACKLOG_FILE == backlog
    loaded = runner.load_backlog()
    assert loaded["backlog_id"] == "sprint-env"


def test_runner_raises_on_invalid_backlog_yaml_object(monkeypatch, tmp_path):
    invalid_backlog = tmp_path / "invalid-backlog.yaml"
    invalid_backlog.write_text("- not\n- a\n- dict\n", encoding="utf-8")

    monkeypatch.setenv("CTOA_BACKLOG_FILE", str(invalid_backlog))
    runner = _load_runner_module("runner_invalid_backlog_object")

    with pytest.raises(ValueError, match="Invalid YAML object"):
        runner.load_backlog()


def test_runner_raises_on_missing_backlog_file(monkeypatch, tmp_path):
    missing_backlog = tmp_path / "missing-backlog.yaml"

    monkeypatch.setenv("CTOA_BACKLOG_FILE", str(missing_backlog))
    runner = _load_runner_module("runner_missing_backlog")

    with pytest.raises(FileNotFoundError, match="Missing backlog file"):
        runner.load_backlog()
