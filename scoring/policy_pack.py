"""Governance policy pack for tool recommendations."""
from __future__ import annotations

from typing import Any


def apply_rules(recommended_tools: list[dict[str, Any]], task_type: str) -> list[dict[str, Any]]:
    """Apply the default policy layer to a ranked tool list.

    The current policy pack is intentionally conservative: it preserves the
    ranking produced upstream and gives the repo a concrete governance surface
    for docs and future rule expansion.
    """
    _ = task_type
    return list(recommended_tools)

