#!/usr/bin/env python3
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import yaml

ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = ROOT / "runtime" / "task-state.yaml"

STATUS_LABEL_COLORS = {
    "status/new": "c9d1d9",
    "status/in_progress": "1f6feb",
    "status/in_qa": "8250df",
    "status/in_ci_gate": "d4a72c",
    "status/waiting_approval": "fb8500",
    "status/released": "2da44e",
    "status/blocked": "cf222e",
}


def parse_iso(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def load_state() -> Dict[str, Any]:
    if not STATE_FILE.exists():
        return {}
    with STATE_FILE.open("r", encoding="utf-8") as f:
        payload = yaml.safe_load(f) or {}
    if not isinstance(payload, dict):
        return {}
    return payload


def github_api(method: str, url: str, token: str, payload: Optional[Dict[str, Any]] = None) -> Any:
    data = None
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Authorization": f"Bearer {token}",
        "User-Agent": "ctoa-status-sync",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = Request(url=url, method=method, headers=headers, data=data)
    with urlopen(req, timeout=30) as res:
        body = res.read().decode("utf-8")
        return json.loads(body) if body else {}


def ensure_status_labels(base: str, token: str) -> None:
    for label, color in STATUS_LABEL_COLORS.items():
        try:
            github_api(
                "POST",
                f"{base}/labels",
                token,
                {
                    "name": label,
                    "color": color,
                    "description": f"CTOA task status: {label.split('/', 1)[1]}",
                },
            )
        except HTTPError as ex:
            # 422 means label already exists, which is fine.
            if ex.code != 422:
                raise


def task_map(state: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    tasks = state.get("tasks", []) if isinstance(state.get("tasks"), list) else []
    for t in tasks:
        if not isinstance(t, dict):
            continue
        task_id = str(t.get("id", "")).strip()
        if task_id:
            out[task_id] = t
    return out


def backlog_issue_map(open_issues: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    pattern = re.compile(r"^\[(CTOA-\d+)\]\s+")
    for issue in open_issues:
        title = str(issue.get("title", ""))
        m = pattern.match(title)
        if m:
            out[m.group(1)] = issue
    return out


def desired_status_label(task: Dict[str, Any]) -> str:
    status = str(task.get("status", "NEW")).lower()
    return f"status/{status}"


def sync_status_labels(base: str, token: str, tasks: Dict[str, Dict[str, Any]], issues: Dict[str, Dict[str, Any]]) -> int:
    updated = 0
    for task_id, issue in issues.items():
        task = tasks.get(task_id)
        if task is None:
            continue

        labels = [str(l.get("name", "")) for l in issue.get("labels", [])]
        non_status = [l for l in labels if not l.startswith("status/")]
        new_status = desired_status_label(task)
        desired = non_status + [new_status]

        if labels == desired:
            continue

        github_api(
            "PATCH",
            f"{base}/issues/{issue['number']}",
            token,
            {"labels": desired},
        )
        updated += 1

    return updated


def build_sla_alert(tasks: Dict[str, Dict[str, Any]], issues: Dict[str, Dict[str, Any]], threshold_hours: int) -> Optional[str]:
    now = datetime.now(timezone.utc)
    overdue: List[Dict[str, Any]] = []

    for task_id, task in tasks.items():
        if str(task.get("status", "")) != "WAITING_APPROVAL":
            continue

        updated_at = parse_iso(str(task.get("updated_at", "")))
        if not updated_at:
            continue

        age_hours = (now - updated_at).total_seconds() / 3600.0
        if age_hours <= threshold_hours:
            continue

        issue = issues.get(task_id)
        overdue.append(
            {
                "task_id": task_id,
                "title": task.get("title", ""),
                "age_hours": age_hours,
                "issue_number": issue.get("number") if issue else None,
                "updated_at": str(task.get("updated_at", "")),
            }
        )

    if not overdue:
        return None

    overdue.sort(key=lambda x: (-x["age_hours"], x["task_id"]))
    marker = "<!-- ctoa-sla-alert:" + "|".join([f"{o['task_id']}@{o['updated_at']}" for o in overdue]) + " -->"

    lines: List[str] = [marker, "## SLA Alert: Approval Pending >12h", ""]
    lines.append(f"- Generated (UTC): {now.replace(microsecond=0).isoformat()}")
    lines.append(f"- Threshold: {threshold_hours}h")
    lines.append("")
    for o in overdue:
        issue_ref = f"#{o['issue_number']}" if o["issue_number"] else "n/a"
        lines.append(f"- {o['task_id']}: {o['title']} | age={o['age_hours']:.1f}h | issue={issue_ref}")

    return "\n".join(lines) + "\n"


def post_sla_alert_if_needed(base: str, token: str, live_issue_number: int, body: Optional[str]) -> bool:
    if not body:
        return False

    marker = body.splitlines()[0].strip()
    comments = github_api("GET", f"{base}/issues/{live_issue_number}/comments?per_page=100", token)
    for c in comments:
        if marker in str(c.get("body", "")):
            print("[status-sync] SLA alert already posted for current task set")
            return False

    github_api(
        "POST",
        f"{base}/issues/{live_issue_number}/comments",
        token,
        {"body": body},
    )
    return True


def main() -> None:
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PAT")
    repo = os.getenv("GITHUB_REPOSITORY", "famatyyk/CTOAi")
    live_issue_number = int(os.getenv("CTOA_LIVE_ISSUE_NUMBER", "1"))
    threshold_hours = int(os.getenv("CTOA_APPROVAL_SLA_HOURS", "12"))

    if not token:
        raise RuntimeError("Missing GITHUB_TOKEN or GITHUB_PAT")

    state = load_state()
    if not state:
        raise RuntimeError("Missing or invalid runtime state file")

    tasks = task_map(state)
    base = f"https://api.github.com/repos/{repo}"

    ensure_status_labels(base, token)

    open_issues = github_api("GET", f"{base}/issues?state=open&per_page=100", token)
    issues = backlog_issue_map(open_issues)

    label_updates = sync_status_labels(base, token, tasks, issues)

    sla_body = build_sla_alert(tasks, issues, threshold_hours)
    alert_posted = post_sla_alert_if_needed(base, token, live_issue_number, sla_body)

    print(f"[status-sync] labels_updated={label_updates} sla_alert_posted={alert_posted}")


if __name__ == "__main__":
    main()
