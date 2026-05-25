"""AGENT 7: Main decision brain — delegates to rules (Phase 1) or ML (Phase 2)."""
from __future__ import annotations
from ..perception.state import GameState
from .rules import evaluate_rules

_USE_ML = False  # Switch to True when Agent 4 delivers trained model


def decide_action(state: GameState) -> str:
    """Return action string for current game state."""
    if _USE_ML:
        try:
            from .ml_model import predict_action
            return predict_action(state)
        except Exception:
            pass  # fall through to rules on ML failure
    return evaluate_rules(state)
