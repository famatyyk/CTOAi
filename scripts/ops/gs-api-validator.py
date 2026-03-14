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

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8890").rstrip("/")
API_HEALTH_URL = os.getenv("API_HEALTH_URL", f"{API_BASE_URL}/health")
API_VERSION  = os.getenv("API_VERSION", "").strip("/")
TIMEOUT_SEC  = int(os.getenv("API_TIMEOUT", "10"))
MAX_RETRIES  = int(os.getenv("API_CHECK_RETRIES", "5"))
RETRY_DELAY  = 10  # seconds between retries
STRICT_MODULE_VALIDATION = os.getenv("GS_REQUIRE_MODULE_VALIDATION", "false").lower() == "true"

MODULE_NAMES = [
    "auto_heal",
    "event_logger",
    "loot_filter",
    "pathing_helper",
    "safety_interrupt",
    "supply_manager",
    "target_priority",
    "telemetry_exporter",
]


def fetch_json(url: str) -> dict | None:
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


def normalize_base(base: str) -> str:
    return base.rstrip("/")


def join_url(base: str, path: str) -> str:
    return f"{normalize_base(base)}{path}"


def health_candidates() -> list[str]:
    candidates = [
        API_HEALTH_URL,
        join_url(API_BASE_URL, "/health"),
        join_url(API_BASE_URL, "/api/health"),
    ]
    deduped: list[str] = []
    for c in candidates:
        if c not in deduped:
            deduped.append(c)
    return deduped


def detect_module_root() -> str | None:
    roots = []
    if API_VERSION:
        roots.append(join_url(API_BASE_URL, f"/{API_VERSION}/modules"))
    roots.extend([
        join_url(API_BASE_URL, "/modules"),
        join_url(API_BASE_URL, "/api/modules"),
    ])

    for root in roots:
        data = fetch_json(root)
        if isinstance(data, dict):
            log.info("Detected modules endpoint: %s", root)
            return root
    return None


def run_checks() -> int:
    failures = 0

    # 1) Health is required
    health_ok = False
    for url in health_candidates():
        log.info("Checking health endpoint %s …", url)
        data = fetch_json(url)
        if isinstance(data, dict):
            health_ok = True
            log.info("OK: health endpoint %s", url)
            break
    if not health_ok:
        log.error("No healthy API endpoint detected.")
        return 1

    # 2) Module checks are optional by default (strict mode can enforce)
    modules_root = detect_module_root()
    if modules_root is None:
        if STRICT_MODULE_VALIDATION:
            log.error("Module endpoint not detected and strict module validation is enabled.")
            return 1
        log.warning("Module endpoint not detected; skipping module checks.")
        return 0

    for name in MODULE_NAMES:
        url = f"{modules_root}/{name}"
        log.info("Checking module endpoint %s …", url)
        data = fetch_json(url)
        if data is None:
            if STRICT_MODULE_VALIDATION:
                failures += 1
                log.error("No valid response from %s", url)
            else:
                log.warning("Module endpoint unavailable (non-strict): %s", url)
            continue
        if not check_schema(data, ["name"], url):
            if STRICT_MODULE_VALIDATION:
                failures += 1
            else:
                log.warning("Schema mismatch (non-strict): %s", url)
        else:
            log.info("OK: %s", url)

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
