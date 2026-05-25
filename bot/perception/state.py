"""AGENT 7: Game state data model."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Position:
    x: int = 0
    y: int = 0
    z: int = 7  # floor level


@dataclass
class GameState:
    """Snapshot of current game state parsed from screen."""
    hp: int = 0
    hp_max: int = 100
    mp: int = 0
    mp_max: int = 100
    position: Position = field(default_factory=Position)
    target_id: Optional[int] = None
    target_hp_pct: int = 0
    bag_full: bool = False
    is_attacking: bool = False
    timestamp: float = 0.0

    @property
    def hp_pct(self) -> float:
        return (self.hp / self.hp_max * 100) if self.hp_max > 0 else 0

    @property
    def mp_pct(self) -> float:
        return (self.mp / self.mp_max * 100) if self.mp_max > 0 else 0

    def is_low_hp(self, threshold: int = 30) -> bool:
        return self.hp_pct < threshold

    def is_low_mp(self, threshold: int = 20) -> bool:
        return self.mp_pct < threshold
