import sys
from pathlib import Path

import pytest

from runner import process_safety


def test_resolve_python_defaults_to_current_interpreter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CTOA_PYTHON_BIN", raising=False)

    assert process_safety.resolve_python() == sys.executable


def test_resolve_executable_rejects_missing_absolute_path(tmp_path: Path) -> None:
    missing = tmp_path / "missing-tool"

    with pytest.raises(process_safety.ExecutableUnavailableError):
        process_safety.resolve_executable(str(missing))


def test_resolve_executable_accepts_existing_absolute_path(tmp_path: Path) -> None:
    executable = tmp_path / "tool.exe"
    executable.write_text("", encoding="utf-8")

    assert process_safety.resolve_executable(str(executable)) == str(executable)


def test_resolve_executable_honors_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CTOA_TEST_BIN", sys.executable)

    assert process_safety.resolve_executable("missing-tool", env_var="CTOA_TEST_BIN") == sys.executable


def test_run_trusted_rejects_empty_command() -> None:
    with pytest.raises(ValueError):
        process_safety.run_trusted([])


def test_start_trusted_rejects_empty_command() -> None:
    with pytest.raises(ValueError):
        process_safety.start_trusted([])
