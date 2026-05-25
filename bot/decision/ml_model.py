"""AGENT 4: Double Q-learning — Sprint 6 AI upgrade.

Replaces single tabular Q-learning with Double Q-learning (van Hasselt 2010).
Two Q-tables (A and B) alternate updates — selection uses one, evaluation uses other.
Eliminates overestimation bias → more stable policy, better combat decisions.

State space: 6D (hp_bucket, mp_bucket, has_target, bag_full, level_tier, nearby)
Action space: 10 actions
Hyperparameters: α=0.10, γ=0.90, ε=0.15 (decays to 0.05 over 50k steps)
Persistence: both tables saved to data/qtable_a.json + data/qtable_b.json
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
ALPHA        = 0.10    # learning rate
GAMMA        = 0.90    # discount factor
EPSILON_MAX  = 0.15    # initial exploration rate
EPSILON_MIN  = 0.05    # minimum exploration rate (after decay)
EPSILON_DECAY_STEPS = 50_000

_DATA_DIR    = Path(os.environ.get("BOT_DB_PATH", "data/bot.db")).parent
_QTABLE_A    = _DATA_DIR / "qtable_a.json"
_QTABLE_B    = _DATA_DIR / "qtable_b.json"
_STEPS_FILE  = _DATA_DIR / "dql_steps.json"

# Two Q-tables
_Q_A: dict[str, dict[str, float]] = {}
_Q_B: dict[str, dict[str, float]] = {}
_step_count: int = 0
_loaded = False


def _load() -> None:
    global _loaded, _step_count
    if _loaded:
        return
    _loaded = True
    for path, table in ((_QTABLE_A, _Q_A), (_QTABLE_B, _Q_B)):
        if path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    table.update(json.load(f))
                logger.info("DQL table %s loaded: %d states", path.name, len(table))
            except Exception as e:
                logger.warning("DQL table load failed (%s): %s", path.name, e)
    if _STEPS_FILE.exists():
        try:
            _step_count = json.loads(_STEPS_FILE.read_text()).get("steps", 0)
        except Exception:
            pass


def save_qtable() -> None:
    """Persist both Q-tables and step counter to disk."""
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        for path, table in ((_QTABLE_A, _Q_A), (_QTABLE_B, _Q_B)):
            with open(path, "w", encoding="utf-8") as f:
                json.dump(table, f)
        _STEPS_FILE.write_text(json.dumps({"steps": _step_count}))
        logger.debug("DQL tables saved: A=%d B=%d states, step=%d",
                     len(_Q_A), len(_Q_B), _step_count)
    except Exception as e:
        logger.warning("DQL save failed: %s", e)


def _epsilon() -> float:
    """Linearly decay ε from EPSILON_MAX → EPSILON_MIN over EPSILON_DECAY_STEPS."""
    ratio = min(1.0, _step_count / EPSILON_DECAY_STEPS)
    return EPSILON_MAX - ratio * (EPSILON_MAX - EPSILON_MIN)


def _state_key(state: GameState) -> str:
    hp_bucket  = min(4, int(state.hp_pct // 20))
    mp_bucket  = min(4, int(state.mp_pct // 20))
    has_target = 1 if state.target_id else 0
    bag_full   = 1 if state.bag_full else 0
    level_tier = min(4, (state.level - 1) // 10)
    has_nearby = 1 if state.nearby_monsters else 0
    return f"{hp_bucket}_{mp_bucket}_{has_target}_{bag_full}_{level_tier}_{has_nearby}"


def _row(table: dict, key: str) -> dict[str, float]:
    if key not in table:
        table[key] = {a: 0.0 for a in ACTIONS}
    return table[key]


def predict_action(state: GameState) -> str:
    """ε-greedy Double Q-learning action selection.

    Uses average of both Q-tables for exploitation (reduces overestimation).
    """
    _load()
    global _step_count
    try:
        _step_count += 1
        if random.random() < _epsilon():
            return random.choice(ACTIONS)   # explore
        key = _state_key(state)
        row_a = _row(_Q_A, key)
        row_b = _row(_Q_B, key)
        # Average both tables for stable greedy selection
        combined = {a: (row_a[a] + row_b[a]) / 2 for a in ACTIONS}
        return max(combined, key=lambda a: combined[a])
    except Exception as e:
        logger.warning("DQL predict_action failed: %s", e)
        return "idle"


def update_q(state: GameState, action: str, reward: float,
             next_state: GameState) -> None:
    """Double Q-learning update — alternates which table updates each step.

    With prob 0.5:
      - Table A selects best action for next state
      - Table B evaluates that action (prevents maximisation bias)
    Or vice versa.
    """
    _load()
    try:
        key      = _state_key(state)
        next_key = _state_key(next_state)

        if random.random() < 0.5:
            # Update A, evaluate with B
            row_a      = _row(_Q_A, key)
            next_row_a = _row(_Q_A, next_key)
            next_row_b = _row(_Q_B, next_key)
            best_action_a = max(next_row_a, key=lambda a: next_row_a[a])
            target = reward + GAMMA * next_row_b[best_action_a]
            row_a[action] += ALPHA * (target - row_a.get(action, 0.0))
        else:
            # Update B, evaluate with A
            row_b      = _row(_Q_B, key)
            next_row_b = _row(_Q_B, next_key)
            next_row_a = _row(_Q_A, next_key)
            best_action_b = max(next_row_b, key=lambda a: next_row_b[a])
            target = reward + GAMMA * next_row_a[best_action_b]
            row_b[action] += ALPHA * (target - row_b.get(action, 0.0))

        # Probabilistic save (1% chance per update)
        if random.random() < 0.01:
            save_qtable()

    except Exception as e:
        logger.warning("DQL update_q failed: %s", e)


def compute_reward(prev_state: GameState, action: str, result: str,
                   curr_state: GameState) -> float:
    """Shape reward signal from state transition (unchanged from Sprint 5)."""
    reward = 0.0

    hp_delta = curr_state.hp_pct - prev_state.hp_pct
    if hp_delta < 0:
        reward += hp_delta * 0.5

    if (prev_state.target_id is not None and prev_state.target_hp_pct > 0
            and curr_state.target_hp_pct == 0):
        reward += 15.0

    if action == "loot" and result == "ok":
        reward += 5.0

    if action in ("use_hp_potion", "use_strong_hp_potion") and prev_state.hp_pct > 70:
        reward -= 3.0

    if action == "flee_to_depot" and prev_state.hp_pct > 20:
        reward -= 2.0

    if action == "idle":
        reward -= 0.5

    return reward
