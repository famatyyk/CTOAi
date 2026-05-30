"""Agent registry backed by agents/ctoa-agents.yaml."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

_REGISTRY_PATH = Path(__file__).with_name('ctoa-agents.yaml')
_REQUIRED_AGENT_FIELDS = {
    'id',
    'name',
    'description',
    'role',
    'mission',
    'capabilities',
    'assigned_tasks',
    'tool_score_weight',
}


def _normalize_agent(agent: dict[str, Any]) -> dict[str, Any]:
    return {
        'name': str(agent.get('name', agent['id'])),
        'description': str(agent.get('description', agent.get('mission', ''))),
        'role': str(agent.get('role', '')),
        'mission': str(agent.get('mission', '')),
        'inputs': list(agent.get('inputs', [])),
        'outputs': list(agent.get('outputs', [])),
        'kpi': list(agent.get('kpi', [])),
        'capabilities': list(agent.get('capabilities', [])),
        'assigned_tasks': list(agent.get('assigned_tasks', [])),
        'tool_score_weight': dict(agent.get('tool_score_weight', {})),
    }


def _read_registry_payload(registry_path: Path = _REGISTRY_PATH) -> dict[str, Any]:
    if not registry_path.exists():
        return {}
    payload = yaml.safe_load(registry_path.read_text(encoding='utf-8-sig')) or {}
    return payload if isinstance(payload, dict) else {}


def _load_registry(registry_path: Path = _REGISTRY_PATH) -> dict[str, dict[str, Any]]:
    payload = _read_registry_payload(registry_path)
    agents = payload.get('agents', [])

    registry: dict[str, dict[str, Any]] = {}
    for agent in agents:
        if not isinstance(agent, dict) or 'id' not in agent:
            continue
        registry[str(agent['id'])] = _normalize_agent(agent)
    return registry


def validate_registry_consistency(registry_path: Path = _REGISTRY_PATH) -> list[str]:
    payload = _read_registry_payload(registry_path)
    raw_agents = payload.get('agents', []) if isinstance(payload, dict) else []
    registry = _load_registry(registry_path)
    issues: list[str] = []
    seen_ids: set[str] = set()

    for agent in raw_agents:
        if not isinstance(agent, dict):
            issues.append('registry contains a non-dict agent entry')
            continue

        agent_id = str(agent.get('id', ''))
        if not agent_id:
            issues.append('registry contains an agent without id')
            continue
        if agent_id in seen_ids:
            issues.append(f'duplicate agent id: {agent_id}')
        seen_ids.add(agent_id)

        missing_fields = sorted(field for field in _REQUIRED_AGENT_FIELDS if field not in agent)
        if missing_fields:
            issues.append(f'{agent_id} missing fields: {", ".join(missing_fields)}')

        weights = agent.get('tool_score_weight', {})
        if not isinstance(weights, dict) or not weights:
            issues.append(f'{agent_id} has invalid tool_score_weight')
        else:
            total = sum(float(value) for value in weights.values())
            if abs(total - 1.0) > 0.11:
                issues.append(f'{agent_id} tool_score_weight sums to {total:.2f}')

        capabilities = agent.get('capabilities', [])
        if not isinstance(capabilities, list) or not capabilities:
            issues.append(f'{agent_id} has no capabilities')

    if set(registry.keys()) != seen_ids:
        issues.append('loaded registry keys do not match raw YAML ids')

    return issues


AGENTS = _load_registry()


def get_agent_config(agent_id):
    """Get agent configuration."""
    return AGENTS.get(agent_id)


def list_agents():
    """List all agents."""
    return list(AGENTS.keys())


def get_agents_for_task(task_id):
    """Get agents assigned to a task."""
    agents = []
    for agent_id, config in AGENTS.items():
        if task_id in config.get('assigned_tasks', []):
            agents.append(agent_id)
    return agents


def _load_toolkit_registry(registry_path: str = 'agents/toolkit/editable_agents.json'):
    """Load editable AI Toolkit agent registry from JSON file."""
    path = Path(registry_path)
    if not path.exists():
        return {}

    with path.open('r', encoding='utf-8-sig') as handle:
        payload = json.load(handle)

    return payload.get('agents', {}) if isinstance(payload, dict) else {}


def list_toolkit_agents(registry_path: str = 'agents/toolkit/editable_agents.json'):
    """List editable toolkit agent IDs."""
    return list(_load_toolkit_registry(registry_path).keys())


def get_toolkit_agent_config(agent_id: str, registry_path: str = 'agents/toolkit/editable_agents.json'):
    """Get editable toolkit agent configuration by ID."""
    return _load_toolkit_registry(registry_path).get(agent_id)
