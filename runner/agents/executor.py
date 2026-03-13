"""Compatibility executor bridge for runtime dispatch.

This module exposes ``execute_agent_for_task`` from the legacy
``runner/agents.py`` while migration to package-native implementation is in
progress.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any, Dict


def _load_legacy_agents_module() -> ModuleType:
    """Load ``runner/agents.py`` regardless of package shadowing."""
    this_file = Path(__file__).resolve()
    legacy_path = this_file.parent.parent / "agents.py"
    spec = importlib.util.spec_from_file_location("runner_legacy_agents", legacy_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create spec for legacy agents module: {legacy_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_legacy = _load_legacy_agents_module()

# Preserve legacy signature/behavior while callers move to package-native path.
execute_agent_for_task = _legacy.execute_agent_for_task  # type: ignore[attr-defined]

__all__ = ["execute_agent_for_task"]
