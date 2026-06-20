import subprocess

from scripts.ops import ctoa_env_doctor as doctor


def test_doctor_reports_fail_when_git_missing(monkeypatch):
    monkeypatch.setattr(doctor, "resolve_git", lambda: (_ for _ in ()).throw(doctor.GitUnavailableError("missing git")))

    report = doctor.run_doctor(doctor.DEFAULT_ORIGIN)

    assert report["status"] == "FAIL"
    assert report["checks"][0]["id"] == "git_binary"
    assert report["checks"][0]["status"] == "fail"


def test_doctor_reports_ok_when_checks_pass(monkeypatch):
    def fake_run_git(args, **kwargs):
        if args == ["--version"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="git version 2.54.0\n", stderr="")
        if args == ["remote", "get-url", "origin"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout=f"{doctor.DEFAULT_ORIGIN}\n", stderr="")
        if args == ["ls-remote", doctor.DEFAULT_ORIGIN, "HEAD"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="abc123\tHEAD\n", stderr="")
        if args == ["status", "--porcelain"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
        if args == ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="origin/main\n", stderr="")
        if args == ["rev-list", "--left-right", "--count", "origin/main...HEAD"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="0\t0\n", stderr="")
        raise AssertionError(f"Unexpected git args: {args}")

    monkeypatch.setattr(doctor, "resolve_git", lambda: r"C:\Program Files\Git\cmd\git.exe")
    monkeypatch.setattr(doctor, "run_git", fake_run_git)

    report = doctor.run_doctor(doctor.DEFAULT_ORIGIN)

    assert report["status"] == "OK"
    assert all(item["status"] == "ok" for item in report["checks"])

