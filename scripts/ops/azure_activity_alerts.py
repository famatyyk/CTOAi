#!/usr/bin/env python3
"""Ingest, normalize, classify, and route Azure Activity Log alerts."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
from urllib import error as urlerror
from urllib import request as urlrequest


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_JSONL = ROOT / "runtime" / "alerts" / "azure-activity-alerts.jsonl"

SEVERITY_ORDER = {
    "info": 1,
    "warning": 2,
    "critical": 3,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Azure Activity Log alert automation")
    parser.add_argument("--source-file", default="", help="Path to JSON/JSONL payload")
    parser.add_argument(
        "--source-format",
        default="auto",
        choices=["auto", "json", "jsonl"],
        help="Input file format. 'auto' infers from extension.",
    )
    parser.add_argument(
        "--ingest-mode",
        default="file",
        choices=["file", "stdin"],
        help="Ingest from file or stdin JSON payload (webhook style).",
    )
    parser.add_argument(
        "--routes",
        default="console,jsonl",
        help="Comma-separated routes: console,jsonl,webhook,discord_webhook",
    )
    parser.add_argument(
        "--webhook-url",
        default=os.getenv("CTOA_AZURE_ALERT_WEBHOOK_URL", ""),
        help="Webhook destination used when routes include webhook.",
    )
    parser.add_argument(
        "--discord-webhook-url",
        default=os.getenv("CTOA_AZURE_DISCORD_WEBHOOK_URL", ""),
        help="Discord webhook destination used when routes include discord_webhook.",
    )
    parser.add_argument(
        "--output-jsonl",
        default=str(DEFAULT_OUTPUT_JSONL),
        help="JSONL output file for routed alerts.",
    )
    parser.add_argument(
        "--min-severity",
        default="warning",
        choices=["info", "warning", "critical"],
        help="Only route alerts at or above this severity.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Compute alerts without network writes")
    return parser.parse_args()


def _iso_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        for key in ("value", "localizedValue", "name"):
            text = value.get(key)
            if isinstance(text, str) and text.strip():
                return text.strip()
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value)


def _severity_meets(value: str, threshold: str) -> bool:
    return SEVERITY_ORDER.get(value, 0) >= SEVERITY_ORDER.get(threshold, 0)


def _escalate(current: str, candidate: str) -> str:
    if SEVERITY_ORDER.get(candidate, 0) > SEVERITY_ORDER.get(current, 0):
        return candidate
    return current


def parse_records_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]

    if isinstance(payload, dict):
        records = payload.get("records")
        if isinstance(records, list):
            return [row for row in records if isinstance(row, dict)]

        tables = payload.get("tables")
        if isinstance(tables, list):
            out: list[dict[str, Any]] = []
            for table in tables:
                if not isinstance(table, dict):
                    continue
                columns = table.get("columns")
                rows = table.get("rows")
                if not isinstance(columns, list) or not isinstance(rows, list):
                    continue
                col_names = [str(col.get("name", "")) if isinstance(col, dict) else "" for col in columns]
                for row in rows:
                    if not isinstance(row, list):
                        continue
                    item = {col_names[i]: row[i] for i in range(min(len(col_names), len(row))) if col_names[i]}
                    out.append(item)
            return out

        return [payload]

    return []


def load_records_from_file(path: Path, source_format: str = "auto") -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")

    fmt = source_format
    if fmt == "auto":
        fmt = "jsonl" if path.suffix.lower() == ".jsonl" else "json"

    if fmt == "jsonl":
        parsed = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            parsed.append(json.loads(stripped))
        return parse_records_payload(parsed)

    payload = json.loads(text)
    return parse_records_payload(payload)


def load_records_from_stdin() -> list[dict[str, Any]]:
    payload = json.load(sys.stdin)
    return parse_records_payload(payload)


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    operation = _as_text(record.get("operationName") or record.get("OperationNameValue") or record.get("OperationName"))
    status = _as_text(record.get("status") or record.get("ActivityStatusValue") or record.get("ActivityStatus"))
    sub_status = _as_text(record.get("subStatus") or record.get("ActivitySubstatusValue") or record.get("SubStatus"))
    resource_id = _as_text(record.get("resourceId") or record.get("ResourceId") or record.get("_ResourceId"))
    caller = _as_text(record.get("caller") or record.get("Caller") or record.get("Claims_d"))
    correlation_id = _as_text(record.get("correlationId") or record.get("CorrelationId"))
    category = _as_text(record.get("category") or record.get("Category"))

    timestamp = _as_text(
        record.get("eventTimestamp")
        or record.get("EventSubmissionTimestamp")
        or record.get("submissionTimestamp")
        or record.get("TimeGenerated")
    ) or _iso_now()

    normalized = {
        "timestamp": timestamp,
        "event_type": "azure_activity_log",
        "operation_name": operation,
        "status": status,
        "sub_status": sub_status,
        "resource_id": resource_id,
        "caller": caller,
        "correlation_id": correlation_id,
        "category": category,
        "raw": record,
    }
    return normalized


def classify_high_impact(normalized: dict[str, Any]) -> dict[str, Any]:
    operation = normalized.get("operation_name", "") or ""
    resource_id = normalized.get("resource_id", "") or ""
    status = (normalized.get("status", "") or "").lower()
    sub_status = (normalized.get("sub_status", "") or "").lower()

    operation_l = operation.lower()
    resource_l = resource_id.lower()

    severity = "info"
    reasons: list[str] = []
    labels: list[str] = []

    if operation_l.startswith("microsoft.authorization/roleassignments/"):
        severity = _escalate(severity, "critical")
        reasons.append("RBAC assignment change")
        labels.append("rbac_change")

    if "policy" in operation_l and operation_l.startswith("microsoft.authorization/"):
        severity = _escalate(severity, "critical")
        reasons.append("Policy assignment or definition change")
        labels.append("policy_change")

    if operation_l.endswith("/delete") or "/delete" in operation_l:
        severity = _escalate(severity, "critical")
        reasons.append("Resource delete operation")
        labels.append("delete_operation")

    if operation_l.startswith("microsoft.network/"):
        severity = _escalate(severity, "warning")
        reasons.append("Networking configuration change")
        labels.append("network_change")

    if operation_l.startswith("microsoft.keyvault/") or "providers/microsoft.keyvault/" in resource_l:
        severity = _escalate(severity, "critical")
        reasons.append("Key Vault related change")
        labels.append("keyvault_change")

    if status == "failed":
        severity = _escalate(severity, "warning")
        reasons.append("Operation failed")
        labels.append("operation_failed")

    if sub_status in {"forbidden", "unauthorized", "authorizationfailed"}:
        severity = _escalate(severity, "critical")
        reasons.append("Authorization failure")
        labels.append("authorization_failure")

    return {
        "severity": severity,
        "high_impact": bool(reasons),
        "reasons": reasons,
        "labels": labels,
    }


def build_alert(normalized: dict[str, Any], classification: dict[str, Any]) -> dict[str, Any]:
    summary = (
        f"[{classification['severity'].upper()}] "
        f"{normalized.get('operation_name') or 'unknown_operation'} "
        f"status={normalized.get('status') or 'unknown'} "
        f"subStatus={normalized.get('sub_status') or 'unknown'}"
    )

    return {
        "generated_at": _iso_now(),
        "source": "azure_activity_log",
        "summary": summary,
        "severity": classification["severity"],
        "high_impact": classification["high_impact"],
        "reasons": classification["reasons"],
        "labels": classification["labels"],
        "event": {
            "timestamp": normalized.get("timestamp"),
            "operation_name": normalized.get("operation_name"),
            "status": normalized.get("status"),
            "sub_status": normalized.get("sub_status"),
            "resource_id": normalized.get("resource_id"),
            "caller": normalized.get("caller"),
            "correlation_id": normalized.get("correlation_id"),
            "category": normalized.get("category"),
        },
    }


def build_discord_payload(alert: dict[str, Any]) -> dict[str, Any]:
    severity = str(alert.get("severity", "info")).lower()
    color = 3447003
    if severity == "warning":
        color = 16776960
    elif severity == "critical":
        color = 15158332

    event = alert.get("event", {}) if isinstance(alert.get("event"), dict) else {}
    reasons = alert.get("reasons") if isinstance(alert.get("reasons"), list) else []
    reason_text = ", ".join(str(item) for item in reasons) if reasons else "none"

    description = (
        f"operation={event.get('operation_name') or 'unknown'}\n"
        f"status={event.get('status') or 'unknown'}\n"
        f"subStatus={event.get('sub_status') or 'unknown'}\n"
        f"resourceId={event.get('resource_id') or 'unknown'}\n"
        f"caller={event.get('caller') or 'unknown'}\n"
        f"correlationId={event.get('correlation_id') or 'unknown'}\n"
        f"reasons={reason_text}"
    )

    return {
        "content": str(alert.get("summary", "Azure activity alert")),
        "embeds": [
            {
                "title": "Azure Activity Alert",
                "description": description,
                "color": color,
            }
        ],
    }


def post_json(url: str, payload: dict[str, Any], timeout_s: int = 8) -> tuple[bool, str]:
    req = urlrequest.Request(
        url,
        data=json.dumps(payload, ensure_ascii=True).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "CTOA-AzureAlerts/1.0"},
        method="POST",
    )
    try:
        with urlrequest.urlopen(req, timeout=timeout_s) as resp:  # nosec B310
            code = getattr(resp, "status", 200)
            return 200 <= int(code) < 300, f"http_{code}"
    except urlerror.HTTPError as exc:
        return False, f"http_{exc.code}"
    except Exception as exc:  # pragma: no cover - defensive path
        return False, f"error:{exc.__class__.__name__}"


def route_alert(
    alert: dict[str, Any],
    routes: list[str],
    output_jsonl: Path,
    webhook_url: str,
    discord_webhook_url: str,
    dry_run: bool,
    post_json_fn: Callable[[str, dict[str, Any]], tuple[bool, str]] = post_json,
) -> dict[str, Any]:
    result: dict[str, Any] = {}

    if "console" in routes:
        print(json.dumps(alert, ensure_ascii=True))
        result["console"] = "printed"

    if "jsonl" in routes:
        output_jsonl.parent.mkdir(parents=True, exist_ok=True)
        if not dry_run:
            with output_jsonl.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(alert, ensure_ascii=True) + "\n")
        result["jsonl"] = "written" if not dry_run else "skipped_dry_run"

    if "webhook" in routes:
        if not webhook_url:
            result["webhook"] = "missing_webhook_url"
        elif dry_run:
            result["webhook"] = "skipped_dry_run"
        else:
            ok, detail = post_json_fn(webhook_url, alert)
            result["webhook"] = "sent" if ok else f"failed:{detail}"

    if "discord_webhook" in routes:
        target_url = discord_webhook_url or webhook_url
        if not target_url:
            result["discord_webhook"] = "missing_discord_webhook_url"
        elif dry_run:
            result["discord_webhook"] = "skipped_dry_run"
        else:
            payload = build_discord_payload(alert)
            ok, detail = post_json_fn(target_url, payload)
            result["discord_webhook"] = "sent" if ok else f"failed:{detail}"

    return result


def run_pipeline(args: argparse.Namespace) -> dict[str, Any]:
    if args.ingest_mode == "stdin":
        records = load_records_from_stdin()
    else:
        if not args.source_file:
            raise ValueError("--source-file is required when --ingest-mode=file")
        records = load_records_from_file(Path(args.source_file), args.source_format)

    routes = [part.strip() for part in str(args.routes).split(",") if part.strip()]
    output_jsonl = Path(args.output_jsonl).resolve()

    total = len(records)
    routed = 0
    filtered = 0

    for record in records:
        normalized = normalize_record(record)
        classification = classify_high_impact(normalized)
        if not _severity_meets(classification["severity"], args.min_severity):
            filtered += 1
            continue

        alert = build_alert(normalized, classification)
        route_alert(
            alert,
            routes=routes,
            output_jsonl=output_jsonl,
            webhook_url=args.webhook_url,
            discord_webhook_url=getattr(args, "discord_webhook_url", ""),
            dry_run=bool(args.dry_run),
        )
        routed += 1

    result = {
        "ok": True,
        "total_records": total,
        "routed_alerts": routed,
        "filtered_alerts": filtered,
        "min_severity": args.min_severity,
        "routes": routes,
    }
    return result


def main() -> int:
    args = parse_args()
    try:
        result = run_pipeline(args)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=True), file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

