"""
AGENT 7: CODE SMITH — Tibia Bot Entry Point
============================================
Main bot loop: Perceive → Decide → Act → Log
Target tick rate: 500ms
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
    ]
)
logger = logging.getLogger("bot.main")

from bot.perception.screen import capture_region_pixels
from bot.perception.parser import parse_game_state
from bot.decision.brain import decide_action
from bot.action import execute_action
from bot.safety.session import SessionManager
from bot.data.db import create_session, close_session
from bot.data.telemetry import set_session, log_event

TICK_MS = 500  # ms per bot loop iteration


def run() -> None:
    logger.info("=== TIBIA BOT STARTING ===")
    session_id = create_session()
    set_session(session_id)
    session = SessionManager()

    def _shutdown(sig, frame):
        logger.info("Shutdown signal received.")
        close_session(session_id)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    tick = 0
    try:
        while session.is_active():
            t0 = time.perf_counter()
            tick += 1

            # 1. Perceive
            pixels = capture_region_pixels()
            state  = parse_game_state(pixels)

            # 2. Decide
            action = decide_action(state)

            # 3. Act
            result = execute_action(action)

            # 4. Telemetry
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            log_event(action, result, elapsed_ms)

            if tick % 20 == 0:
                logger.info(
                    "Tick %d | HP: %d%% MP: %d%% | Action: %s | %dms",
                    tick, state.hp_pct, state.mp_pct, action, elapsed_ms
                )

            # 5. Sleep remainder of tick
            sleep_ms = max(0, TICK_MS - elapsed_ms)
            time.sleep(sleep_ms / 1000)

    except Exception as e:
        logger.exception("Fatal error in bot loop: %s", e)
    finally:
        close_session(session_id)
        logger.info("=== BOT SESSION ENDED ===")


if __name__ == "__main__":
    run()
