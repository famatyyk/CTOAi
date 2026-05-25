"""AGENT 7: Main decision brain — delegates to rules (Phase 1) or Q-learning (Phase 2)."""
from __future__ import annotations
import copy
from ..perception.state import GameState
from .rules import evaluate_rules

_USE_ML = True   # AGENT 4: Q-learning activated (Sprint 4)

_prev_state: GameState | None = None
_prev_action: str = "idle"


def decide_action(state: GameState) -> str:
    """Return action string for current game state.

    When ML is active:
    1. Computes reward for previous (state, action) pair
    2. Updates Q-table
    3. Picks next action via ε-greedy policy with rules fallback
    """
    global _prev_state, _prev_action

    if _USE_ML:
        try:
            from .ml_model import predict_action, update_q, compute_reward, save_qtable
            import threading

            # Reward feedback from last step
            if _prev_state is not None:
                reward = compute_reward(_prev_state, _prev_action, "ok", state)
                update_q(_prev_state, _prev_action, reward, state)

            action = predict_action(state)

            # Save Q-table periodically on background thread (every ~100 calls)
            import random
            if random.random() < 0.01:
                threading.Thread(target=save_qtable, daemon=True).start()

            _prev_state  = copy.copy(state)
            _prev_action = action
            return action

        except Exception:
            pass  # fall through to rules on any ML failure

    return evaluate_rules(state)
