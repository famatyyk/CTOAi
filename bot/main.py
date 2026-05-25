"""AGENT 7: CODE SMITH -- Tibia Bot Entry Point
============================================
Main bot loop: Perceive -> Decide -> Act -> Log

Sprint 3: Integrated Agent 6 game data (level-aware routing)
         and Agent 3 telemetry (gold/hr, exp/hr, kills).
Sprint 9: SessionScheduler (AGENT 5) wired in for sophisticated
         session/break control.  DQN step count logged per tick.
"""
from __future__ import annotations
import time
import logging
import signal
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("data/bot.log"),
    ],
)
logger = logging.getLogger("bot.main")

from bot.perception.screen import capture_region_pixels
from bot.perception.parser import parse_game_state
from bot.decision.brain import decide_action
from bot.action import execute_action, set_current_state
from bot.safety.scheduler import get_scheduler
from bot.data.db import create_session, close_session
from bot.data.telemetry import set_session, log_event, get_stats

TICK_MS    = 500    # ms per bot loop iteration
STATS_EVERY = 240   # print stats every N ticks (~2 min)
# Check scheduler every N ticks (avoids constant datetime calls)
SCHED_CHECK_EVERY = 20


def run() -> None:
    logger.info("=== TIBIA BOT STARTING ===")
    session_id = create_session()
    set_session(session_id)
    scheduler  = get_scheduler()

    def _shutdown(sig, frame):
        logger.info("Shutdown signal received.")
        _print_stats()
        close_session(session_id)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    def _print_stats():
        s = get_stats()
        logger.info(
            "STATS | Gold/hr: %d | Exp/hr: %d | Kills: %d | Session: %.2fh | Sched: %s",
            s["gold_hr"], s["exp_hr"], s["kills"], s["session_hours"],
            scheduler.status(),
        )

    tick = 0
    try:
        while True:
            tick += 1
            t0 = time.perf_counter()

            # Scheduler gate: pause gracefully when outside active window / on break
            if tick % SCHED_CHECK_EVERY == 0:
                scheduler.tick()
                if not scheduler.should_run():
                    st = scheduler.status()
                    if st.get("on_break"):
                        logger.info("Scheduler: on break -- sleeping 60s")
                    else:
                        logger.info("Scheduler: outside active window -- sleeping 60s")
                    time.sleep(60)
                    continue

            # 1. Perceive
            pixels = capture_region_pixels()
            state  = parse_game_state(pixels)

            # 2. Share state with action dispatcher (Agent 6 routing)
            set_current_state(state)

            # 3. Decide (includes DQN reward + Q-table update internally)
            action = decide_action(state)

            # 4. Act
            result = execute_action(action)

            # 5. Telemetry
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            log_event(action, result, elapsed_ms)

            if tick % 20 == 0:
                logger.info(
                    "Tick %d | Lvl: %d | HP: %d%% MP: %d%% | Action: %s | %dms",
                    tick, state.level, state.hp_pct, state.mp_pct, action, elapsed_ms,
                )

            if tick % STATS_EVERY == 0:
                _print_stats()

            # 6. Sleep remainder of tick
            sleep_ms = max(0, TICK_MS - elapsed_ms)
            time.sleep(sleep_ms / 1000)

    except Exception as e:
        logger.exception("Fatal error in bot loop: %s", e)
    finally:
        _print_stats()
        close_session(session_id)
        logger.info("=== BOT SESSION ENDED ===")


if __name__ == "__main__":
    run()
