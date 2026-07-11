"""AGENT 5: Session scheduler — anti-detection timing control.

Strategy:
  - Bot runs in configurable active windows (e.g. 09:00-23:00)
  - Each session lasts 4-8h with random variation (+/-30 min)
  - Mandatory breaks between sessions (15-45 min)
  - Night-time hard stop (00:00-08:00 by default)
  - Weekly schedule variation (weekends slightly shorter)
  - Random micro-pauses (~0.2% ticks): simulates reading/AFK

Config via environment variables or constructor kwargs:
  BOT_ACTIVE_START=9    (hour, 24h format, default 9)
  BOT_ACTIVE_END=23     (hour, default 23)
  BOT_SESSION_MIN=4     (hours, default 4)
  BOT_SESSION_MAX=8     (hours, default 8)
  BOT_BREAK_MIN=15      (minutes, default 15)
  BOT_BREAK_MAX=45      (minutes, default 45)
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from typing import Optional

from . import nonsecurity_random as random

logger = logging.getLogger(__name__)


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, default))
    except (ValueError, TypeError):
        return default


class SessionScheduler:
    """Controls bot session timing to mimic human play patterns."""

    def __init__(
        self,
        active_start: int = _env_int("BOT_ACTIVE_START", 9),
        active_end: int = _env_int("BOT_ACTIVE_END", 23),
        session_min_h: float = _env_int("BOT_SESSION_MIN", 4),
        session_max_h: float = _env_int("BOT_SESSION_MAX", 8),
        break_min_m: int = _env_int("BOT_BREAK_MIN", 15),
        break_max_m: int = _env_int("BOT_BREAK_MAX", 45),
    ):
        self.active_start = active_start
        self.active_end = active_end
        self.session_min_h = session_min_h
        self.session_max_h = session_max_h
        self.break_min_m = break_min_m
        self.break_max_m = break_max_m

        self._session_start: Optional[float] = None
        self._session_end: Optional[float] = None
        self._on_break: bool = False
        self._break_until: Optional[float] = None

        self._plan_session()

    # ── Public API ────────────────────────────────────────────────────────────

    def should_run(self) -> bool:
        """Return True if bot should be actively running right now."""
        now = time.time()
        dt = datetime.fromtimestamp(now)

        # Hard night-time stop
        if not self._in_active_window(dt):
            logger.debug(
                "Scheduler: outside active window (%02d:00–%02d:00)",
                self.active_start,
                self.active_end,
            )
            return False

        # On break?
        if self._on_break:
            if self._break_until and now < self._break_until:
                remaining = int(self._break_until - now)
                logger.debug("Scheduler: on break, %ds remaining", remaining)
                return False
            else:
                # Break over — plan new session
                self._on_break = False
                self._plan_session()

        # Session expired?
        if self._session_end and now >= self._session_end:
            self._start_break()
            return False

        return True

    def tick(self) -> None:
        """Call once per bot tick to log session state (optional)."""
        if self._session_end:
            remaining = max(0, self._session_end - time.time())
            if remaining < 300 and int(remaining) % 60 == 0:
                logger.info("Scheduler: session ends in %.0f min", remaining / 60)

    def session_elapsed_s(self) -> float:
        """Seconds since current session started."""
        if self._session_start is None:
            return 0.0
        return time.time() - self._session_start

    def status(self) -> dict:
        """Return human-readable scheduler state."""
        return {
            "should_run": self.should_run(),
            "on_break": self._on_break,
            "break_until": datetime.fromtimestamp(self._break_until).strftime(
                "%H:%M:%S"
            )
            if self._break_until
            else None,
            "session_elapsed_m": round(self.session_elapsed_s() / 60, 1),
            "session_ends_at": datetime.fromtimestamp(self._session_end).strftime(
                "%H:%M:%S"
            )
            if self._session_end
            else None,
            "active_window": f"{self.active_start:02d}:00–{self.active_end:02d}:00",
        }

    # ── Private helpers ───────────────────────────────────────────────────────

    def _in_active_window(self, dt: datetime) -> bool:
        """True if current hour is within active window."""
        h = dt.hour
        if self.active_start == self.active_end:
            return False
        if self.active_start < self.active_end:
            return self.active_start <= h <= self.active_end
        # Overnight window (e.g. 22:00–06:00)
        return h >= self.active_start or h <= self.active_end

    def _plan_session(self) -> None:
        """Randomise session length with slight weekend variation."""
        dt = datetime.now()
        is_weekend = dt.weekday() >= 5  # Saturday=5, Sunday=6
        jitter = random.uniform(-0.5, 0.5)  # ±30 min
        base_h = random.uniform(self.session_min_h, self.session_max_h)
        # Weekends: slightly shorter (more realistic)
        if is_weekend:
            base_h *= random.uniform(0.75, 0.95)
        duration_s = (base_h + jitter) * 3600
        duration_s = max(3600, duration_s)  # never less than 1h

        self._session_start = time.time()
        self._session_end = self._session_start + duration_s
        self._on_break = False

        logger.info(
            "Scheduler: new session planned — %.1fh until %s",
            duration_s / 3600,
            datetime.fromtimestamp(self._session_end).strftime("%H:%M"),
        )

    def _start_break(self) -> None:
        """Trigger a mandatory break."""
        break_s = random.randint(self.break_min_m, self.break_max_m) * 60
        # Randomise ±10%
        break_s = int(break_s * random.uniform(0.9, 1.1))
        self._on_break = True
        self._break_until = time.time() + break_s
        self._session_start = None
        self._session_end = None
        logger.info(
            "Scheduler: break started — %.0f min until %s",
            break_s / 60,
            datetime.fromtimestamp(self._break_until).strftime("%H:%M"),
        )


# Module-level singleton
_scheduler: Optional[SessionScheduler] = None


def get_scheduler() -> SessionScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = SessionScheduler()
    return _scheduler
