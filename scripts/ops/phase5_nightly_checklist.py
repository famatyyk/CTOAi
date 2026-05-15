#!/usr/bin/env python3
"""Generate a checklist report for the first 3 nightly Phase-5 dry-check runs."""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVIDENCE_DIR = ROOT / "docs" / "evidence" / "vps-worktree-hygiene"
DEFAULT_OUTPUT = DEFAULT_EVIDENCE_DIR / "phase5-nightly-checklist.md"
SNAPSHOT_PREFIX = "phase5-drycheck-"
TIMESTAMP_PATTERN = re.compile(r"^phase5-drycheck-(\d{8}T\d{6}Z)$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate checklist report for first 3 nightly Phase-5 dry-check runs"
    )
    parser.add_argument("--evidence-dir", default=str(DEFAULT_EVIDENCE_DIR))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--json-out", default="")
    parser.add_argument("--target-runs", type=int, default=3)
    parser.add_argument("--nightly-hour", type=int, default=2)
    parser.add_argument("--nightly-minute", type=int, default=20)
    parser.add_argument(
        "--window-minutes",
        type=int,
        default=45,
        help="Allowed delta from scheduled nightly time in minutes",
    )
    parser.add_argument(
        "--require-complete",
        action="store_true",
        help="Return non-zero until all target nightly runs are collected",
    )
    return parser.parse_args()


def _parse_snapshot_timestamp(name: str) -> datetime | None:
    match = TIMESTAMP_PATTERN.match(name)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
    except ValueError:
        return None


def _parse_summary(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    payload: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key:
            payload[key] = value
    return payload


def _nightly_delta_minutes(ts: datetime, nightly_hour: int, nightly_minute: int) -> int:
    scheduled = datetime(ts.year, ts.month, ts.day, nightly_hour, nightly_minute, tzinfo=UTC)
    return int(abs((ts - scheduled).total_seconds()) // 60)


def _build_snapshot_record(
    snapshot_dir: Path,
    ts: datetime,
    nightly_hour: int,
    nightly_minute: int,
    window_minutes: int,
) -> dict[str, Any]:
    summary = _parse_summary(snapshot_dir / "summary.md")

    status_path = snapshot_dir / "status-porcelain.txt"
    porcelain_exists = status_path.exists()
    porcelain_empty: bool | None
    if porcelain_exists:
        porcelain_empty = not status_path.read_text(encoding="utf-8").strip()
    else:
        porcelain_empty = None

    delta_minutes = _nightly_delta_minutes(ts, nightly_hour, nightly_minute)
    nightly_window_match = delta_minutes <= window_minutes

    record: dict[str, Any] = {
        "snapshot": snapshot_dir.name,
        "path": str(snapshot_dir),
        "timestamp_utc": ts.strftime("%Y%m%dT%H%M%SZ"),
        "branch": summary.get("branch", "UNKNOWN"),
        "head": summary.get("head", "UNKNOWN"),
        "result": summary.get("result", "UNKNOWN"),
        "status": summary.get("status", "UNKNOWN"),
        "mirror_policy": summary.get("mirror_policy", "UNKNOWN"),
        "porcelain_exists": porcelain_exists,
        "porcelain_empty": porcelain_empty,
        "nightly_delta_minutes": delta_minutes,
        "nightly_window_match": nightly_window_match,
        "ok": False,
        "alerts": [],
    }
    return record


def _evaluate_nightly_record(record: dict[str, Any]) -> dict[str, Any]:
    alerts: list[str] = []

    if record["result"] != "PASS":
        alerts.append("result_not_pass")
    if record["status"] != "CLEAN":
        alerts.append("status_not_clean")
    if record["branch"] != "main":
        alerts.append("branch_not_main")
    if record["mirror_policy"] != "SATISFIED":
        alerts.append("mirror_policy_not_satisfied")
    if record["porcelain_empty"] is not True:
        alerts.append("porcelain_not_empty")

    record["alerts"] = alerts
    record["ok"] = len(alerts) == 0
    return record


def build_report(
    evidence_dir: Path,
    target_runs: int,
    nightly_hour: int,
    nightly_minute: int,
    window_minutes: int,
) -> dict[str, Any]:
    snapshots: list[dict[str, Any]] = []
    if evidence_dir.exists():
        for child in evidence_dir.iterdir():
            if not child.is_dir() or not child.name.startswith(SNAPSHOT_PREFIX):
                continue
            ts = _parse_snapshot_timestamp(child.name)
            if ts is None:
                continue
            snapshots.append(
                _build_snapshot_record(
                    snapshot_dir=child,
                    ts=ts,
                    nightly_hour=nightly_hour,
                    nightly_minute=nightly_minute,
                    window_minutes=window_minutes,
                )
            )

    snapshots.sort(key=lambda item: item["timestamp_utc"])
    nightly_runs = [_evaluate_nightly_record(dict(item)) for item in snapshots if item["nightly_window_match"]]
    selected_nightly = nightly_runs[:target_runs]
    non_nightly = [item for item in snapshots if not item["nightly_window_match"]]

    alerts_count = sum(1 for item in selected_nightly if not item["ok"])
    pending_runs = max(0, target_runs - len(selected_nightly))

    if alerts_count > 0:
        overall_status = "ATTENTION"
    elif pending_runs > 0:
        overall_status = "IN_PROGRESS"
    else:
        overall_status = "COMPLETE"

    return {
        "generated_utc": datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"),
        "evidence_dir": str(evidence_dir),
        "target_runs": target_runs,
        "nightly_hour": nightly_hour,
        "nightly_minute": nightly_minute,
        "window_minutes": window_minutes,
        "overall_status": overall_status,
        "alerts_count": alerts_count,
        "pending_runs": pending_runs,
        "selected_nightly_runs": len(selected_nightly),
        "nightly_runs": selected_nightly,
        "non_nightly_runs": non_nightly,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Phase-5 Nightly Dry-Check Checklist")
    lines.append("")
    lines.append(f"generated_utc: {report['generated_utc']}")
    lines.append(f"overall_status: {report['overall_status']}")
    lines.append(f"target_runs: {report['target_runs']}")
    lines.append(f"selected_nightly_runs: {report['selected_nightly_runs']}")
    lines.append(f"pending_runs: {report['pending_runs']}")
    lines.append(
        "nightly_schedule_utc: "
        f"{report['nightly_hour']:02d}:{report['nightly_minute']:02d} (+/- {report['window_minutes']} min)"
    )
    lines.append("")
    lines.append("## Checklist")
    lines.append("")

    nightly_runs = report["nightly_runs"]
    for index in range(1, report["target_runs"] + 1):
        if index <= len(nightly_runs):
            run = nightly_runs[index - 1]
            mark = "x" if run["ok"] else " "
            verdict = "OK" if run["ok"] else "ALERT"
            lines.append(
                f"- [{mark}] Run {index}: {run['snapshot']} at {run['timestamp_utc']} ({verdict})"
            )
        else:
            lines.append(f"- [ ] Run {index}: PENDING (no nightly snapshot in configured window)")

    lines.append("")
    lines.append("## Nightly Runs")
    lines.append("")
    lines.append("| Run | Snapshot | Timestamp UTC | Result | Status | Branch | Porcelain Empty | Mirror Policy | Alert |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")

    for index in range(1, report["target_runs"] + 1):
        if index <= len(nightly_runs):
            run = nightly_runs[index - 1]
            alert_text = "NONE" if run["ok"] else ",".join(run["alerts"])
            lines.append(
                "| "
                f"{index} | {run['snapshot']} | {run['timestamp_utc']} | {run['result']} | {run['status']} | "
                f"{run['branch']} | {run['porcelain_empty']} | {run['mirror_policy']} | {alert_text} |"
            )
        else:
            lines.append(f"| {index} | PENDING | - | - | - | - | - | - | PENDING |")

    non_nightly_runs = report["non_nightly_runs"]
    if non_nightly_runs:
        lines.append("")
        lines.append("## Observed Non-Nightly Runs")
        lines.append("")
        lines.append("| Snapshot | Timestamp UTC | Result | Status | Delta To Nightly (min) |")
        lines.append("| --- | --- | --- | --- | --- |")
        for run in non_nightly_runs:
            lines.append(
                f"| {run['snapshot']} | {run['timestamp_utc']} | {run['result']} | "
                f"{run['status']} | {run['nightly_delta_minutes']} |"
            )

    lines.append("")
    lines.append("## Alert Rule")
    lines.append("")
    lines.append("Alert when any nightly run has non-empty status-porcelain or summary result/status differs from PASS/CLEAN.")

    return "\n".join(lines) + "\n"


def determine_exit_code(report: dict[str, Any], require_complete: bool) -> int:
    if report["alerts_count"] > 0:
        return 1
    if require_complete and report["pending_runs"] > 0:
        return 2
    return 0


def main() -> int:
    args = parse_args()
    evidence_dir = Path(args.evidence_dir).resolve()
    output_path = Path(args.output).resolve()
    json_out_path = Path(args.json_out).resolve() if args.json_out else None

    report = build_report(
        evidence_dir=evidence_dir,
        target_runs=args.target_runs,
        nightly_hour=args.nightly_hour,
        nightly_minute=args.nightly_minute,
        window_minutes=args.window_minutes,
    )

    markdown = render_markdown(report)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")

    if json_out_path is not None:
        json_out_path.parent.mkdir(parents=True, exist_ok=True)
        json_out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(
        "[phase5-nightly-checklist] "
        f"status={report['overall_status']} "
        f"nightly_runs={report['selected_nightly_runs']}/{report['target_runs']} "
        f"alerts={report['alerts_count']} "
        f"output={output_path}"
    )

    return determine_exit_code(report, require_complete=args.require_complete)


if __name__ == "__main__":
    raise SystemExit(main())