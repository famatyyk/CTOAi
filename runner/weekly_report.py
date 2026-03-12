#!/usr/bin/env python3
import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen


def github_api(method: str, url: str, token: str, payload: Optional[Dict[str, Any]] = None) -> Any:
    data = None
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Authorization": f"Bearer {token}",
        "User-Agent": "ctoa-weekly-report",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = Request(url=url, method=method, headers=headers, data=data)
    with urlopen(req, timeout=30) as res:
        body = res.read().decode("utf-8")
        return json.loads(body) if body else {}


def iso_week_key(now: datetime) -> str:
    y, w, _ = now.isocalendar()
    return f"{y}-W{w:02d}"


def parse_date(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def build_weekly_comment(repo: str, token: str) -> str:
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=7)
    week_key = iso_week_key(now)

    base = f"https://api.github.com/repos/{repo}"
    issues = github_api("GET", f"{base}/issues?state=all&per_page=100", token)

    backlog_issues: List[Dict[str, Any]] = []
    for i in issues:
        labels = [l.get("name", "") for l in i.get("labels", [])]
        if "ctoa-backlog" in labels:
            backlog_issues.append(i)

    created_7d = 0
    closed_7d = 0
    open_count = 0
    for i in backlog_issues:
        created = parse_date(str(i.get("created_at")))
        if created >= since:
            created_7d += 1
        if i.get("state") == "open":
            open_count += 1
        closed_at = i.get("closed_at")
        if closed_at:
            closed_dt = parse_date(str(closed_at))
            if closed_dt >= since:
                closed_7d += 1

    runs = github_api("GET", f"{base}/actions/runs?per_page=100", token).get("workflow_runs", [])
    pipeline_runs = [r for r in runs if r.get("name") == "CTOA Pipeline"]

    status_counter = Counter()
    for r in pipeline_runs:
        created = parse_date(str(r.get("created_at")))
        if created < since:
            continue
        conclusion = str(r.get("conclusion") or "in_progress")
        status_counter[conclusion] += 1

    total_runs = sum(status_counter.values())
    success_runs = status_counter.get("success", 0)
    success_rate = (success_runs / total_runs * 100.0) if total_runs > 0 else 0.0

    marker = f"<!-- ctoa-weekly-report:{week_key} -->"
    lines: List[str] = []
    lines.append(marker)
    lines.append("## CTOA Weekly Management Report")
    lines.append("")
    lines.append(f"- Week: {week_key}")
    lines.append(f"- Generated (UTC): {now.replace(microsecond=0).isoformat()}")
    lines.append("")
    lines.append("### Backlog Throughput (7d)")
    lines.append(f"- Created backlog issues: {created_7d}")
    lines.append(f"- Closed backlog issues: {closed_7d}")
    lines.append(f"- Currently open backlog issues: {open_count}")
    lines.append("")
    lines.append("### Pipeline Health (7d)")
    lines.append(f"- Total CTOA Pipeline runs: {total_runs}")
    lines.append(f"- Success runs: {success_runs}")
    lines.append(f"- Success rate: {success_rate:.1f}%")
    lines.append(f"- Waiting runs: {status_counter.get('in_progress', 0)}")
    lines.append(f"- Failed runs: {status_counter.get('failure', 0)}")
    lines.append("")
    lines.append("### Executive Note")
    lines.append("- Focus next week: move top-priority WAITING_APPROVAL tasks through release gate with minimal cycle time.")

    return "\n".join(lines) + "\n"


def main() -> None:
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PAT")
    repo = os.getenv("GITHUB_REPOSITORY", "famatyyk/CTOAi")
    issue_number = int(os.getenv("CTOA_LIVE_ISSUE_NUMBER", "1"))

    if not token:
        raise RuntimeError("Missing GITHUB_TOKEN or GITHUB_PAT")

    comment_body = build_weekly_comment(repo, token)
    marker = comment_body.splitlines()[0].strip()

    base = f"https://api.github.com/repos/{repo}"
    comments = github_api("GET", f"{base}/issues/{issue_number}/comments?per_page=100", token)
    for c in comments:
        if marker in str(c.get("body", "")):
            print(f"[weekly-report] comment already exists for {marker}")
            return

    created = github_api(
        "POST",
        f"{base}/issues/{issue_number}/comments",
        token,
        {"body": comment_body},
    )
    print(f"[weekly-report] created comment #{created.get('id')} on issue #{issue_number}")


if __name__ == "__main__":
    main()
