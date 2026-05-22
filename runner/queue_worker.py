#!/usr/bin/env python3
"""Minimal Redis-backed worker for CTOA orchestration jobs."""

import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from redis import Redis

ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = Path(os.getenv("CTOA_WORKER_LOG", str(ROOT / "logs" / "queue-worker.log")))
REDIS_URL = os.getenv("CTOA_REDIS_URL", "redis://127.0.0.1:6379/0")
QUEUE_KEY = os.getenv("CTOA_REDIS_QUEUE", "ctoa:jobs")
RESULTS_KEY = os.getenv("CTOA_REDIS_RESULTS", "ctoa:jobs:results")
BLOCK_SECONDS = int(os.getenv("CTOA_WORKER_BLOCK_SECONDS", "5"))


def _setup_logging() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [queue-worker] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
        ],
    )


def _run_action(action: str) -> dict[str, Any]:
    if action == "orchestrator.tick":
        argv = [sys.executable, "runner/runner.py", "tick"]
    elif action == "orchestrator.report":
        argv = [sys.executable, "runner/runner.py", "report"]
    else:
        return {"ok": False, "detail": f"Unsupported action: {action}"}

    proc = subprocess.run(
        argv,
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        timeout=120,
    )
    return {
        "ok": proc.returncode == 0,
        "code": proc.returncode,
        "stdout": (proc.stdout or "")[:4000],
        "stderr": (proc.stderr or "")[:4000],
    }


def main() -> int:
    _setup_logging()
    redis_cli = Redis.from_url(REDIS_URL, decode_responses=True)
    logging.info("queue-worker started queue=%s redis=%s", QUEUE_KEY, REDIS_URL)

    while True:
        item = redis_cli.brpop(QUEUE_KEY, timeout=BLOCK_SECONDS)
        if not item:
            continue

        _, payload_raw = item
        received_at = datetime.now(timezone.utc).isoformat()

        try:
            job = json.loads(payload_raw)
        except Exception:
            job = {"action": "unknown", "raw": payload_raw}

        job_id = str(job.get("id", f"job-{int(time.time())}"))
        action = str(job.get("action", "orchestrator.tick"))

        logging.info("processing id=%s action=%s", job_id, action)
        started = time.perf_counter()
        result = _run_action(action)
        duration = round(time.perf_counter() - started, 3)

        report = {
            "id": job_id,
            "action": action,
            "received_at": received_at,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "duration_s": duration,
            **result,
        }

        redis_cli.lpush(RESULTS_KEY, json.dumps(report, ensure_ascii=True))
        redis_cli.ltrim(RESULTS_KEY, 0, 199)

        level = logging.INFO if report.get("ok") else logging.ERROR
        logging.log(level, "finished id=%s action=%s ok=%s duration=%.3fs", job_id, action, report.get("ok"), duration)


if __name__ == "__main__":
    raise SystemExit(main())