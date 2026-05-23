#!/usr/bin/env python3
"""Simple webhook listener for Azure Activity Log payloads."""

from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import azure_activity_alerts as alerts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Webhook listener for Azure Activity Log payloads")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8791)
    parser.add_argument("--path", default="/azure/activity")
    parser.add_argument(
        "--webhook-secret",
        default=os.getenv("CTOA_AZURE_INGEST_SECRET", ""),
        help="Optional shared secret expected in X-Webhook-Secret header.",
    )
    parser.add_argument("--routes", default="console,jsonl,discord_webhook")
    parser.add_argument(
        "--webhook-url",
        default=os.getenv("CTOA_AZURE_ALERT_WEBHOOK_URL", ""),
        help="Forward destination used when routes include webhook.",
    )
    parser.add_argument(
        "--discord-webhook-url",
        default=os.getenv("CTOA_AZURE_DISCORD_WEBHOOK_URL", ""),
        help="Discord destination used when routes include discord_webhook.",
    )
    parser.add_argument(
        "--output-jsonl",
        default=str(Path("runtime") / "alerts" / "azure-activity-alerts.jsonl"),
    )
    parser.add_argument("--min-severity", default="warning", choices=["info", "warning", "critical"])
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


class _Handler(BaseHTTPRequestHandler):
    args: argparse.Namespace

    def _write_json(self, code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != self.args.path:
            self._write_json(404, {"ok": False, "error": "not_found"})
            return

        if self.args.webhook_secret:
            got = self.headers.get("X-Webhook-Secret", "")
            if got != self.args.webhook_secret:
                self._write_json(403, {"ok": False, "error": "forbidden"})
                return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            self._write_json(400, {"ok": False, "error": f"bad_payload:{exc.__class__.__name__}"})
            return

        records = alerts.parse_records_payload(payload)
        routes = [part.strip() for part in self.args.routes.split(",") if part.strip()]
        output_jsonl = Path(self.args.output_jsonl)

        routed = 0
        filtered = 0
        for record in records:
            normalized = alerts.normalize_record(record)
            classified = alerts.classify_high_impact(normalized)
            if not alerts._severity_meets(classified["severity"], self.args.min_severity):
                filtered += 1
                continue
            alert = alerts.build_alert(normalized, classified)
            alerts.route_alert(
                alert,
                routes=routes,
                output_jsonl=output_jsonl,
                webhook_url=self.args.webhook_url,
                discord_webhook_url=self.args.discord_webhook_url,
                dry_run=bool(self.args.dry_run),
            )
            routed += 1

        self._write_json(
            200,
            {
                "ok": True,
                "received_records": len(records),
                "routed_alerts": routed,
                "filtered_alerts": filtered,
            },
        )

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return


def main() -> int:
    args = parse_args()
    _Handler.args = args
    server = ThreadingHTTPServer((args.host, args.port), _Handler)
    print(
        json.dumps(
            {
                "ok": True,
                "listener": f"http://{args.host}:{args.port}{args.path}",
                "routes": args.routes,
                "min_severity": args.min_severity,
            },
            ensure_ascii=True,
        )
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())