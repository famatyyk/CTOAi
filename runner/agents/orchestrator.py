#!/usr/bin/env python3
"""Orchestrator – runs the full agent pipeline once.

Order:
  1. scout_agent   – NEW servers → SCOUTING → INGESTED
  2. ingest_agent  – INGESTED → fetch game data → READY
  3. brain_v2      – READY → queue module tasks
  4. generator_agent – QUEUED → render files → GENERATED
  5. validator_agent – GENERATED → quality check → VALIDATED / FAILED
  6. publisher_agent – check launcher day criteria → release if met

Designed to be called by:
  systemd timer (ctoa-agents-orchestrator.timer, every 10 min)
  OR: python3 -m runner.agents.orchestrator

Crash safety:
  - Each agent runs in a try/except; pipeline continues even if one fails.
  - All errors are written to agent_runs table.
"""
from __future__ import annotations

import logging
import sys
import time
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [orchestrator] %(levelname)s %(message)s",
)
log = logging.getLogger("orchestrator")

PIPELINE = [
    ("scout_agent",     "runner.agents.scout_agent"),
    ("ingest_agent",    "runner.agents.ingest_agent"),
    ("brain_v2",        "runner.agents.brain_v2"),
    ("generator_agent", "runner.agents.generator_agent"),
    ("validator_agent", "runner.agents.validator_agent"),
    ("publisher_agent", "runner.agents.publisher_agent"),
]


def run_pipeline() -> None:
    start = datetime.now(timezone.utc)
    log.info("=== Orchestrator start %s ===", start.strftime("%Y-%m-%d %H:%M:%S UTC"))

    results: dict[str, str] = {}

    for name, module_path in PIPELINE:
        t0 = time.monotonic()
        try:
            # Dynamic import + run_once()
            parts = module_path.rsplit(".", 1)
            mod = __import__(module_path, fromlist=[parts[-1]])
            mod.run_once()
            elapsed = time.monotonic() - t0
            results[name] = f"ok ({elapsed:.1f}s)"
            log.info("  ✓ %-20s  %.1fs", name, elapsed)
        except Exception as exc:
            elapsed = time.monotonic() - t0
            results[name] = f"error: {exc}"
            log.error("  ✗ %-20s  %.1fs  %s", name, elapsed, exc)
            # Try to write to DB (may fail if DB is down)
            try:
                from runner.agents import db
                db.log_run(name, "error", str(exc)[:2000])
            except Exception:
                pass

    total = (datetime.now(timezone.utc) - start).total_seconds()
    summary = " | ".join(f"{k}={v}" for k, v in results.items())
    log.info("=== Orchestrator done in %.1fs: %s ===", total, summary)


if __name__ == "__main__":
    run_pipeline()
