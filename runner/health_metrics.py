#!/usr/bin/env python3
"""CTOA VPS Health Metrics Collector with optional live watch mode."""

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

# Configuration
ROOT = Path(__file__).resolve().parent.parent
RUNTIME_DIR = ROOT / "runtime"
HEALTH_LATEST_FILE = RUNTIME_DIR / "health-latest.json"
HEALTH_HISTORY_FILE = RUNTIME_DIR / "health-history.jsonl"

VPS_HOST = os.environ.get("CTOA_VPS_HOST") or socket.gethostname()
GITHUB_PAT = os.environ.get("CTOA_GITHUB_PAT") or os.environ.get("GITHUB_PAT")
REPO_OWNER = os.environ.get("CTOA_REPO_OWNER", "famatyyk")
REPO_NAME = os.environ.get("CTOA_REPO_NAME", "CTOAi")
HEALTH_ISSUE_ID = int(os.environ.get("CTOA_HEALTH_ISSUE_ID", "2"))


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_proc_stat_totals() -> Optional[Tuple[int, int]]:
    path = Path("/proc/stat")
    if not path.exists():
        return None
    line = path.read_text(encoding="utf-8", errors="ignore").splitlines()[0]
    parts = [int(x) for x in line.split()[1:8]]
    user, nice, system_v, idle, iowait, irq, softirq = parts
    idle_all = idle + iowait
    total = user + nice + system_v + idle + iowait + irq + softirq
    return total, idle_all


def read_cpu_percent(sample_seconds: float = 0.2) -> Optional[float]:
    first = _read_proc_stat_totals()
    if first is not None:
        time.sleep(sample_seconds)
        second = _read_proc_stat_totals()
        if second is None:
            return None
        total_delta = second[0] - first[0]
        idle_delta = second[1] - first[1]
        if total_delta <= 0:
            return 0.0
        busy = total_delta - idle_delta
        return round((busy / total_delta) * 100.0, 2)

    if os.name == "nt":
        cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            "(Get-Counter '\\Processor(_Total)\\% Processor Time').CounterSamples[0].CookedValue",
        ]
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        if out.returncode == 0:
            raw = out.stdout.strip().replace(",", ".")
            try:
                return round(float(raw), 2)
            except ValueError:
                pass

        fallback = subprocess.run(["wmic", "cpu", "get", "loadpercentage", "/value"], capture_output=True, text=True, timeout=5)
        if fallback.returncode == 0:
            for line in fallback.stdout.splitlines():
                if line.lower().startswith("loadpercentage="):
                    raw = line.split("=", 1)[1].strip()
                    if raw.isdigit():
                        return float(raw)
    return None


def read_memory_percent() -> Tuple[Optional[float], Optional[int], Optional[int]]:
    meminfo = Path("/proc/meminfo")
    if not meminfo.exists():
        if os.name == "nt":
            cmd = [
                "powershell",
                "-NoProfile",
                "-Command",
                "$os=Get-CimInstance Win32_OperatingSystem; @{total=[double]$os.TotalVisibleMemorySize;free=[double]$os.FreePhysicalMemory} | ConvertTo-Json -Compress",
            ]
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if out.returncode != 0:
                return None, None, None

            try:
                payload = json.loads(out.stdout.strip())
            except json.JSONDecodeError:
                return None, None, None

            total_kib = int(payload.get("total", 0))
            free_kib = int(payload.get("free", 0))
            if not total_kib or free_kib is None:
                return None, None, None

            used_kib = total_kib - free_kib
            used_pct = round((used_kib / total_kib) * 100.0, 2)
            return used_pct, used_kib // 1024, total_kib // 1024
        return None, None, None

    values: Dict[str, int] = {}
    for line in meminfo.read_text(encoding="utf-8", errors="ignore").splitlines():
        key, raw = line.split(":", 1)
        val = raw.strip().split()[0]
        values[key] = int(val)

    total_kib = values.get("MemTotal")
    avail_kib = values.get("MemAvailable")
    if not total_kib or avail_kib is None:
        return None, None, None

    used_kib = total_kib - avail_kib
    used_pct = round((used_kib / total_kib) * 100.0, 2)
    return used_pct, used_kib // 1024, total_kib // 1024


def read_disk_percent(path: str = "/") -> Tuple[float, int, int]:
    usage = shutil.disk_usage(path)
    used = usage.total - usage.free
    used_pct = round((used / usage.total) * 100.0, 2)
    return used_pct, used // (1024 * 1024 * 1024), usage.total // (1024 * 1024 * 1024)


def read_uptime_human() -> str:
    uptime_file = Path("/proc/uptime")
    if uptime_file.exists():
        seconds = int(float(uptime_file.read_text(encoding="utf-8").split()[0]))
        days, rem = divmod(seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, _ = divmod(rem, 60)
        parts: List[str] = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        parts.append(f"{minutes}m")
        return " ".join(parts)

    result = subprocess.run(["uptime", "-p"], capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        return result.stdout.strip()
    return "unknown"


def read_load_average() -> Optional[Tuple[float, float, float]]:
    try:
        return tuple(round(x, 2) for x in os.getloadavg())
    except OSError:
        return None


def check_processes(processes_to_check: List[str]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    if os.name == "nt":
        ps = subprocess.run(["tasklist"], capture_output=True, text=True, timeout=5)
        if ps.returncode != 0:
            for p in processes_to_check:
                result[p] = "unknown"
            return result
        output = ps.stdout.lower()
        for proc in processes_to_check:
            proc_base = proc.lower().replace(".exe", "")
            result[proc] = "running" if (f"{proc_base}.exe" in output or proc_base in output) else "not_found"
        return result

    ps = subprocess.run(["ps", "-eo", "comm"], capture_output=True, text=True, timeout=5)
    if ps.returncode != 0:
        for p in processes_to_check:
            result[p] = "unknown"
        return result

    running = set(line.strip() for line in ps.stdout.splitlines() if line.strip())
    for proc in processes_to_check:
        result[proc] = "running" if proc in running else "not_found"
    return result


def collect_metrics() -> Dict[str, object]:
    """Collect VPS system metrics from Linux runtime data."""
    metrics: Dict[str, object] = {
        "timestamp": now_iso(),
        "host": VPS_HOST,
        "cpu_pct": None,
        "memory_used_pct": None,
        "memory_used_mb": None,
        "memory_total_mb": None,
        "disk_used_pct": None,
        "disk_used_gb": None,
        "disk_total_gb": None,
        "loadavg": None,
        "processes": {},
        "uptime": "unknown",
    }

    errors: List[str] = []

    try:
        metrics["cpu_pct"] = read_cpu_percent()
    except Exception as ex:  # pragma: no cover - defensive fallback
        errors.append(f"cpu: {ex}")

    try:
        mem_pct, mem_used_mb, mem_total_mb = read_memory_percent()
        metrics["memory_used_pct"] = mem_pct
        metrics["memory_used_mb"] = mem_used_mb
        metrics["memory_total_mb"] = mem_total_mb
    except Exception as ex:  # pragma: no cover - defensive fallback
        errors.append(f"memory: {ex}")

    try:
        disk_root = "/" if os.name != "nt" else (os.environ.get("SystemDrive", "C:") + "\\")
        disk_pct, disk_used_gb, disk_total_gb = read_disk_percent(disk_root)
        metrics["disk_used_pct"] = disk_pct
        metrics["disk_used_gb"] = disk_used_gb
        metrics["disk_total_gb"] = disk_total_gb
    except Exception as ex:  # pragma: no cover - defensive fallback
        errors.append(f"disk: {ex}")

    try:
        metrics["loadavg"] = read_load_average()
    except Exception as ex:  # pragma: no cover - defensive fallback
        errors.append(f"loadavg: {ex}")

    try:
        default_processes = ["python3", "sshd", "systemd"] if os.name != "nt" else ["python", "powershell"]
        metrics["processes"] = check_processes(default_processes)
    except Exception as ex:  # pragma: no cover - defensive fallback
        errors.append(f"processes: {ex}")

    try:
        metrics["uptime"] = read_uptime_human()
    except Exception as ex:  # pragma: no cover - defensive fallback
        errors.append(f"uptime: {ex}")

    if errors:
        metrics["error"] = "; ".join(errors)

    return metrics


def check_thresholds(metrics: Dict[str, object]) -> List[str]:
    alerts: List[str] = []
    cpu = metrics.get("cpu_pct")
    mem = metrics.get("memory_used_pct")
    disk = metrics.get("disk_used_pct")

    if isinstance(cpu, (float, int)) and cpu >= 85.0:
        alerts.append(f"CPU high: {cpu}%")
    if isinstance(mem, (float, int)) and mem >= 90.0:
        alerts.append(f"Memory high: {mem}%")
    if isinstance(disk, (float, int)) and disk >= 90.0:
        alerts.append(f"Disk high: {disk}%")

    for proc, status in (metrics.get("processes") or {}).items():
        if status != "running":
            alerts.append(f"Process not running: {proc}")

    return alerts


def format_health_dashboard(metrics: Dict[str, object], alerts: List[str]) -> str:
    """Format metrics as GitHub Issue markdown."""
    timestamp = str(metrics.get("timestamp", "unknown"))
    loadavg = metrics.get("loadavg")
    if isinstance(loadavg, tuple):
        loadavg_text = "/".join(str(x) for x in loadavg)
    else:
        loadavg_text = "n/a"

    lines: List[str] = []
    lines.append("## VPS Health Dashboard")
    lines.append(f"**Updated:** {timestamp}")
    lines.append(f"**Host:** {metrics.get('host', 'unknown')}")
    lines.append("")
    lines.append("### System Status")
    lines.append(f"- **Uptime:** {metrics.get('uptime', 'unknown')}")
    lines.append(f"- **CPU:** {metrics.get('cpu_pct', 'n/a')}%")
    lines.append(
        f"- **Memory:** {metrics.get('memory_used_pct', 'n/a')}% "
        f"({metrics.get('memory_used_mb', 'n/a')}MB / {metrics.get('memory_total_mb', 'n/a')}MB)"
    )
    lines.append(
        f"- **Disk /**: {metrics.get('disk_used_pct', 'n/a')}% "
        f"({metrics.get('disk_used_gb', 'n/a')}GB / {metrics.get('disk_total_gb', 'n/a')}GB)"
    )
    lines.append(f"- **Load avg (1m/5m/15m):** {loadavg_text}")
    lines.append("")
    lines.append("### Key Processes")
    for proc, status in (metrics.get("processes") or {}).items():
        lines.append(f"- `{proc}`: {status}")

    if "error" in metrics:
        lines.append("")
        lines.append("### Errors")
        lines.append(f"`{metrics['error']}`")

    lines.append("")
    lines.append("### Alerts")
    if alerts:
        for alert in alerts:
            lines.append(f"- ALERT: {alert}")
    else:
        lines.append("- OK: no active alerts")
    lines.append(f"- Last check: {timestamp}")
    lines.append("")
    lines.append("---")
    lines.append(
        f"*Dashboard auto-updated* | "
        f"[View metrics](https://github.com/{REPO_OWNER}/{REPO_NAME}/issues/{HEALTH_ISSUE_ID})"
    )
    lines.append("")
    return "\n".join(lines)


def publish_to_github(dashboard_md: str) -> bool:
    """Publish health dashboard to GitHub Issue #2 as a comment."""
    if not GITHUB_PAT:
        print("[health] GITHUB_PAT/CTOA_GITHUB_PAT not set, skipping publish")
        return False

    api_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues/{HEALTH_ISSUE_ID}/comments"
    headers = {
        "Authorization": f"Bearer {GITHUB_PAT}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    payload = {"body": dashboard_md}
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=15)
        if response.status_code == 201:
            print(f"[health] Published health dashboard to Issue #{HEALTH_ISSUE_ID}")
            return True
        print(f"[health] GitHub API returned {response.status_code}")
        print(response.text[:500])
        return False
    except Exception as ex:  # pragma: no cover - network dependent
        print(f"[health] Failed to publish: {ex}")
        return False


def persist_snapshot(metrics: Dict[str, object], alerts: List[str]) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"metrics": metrics, "alerts": alerts}
    HEALTH_LATEST_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    with HEALTH_HISTORY_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=True) + "\n")


def print_live_line(metrics: Dict[str, object], alerts: List[str]) -> None:
    cpu = metrics.get("cpu_pct", "n/a")
    mem = metrics.get("memory_used_pct", "n/a")
    disk = metrics.get("disk_used_pct", "n/a")
    ts = metrics.get("timestamp", "?")
    alert_tag = "ALERT" if alerts else "OK"
    print(f"[{ts}] CPU={cpu}% MEM={mem}% DISK={disk}% STATUS={alert_tag}")
    if alerts:
        for alert in alerts:
            print(f"  - {alert}")


def run_once(publish: bool) -> int:
    metrics = collect_metrics()
    alerts = check_thresholds(metrics)
    persist_snapshot(metrics, alerts)
    print_live_line(metrics, alerts)

    if publish:
        dashboard = format_health_dashboard(metrics, alerts)
        if not publish_to_github(dashboard):
            return 1
    return 0


def run_watch(interval: int, samples: int, publish: bool, cpu_sustain: int = 3) -> int:
    """Watch mode with CPU alert debounce: alert only after cpu_sustain consecutive high samples."""
    cpu_streak = 0
    iteration = 0
    while True:
        iteration += 1
        metrics = collect_metrics()
        raw_alerts = check_thresholds(metrics)

        # Debounce CPU: split out CPU alerts and only fire after sustained streak
        cpu_alerts = [a for a in raw_alerts if a.startswith("CPU high")]
        other_alerts = [a for a in raw_alerts if not a.startswith("CPU high")]

        if cpu_alerts:
            cpu_streak += 1
        else:
            cpu_streak = 0

        # Attach CPU alert only once streak threshold is reached
        alerts = other_alerts + (cpu_alerts if cpu_streak >= cpu_sustain else [])
        if cpu_alerts and cpu_streak < cpu_sustain:
            print(f"  [CPU spike {cpu_streak}/{cpu_sustain}, holding alert]")

        persist_snapshot(metrics, alerts)
        print_live_line(metrics, alerts)

        if publish:
            dashboard = format_health_dashboard(metrics, alerts)
            publish_to_github(dashboard)

        if samples > 0 and iteration >= samples:
            return 0
        time.sleep(max(1, interval))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CTOA health monitor")
    parser.add_argument("--watch", action="store_true", help="Run in live watch mode")
    parser.add_argument("--interval", type=int, default=10, help="Watch interval in seconds")
    parser.add_argument("--samples", type=int, default=0, help="Stop after N samples (0 = infinite)")
    parser.add_argument(
        "--cpu-sustain-samples",
        type=int,
        default=3,
        help="Consecutive high-CPU samples required before firing alert (default: 3, ~30s at 10s interval)",
    )
    parser.add_argument("--publish", dest="publish", action="store_true", help="Publish to GitHub Issue")
    parser.add_argument("--no-publish", dest="publish", action="store_false", help="Do not publish to GitHub")
    parser.set_defaults(publish=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.watch:
        return run_watch(
            interval=args.interval,
            samples=args.samples,
            publish=args.publish,
            cpu_sustain=args.cpu_sustain_samples,
        )
    return run_once(publish=args.publish)


if __name__ == "__main__":
    sys.exit(main())
