"""AGENT 5: Session safety — time limits, breaks, overnight pause."""
from __future__ import annotations
import time
import random
import logging

logger = logging.getLogger(__name__)

# Seconds
SESSION_MIN = 4 * 3600
SESSION_MAX = 8 * 3600
BREAK_EVERY_MIN = 45 * 60
BREAK_EVERY_MAX = 90 * 60
BREAK_DUR_MIN   = 3  * 60
BREAK_DUR_MAX   = 15 * 60
NIGHT_START_H   = 2    # 02:00
NIGHT_END_H     = 7    # 07:00


class SessionManager:
    def __init__(self) -> None:
        self._start   = time.time()
        self._limit   = random.uniform(SESSION_MIN, SESSION_MAX)
        self._next_break = self._start + random.uniform(BREAK_EVERY_MIN, BREAK_EVERY_MAX)
        self._active  = True
        logger.info("Session started. Limit: %.1fh", self._limit / 3600)

    def is_active(self) -> bool:
        now = time.time()
        if now - self._start >= self._limit:
            logger.info("Session time limit reached. Stopping.")
            self._active = False
            return False
        if self._is_night():
            logger.info("Night hours — bot sleeping.")
            time.sleep(60)
            return True
        if now >= self._next_break:
            self._take_break()
        return self._active

    def stop(self) -> None:
        self._active = False

    def _take_break(self) -> None:
        duration = random.uniform(BREAK_DUR_MIN, BREAK_DUR_MAX)
        logger.info("Taking break for %.0f seconds.", duration)
        time.sleep(duration)
        self._next_break = time.time() + random.uniform(BREAK_EVERY_MIN, BREAK_EVERY_MAX)

    @staticmethod
    def _is_night() -> bool:
        import datetime
        h = datetime.datetime.now().hour
        return NIGHT_START_H <= h < NIGHT_END_H
