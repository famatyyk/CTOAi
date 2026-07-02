import subprocess
from pathlib import Path

import pytest

from scripts.ops import git_exec


def test_resolve_git_uses_ctoa_git_bin(monkeypatch, tmp_path: Path):
    fake_git = tmp_path / "git.exe"
    fake_git.write_text("", encoding="utf-8")
    monkeypatch.setenv("CTOA_GIT_BIN", str(fake_git))
    monkeypatch.setattr(git_exec.shutil, "which", lambda name: None)

    assert git_exec.resolve_git() == str(fake_git)


def test_resolve_git_uses_path(monkeypatch):
    monkeypatch.delenv("CTOA_GIT_BIN", raising=False)
    monkeypatch.setattr(git_exec.shutil, "which", lambda name: r"C:\mock\git.exe")

    assert git_exec.resolve_git() == r"C:\mock\git.exe"


def test_resolve_git_uses_windows_fallback(monkeypatch, tmp_path: Path):
    fake_git = tmp_path / "git.exe"
    fake_git.write_text("", encoding="utf-8")

    monkeypatch.delenv("CTOA_GIT_BIN", raising=False)
    monkeypatch.setattr(git_exec.shutil, "which", lambda name: None)
    monkeypatch.setattr(git_exec, "_expand_path", lambda value: fake_git)
    monkeypatch.setattr(git_exec, "WINDOWS_GIT_CANDIDATES", (str(fake_git),))
    monkeypatch.setattr(git_exec.os, "name", "nt", raising=False)

    assert git_exec.resolve_git() == str(fake_git)


def test_resolve_git_raises_when_missing(monkeypatch):
    monkeypatch.delenv("CTOA_GIT_BIN", raising=False)
    monkeypatch.setattr(git_exec.shutil, "which", lambda name: None)
    monkeypatch.setattr(git_exec, "WINDOWS_GIT_CANDIDATES", tuple())
    monkeypatch.setattr(git_exec.os, "name", "nt", raising=False)

    with pytest.raises(git_exec.GitUnavailableError):
        git_exec.resolve_git()


def test_run_git_uses_resolved_binary(monkeypatch):
    called: dict[str, object] = {}

    def fake_run(*args, **kwargs):
        called["args"] = args
        called["kwargs"] = kwargs
        return subprocess.CompletedProcess(args=["git"], returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(git_exec, "resolve_git", lambda: r"C:\git\git.exe")
    monkeypatch.setattr(git_exec.subprocess, "run", fake_run)

    result = git_exec.run_git(["status", "--short"], cwd=".")

    assert result.returncode == 0
    assert called["args"][0][0] == r"C:\git\git.exe"
    assert called["args"][0][1:] == ["status", "--short"]
