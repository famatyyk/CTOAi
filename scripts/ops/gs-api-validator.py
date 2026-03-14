#!/usr/bin/env python3
"""
gs-api-validator.py  —  CTOA Commanding Agent: Post-GS API Compliance Check

Called by gs-reset.sh Phase 6 after basic HTTP 200 is confirmed.
Performs a structured API walkthrough against the MythibIA server to ensure:
  - All registered bot module endpoints are reachable
  - Response schemas match the expected contract (key presence check)
  - No deprecated/unknown API versions are active

Exit 0 = all OK  |  Exit 3 = compliance failure
"""
import os
import sys
import json
import time
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [GS-VALIDATOR] %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
log = logging.getLogger("gs-api-validator")

API_BASE     = os.getenv("API_CHECK_URL", "http://127.0.0.1:7777/api")
API_VERSION  = os.getenv("API_VERSION", "v1")
TIMEOUT_SEC  = int(os.getenv("API_TIMEOUT", "10"))
MAX_RETRIES  = int(os.getenv("API_CHECK_RETRIES", "5"))
RETRY_DELAY  = 10  # seconds between retries

# ---------------------------------------------------------------------------
# Expected API contract — adapt to your MythibIA server API
# Each entry: (path, required_response_keys)
# ---------------------------------------------------------------------------
API_CHECKS = [
    ("/health",                    ["status"]),
    ("/modules",                   ["modules"]),
    ("/modules/auto_heal",         ["name", "active"]),
    ("/modules/event_logger",      ["name", "active"]),
    ("/modules/loot_filter",       ["name", "active"]),
    ("/modules/pathing_helper",    ["name", "active"]),
    ("/modules/safety_interrupt",  ["name", "active"]),
    ("/modules/supply_manager",    ["name", "active"]),
    ("/modules/target_priority",   ["name", "active"]),
    ("/modules/telemetry_exporter",["name", "active"]),
]


def fetch_json(path: str) -> dict | None:
    url = f"{API_BASE}/{API_VERSION}{path}"
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_SEC) as resp:
            if resp.status != 200:
                log.warning("HTTP %s for %s", resp.status, url)
                return None
            raw = resp.read()
            return json.loads(raw)
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as exc:
        log.warning("Request failed for %s: %s", url, exc)
        return None


def check_schema(data: dict, required_keys: list[str], path: str) -> bool:
    missing = [k for k in required_keys if k not in data]
    if missing:
        log.error("Schema mismatch at %s — missing keys: %s", path, missing)
        return False
    return True


def run_checks() -> int:
    failures = 0
    for path, required_keys in API_CHECKS:
        log.info("Checking %s%s …", API_BASE, path)
        data = fetch_json(path)
        if data is None:
            log.error("No valid response from %s", path)
            failures += 1
            continue
        if not check_schema(data, required_keys, path):
            failures += 1
        else:
            log.info("OK: %s", path)
    return failures


def main() -> int:
    log.info("=== Post-GS API Compliance Check started at %s ===",
             datetime.now(timezone.utc).isoformat())

    for attempt in range(1, MAX_RETRIES + 1):
        log.info("Attempt %d/%d …", attempt, MAX_RETRIES)
        failures = run_checks()
        if failures == 0:
            log.info("All API checks PASSED.")
            return 0
        if attempt < MAX_RETRIES:
            log.warning("%d check(s) failed. Retrying in %d s …", failures, RETRY_DELAY)
            time.sleep(RETRY_DELAY)

    log.error("API compliance check FAILED after %d attempts.", MAX_RETRIES)
    return 3


if __name__ == "__main__":
    sys.exit(main())
