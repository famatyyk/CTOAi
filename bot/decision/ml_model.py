"""AGENT 4: Q-learning model stub — Phase 2 implementation."""
from __future__ import annotations
from ..perception.state import GameState

# Q-table: state_key → {action: value}
_Q_TABLE: dict[str, dict[str, float]] = {}

ACTIONS = ["attack", "flee_to_depot", "use_hp_potion", "use_mp_potion",
           "loot", "find_monster", "go_to_depot", "idle"]


def _state_key(state: GameState) -> str:
    hp_bucket = int(state.hp_pct // 20)   # 0-4
    mp_bucket = int(state.mp_pct // 20)   # 0-4
    has_target = 1 if state.target_id else 0
    bag_full   = 1 if state.bag_full else 0
    return f"{hp_bucket}_{mp_bucket}_{has_target}_{bag_full}"


def predict_action(state: GameState) -> str:
    """Return best action from Q-table, or 'idle' if no data."""
    key = _state_key(state)
    if key not in _Q_TABLE:
        return "idle"
    return max(_Q_TABLE[key], key=lambda a: _Q_TABLE[key][a])


def update_q(state: GameState, action: str, reward: float,
             next_state: GameState, alpha: float = 0.1, gamma: float = 0.9) -> None:
    """Q-learning update step."""
    key = _state_key(state)
    next_key = _state_key(next_state)

    if key not in _Q_TABLE:
        _Q_TABLE[key] = {a: 0.0 for a in ACTIONS}
    if next_key not in _Q_TABLE:
        _Q_TABLE[next_key] = {a: 0.0 for a in ACTIONS}

    current_q = _Q_TABLE[key].get(action, 0.0)
    max_next_q = max(_Q_TABLE[next_key].values())
    _Q_TABLE[key][action] = current_q + alpha * (reward + gamma * max_next_q - current_q)
