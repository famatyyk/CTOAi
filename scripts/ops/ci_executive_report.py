#!/usr/bin/env python3
"""Generate a weekly CI executive report for CTOAi.

Outputs weighted CI health scores for configurable windows and
adds top risks plus top remediation actions.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.request
from dataclasses import dataclass
from typing import Dict, List


WEIGHTS: Dict[str, int] = {
    "CTOA Pipeline": 40,
    "CTOA Close On Gate": 15,
    "site-pages": 15,
    "CTOA Status Sync": 10,
    "CTOA Issue Sync": 10,
    "CTOA Daily Insights": 5,
    "CTOA Weekly Report": 5,
}


@dataclass
class WorkflowMetric:
    workflow: str
    completed: int
    success: int
    failed: int
    skipped: int
    success_rate_all: float | None
    success_rate_pass_fail: float | None


def _fetch_json(url: str, token: str | None) -> dict:
    headers = {
        "User-Agent": "CTOA-CI-Executive-Report",
        "Accept": "application/vnd.github+json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_runs(owner: str, repo: str, token: str | None, min_cutoff: dt.datetime) -> list[dict]:
    runs: list[dict] = []
    page = 1
    max_pages = 50

    while page <= max_pages:
        url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs?per_page=100&page={page}"
        payload = _fetch_json(url, token)
        batch = payload.get("workflow_runs", [])
        if not batch:
            break

        runs.extend(batch)
        oldest = dt.datetime.fromisoformat(batch[-1]["created_at"].replace("Z", "+00:00"))
        if oldest < min_cutoff:
            break
        page += 1

    # deduplicate by run id
    seen: set[int] = set()
    unique: list[dict] = []
    for run in runs:
        rid = run.get("id")
        if rid in seen:
            continue
        seen.add(rid)
        unique.append(run)

    return unique


def slice_window(runs: list[dict], cutoff: dt.datetime) -> list[dict]:
    out: list[dict] = []
    for run in runs:
        created = dt.datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
        if created >= cutoff:
            out.append(run)
    return out


def metric_for_workflow(runs: list[dict], workflow_name: str) -> WorkflowMetric:
    wf = [r for r in runs if r.get("name") == workflow_name]
    completed = [r for r in wf if r.get("status") == "completed"]
    success = [r for r in completed if r.get("conclusion") == "success"]
    failed = [r for r in completed if r.get("conclusion") == "failure"]
    skipped = [r for r in completed if r.get("conclusion") == "skipped"]

    success_rate_all = None
    if completed:
        success_rate_all = round((len(success) * 100.0) / len(completed), 1)

    pass_fail_count = len(success) + len(failed)
    success_rate_pass_fail = None
    if pass_fail_count:
        success_rate_pass_fail = round((len(success) * 100.0) / pass_fail_count, 1)

    return WorkflowMetric(
        workflow=workflow_name,
        completed=len(completed),
        success=len(success),
        failed=len(failed),
        skipped=len(skipped),
        success_rate_all=success_rate_all,
        success_rate_pass_fail=success_rate_pass_fail,
    )


def weighted_score(metrics: list[WorkflowMetric]) -> float:
    weighted_sum = 0.0
    weight_total = 0.0

    for m in metrics:
        w = float(WEIGHTS[m.workflow])
        rate = m.success_rate_pass_fail
        if rate is None:
            rate = m.success_rate_all if m.success_rate_all is not None else 50.0
        weighted_sum += rate * w
        weight_total += w

    return round(weighted_sum / weight_total, 1) if weight_total else 0.0


def identify_risks(metrics_7d: list[WorkflowMetric], score_7d: float, score_30d: float) -> list[str]:
    by_name = {m.workflow: m for m in metrics_7d}
    risks: list[str] = []

    pipeline = by_name.get("CTOA Pipeline")
    if pipeline and (pipeline.success_rate_pass_fail or 0.0) < 40.0:
        risks.append(
            f"CTOA Pipeline pass/fail success remains low at {pipeline.success_rate_pass_fail or 0.0:.1f}%, reducing overall delivery confidence."
        )

    if score_7d < score_30d:
        risks.append(
            f"7-day CI Health Score ({score_7d:.1f}) is below 30-day baseline ({score_30d:.1f}), indicating short-term reliability regression."
        )

    pages = by_name.get("site-pages")
    if pages and (pages.success_rate_pass_fail or 0.0) < 90.0:
        risks.append(
            f"site-pages reliability is at {pages.success_rate_pass_fail or 0.0:.1f}% pass/fail success; publication lane has low resilience."
        )

    if len(risks) < 3:
        risks.append("Approval-gated runs can remain in waiting state and delay release throughput if review SLA is not enforced.")

    return risks[:3]


def remediation_actions(metrics_7d: list[WorkflowMetric]) -> list[str]:
    by_name = {m.workflow: m for m in metrics_7d}
    pipeline = by_name.get("CTOA Pipeline")
    pages = by_name.get("site-pages")

    actions = [
        (
            "Pipeline hardening sprint",
            f"Run daily failure triage on `CTOA Pipeline` and target pass/fail success >= 40% in 7 days (current: {(pipeline.success_rate_pass_fail or 0.0):.1f}%).",
        ),
        (
            "Approval SLA enforcement",
            "Set explicit `Approval Publish` response SLA (for example 60 minutes), plus waiting-run watch and escalation.",
        ),
        (
            "Pages preflight and stability",
            f"Keep preflight checks in `site-pages` and target >= 95% pass/fail success over the next 5 runs (current: {(pages.success_rate_pass_fail or 0.0):.1f}%).",
        ),
    ]

    return [f"{title}: {desc}" for title, desc in actions]


def render_markdown(
    generated_at: dt.datetime,
    owner_repo: str,
    windows: list[int],
    by_window: dict[int, list[WorkflowMetric]],
    scores: dict[int, float],
) -> str:
    lines: list[str] = []
    lines.append("# CTOA CI Executive Report")
    lines.append("")
    lines.append(f"- Repository: `{owner_repo}`")
    lines.append(f"- Generated at (UTC): `{generated_at.isoformat(timespec='seconds')}`")
    lines.append("")
    lines.append("## CI Health Score")
    lines.append("")
    for window in windows:
        lines.append(f"- `{window}d`: **{scores[window]:.1f} / 100**")
    lines.append("")

    for window in windows:
        lines.append(f"## Workflow Metrics ({window}d)")
        lines.append("")
        lines.append("| Workflow | Completed | Success | Failed | Skipped | Success % (all completed) | Success % (pass/fail only) |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|")
        for m in sorted(by_window[window], key=lambda x: x.workflow.lower()):
            rate_all = "n/a" if m.success_rate_all is None else f"{m.success_rate_all:.1f}%"
            rate_pf = "n/a" if m.success_rate_pass_fail is None else f"{m.success_rate_pass_fail:.1f}%"
            lines.append(
                f"| {m.workflow} | {m.completed} | {m.success} | {m.failed} | {m.skipped} | {rate_all} | {rate_pf} |"
            )
        lines.append("")

    risks = identify_risks(by_window[windows[0]], scores[windows[0]], scores[windows[-1]])
    actions = remediation_actions(by_window[windows[0]])

    lines.append("## Top 3 Risks")
    lines.append("")
    for idx, risk in enumerate(risks, 1):
        lines.append(f"{idx}. {risk}")
    lines.append("")

    lines.append("## Top 3 Remediation Actions")
    lines.append("")
    for idx, action in enumerate(actions, 1):
        lines.append(f"{idx}. {action}")
    lines.append("")

    lines.append("## Notes")
    lines.append("")
    lines.append("- Scores are weighted by workflow criticality.")
    lines.append("- Pass/fail-only rate excludes skipped runs to reduce false pessimism on gate workflows.")
    lines.append("- This report is intended for executive trend tracking and weekly remediation planning.")
    lines.append("")

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate CTOA CI executive weekly report")
    parser.add_argument("--output", default="artifacts/ci-executive-weekly.md", help="Output markdown path")
    parser.add_argument("--window-days", nargs="+", type=int, default=[7, 30], help="Window sizes in days")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    windows = sorted(set(args.window_days))
    if not windows:
        print("No windows provided.", file=sys.stderr)
        return 2

    repo = os.getenv("GITHUB_REPOSITORY", "famatyyk/CTOAi")
    if "/" not in repo:
        print("Invalid GITHUB_REPOSITORY format.", file=sys.stderr)
        return 2
    owner, name = repo.split("/", 1)

    token = os.getenv("GITHUB_TOKEN")
    now = dt.datetime.now(dt.timezone.utc)
    max_window = max(windows)
    min_cutoff = now - dt.timedelta(days=max_window)

    runs = fetch_runs(owner, name, token, min_cutoff)

    by_window: dict[int, list[WorkflowMetric]] = {}
    scores: dict[int, float] = {}
    for window in windows:
        cutoff = now - dt.timedelta(days=window)
        sliced = slice_window(runs, cutoff)
        metrics = [metric_for_workflow(sliced, workflow_name) for workflow_name in WEIGHTS]
        by_window[window] = metrics
        scores[window] = weighted_score(metrics)

    report = render_markdown(now, f"{owner}/{name}", windows, by_window, scores)
    output_path = args.output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(report)

    print(f"Report written to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
