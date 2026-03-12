#!/usr/bin/env python3
import os
import re
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
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
    issues = github_api("GET", f"{base}/issues?state=open&per_page=100", token)

    open_by_task_id: Dict[str, Dict[str, Any]] = {}
    pattern = re.compile(r"^\[(CTOA-\d+)\]\s+")
    for issue in issues:
        title = str(issue.get("title", ""))
        m = pattern.match(title)
        if m:
            open_by_task_id[m.group(1)] = issue

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

    print(f"[issue-sync] backlog={backlog_id} created={created} updated={updated}")


if __name__ == "__main__":
    main()
