"""
CTOA Alerting Rules Configuration
Defines thresholds and actions for VPS health monitoring
"""

from typing import Any, Dict

ALERT_RULES = {
    "cpu": {
        "threshold": 80,  # Percentage
        "duration": 300,  # Seconds (5 minutes sustained)
        "severity": "warning",
        "actions": ["log", "email", "slack"],
        "description": "CPU usage above 80%"
    },

    "memory": {
        "threshold": 85,  # Percentage
        "duration": 300,
        "severity": "warning",
        "actions": ["log", "email"],
        "description": "Memory usage above 85%"
    },

    "disk": {
        "threshold": 90,  # Percentage
        "duration": 0,  # Immediate alert
        "severity": "critical",
        "actions": ["log", "email", "slack", "auto-cleanup-logs"],
        "description": "Disk usage above 90%"
    },

    "process_missing": {
        "processes": ["python3", "systemd"],
        "severity": "critical",
        "actions": ["log", "email", "slack", "auto-restart"],
        "description": "Critical process is missing/not running"
    },

    "api_timeout": {
        "threshold": 10,  # Seconds
        "severity": "warning",
        "actions": ["log", "retry"],
        "description": "GitHub API response time exceeded"
    }
}

ACTION_CONFIG = {
    "log": {
        "enabled": True,
        "target": "/opt/ctoa/logs/alerts.log"
    },

    "email": {
        "enabled": False,  # Enable with SMTP_SERVER env var
        "smtp_server": "${SMTP_SERVER}",
        "from_addr": "ctoa@localhost",
        "to_addrs": "${ALERT_EMAIL}",
        "subject": "CTOA Alert: {alert_name}"
    },

    "slack": {
        "enabled": False,  # Enable with SLACK_WEBHOOK env var
        "webhook_url": "${SLACK_WEBHOOK}",
        "channel": "#ctoa-alerts"
    },

    "auto-restart": {
        "enabled": True,
        "service": "ctoa-runner.service",
        "max_restarts_per_hour": 3
    },

    "auto-cleanup-logs": {
        "enabled": True,
        "target_dir": "/opt/ctoa/logs",
        "keep_days": 7,
        "min_free_space_gb": 5
    }
}

# Alert severity levels
SEVERITY_LEVELS = {
    "info": 1,
    "warning": 2,
    "critical": 3,
    "emergency": 4
}

# Escalation rules
ESCALATION = {
    "warning": {
        "after_count": 3,  # Alert 3 times before escalating
        "escalate_to": "critical"
    },
    "critical": {
        "page_oncall": True,
        "notify_slack": True,
        "action_timeout": 300  # Auto-remediate after 5 min
    }
}


def check_generation_failed_spike(reason_counts: Dict[str, Any], max_fails: int = 3) -> Dict[str, Any]:
    """Return alert state for generation failures in a rolling window."""
    failed = int(reason_counts.get("GENERATION_FAILED", 0) or 0)
    threshold = max(int(max_fails), 0)
    alert_active = failed >= threshold
    alert_active = failed > threshold

    if alert_active:
        reason = f"GENERATION_FAILED spike: {failed}/{threshold} in 24h"
    else:
        reason = "ok"

    return {
        "alert_active": alert_active,
        "alert_reason": reason,
        "failed_count": failed,
        "threshold": threshold,
    }
