"""Non-cryptographic randomness for bot behavior and ML exploration.

This module centralizes random jitter used for scheduling, humanization, and
Q-learning exploration. Do not use it for secrets, tokens, keys, or auth.
"""

from __future__ import annotations

import random as _random
from collections.abc import MutableSequence, Sequence
from typing import TypeVar

T = TypeVar("T")

_RNG = _random.Random()  # nosec


def random() -> float:
    return _RNG.random()  # nosec B311


def randint(left: int, right: int) -> int:
    return _RNG.randint(left, right)  # nosec B311


def uniform(left: float, right: float) -> float:
    return _RNG.uniform(left, right)  # nosec B311


def gauss(mean: float, sigma: float) -> float:
    return _RNG.gauss(mean, sigma)  # nosec B311


def choice(items: Sequence[T]) -> T:
    return _RNG.choice(items)  # nosec B311


def shuffle(items: MutableSequence[T]) -> None:
    _RNG.shuffle(items)  # nosec B311
