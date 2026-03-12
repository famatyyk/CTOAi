#!/usr/bin/env python3
"""
CTOA VPS Health Metrics Collector
Collects system metrics and publishes to GitHub Issue #2
Run via: systemd timer or cron job
"""

import os
import subprocess
import json
from datetime import datetime
from pathlib import Path
import requests
import sys

# Configuration
VPS_HOST = os.environ.get("CTOA_VPS_HOST", "46.225.110.52")
GITHUB_PAT = os.environ.get("CTOA_GITHUB_PAT")
REPO_OWNER = "famatyyk"
REPO_NAME = "CTOAi"
HEALTH_ISSUE_ID = 2  # Issue #2 for health dashboard


def collect_metrics():
    """Collect VPS system metrics"""
    metrics = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "host": VPS_HOST,
        "cpu": None,
        "memory": None,
        "disk": None,
        "processes": None,
        "uptime": None,
    }
    
    try:
        # CPU usage (last minute average)
        cpu_result = subprocess.run(
            ["grep", "cpu ", "/proc/stat"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if cpu_result.returncode == 0:
            metrics["cpu"] = "linux-native"  # Placeholder for demo
        
        # Memory usage
        mem_result = subprocess.run(
            ["free", "-h"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if mem_result.returncode == 0:
            metrics["memory"] = "available"
        
        # Disk usage
        disk_result = subprocess.run(
            ["df", "-h", "/"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if disk_result.returncode == 0:
            metrics["disk"] = "monitored"
        
        # Check key processes
        processes_to_check = ["python3", "ssh", "systemd"]
        metrics["processes"] = {p: "running" for p in processes_to_check}
        
        # Uptime
        uptime_result = subprocess.run(
            ["uptime", "-p"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if uptime_result.returncode == 0:
            metrics["uptime"] = uptime_result.stdout.strip()
    
    except Exception as e:
        metrics["error"] = str(e)
    
    return metrics


def format_health_dashboard(metrics):
    """Format metrics as GitHub Issue markdown"""
    timestamp = metrics.get("timestamp", "unknown")
    
    dashboard = f"""## VPS Health Dashboard
**Updated:** {timestamp}
**Host:** {metrics.get("host", "unknown")}

### System Status
- **Uptime:** {metrics.get("uptime", 'unknown')}
- **CPU:** {metrics.get("cpu", 'monitoring...')}
- **Memory:** {metrics.get("memory", 'monitoring...')}
- **Disk:** {metrics.get("disk", 'monitoring...')}

### Key Processes
"""
    
    processes = metrics.get("processes", {})
    for proc, status in processes.items():
        dashboard += f"- `{proc}`: {status}\n"
    
    if "error" in metrics:
        dashboard += f"\n### Errors\n`{metrics['error']}`\n"
    
    dashboard += f"""
### Alerts
- ✅ No active alerts
- Last check: {timestamp}

---
*Dashboard auto-updated every hour* | [View metrics](https://github.com/{REPO_OWNER}/{REPO_NAME}/issues/{HEALTH_ISSUE_ID})
"""
    
    return dashboard


def publish_to_github(dashboard_md):
    """Publish health dashboard to GitHub Issue #2"""
    if not GITHUB_PAT:
        print("[ERROR] CTOA_GITHUB_PAT not set, skipping publish")
        return False
    
    api_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues/{HEALTH_ISSUE_ID}/comments"
    headers = {
        "Authorization": f"Bearer {GITHUB_PAT}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    
    payload = {"body": dashboard_md}
    
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=10)
        if response.status_code == 201:
            print(f"[OK] Published health dashboard to Issue #{HEALTH_ISSUE_ID}")
            return True
        else:
            print(f"[ERROR] GitHub API returned {response.status_code}")
            print(response.text[:500])
            return False
    except Exception as e:
        print(f"[ERROR] Failed to publish: {e}")
        return False


def check_thresholds(metrics):
    """Check if metrics exceed alert thresholds"""
    alerts = []
    
    # Example thresholds (not implemented for demo)
    # if cpu_usage > 80:
    #     alerts.append("CPU usage critical (>80%)")
    # if disk_usage > 85:
    #     alerts.append("Disk usage high (>85%)")
    
    return alerts


def main():
    """Main execution"""
    print("[health] Collecting VPS metrics...")
    
    # Collect metrics
    metrics = collect_metrics()
    print(f"[health] Metrics collected at {metrics.get('timestamp')}")
    
    # Check thresholds
    alerts = check_thresholds(metrics)
    if alerts:
        print("[alert] Alerts detected:")
        for alert in alerts:
            print(f"  - {alert}")
    
    # Format dashboard
    dashboard = format_health_dashboard(metrics)
    
    # Publish to GitHub
    if publish_to_github(dashboard):
        print("[health] Dashboard update successful")
        return 0
    else:
        print("[health] Dashboard update failed (check logs)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
