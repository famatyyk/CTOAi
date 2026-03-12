#!/usr/bin/env python3
"""Summarize CTOA health trends from health-history.jsonl."""

import argparse
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_HISTORY = ROOT / "runtime" / "health-history.jsonl"


def parse_iso(ts: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def read_rows(path: Path) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    if not path.exists():
        return rows

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def avg(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def summarize_window(rows: List[Dict[str, object]], since: datetime) -> Dict[str, object]:
    cpu_vals: List[float] = []
    mem_vals: List[float] = []
    disk_vals: List[float] = []
    cpu_alerts = 0
    mem_alerts = 0
    disk_alerts = 0
    process_alerts = 0

    for row in rows:
        metrics = row.get("metrics") or {}
        alerts = row.get("alerts") or []
        ts = parse_iso(str(metrics.get("timestamp", "")))
        if not ts or ts < since:
            continue

        cpu = metrics.get("cpu_pct")
        mem = metrics.get("memory_used_pct")
        disk = metrics.get("disk_used_pct")
        if isinstance(cpu, (float, int)):
            cpu_vals.append(float(cpu))
        if isinstance(mem, (float, int)):
            mem_vals.append(float(mem))
        if isinstance(disk, (float, int)):
            disk_vals.append(float(disk))

        for alert in alerts:
            text = str(alert)
            if text.startswith("CPU high"):
                cpu_alerts += 1
            elif text.startswith("Memory high"):
                mem_alerts += 1
            elif text.startswith("Disk high"):
                disk_alerts += 1
            elif text.startswith("Process not running"):
                process_alerts += 1

    return {
        "samples": len(cpu_vals) or len(mem_vals) or len(disk_vals),
        "cpu_avg": avg(cpu_vals),
        "cpu_max": round(max(cpu_vals), 2) if cpu_vals else None,
        "mem_avg": avg(mem_vals),
        "mem_max": round(max(mem_vals), 2) if mem_vals else None,
        "disk_avg": avg(disk_vals),
        "disk_max": round(max(disk_vals), 2) if disk_vals else None,
        "alerts": {
            "cpu": cpu_alerts,
            "memory": mem_alerts,
            "disk": disk_alerts,
            "process": process_alerts,
            "total": cpu_alerts + mem_alerts + disk_alerts + process_alerts,
        },
    }


def print_window(label: str, summary: Dict[str, object]) -> None:
    print(f"## {label}")
    print(f"samples={summary['samples']}")
    print(
        "cpu_avg={cpu_avg}% cpu_max={cpu_max}% | mem_avg={mem_avg}% mem_max={mem_max}% | "
        "disk_avg={disk_avg}% disk_max={disk_max}%".format(**summary)
    )
    alerts = summary["alerts"]
    print(
        f"alerts total={alerts['total']} (cpu={alerts['cpu']}, mem={alerts['memory']}, "
        f"disk={alerts['disk']}, process={alerts['process']})"
    )
    print("")


def main() -> int:
    parser = argparse.ArgumentParser(description="CTOA health trend summary")
    parser.add_argument("--history", type=str, default=str(DEFAULT_HISTORY), help="Path to health-history.jsonl")
    parser.add_argument("--hours", type=int, default=24, help="Custom summary window in hours")
    args = parser.parse_args()

    history_path = Path(args.history)
    rows = read_rows(history_path)
    now = datetime.now(timezone.utc)

    windows = {
        f"Last {args.hours}h": now - timedelta(hours=max(1, args.hours)),
        "Last 24h": now - timedelta(hours=24),
        "Last 7d": now - timedelta(days=7),
    }

    print(f"# CTOA Health Trend Summary\nsource={history_path}\n")
    for label, since in windows.items():
        print_window(label, summarize_window(rows, since))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
