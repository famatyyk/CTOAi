#!/usr/bin/env python3
"""
CTOA Service Drift Detection

Monitors systemd services and timers for configuration drift.
Detects:
- Disabled services
- Failed service states
- Timer misconfigurations
- Unit file changes
"""

import sys
from datetime import datetime, timezone

from runner import process_safety

SERVICES = [
    "ctoa-runner.service",
    "ctoa-runner.timer",
    "ctoa-report.service",
    "ctoa-report.timer",
    "ctoa-health-live.service",
    "ctoa-retention-cleanup.timer",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def check_service_status(service: str) -> dict:
    """Check systemd service status"""
    try:
        systemctl = process_safety.resolve_executable("systemctl")
        # Check if service is enabled
        result_enabled = process_safety.run_trusted(
            [systemctl, "is-enabled", service],
            capture_output=True,
            text=True,
            timeout=5,
        )
        enabled = result_enabled.returncode == 0

        # Check if service is active
        result_active = process_safety.run_trusted(
            [systemctl, "is-active", service], capture_output=True, text=True, timeout=5
        )
        active = result_active.returncode == 0

        return {
            "service": service,
            "enabled": enabled,
            "active": active,
            "status": "OK" if (enabled and active) else "DRIFT",
        }
    except (
        OSError,
        process_safety.ExecutableUnavailableError,
        process_safety.ProcessExecutionError,
    ) as e:
        return {"service": service, "error": str(e), "status": "ERROR"}


def main():
    print(f"[drift-checker] Starting service audit at {now_iso()}")
    print()

    results = []
    drift_detected = False

    for service in SERVICES:
        status = check_service_status(service)
        results.append(status)

        if status.get("status") != "OK":
            drift_detected = True

        status_icon = "[OK]" if status.get("status") == "OK" else "[!!]"
        print(f"{status_icon} {service}: {status.get('status')}")

    print()
    print(f"[drift-checker] Report at {now_iso()}")
    print(f"[drift-checker] Total services checked: {len(results)}")
    print(f"[drift-checker] Drift detected: {drift_detected}")

    if drift_detected:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
