#!/usr/bin/env python3
import os
import re
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.request import Request, urlopen

import yaml

ROOT = Path(__file__).resolve().parent.parent
BACKLOG_FILE = ROOT / "workflows" / "backlog-sprint-001.yaml"


def github_api(method: str, url: str, token: str, payload: Optional[Dict[str, Any]] = None) -> Any:
    data = None
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Authorization": f"Bearer {token}",
        "User-Agent": "ctoa-issue-sync",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = Request(url=url, method=method, data=data, headers=headers)
    with urlopen(req, timeout=30) as res:
        body = res.read().decode("utf-8")
        return json.loads(body) if body else {}


def load_backlog() -> Dict[str, Any]:
    with BACKLOG_FILE.open("r", encoding="utf-8") as f:
        payload = yaml.safe_load(f) or {}
    if not isinstance(payload, dict):
        raise ValueError("Invalid backlog yaml")
    return payload


def make_issue_title(task: Dict[str, Any]) -> str:
    return f"[{task.get('id')}] {task.get('title', 'Untitled')}"


def make_issue_body(backlog_id: str, task: Dict[str, Any]) -> str:
    assignees = ", ".join(task.get("assignees", []))
    deliverables = "\n".join([f"- {d}" for d in task.get("deliverables", [])]) or "- none"
    acceptance = "\n".join([f"- {a}" for a in task.get("acceptance", [])]) or "- none"
    domains = ", ".join(task.get("domain", []))

    return "\n".join(
        [
            "## CTOA Backlog Task",
            f"- Backlog: {backlog_id}",
            f"- Task ID: {task.get('id')}",
            f"- Priority: {task.get('priority', 'P1')}",
            f"- Type: {task.get('type', 'task')}",
            f"- Domain: {domains}",
            f"- Assignees: {assignees}",
            "",
            "## Deliverables",
            deliverables,
            "",
            "## Acceptance",
            acceptance,
            "",
            "## Sync",
            "Managed by runner/issue_sync.py",
        ]
    )


def list_open_issues(base: str, token: str) -> List[Dict[str, Any]]:
    all_issues: List[Dict[str, Any]] = []
    page = 1
    while True:
        issues_page = github_api("GET", f"{base}/issues?state=open&per_page=100&page={page}", token)
        if not isinstance(issues_page, list):
            raise RuntimeError("Invalid issues payload")

        all_issues.extend(issues_page)
        if len(issues_page) < 100:
            break
        page += 1
    return all_issues


def group_backlog_issues_by_task_id(open_issues: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    pattern = re.compile(r"^\[(CTOA-\d+)\]\s+")
    for issue in open_issues:
        title = str(issue.get("title", ""))
        m = pattern.match(title)
        if not m:
            continue
        task_id = m.group(1)
        grouped.setdefault(task_id, []).append(issue)
    return grouped


def split_primary_and_duplicates(issues_by_task_id: Dict[str, List[Dict[str, Any]]]) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    primary_by_task_id: Dict[str, Dict[str, Any]] = {}
    duplicates: List[Dict[str, Any]] = []

    for task_id, issues in issues_by_task_id.items():
        valid_issues = [i for i in issues if isinstance(i.get("number"), int)]
        if not valid_issues:
            continue
        sorted_issues = sorted(valid_issues, key=lambda i: int(i["number"]))
        primary_by_task_id[task_id] = sorted_issues[0]
        duplicates.extend(sorted_issues[1:])

    return primary_by_task_id, duplicates


def main() -> None:
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PAT")
    repo = os.getenv("GITHUB_REPOSITORY", "famatyyk/CTOAi")
    if not token:
        raise RuntimeError("Missing GITHUB_TOKEN or GITHUB_PAT")

    backlog = load_backlog()
    backlog_id = str(backlog.get("backlog_id", "sprint-unknown"))
    tasks = backlog.get("tasks", [])
    if not isinstance(tasks, list):
        raise RuntimeError("Invalid backlog tasks")

    base = f"https://api.github.com/repos/{repo}"
    issues = list_open_issues(base, token)
    grouped_issues = group_backlog_issues_by_task_id(issues)
    open_by_task_id, duplicates = split_primary_and_duplicates(grouped_issues)

    closed_duplicates = 0
    for issue in duplicates:
        github_api(
            "PATCH",
            f"{base}/issues/{issue['number']}",
            token,
            {"state": "closed"},
        )
        closed_duplicates += 1

    created = 0
    updated = 0
    for task in tasks:
        if not isinstance(task, dict):
            continue
        task_id = str(task.get("id", "")).strip()
        if not task_id:
            continue

        title = make_issue_title(task)
        body = make_issue_body(backlog_id, task)
        existing = open_by_task_id.get(task_id)

        if existing is None:
            github_api(
                "POST",
                f"{base}/issues",
                token,
                {
                    "title": title,
                    "body": body,
                    "labels": ["ctoa", "ctoa-backlog", backlog_id.lower(), task_id.lower()],
                },
            )
            created += 1
        else:
            github_api(
                "PATCH",
                f"{base}/issues/{existing['number']}",
                token,
                {
                    "title": title,
                    "body": body,
                },
            )
            updated += 1

    print(
        f"[issue-sync] backlog={backlog_id} created={created} updated={updated} closed_duplicates={closed_duplicates}"
    )


if __name__ == "__main__":
    main()
