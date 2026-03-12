#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import yaml

# Import AI agent executor
try:
    from agents import execute_agent_for_task
except ImportError:
    from runner.agents import execute_agent_for_task

ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_BACKLOG = ROOT / "workflows" / "backlog-sprint-001.yaml"
_BACKLOG_RAW = os.environ.get("CTOA_BACKLOG_FILE", str(_DEFAULT_BACKLOG))
BACKLOG_FILE = Path(_BACKLOG_RAW)
if not BACKLOG_FILE.is_absolute():
    BACKLOG_FILE = ROOT / BACKLOG_FILE
STATE_FILE = ROOT / "runtime" / "task-state.yaml"

STATUS_FLOW = [
    "NEW",
    "IN_PROGRESS",
    "IN_QA",
    "IN_CI_GATE",
    "WAITING_APPROVAL",
    "RELEASED",
    "BLOCKED",
]

AUTO_TRANSITIONS = {
    "IN_PROGRESS": (2, "IN_QA"),
    "IN_QA": (1, "IN_CI_GATE"),
    "IN_CI_GATE": (1, "WAITING_APPROVAL"),
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Invalid YAML object in {path}")
    return data


def save_yaml(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, sort_keys=False, allow_unicode=False)


def load_backlog() -> Dict[str, Any]:
    if not BACKLOG_FILE.exists():
        raise FileNotFoundError(f"Missing backlog file: {BACKLOG_FILE}")
    return load_yaml(BACKLOG_FILE)


def init_state(backlog: Dict[str, Any]) -> Dict[str, Any]:
    tasks = backlog.get("tasks", [])
    if not isinstance(tasks, list):
        raise ValueError("Invalid backlog format: tasks must be a list")

    state_tasks: List[Dict[str, Any]] = []
    for t in tasks:
        if not isinstance(t, dict):
            continue
        state_tasks.append(
            {
                "id": t.get("id"),
                "title": t.get("title", ""),
                "priority": t.get("priority", "P1"),
                "type": t.get("type", "code"),
                "domain": t.get("domain", []),
                "assignees": t.get("assignees", []),
                "deliverables": t.get("deliverables", []),
                "status": "NEW",
                "ticks_in_status": 0,
                "updated_at": now_iso(),
            }
        )

    return {
        "backlog_id": backlog.get("backlog_id", "unknown"),
        "last_tick_at": None,
        "tasks": state_tasks,
        "history": [],
    }


def load_state(backlog: Dict[str, Any]) -> Dict[str, Any]:
    if not STATE_FILE.exists():
        state = init_state(backlog)
        save_yaml(STATE_FILE, state)
        return state

    state = load_yaml(STATE_FILE)
    if "tasks" not in state or not isinstance(state["tasks"], list):
        state = init_state(backlog)
        save_yaml(STATE_FILE, state)
        return state

    # Switch to fresh state when a new backlog is selected.
    if state.get("backlog_id") != backlog.get("backlog_id"):
        state = init_state(backlog)
        save_yaml(STATE_FILE, state)
    return state


def status_rank(status: str) -> int:
    try:
        return STATUS_FLOW.index(status)
    except ValueError:
        return 999


def priority_rank(priority: str) -> int:
    order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    return order.get(priority, 9)


def transition_task(task: Dict[str, Any], new_status: str, reason: str) -> Dict[str, Any]:
    old_status = str(task.get("status", "UNKNOWN"))
    task["status"] = new_status
    task["ticks_in_status"] = 0
    task["updated_at"] = now_iso()
    task.setdefault("notes", []).append({"at": now_iso(), "reason": reason, "status": new_status})
    return {
        "at": now_iso(),
        "event": "transition",
        "task_id": task.get("id"),
        "from_status": old_status,
        "to_status": new_status,
        "reason": reason,
    }


def tick(backlog: Dict[str, Any], state: Dict[str, Any], invoke_agents: bool = False) -> Dict[str, Any]:
    max_parallel = int(backlog.get("rules", {}).get("max_parallel_tasks", 3))
    tasks = state.get("tasks", [])
    transitions: List[Dict[str, Any]] = []

    for task in tasks:
        status = task.get("status", "NEW")
        if status in AUTO_TRANSITIONS:
            task["ticks_in_status"] = int(task.get("ticks_in_status", 0)) + 1
            limit, target = AUTO_TRANSITIONS[status]
            if task["ticks_in_status"] >= limit:
                transitions.append(transition_task(task, target, f"auto transition {status} -> {target}"))

    active_states = {"IN_PROGRESS", "IN_QA", "IN_CI_GATE", "WAITING_APPROVAL"}
    active_count = sum(1 for t in tasks if t.get("status") in active_states)

    candidates = [t for t in tasks if t.get("status") == "NEW"]
    candidates.sort(key=lambda t: (priority_rank(str(t.get("priority", "P1"))), str(t.get("id", ""))))

    for task in candidates:
        if active_count >= max_parallel:
            break
        transitions.append(transition_task(task, "IN_PROGRESS", "scheduled by hourly planner"))
        
        # If agents are enabled, invoke agent immediately when task starts
        if invoke_agents:
            agent_event = execute_task_agent(task, backlog)
            state.setdefault("history", []).append(agent_event)
        
        active_count += 1

    state["last_tick_at"] = now_iso()
    state.setdefault("history", []).extend(transitions)
    state.setdefault("history", []).append({"at": now_iso(), "event": "tick", "active": active_count})
    return state


def approve_task(state: Dict[str, Any], task_id: str) -> Dict[str, Any]:
    for task in state.get("tasks", []):
        if str(task.get("id")) == task_id:
            if task.get("status") != "WAITING_APPROVAL":
                raise ValueError(f"Task {task_id} is not in WAITING_APPROVAL")
            state.setdefault("history", []).append(transition_task(task, "RELEASED", "manual approval"))
            state.setdefault("history", []).append({"at": now_iso(), "event": "approval", "task_id": task_id})
            return state
    raise ValueError(f"Task not found: {task_id}")


def execute_task_agent(task: Dict[str, Any], backlog: Dict[str, Any]) -> Dict[str, Any]:
    """
    Invoke AI agent to execute task and generate deliverables.
    Routes to specific agent based on task domain/type.
    """
    task_id = task.get("id", "unknown")
    print(f"[runner] Invoking AI agent for {task_id}")
    
    try:
        # Route to appropriate agent
        result = execute_agent_for_task(task)
        return {
            "at": now_iso(),
            "event": "agent_exec",
            "task_id": task_id,
            "status": result.get("status", "initiated"),
            "agent_result": result
        }
    except Exception as e:
        print(f"[runner] Agent execution failed for {task_id}: {e}")
        return {
            "at": now_iso(),
            "event": "agent_exec_error",
            "task_id": task_id,
            "error": str(e)
        }


def build_report(backlog: Dict[str, Any], state: Dict[str, Any]) -> str:
    tasks = state.get("tasks", [])
    counts = Counter([str(t.get("status", "UNKNOWN")) for t in tasks])
    total_tasks = len(tasks)
    released_count = counts.get("RELEASED", 0)
    progress_pct = (released_count / total_tasks * 100.0) if total_tasks > 0 else 0.0

    lines = []
    lines.append("# CTOA Live Status")
    lines.append("")
    lines.append(f"- Generated: {now_iso()}")
    lines.append(f"- Backlog: {backlog.get('backlog_id', 'unknown')}")
    lines.append(f"- Last tick: {state.get('last_tick_at')}")
    lines.append(f"- Sprint progress: {progress_pct:.1f}% ({released_count}/{total_tasks})")
    lines.append("")

    lines.append("## Sprint Progress")
    lines.append(f"- Completed: {released_count}")
    lines.append(f"- Total: {total_tasks}")
    lines.append(f"- Progress: {progress_pct:.1f}%")
    lines.append("")

    lines.append("## Status Counts")
    for status in STATUS_FLOW:
        lines.append(f"- {status}: {counts.get(status, 0)}")

    lines.append("")
    lines.append("## Active Tasks")
    active = [
        t
        for t in tasks
        if t.get("status") in {"IN_PROGRESS", "IN_QA", "IN_CI_GATE", "WAITING_APPROVAL"}
    ]
    active.sort(key=lambda t: (status_rank(str(t.get("status"))), priority_rank(str(t.get("priority"))), str(t.get("id"))))

    if not active:
        lines.append("- none")
    else:
        for t in active:
            lines.append(
                f"- {t.get('id')}: {t.get('title')} | {t.get('status')} | {t.get('priority')} | assignees={','.join(t.get('assignees', []))}"
            )

    lines.append("")
    lines.append("## Waiting Approval")
    waiting = [t for t in tasks if t.get("status") == "WAITING_APPROVAL"]
    if not waiting:
        lines.append("- none")
    else:
        for t in waiting:
            lines.append(f"- {t.get('id')}: {t.get('title')}")

    lines.append("")
    lines.append("## Top Blockers")
    blocked = [t for t in tasks if t.get("status") == "BLOCKED"]
    blocked.sort(key=lambda t: (priority_rank(str(t.get("priority", "P1"))), str(t.get("id", ""))))
    if not blocked:
        lines.append("- none")
    else:
        for t in blocked[:3]:
            notes = t.get("notes", [])
            reason = "no reason captured"
            if isinstance(notes, list) and notes:
                last_note = notes[-1]
                reason = str(last_note.get("reason", reason))
            lines.append(f"- {t.get('id')}: {t.get('title')} | {t.get('priority')} | reason={reason}")

    lines.append("")
    lines.append("## ETA to Next Approval")
    if waiting:
        lines.append("- now (task already waiting for approval)")
    else:
        in_ci_gate = [t for t in tasks if t.get("status") == "IN_CI_GATE"]
        in_qa = [t for t in tasks if t.get("status") == "IN_QA"]
        in_progress = [t for t in tasks if t.get("status") == "IN_PROGRESS"]

        # Current automation moves one status step per hourly cycle.
        eta_hours: Optional[int] = None
        if in_ci_gate:
            eta_hours = 1
        elif in_qa:
            eta_hours = 2
        elif in_progress:
            eta_hours = 3

        if eta_hours is None:
            lines.append("- unknown (no active tasks in pipeline)")
        else:
            lines.append(f"- approx {eta_hours}h (based on hourly auto-transitions)")

    return "\n".join(lines) + "\n"


def github_api(method: str, url: str, token: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    data = None
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Authorization": f"Bearer {token}",
        "User-Agent": "ctoa-runner",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = Request(url=url, method=method, headers=headers, data=data)
    with urlopen(req, timeout=30) as res:
        body = res.read().decode("utf-8")
        return json.loads(body) if body else {}


def upsert_live_issue(markdown: str) -> None:
    token = os.getenv("GITHUB_PAT")
    repo = os.getenv("GITHUB_REPOSITORY", "famatyyk/CTOAi")
    issue_title = os.getenv("CTOA_LIVE_ISSUE_TITLE", "CTOA Live Status")

    if not token:
        print("[report] GITHUB_PAT is not set, skipping GitHub publish")
        return

    base = f"https://api.github.com/repos/{repo}"
    query = f"{base}/issues?state=open&per_page=100"
    issues = github_api("GET", query, token)

    target_issue = None
    for item in issues:
        if item.get("title") == issue_title and "pull_request" not in item:
            target_issue = item
            break

    if target_issue is None:
        created = github_api(
            "POST",
            f"{base}/issues",
            token,
            {"title": issue_title, "body": markdown},
        )
        print(f"[report] Created issue #{created.get('number')} for live status")
        return

    updated = github_api(
        "PATCH",
        f"{base}/issues/{target_issue['number']}",
        token,
        {"body": markdown},
    )
    print(f"[report] Updated issue #{updated.get('number')} for live status")


def main() -> None:
    parser = argparse.ArgumentParser(description="CTOA VPS runner")
    sub = parser.add_subparsers(dest="command", required=True)

    tick_p = sub.add_parser("tick", help="Advance scheduler state")
    tick_p.add_argument("--agents", action="store_true", help="Invoke AI agents for new tasks")

    approve_p = sub.add_parser("approve", help="Manually approve task in WAITING_APPROVAL")
    approve_p.add_argument("--task", required=True, help="Task ID, e.g. CTOA-001")

    report_p = sub.add_parser("report", help="Generate live report")
    report_p.add_argument("--publish", action="store_true", help="Publish report to GitHub issue")

    args = parser.parse_args()

    backlog = load_backlog()
    state = load_state(backlog)

    if args.command == "tick":
        invoke_agents = getattr(args, "agents", False)
        state = tick(backlog, state, invoke_agents=invoke_agents)
        save_yaml(STATE_FILE, state)
        print(f"[tick] completed at {state.get('last_tick_at')}")
        if invoke_agents:
            print(f"[tick] AI agents invoked for new tasks")
        return

    if args.command == "approve":
        state = approve_task(state, args.task)
        save_yaml(STATE_FILE, state)
        print(f"[approve] released task {args.task}")
        return

    if args.command == "report":
        markdown = build_report(backlog, state)
        print(markdown)
        if args.publish:
            try:
                upsert_live_issue(markdown)
            except HTTPError as ex:
                print(f"[report] GitHub API error: {ex.code} {ex.reason}")
                raise
        return


if __name__ == "__main__":
    main()
