"""CTOA agents package.

This package also provides a compatibility bridge for legacy imports that
expect ``execute_agent_for_task`` to come from ``agents``.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any, Dict


def _load_legacy_agents_module() -> ModuleType:
	"""Load ``runner/agents.py`` even when this package shadows ``agents``.

	We cannot rely on a normal ``import agents`` because this package directory
	has the same name and takes precedence on ``sys.path`` in some test setups.
	"""
	this_file = Path(__file__).resolve()
	legacy_path = this_file.parent.parent / "agents.py"
	spec = importlib.util.spec_from_file_location("runner_legacy_agents", legacy_path)
	if spec is None or spec.loader is None:
		raise ImportError(f"Cannot create spec for legacy agents module: {legacy_path}")

	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


_legacy = _load_legacy_agents_module()

# Re-export the legacy execution entrypoint expected by runner/tests.
execute_agent_for_task = _legacy.execute_agent_for_task  # type: ignore[attr-defined]

__all__ = ["execute_agent_for_task"]
