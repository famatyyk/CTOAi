"""AGENT 4: Q-learning model — Phase 2 AI (ACTIVE).

State space: (hp_bucket, mp_bucket, has_target, bag_full, level_tier, nearby)
Action space: 10 actions
Reward: shaped per combat outcome logged via telemetry
Persistence: Q-table saved to data/qtable.json (auto-loaded on start)
"""
from __future__ import annotations

import json
import logging
import os
import random
from pathlib import Path

from ..perception.state import GameState

logger = logging.getLogger(__name__)

ACTIONS = [
    "attack", "flee_to_depot", "use_hp_potion", "use_mp_potion",
    "loot", "select_target", "follow_route", "go_to_depot", "idle", "use_strong_hp_potion",
]

# Hyperparameters
ALPHA   = 0.10   # learning rate
GAMMA   = 0.90   # discount factor
EPSILON = 0.15   # exploration rate (ε-greedy)

_QTABLE_PATH = Path(os.environ.get("BOT_DB_PATH", "data/bot.db")).parent / "qtable.json"
_Q_TABLE: dict[str, dict[str, float]] = {}
_loaded = False


def _load_qtable() -> None:
    global _loaded
    if _loaded:
        return
    _loaded = True
    if _QTABLE_PATH.exists():
        try:
            with open(_QTABLE_PATH, encoding="utf-8") as f:
                _Q_TABLE.update(json.load(f))
            logger.info("Q-table loaded: %d states from %s", len(_Q_TABLE), _QTABLE_PATH)
        except Exception as e:
            logger.warning("Q-table load failed: %s", e)


def save_qtable() -> None:
    """Persist Q-table to disk (call periodically / on shutdown)."""
    try:
        _QTABLE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_QTABLE_PATH, "w", encoding="utf-8") as f:
            json.dump(_Q_TABLE, f)
        logger.debug("Q-table saved: %d states", len(_Q_TABLE))
    except Exception as e:
        logger.warning("Q-table save failed: %s", e)


def _state_key(state: GameState) -> str:
    hp_bucket    = min(4, int(state.hp_pct // 20))   # 0-4
    mp_bucket    = min(4, int(state.mp_pct // 20))   # 0-4
    has_target   = 1 if state.target_id else 0
    bag_full     = 1 if state.bag_full else 0
    level_tier   = min(4, (state.level - 1) // 10)   # 0=1-10, 1=11-20, 2=21-30, 3=31-40, 4=41+
    has_nearby   = 1 if state.nearby_monsters else 0
    return f"{hp_bucket}_{mp_bucket}_{has_target}_{bag_full}_{level_tier}_{has_nearby}"


def _get_row(key: str) -> dict[str, float]:
    if key not in _Q_TABLE:
        _Q_TABLE[key] = {a: 0.0 for a in ACTIONS}
    return _Q_TABLE[key]


def predict_action(state: GameState) -> str:
    """Return action via ε-greedy policy. Falls back to rules on error."""
    _load_qtable()
    try:
        if random.random() < EPSILON:
            return random.choice(ACTIONS)   # explore
        key = _state_key(state)
        row = _get_row(key)
        return max(row, key=lambda a: row[a])  # exploit
    except Exception as e:
        logger.warning("predict_action failed: %s", e)
        return "idle"


def update_q(state: GameState, action: str, reward: float,
             next_state: GameState) -> None:
    """Q-learning TD update: Q(s,a) ← Q(s,a) + α[r + γ·maxQ(s',·) − Q(s,a)]"""
    _load_qtable()
    try:
        key      = _state_key(state)
        next_key = _state_key(next_state)
        row      = _get_row(key)
        next_row = _get_row(next_key)
        current  = row.get(action, 0.0)
        max_next = max(next_row.values())
        row[action] = current + ALPHA * (reward + GAMMA * max_next - current)
    except Exception as e:
        logger.warning("update_q failed: %s", e)


def compute_reward(prev_state: GameState, action: str, result: str,
                   curr_state: GameState) -> float:
    """Shape reward signal from state transition.

    Positive:  killing target (hp dropped to 0), gaining exp, looting gold
    Negative:  losing HP, using potion inefficiently, dying (hp→0)
    """
    reward = 0.0

    # Penalise HP loss heavily
    hp_delta = curr_state.hp_pct - prev_state.hp_pct
    if hp_delta < 0:
        reward += hp_delta * 0.5   # e.g. -20% HP → -10 reward

    # Reward for killing target
    if (prev_state.target_id is not None and prev_state.target_hp_pct > 0
            and curr_state.target_hp_pct == 0):
        reward += 15.0

    # Reward for looting (assumed gold)
    if action == "loot" and result == "ok":
        reward += 5.0

    # Penalise potion waste (used potion but HP was already high)
    if action in ("use_hp_potion", "use_strong_hp_potion") and prev_state.hp_pct > 70:
        reward -= 3.0

    # Penalise fleeing unless critical
    if action == "flee_to_depot" and prev_state.hp_pct > 20:
        reward -= 2.0

    # Penalise idle
    if action == "idle":
        reward -= 0.5

    return reward
