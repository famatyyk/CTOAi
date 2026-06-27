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
from bot.config.runtime_profile import get_bool, get_str
from bot.safety.scheduler import get_scheduler
from bot.data.db import create_session, close_session
from bot.data.telemetry import set_session, log_event, log_loop_event, get_stats
from bot.runtime.live_state import emit_live_state

TICK_MS    = 500    # ms per bot loop iteration
STATS_EVERY = 240   # print stats every N ticks (~2 min)
# Check scheduler every N ticks (avoids constant datetime calls)
SCHED_CHECK_EVERY = 20


def _manual_action(state) -> str:
    if get_bool("BOT_AUTO_FOLLOW", False):
        return "auto_follow"
    if get_bool("BOT_SPELL_ROTATION_ENABLED", False) and getattr(state, "target_id", None) is not None:
        return "rotate_spell"
    return "idle"


def _record_loop_telemetry(tick: int, elapsed_ms: int, stage: str, ok: bool, details: dict[str, object]) -> None:
    log_loop_event(
        "bot.main",
        stage,
        elapsed_ms,
        ok=ok,
        error="" if ok else str(details.get("error", "")),
        details={"tick": tick, **details},
    )


def run() -> None:
    logger.info("=== TIBIA BOT STARTING ===")
    action_mode = get_str("BOT_ACTION_MODE", "full").strip().lower()
    if action_mode in {"follow_only", "auto_follow_only", "autofollow_only"}:
        logger.info("Action mode: follow_only (only auto_follow will be executed)")
    elif action_mode in {"manual", "modules", "overlay"}:
        logger.info("Action mode: manual (only explicitly enabled modules will run)")
    else:
        logger.info("Action mode: full (rules/ML decision engine)")

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
    prev_state = None
    try:
        while True:
            tick += 1
            loop_started = time.perf_counter()
            loop_stage = "scheduler"
            scheduler_ms = 0

            # Scheduler gate: pause gracefully when outside active window / on break
            if tick % SCHED_CHECK_EVERY == 0:
                scheduler_started = time.perf_counter()
                scheduler.tick()
                scheduler_ms = int((time.perf_counter() - scheduler_started) * 1000)
                if not scheduler.should_run():
                    st = scheduler.status()
                    if st.get("on_break"):
                        logger.info("Scheduler: on break -- sleeping 60s")
                    else:
                        logger.info("Scheduler: outside active window -- sleeping 60s")
                    elapsed_ms = int((time.perf_counter() - loop_started) * 1000)
                    _record_loop_telemetry(
                        tick,
                        elapsed_ms,
                        "scheduler_sleep",
                        True,
                        {
                            "scheduler_ms": scheduler_ms,
                            "on_break": bool(st.get("on_break")),
                            "status": st.get("status", ""),
                        },
                    )
                    time.sleep(60)
                    continue

            # 1. Perceive
            loop_stage = "capture"
            capture_started = time.perf_counter()
            pixels = capture_region_pixels()
            capture_ms = int((time.perf_counter() - capture_started) * 1000)

            loop_stage = "perception"
            perception_started = time.perf_counter()
            state  = parse_game_state(pixels, prev_state=prev_state)
            perception_ms = int((time.perf_counter() - perception_started) * 1000)
            prev_state = state

            # 2. Share state with action dispatcher (Agent 6 routing)
            loop_stage = "dispatch"
            dispatch_started = time.perf_counter()
            set_current_state(state)

            # 3. Decide (includes DQN reward + Q-table update internally)
            if action_mode in {"follow_only", "auto_follow_only", "autofollow_only"}:
                action = "auto_follow"
            elif action_mode in {"manual", "modules", "overlay"}:
                action = _manual_action(state)
            else:
                action = decide_action(state)

            # 4. Act
            result = execute_action(action)
            dispatch_ms = int((time.perf_counter() - dispatch_started) * 1000)

            # 5. Telemetry
            loop_stage = "telemetry"
            telemetry_started = time.perf_counter()
            elapsed_ms = int((time.perf_counter() - loop_started) * 1000)
            log_event(action, result, elapsed_ms)
            emit_live_state(
                hp_pct=state.hp_pct,
                mp_pct=state.mp_pct,
                target_pct=state.target_hp_pct,
                action=action,
                action_result=result,
                level=state.level,
                tick_ms=int((time.perf_counter() - loop_started) * 1000),
            )
            telemetry_ms = int((time.perf_counter() - telemetry_started) * 1000)
            elapsed_ms = int((time.perf_counter() - loop_started) * 1000)
            _record_loop_telemetry(
                tick,
                elapsed_ms,
                "tick",
                True,
                {
                    "scheduler_ms": scheduler_ms,
                    "capture_ms": capture_ms,
                    "perception_ms": perception_ms,
                    "dispatch_ms": dispatch_ms,
                    "telemetry_ms": telemetry_ms,
                    "action": action,
                    "result": result,
                    "status": "ok",
                },
            )

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
        elapsed_ms = int((time.perf_counter() - loop_started) * 1000)
        _record_loop_telemetry(
            tick,
            elapsed_ms,
            loop_stage,
            False,
            {
                "scheduler_ms": scheduler_ms,
                "error": f"{type(e).__name__}: {e}",
                "status": "error",
            },
        )
        logger.exception("Fatal error in bot loop: %s", e)
    finally:
        _print_stats()
        close_session(session_id)
        logger.info("=== BOT SESSION ENDED ===")


if __name__ == "__main__":
    run()
