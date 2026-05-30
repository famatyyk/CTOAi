# AI Toolkit Editable Agents

Edit this file to quickly manage training/eval agents:
- agents/toolkit/editable_agents.json

Each agent maps to:
- prompt_path (prompt variant)
- dataset_path (evaluation dataset)
- results_path (where to store model outputs)

Quick validation in Python:
- from agents.definitions import list_toolkit_agents, get_toolkit_agent_config
- print(list_toolkit_agents())

Recommended run flow:
1. Edit prompt variants in evals/prompt-variants/
2. Keep dataset in evals/runs/run-001/dataset.jsonl
3. Generate per-agent result files
4. Aggregate metrics with:
- python scripts/ops/aggregate_agent_eval.py <results.jsonl>
