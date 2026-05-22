#!/usr/bin/env python3
"""CLI helper to enqueue CTOA worker jobs into Redis."""

import argparse
import json
import os
import time
from datetime import datetime, timezone

from redis import Redis


def main() -> int:
    parser = argparse.ArgumentParser(description="Enqueue a CTOA worker job")
    parser.add_argument("--action", default="orchestrator.tick", choices=["orchestrator.tick", "orchestrator.report"])
    parser.add_argument("--queue", default=os.getenv("CTOA_REDIS_QUEUE", "ctoa:jobs"))
    parser.add_argument("--redis-url", default=os.getenv("CTOA_REDIS_URL", "redis://127.0.0.1:6379/0"))
    args = parser.parse_args()

    redis_cli = Redis.from_url(args.redis_url, decode_responses=True)
    job = {
        "id": f"job-{int(time.time())}",
        "action": args.action,
        "requested_at": datetime.now(timezone.utc).isoformat(),
    }
    redis_cli.lpush(args.queue, json.dumps(job, ensure_ascii=True))
    depth = redis_cli.llen(args.queue)
    print(json.dumps({"ok": True, "queue": args.queue, "depth": depth, "job": job}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())