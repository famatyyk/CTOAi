"""Subprocess guardrails for trusted local tooling."""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404
import sys
from pathlib import Path
from typing import Any


# This module centralizes subprocess execution behind executable resolution.
WINDOWS_GIT = Path(r"C:\Program Files\Git\cmd\git.exe")
CREATE_NEW_PROCESS_GROUP = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)


class ExecutableUnavailableError(RuntimeError):
    pass


ProcessExecutionError = subprocess.SubprocessError
ProcessTimeoutExpired = subprocess.TimeoutExpired
TrustedProcess = subprocess.Popen


def _resolve_candidate(value: str) -> str:
    raw = str(value or "").strip().strip('"')
    if not raw:
        raise ExecutableUnavailableError("empty executable path")
    path = Path(raw).expanduser()
    if path.is_absolute():
        if path.is_file():
            return str(path)
        raise ExecutableUnavailableError(f"executable not found: {path}")
    resolved = shutil.which(raw)
    if resolved:
        return resolved
    raise ExecutableUnavailableError(f"executable not found on PATH: {raw}")


def resolve_executable(
    name: str,
    *,
    env_var: str | None = None,
    fallback_paths: tuple[Path, ...] = (),
) -> str:
    raw_name = str(name or "").strip()
    separators = [os.sep]
    if os.altsep:
        separators.append(os.altsep)

    if raw_name and (
        Path(raw_name).is_absolute()
        or any(separator in raw_name for separator in separators)
    ):
        return _resolve_candidate(raw_name)

    if env_var:
        configured = os.environ.get(env_var, "").strip()
        if configured:
            return _resolve_candidate(configured)

    resolved = shutil.which(name)
    if resolved:
        return resolved

    for candidate in fallback_paths:
        if candidate.is_file():
            return str(candidate)

    raise ExecutableUnavailableError(f"executable not found: {name}")


def resolve_git() -> str:
    return resolve_executable(
        "git", env_var="CTOA_GIT_BIN", fallback_paths=(WINDOWS_GIT,)
    )


def resolve_python() -> str:
    configured = os.environ.get("CTOA_PYTHON_BIN", "").strip()
    if configured:
        return _resolve_candidate(configured)
    if sys.executable:
        return sys.executable
    return resolve_executable("python3")


def run_trusted(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
    if not command:
        raise ValueError("command must not be empty")
    # command[0] is resolved by resolve_executable/resolve_git/resolve_python before execution.
    return subprocess.run(command, **kwargs)  # nosec B603


def start_trusted(command: list[str], **kwargs: Any) -> subprocess.Popen[str]:
    if not command:
        raise ValueError("command must not be empty")
    # command[0] is resolved by resolve_executable/resolve_git/resolve_python before execution.
    return subprocess.Popen(command, **kwargs)  # nosec B603
