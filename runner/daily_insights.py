#!/usr/bin/env python3
import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen

import yaml

ROOT = Path(__file__).resolve().parent.parent
BACKLOG_FILE = ROOT / "workflows" / "backlog-sprint-001.yaml"
STATE_FILE = ROOT / "runtime" / "task-state.yaml"


def parse_iso(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        return {}
    return data


def github_api(method: str, url: str, token: str, payload: Optional[Dict[str, Any]] = None) -> Any:
    data = None
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Authorization": f"Bearer {token}",
        "User-Agent": "ctoa-daily-insights",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = Request(url=url, method=method, headers=headers, data=data)
    with urlopen(req, timeout=30) as res:
        body = res.read().decode("utf-8")
        return json.loads(body) if body else {}


def build_daily_comment(backlog: Dict[str, Any], state: Dict[str, Any]) -> str:
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=24)

    tasks = state.get("tasks", []) if isinstance(state.get("tasks"), list) else []
    history = state.get("history", []) if isinstance(state.get("history"), list) else []

    transitions_24h = []
    for h in history:
        if not isinstance(h, dict):
            continue
        if h.get("event") != "transition":
            continue
        at = parse_iso(str(h.get("at", "")))
        if at and at >= since:
            transitions_24h.append(h)

    to_status_counter = Counter([str(t.get("to_status", "UNKNOWN")) for t in transitions_24h])

    blocked_24h = []
    for t in tasks:
        status = str(t.get("status", ""))
        updated = parse_iso(str(t.get("updated_at", "")))
        if not updated:
            continue
        age_hours = (now - updated).total_seconds() / 3600.0
        if status != "RELEASED" and age_hours > 24.0:
            blocked_24h.append((t, age_hours))

    blocked_24h.sort(key=lambda x: (-x[1], str(x[0].get("id", ""))))

    waiting = [t for t in tasks if str(t.get("status")) == "WAITING_APPROVAL"]
    waiting.sort(key=lambda t: (str(t.get("priority", "P9")), str(t.get("id", ""))))

    in_ci_gate = [t for t in tasks if str(t.get("status")) == "IN_CI_GATE"]
    in_ci_gate.sort(key=lambda t: (str(t.get("priority", "P9")), str(t.get("id", ""))))

    in_qa = [t for t in tasks if str(t.get("status")) == "IN_QA"]
    in_qa.sort(key=lambda t: (str(t.get("priority", "P9")), str(t.get("id", ""))))

    candidates = waiting + in_ci_gate + in_qa
    suggestions = candidates[:3]

    marker = f"<!-- ctoa-daily-insight:{now.date().isoformat()} -->"
    lines: List[str] = []
    lines.append(marker)
    lines.append("## CTOA Daily Insight")
    lines.append("")
    lines.append(f"- Date (UTC): {now.date().isoformat()}")
    lines.append(f"- Backlog: {backlog.get('backlog_id', 'unknown')}")
    lines.append(f"- Last tick: {state.get('last_tick_at')}")
    lines.append("")

    lines.append("### Trend 24h")
    lines.append(f"- NEW -> IN_PROGRESS: {to_status_counter.get('IN_PROGRESS', 0)}")
    lines.append(f"- -> WAITING_APPROVAL: {to_status_counter.get('WAITING_APPROVAL', 0)}")
    lines.append(f"- -> RELEASED: {to_status_counter.get('RELEASED', 0)}")
    lines.append("")

    lines.append("### Alert: Tasks Stuck >24h")
    if not blocked_24h:
        lines.append("- none")
    else:
        for t, age in blocked_24h[:5]:
            lines.append(
                f"- {t.get('id')}: {t.get('title')} | status={t.get('status')} | age={age:.1f}h"
            )
    lines.append("")

    lines.append("### Next 3 for Approval")
    if not suggestions:
        lines.append("- none")
    else:
        for t in suggestions:
            lines.append(
                f"- {t.get('id')}: {t.get('title')} | status={t.get('status')} | priority={t.get('priority')}"
            )

    return "\n".join(lines) + "\n"


def comment_daily_insight(comment_body: str) -> None:
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PAT")
    repo = os.getenv("GITHUB_REPOSITORY", "famatyyk/CTOAi")
    issue_number = int(os.getenv("CTOA_LIVE_ISSUE_NUMBER", "1"))
    if not token:
        raise RuntimeError("Missing GITHUB_TOKEN or GITHUB_PAT")

    date_marker = comment_body.splitlines()[0].strip()
    base = f"https://api.github.com/repos/{repo}"
    comments = github_api("GET", f"{base}/issues/{issue_number}/comments?per_page=100", token)

    for c in comments:
        body = str(c.get("body", ""))
        if date_marker in body:
            print(f"[daily-insight] comment already exists for {date_marker}")
            return

    created = github_api(
        "POST",
        f"{base}/issues/{issue_number}/comments",
        token,
        {"body": comment_body},
    )
    print(f"[daily-insight] created comment #{created.get('id')} on issue #{issue_number}")


def main() -> None:
    backlog = load_yaml(BACKLOG_FILE)
    state = load_yaml(STATE_FILE)
    if not backlog:
        raise RuntimeError("Missing or invalid backlog file")
    if not state:
        raise RuntimeError("Missing or invalid runtime state file")

    comment = build_daily_comment(backlog, state)
    print(comment)
    comment_daily_insight(comment)


if __name__ == "__main__":
    main()
