#!/usr/bin/env python3
"""Brain v2 – reads READY servers from DB and decides what to generate next.

Logic:
  For each READY server:
    - Load game_data from DB
    - Walk the TEMPLATES catalog; skip templates whose requirements aren't met
    - For each eligible template that hasn't been generated yet → INSERT QUEUED module
    - Respect DAILY_MODULE_LIMIT and DAILY_PROGRAM_LIMIT

Daily limits (read from env or defaults):
    CTOA_DAILY_MODULE_LIMIT   default 50
    CTOA_DAILY_PROGRAM_LIMIT  default 5
    CTOA_MIN_QUALITY          default 90   (programs must reach this to count toward program limit)

Run: python3 -m runner.agents.brain_v2
"""
from __future__ import annotations

import logging
import os
from datetime import date

from runner.agents import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [brain_v2] %(levelname)s %(message)s",
)
log = logging.getLogger("brain_v2")

DAILY_MODULE_LIMIT  = int(os.environ.get("CTOA_DAILY_MODULE_LIMIT",  "50"))
DAILY_PROGRAM_LIMIT = int(os.environ.get("CTOA_DAILY_PROGRAM_LIMIT", "5"))
MIN_QUALITY         = int(os.environ.get("CTOA_MIN_QUALITY",          "90"))

# ─── Template catalog ────────────────────────────────────────────────────────
# Each entry:
#   id       - unique template identifier (also used as task_id prefix)
#   name     - human description
#   category - base | combat | hunt | economy | social | program
#   requires - list of game_data.data_type values needed (empty = always eligible)
#   output   - output filename (.lua or .py)
#   is_program - if True, counts toward program limit (not module limit)

TEMPLATES: list[dict] = [
    # ── Base pack ────────────────────────────────────────────────────────────
    {"id": "auto_heal",        "category": "base",    "requires": [],            "output": "auto_heal.lua"},
    {"id": "auto_reconnect",   "category": "base",    "requires": [],            "output": "auto_reconnect.lua"},
    {"id": "loot_filter",      "category": "base",    "requires": [],            "output": "loot_filter.lua"},
    # ── Combat pack ──────────────────────────────────────────────────────────
    {"id": "cavebot_pathing",  "category": "combat",  "requires": [],            "output": "cavebot_pathing.lua"},
    {"id": "target_selector",  "category": "combat",  "requires": [],            "output": "target_selector.lua"},
    {"id": "anti_stuck",       "category": "combat",  "requires": [],            "output": "anti_stuck.lua"},
    {"id": "alarmy",           "category": "combat",  "requires": [],            "output": "alarmy.lua"},
    # ── Hunt pack ────────────────────────────────────────────────────────────
    {"id": "healer_profiles",  "category": "hunt",    "requires": [],            "output": "healer_profiles.lua"},
    {"id": "flee_logic",       "category": "hunt",    "requires": [],            "output": "flee_logic.lua"},
    {"id": "target_blacklist", "category": "hunt",    "requires": [],            "output": "target_blacklist.lua"},
    {"id": "auto_resupply",    "category": "hunt",    "requires": [],            "output": "auto_resupply.lua"},
    # ── Server-aware modules (need game_data) ────────────────────────────────
    {"id": "server_blacklist", "category": "combat",  "requires": ["monsters"],  "output": "server_blacklist.lua"},
    {"id": "server_loot_map",  "category": "economy", "requires": ["items"],     "output": "server_loot_map.lua"},
    {"id": "highscore_scout",  "category": "social",  "requires": ["highscores"],"output": "highscore_scout.lua"},
    {"id": "server_stats_lua", "category": "social",  "requires": ["server_info"],"output": "server_stats.lua"},
    {"id": "player_tracker",   "category": "social",  "requires": ["players"],   "output": "player_tracker.lua"},
    # ── Orchestrators / Programs ─────────────────────────────────────────────
    {"id": "hunt_orchestrator","category": "program", "requires": [],            "output": "hunt_orchestrator.lua", "is_program": True},
    {"id": "economy_bot",      "category": "program", "requires": ["items"],     "output": "economy_bot.lua",       "is_program": True},
    {"id": "pvp_guard",        "category": "program", "requires": ["players"],   "output": "pvp_guard.lua",         "is_program": True},
    # ── Economy ──────────────────────────────────────────────────────────────
    {"id": "depot_manager",    "category": "economy", "requires": [],            "output": "depot_manager.lua"},
    {"id": "gold_tracker",     "category": "economy", "requires": [],            "output": "gold_tracker.lua"},
    {"id": "bank_automation",  "category": "economy", "requires": [],            "output": "bank_automation.lua"},
    # ── Safety / Anti-detection ───────────────────────────────────────────────
    {"id": "human_delay",      "category": "base",    "requires": [],            "output": "human_delay.lua"},
    {"id": "break_scheduler",  "category": "base",    "requires": [],            "output": "break_scheduler.lua"},
    {"id": "login_randomizer", "category": "base",    "requires": [],            "output": "login_randomizer.lua"},
    # ── Advanced combat ──────────────────────────────────────────────────────
    {"id": "rune_maker",       "category": "combat",  "requires": [],            "output": "rune_maker.lua"},
    {"id": "combo_spells",     "category": "combat",  "requires": [],            "output": "combo_spells.lua"},
    {"id": "area_spell_ctrl",  "category": "combat",  "requires": [],            "output": "area_spell_ctrl.lua"},
    # ── Leveling ─────────────────────────────────────────────────────────────
    {"id": "exp_tracker",      "category": "hunt",    "requires": [],            "output": "exp_tracker.lua"},
    {"id": "session_log",      "category": "hunt",    "requires": [],            "output": "session_log.lua"},
    {"id": "respawn_optimizer","category": "hunt",    "requires": ["monsters"],  "output": "respawn_optimizer.lua"},
]


def _get_daily_counts() -> tuple[int, int]:
    today = date.today().isoformat()
    row = db.query_one(
        "SELECT modules_generated, programs_generated FROM daily_stats WHERE dt=%s",
        (today,),
    )
    if not row:
        db.execute(
            "INSERT INTO daily_stats (dt) VALUES (%s) ON CONFLICT DO NOTHING",
            (today,),
        )
        return 0, 0
    return row["modules_generated"], row["programs_generated"]


def _existing_task_ids(server_id: int) -> set[str]:
    rows = db.query_all(
        "SELECT task_id FROM modules WHERE server_id=%s",
        (server_id,),
    )
    return {r["task_id"] for r in rows}


def _available_data_types(server_id: int) -> set[str]:
    rows = db.query_all(
        "SELECT DISTINCT data_type FROM game_data WHERE server_id=%s",
        (server_id,),
    )
    return {r["data_type"] for r in rows}


def plan_for_server(server_id: int) -> int:
    """Queue eligible templates for a READY server. Returns number queued."""
    modules_today, programs_today = _get_daily_counts()
    if modules_today >= DAILY_MODULE_LIMIT and programs_today >= DAILY_PROGRAM_LIMIT:
        log.info("Daily limits reached (%d mod / %d prog) – skipping", modules_today, programs_today)
        return 0

    existing = _existing_task_ids(server_id)
    available_data = _available_data_types(server_id)
    queued = 0
    task_counter = len(existing) + 1

    for tmpl in TEMPLATES:
        if modules_today >= DAILY_MODULE_LIMIT and not tmpl.get("is_program"):
            continue
        if programs_today >= DAILY_PROGRAM_LIMIT and tmpl.get("is_program"):
            continue

        # Check data requirements
        if tmpl["requires"] and not all(r in available_data for r in tmpl["requires"]):
            continue

        task_id = f"SRV{server_id:03d}-{tmpl['id'].upper()[:20]}"
        if task_id in existing:
            continue

        db.execute(
            """
            INSERT INTO modules (server_id, task_id, template, output_file, status, queued_at)
            VALUES (%s, %s, %s, %s, 'QUEUED', now())
            ON CONFLICT (task_id) DO NOTHING
            """,
            (server_id, task_id, tmpl["id"], tmpl["output"]),
        )
        queued += 1

        if tmpl.get("is_program"):
            programs_today += 1
        else:
            modules_today += 1
        task_counter += 1

        log.info("  Queued %s → %s", task_id, tmpl["output"])

    return queued


def run_once() -> None:
    # Ensure modules table has queued_at for queue->generated latency KPI.
    db.execute("ALTER TABLE modules ADD COLUMN IF NOT EXISTS queued_at TIMESTAMPTZ")
    db.execute("UPDATE modules SET queued_at=now() WHERE queued_at IS NULL")

    servers = db.query_all("SELECT id, url FROM servers WHERE status='READY' ORDER BY id")
    if not servers:
        log.info("No READY servers to plan")
        return

    total = 0
    for srv in servers:
        try:
            n = plan_for_server(srv["id"])
            total += n
            log.info("Server #%d: %d tasks queued", srv["id"], n)
        except Exception as exc:
            log.error("Brain error for server #%d: %s", srv["id"], exc)
            db.log_run("brain_v2", "error", str(exc))

    db.log_run("brain_v2", "ok", f"total queued: {total}")
    log.info("Brain done – %d tasks queued across %d servers", total, len(servers))


if __name__ == "__main__":
    run_once()
