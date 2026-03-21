"""
Hybrid Tibia Bot - Template Matching + A* Pathfinding + oCTObot Logic

Architecture:
  ├─ vision_layer.py      (Template matching for GPS, Health, Targeting)
  ├─ pathfinding.py       (A* with game-aware weights)
  ├─ prompt_logic.py      (oCTObot decision prompts)
  ├─ state_manager.py     (Game state tracking)
  ├─ metrics.py           (XP, Balance, Supplies tracking)
  └─ bot_runner.py        (Main orchestration)
"""

from .bot_runner import BotConfig, HybridBotRunner
from .metrics import MetricsCollector
from .pathfinding import Pathfinder
from .prompt_logic import PromptLogic
from .state_manager import StateManager
from .vision_layer import VisionLayer

__version__ = "1.0.0"
__all__ = [
    "BotConfig",
    "HybridBotRunner",
    "MetricsCollector",
    "VisionLayer",
    "Pathfinder",
    "PromptLogic",
    "StateManager",
]
