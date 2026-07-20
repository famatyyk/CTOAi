#!/usr/bin/env python3
"""Audit CTOAi source and deployment exposure without printing credentials."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runner.process_safety import (  # noqa: E402
    ExecutableUnavailableError,
    resolve_executable,
    run_trusted,
)


DEFAULT_POLICY = ROOT / "config" / "security" / "public-exposure-policy.json"
DEFAULT_REPORT = ROOT / "runtime" / "audits" / "public-exposure-latest.json"


class ExposureAuditUnavailable(RuntimeError):
    """Raised when an external control plane cannot be checked safely."""


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def _run_json(argv: list[str], *, cwd: Path = ROOT, timeout: int = 45) -> Any:
    result = run_trusted(
        argv,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        raise ExposureAuditUnavailable(
            f"Command {Path(argv[0]).name} returned {result.returncode}"
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ExposureAuditUnavailable(
            f"Command {Path(argv[0]).name} returned invalid JSON"
        ) from exc


def _branch_map(gh: str, repository: str) -> dict[str, str]:
    payload = _run_json(
        [
            gh,
            "api",
            "--method",
            "GET",
            f"repos/{repository}/branches?per_page=100",
        ]
    )
    if not isinstance(payload, list):
        raise ExposureAuditUnavailable("GitHub branches response is not a list")
    return {
        str(item.get("name")): str((item.get("commit") or {}).get("sha"))
        for item in payload
        if isinstance(item, dict) and item.get("name")
    }


def collect_snapshot(policy: dict[str, Any]) -> dict[str, Any]:
    github_policy = policy.get("github") or {}
    vercel_policy = policy.get("vercel") or {}
    owner = str(github_policy.get("owner") or "").strip()
    if not owner:
        raise ValueError("github.owner is required")

    gh = resolve_executable("gh", env_var="CTOA_GH_BIN")
    vercel = resolve_executable("vercel", env_var="CTOA_VERCEL_BIN")

    repositories = _run_json(
        [
            gh,
            "api",
            "--method",
            "GET",
            "user/repos?affiliation=owner&per_page=100&sort=updated",
        ]
    )
    if not isinstance(repositories, list):
        raise ExposureAuditUnavailable("GitHub repositories response is not a list")

    public_fork_branches: dict[str, dict[str, Any]] = {}
    allowed_forks = {
        str(item.get("repository")): item
        for item in github_policy.get("allowed_public_upstream_forks", [])
        if isinstance(item, dict) and item.get("repository")
    }
    for repository in repositories:
        if not isinstance(repository, dict):
            continue
        full_name = str(repository.get("full_name") or "")
        if not repository.get("fork") or repository.get("private"):
            continue
        fork_policy = allowed_forks.get(full_name)
        if not fork_policy:
            continue
        upstream = str(fork_policy.get("upstream") or "")
        detail = _run_json([gh, "api", f"repos/{full_name}"])
        public_fork_branches[full_name] = {
            "upstream": upstream,
            "reported_parent": str((detail.get("parent") or {}).get("full_name")),
            "fork_branches": _branch_map(gh, full_name),
            "upstream_branches": _branch_map(gh, upstream),
        }

    aliases = _run_json(
        [
            vercel,
            "alias",
            "list",
            "--format",
            "json",
            "--limit",
            "100",
            "--scope",
            str(vercel_policy.get("scope") or ""),
            "--no-color",
        ]
    )
    protection = _run_json(
        [
            vercel,
            "project",
            "protection",
            str(vercel_policy.get("project") or ""),
            "--format",
            "json",
            "--scope",
            str(vercel_policy.get("scope") or ""),
            "--no-color",
        ]
    )

    link_path = ROOT / str(vercel_policy.get("project_link_file") or "")
    link = _load_json(link_path)
    project_id = str(link.get("projectId") or "")
    team_id = str(link.get("orgId") or "")
    if not project_id or not team_id:
        raise ExposureAuditUnavailable("Vercel project link is incomplete")
    project = _run_json(
        [
            vercel,
            "api",
            f"/v9/projects/{project_id}?teamId={team_id}",
            "--cwd",
            str(ROOT / "web"),
            "--no-color",
        ],
        cwd=ROOT / "web",
    )

    return {
        "github": {
            "owner": owner,
            "repositories": repositories,
            "public_fork_branches": public_fork_branches,
        },
        "vercel": {
            "aliases": aliases,
            "protection": protection,
            "project": project,
        },
    }


def _check(name: str, passed: bool, detail: str) -> dict[str, str]:
    return {"name": name, "status": "passed" if passed else "failed", "detail": detail}


def evaluate_snapshot(
    policy: dict[str, Any], snapshot: dict[str, Any]
) -> dict[str, Any]:
    github_policy = policy.get("github") or {}
    vercel_policy = policy.get("vercel") or {}
    repositories = (snapshot.get("github") or {}).get("repositories") or []
    checks: list[dict[str, str]] = []

    public_non_forks = sorted(
        str(repo.get("full_name"))
        for repo in repositories
        if isinstance(repo, dict) and not repo.get("fork") and not repo.get("private")
    )
    checks.append(
        _check(
            "github_owned_sources_private",
            not public_non_forks,
            "all owned non-fork repositories are private"
            if not public_non_forks
            else "public owned repositories: " + ", ".join(public_non_forks),
        )
    )

    pages_enabled = sorted(
        str(repo.get("full_name"))
        for repo in repositories
        if isinstance(repo, dict) and repo.get("has_pages")
    )
    checks.append(
        _check(
            "github_pages_disabled",
            not pages_enabled,
            "no owned repository publishes Pages"
            if not pages_enabled
            else "Pages enabled: " + ", ".join(pages_enabled),
        )
    )

    allowed_forks = {
        str(item.get("repository")): item
        for item in github_policy.get("allowed_public_upstream_forks", [])
        if isinstance(item, dict) and item.get("repository")
    }
    public_forks = {
        str(repo.get("full_name"))
        for repo in repositories
        if isinstance(repo, dict) and repo.get("fork") and not repo.get("private")
    }
    unexpected_forks = sorted(public_forks - set(allowed_forks))
    checks.append(
        _check(
            "github_public_forks_allowlisted",
            not unexpected_forks,
            "public forks are explicitly allowlisted"
            if not unexpected_forks
            else "unexpected public forks: " + ", ".join(unexpected_forks),
        )
    )

    branch_snapshots = (snapshot.get("github") or {}).get("public_fork_branches") or {}
    divergent: list[str] = []
    for repository in sorted(public_forks & set(allowed_forks)):
        fork_snapshot = branch_snapshots.get(repository) or {}
        expected_upstream = str(allowed_forks[repository].get("upstream") or "")
        if str(fork_snapshot.get("reported_parent") or "") != expected_upstream:
            divergent.append(f"{repository}: parent mismatch")
            continue
        fork_branches = fork_snapshot.get("fork_branches") or {}
        upstream_branches = fork_snapshot.get("upstream_branches") or {}
        for branch, sha in sorted(fork_branches.items()):
            if upstream_branches.get(branch) != sha:
                divergent.append(f"{repository}:{branch}")
    checks.append(
        _check(
            "github_public_forks_match_upstream",
            not divergent,
            "allowlisted public forks contain no divergent branches"
            if not divergent
            else "divergent public fork branches: " + ", ".join(divergent),
        )
    )

    vercel = snapshot.get("vercel") or {}
    alias_payload = vercel.get("aliases") or {}
    aliases = alias_payload.get("aliases") if isinstance(alias_payload, dict) else []
    aliases = aliases if isinstance(aliases, list) else []
    checks.append(
        _check(
            "vercel_public_aliases_absent",
            not aliases,
            "Vercel alias inventory is empty"
            if not aliases
            else f"Vercel exposes {len(aliases)} alias(es)",
        )
    )

    project = vercel.get("project") or {}
    expected_auto_assign = bool(vercel_policy.get("auto_assign_custom_domains"))
    observed_auto_assign = project.get("autoAssignCustomDomains")
    checks.append(
        _check(
            "vercel_auto_alias_assignment_disabled",
            observed_auto_assign is expected_auto_assign,
            f"autoAssignCustomDomains={str(observed_auto_assign).lower()}",
        )
    )

    protection = vercel.get("protection") or {}
    deployment_type = str(
        (protection.get("ssoProtection") or {}).get("deploymentType") or ""
    )
    allowed_types = {
        str(value) for value in vercel_policy.get("allowed_sso_deployment_types", [])
    }
    checks.append(
        _check(
            "vercel_deployments_require_authentication",
            deployment_type in allowed_types,
            f"sso deployment type: {deployment_type or 'missing'}",
        )
    )

    status = (
        "passed" if all(check["status"] == "passed" for check in checks) else "failed"
    )
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": policy.get("mode"),
        "status": status,
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    policy_path = args.policy if args.policy.is_absolute() else ROOT / args.policy
    report_path = args.json_out if args.json_out.is_absolute() else ROOT / args.json_out
    policy = _load_json(policy_path)
    try:
        snapshot = collect_snapshot(policy)
        report = evaluate_snapshot(policy, snapshot)
    except (ExecutableUnavailableError, ExposureAuditUnavailable, OSError) as exc:
        report = {
            "schema_version": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "mode": policy.get("mode"),
            "status": "unavailable",
            "checks": [],
            "error": str(exc),
        }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"[public-exposure] status={report['status']} report={report_path}")
    for check in report.get("checks", []):
        print(f"- {check['status']}: {check['name']} ({check['detail']})")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
