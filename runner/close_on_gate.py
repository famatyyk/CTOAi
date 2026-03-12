#!/usr/bin/env python3
import json
import os
import re
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen


def github_api(method: str, url: str, token: str, payload: Optional[Dict[str, Any]] = None) -> Any:
    data = None
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Authorization": f"Bearer {token}",
        "User-Agent": "ctoa-close-on-gate",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = Request(url=url, method=method, headers=headers, data=data)
    with urlopen(req, timeout=30) as res:
        body = res.read().decode("utf-8")
        return json.loads(body) if body else {}


def parse_waiting_task_ids(issue_body: str) -> List[str]:
    marker = "## Waiting Approval"
    start = issue_body.find(marker)
    if start < 0:
        return []

    section = issue_body[start + len(marker):]
    next_header = section.find("\n## ")
    if next_header >= 0:
        section = section[:next_header]

    ids: List[str] = []
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("- "):
            continue
        m = re.match(r"-\s+(CTOA-\d+):", line)
        if m:
            ids.append(m.group(1))
    return ids


def main() -> None:
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PAT")
    repo = os.getenv("GITHUB_REPOSITORY", "famatyyk/CTOAi")
    live_issue_number = int(os.getenv("CTOA_LIVE_ISSUE_NUMBER", "1"))

    if not token:
        raise RuntimeError("Missing GITHUB_TOKEN or GITHUB_PAT")

    base = f"https://api.github.com/repos/{repo}"
    live_issue = github_api("GET", f"{base}/issues/{live_issue_number}", token)
    body = str(live_issue.get("body", ""))
    waiting_ids = parse_waiting_task_ids(body)

    if not waiting_ids:
        print("[close-on-gate] no tasks in waiting approval section")
        return

    open_issues = github_api("GET", f"{base}/issues?state=open&per_page=100", token)
    by_task_id: Dict[str, Dict[str, Any]] = {}
    title_pattern = re.compile(r"^\[(CTOA-\d+)\]\s+")
    for issue in open_issues:
        title = str(issue.get("title", ""))
        m = title_pattern.match(title)
        if m:
            by_task_id[m.group(1)] = issue

    closed = 0
    for task_id in waiting_ids:
        issue = by_task_id.get(task_id)
        if issue is None:
            continue

        number = int(issue["number"])
        github_api(
            "PATCH",
            f"{base}/issues/{number}",
            token,
            {"state": "closed", "state_reason": "completed"},
        )
        github_api(
            "POST",
            f"{base}/issues/{number}/comments",
            token,
            {
                "body": (
                    "Auto-closed by CTOA gate automation after successful approval publish.\n"
                    "If this was closed by mistake, reopen and annotate root cause."
                )
            },
        )
        closed += 1

    print(f"[close-on-gate] waiting={len(waiting_ids)} closed={closed}")


if __name__ == "__main__":
    main()
