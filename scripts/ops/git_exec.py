#!/usr/bin/env python3
"""Shared git execution helpers for ops scripts."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Sequence

WINDOWS_GIT_CANDIDATES = (
    r"C:\Program Files\Git\cmd\git.exe",
    r"C:\Program Files\Git\bin\git.exe",
    r"C:\Program Files (x86)\Git\cmd\git.exe",
    r"%LOCALAPPDATA%\Programs\Git\cmd\git.exe",
)


class GitUnavailableError(RuntimeError):
    """Raised when git executable cannot be resolved."""


def _expand_path(value: str) -> Path:
    return Path(os.path.expandvars(value)).expanduser()


def resolve_git() -> str:
    """Return absolute path to git executable.

    Resolution order:
    1. ``CTOA_GIT_BIN`` environment variable
    2. ``git`` from PATH
    3. Windows fallback install paths
    """

    custom = os.getenv("CTOA_GIT_BIN", "").strip()
    if custom:
        candidate = _expand_path(custom)
        if candidate.is_file():
            return str(candidate)
        raise GitUnavailableError(
            "CTOA_GIT_BIN is set but does not point to a valid executable: "
            f"{candidate}"
        )

    git_from_path = shutil.which("git")
    if git_from_path:
        return git_from_path

    if os.name == "nt":
        for raw_candidate in WINDOWS_GIT_CANDIDATES:
            candidate = _expand_path(raw_candidate)
            if candidate.is_file():
                return str(candidate)

    raise GitUnavailableError(
        "Git executable not found. Install Git, add it to PATH, or set "
        "CTOA_GIT_BIN to git.exe (example: C:\\Program Files\\Git\\cmd\\git.exe)."
    )


def run_git(
    args: Sequence[str],
    *,
    cwd: Path | str,
    check: bool = True,
    capture_output: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run git with consistent resolution and text output."""

    if not args:
        raise ValueError("run_git requires at least one git argument")

    git_exe = resolve_git()
    return subprocess.run(
        [git_exe, *args],
        cwd=str(cwd),
        check=check,
        capture_output=capture_output,
        text=True,
    )

