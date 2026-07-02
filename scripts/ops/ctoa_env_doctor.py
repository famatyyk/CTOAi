#!/usr/bin/env python3
"""Local preflight checks before pull/rebase/push."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

try:
    from scripts.ops.git_exec import GitUnavailableError, resolve_git, run_git
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from git_exec import GitUnavailableError, resolve_git, run_git

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ORIGIN = "git@github.com:famatyyk/CTOAi.git"


def _check_git() -> dict[str, Any]:
    try:
        git_exe = resolve_git()
        version = run_git(["--version"], cwd=ROOT).stdout.strip()
    except GitUnavailableError as exc:
        return {
            "id": "git_binary",
            "status": "fail",
            "message": str(exc),
            "remediation": "Install Git and add it to PATH, or set CTOA_GIT_BIN.",
        }

    return {
        "id": "git_binary",
        "status": "ok",
        "message": f"{version} ({git_exe})",
    }


def _origin_url() -> str:
    return run_git(["remote", "get-url", "origin"], cwd=ROOT).stdout.strip()


def _check_origin(expected_origin: str) -> dict[str, Any]:
    try:
        origin = _origin_url()
    except subprocess.CalledProcessError as exc:
        return {
            "id": "origin_remote",
            "status": "fail",
            "message": exc.stderr.strip() or "Unable to read origin remote.",
            "remediation": f"Set origin to SSH: git remote set-url origin {expected_origin}",
        }

    if origin != expected_origin:
        return {
            "id": "origin_remote",
            "status": "fail",
            "message": f"origin is '{origin}' (expected '{expected_origin}')",
            "remediation": f"Run: git remote set-url origin {expected_origin}",
        }

    return {
        "id": "origin_remote",
        "status": "ok",
        "message": f"origin={origin}",
    }


def _check_worktree_clean() -> dict[str, Any]:
    status_lines = [line for line in run_git(["status", "--porcelain"], cwd=ROOT).stdout.splitlines() if line.strip()]
    if status_lines:
        return {
            "id": "worktree_clean",
            "status": "fail",
            "message": f"Working tree not clean ({len(status_lines)} changes).",
            "details": status_lines[:20],
            "remediation": "Commit/stash/clean changes before pull/rebase/push.",
        }
    return {
        "id": "worktree_clean",
        "status": "ok",
        "message": "Working tree is clean.",
    }


def _check_upstream_sync() -> dict[str, Any]:
    try:
        upstream = run_git(
            ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
            cwd=ROOT,
        ).stdout.strip()
    except subprocess.CalledProcessError:
        return {
            "id": "upstream_sync",
            "status": "warn",
            "message": "No upstream tracking branch configured for current branch.",
            "remediation": "Set upstream with: git branch --set-upstream-to origin/<branch>",
        }

    counts_raw = run_git(["rev-list", "--left-right", "--count", f"{upstream}...HEAD"], cwd=ROOT).stdout.strip()
    behind, ahead = [int(part) for part in counts_raw.split()]
    if ahead == 0 and behind == 0:
        return {
            "id": "upstream_sync",
            "status": "ok",
            "message": f"Branch in sync with {upstream}.",
        }

    return {
        "id": "upstream_sync",
        "status": "fail",
        "message": f"Branch diverged from {upstream}: ahead={ahead}, behind={behind}.",
        "remediation": "Fetch and rebase before pushing.",
    }


def _check_ssh_access(expected_origin: str) -> dict[str, Any]:
    probe = run_git(["ls-remote", expected_origin, "HEAD"], cwd=ROOT, check=False)
    if probe.returncode == 0:
        head = probe.stdout.strip().splitlines()[0] if probe.stdout.strip() else "HEAD resolved"
        return {
            "id": "ssh_access",
            "status": "ok",
            "message": f"SSH access OK ({head}).",
        }

    message = (probe.stderr or probe.stdout).strip()
    return {
        "id": "ssh_access",
        "status": "fail",
        "message": message or "SSH probe failed.",
        "remediation": "Load SSH key and verify with: ssh -T git@github.com",
    }


def run_doctor(expected_origin: str) -> dict[str, Any]:
    checks = [_check_git()]
    if checks[0]["status"] == "fail":
        summary_status = "FAIL"
        return {"status": summary_status, "checks": checks}

    checks.extend(
        [
            _check_origin(expected_origin),
            _check_ssh_access(expected_origin),
            _check_worktree_clean(),
            _check_upstream_sync(),
        ]
    )

    status_order = {"ok": 0, "warn": 1, "fail": 2}
    worst = max(status_order[item["status"]] for item in checks)
    summary_status = {0: "OK", 1: "WARN", 2: "FAIL"}[worst]
    return {"status": summary_status, "checks": checks}


def _print_human(report: dict[str, Any]) -> None:
    print("CTOA local env doctor")
    print("---------------------")
    for check in report["checks"]:
        badge = {"ok": "[OK]", "warn": "[WARN]", "fail": "[FAIL]"}[check["status"]]
        print(f"{badge} {check['id']}: {check['message']}")
        if check.get("details"):
            for line in check["details"]:
                print(f"  - {line}")
        if check.get("remediation"):
            print(f"  -> {check['remediation']}")
    print(f"\nOverall status: {report['status']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="CTOA local environment doctor")
    parser.add_argument(
        "--expected-origin",
        default=DEFAULT_ORIGIN,
        help="Expected SSH origin URL for local development",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print report as JSON",
    )
    args = parser.parse_args()

    report = run_doctor(args.expected_origin)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        _print_human(report)

    return 0 if report["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())

