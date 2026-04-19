"""
CTOA AI Toolkit — Azure AI Foundry Hosted Agent Adapter

Wraps the CTOA orchestrator pipeline as a Foundry-compatible HTTP service
using the azure-ai-agentserver-core custom framework adapter.

Supported commands (user input → action):
  run pipeline         → run full scout→ingest→brain→generate→validate→publish
  run <step>           → run single pipeline step by name
  status               → current task-state.yaml summary
  sprint               → active sprint backlog info
  help                 → show available commands

Usage:
  python ctoa_foundry_agent.py          (starts HTTP server on :8088)
  POST http://localhost:8088/responses  {"input": "run pipeline"}
"""

from __future__ import annotations

import io
import json
import logging
import os
import sys
from contextlib import redirect_stdout
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncGenerator, Dict

from dotenv import load_dotenv

load_dotenv(override=False)

# ---------------------------------------------------------------------------
# azure-ai-agentserver-core imports
# ---------------------------------------------------------------------------
from azure.ai.agentserver.core import AgentRunContext, FoundryCBAgent
from azure.ai.agentserver.core.models import Response as OpenAIResponse, ResponseStreamEvent
from azure.ai.agentserver.core.models.projects import (
    ItemContentOutputText,
    ResponseCompletedEvent,
    ResponseCreatedEvent,
    ResponseOutputItemAddedEvent,
    ResponsesAssistantMessageItemResource,
    ResponseTextDeltaEvent,
    ResponseTextDoneEvent,
)
from azure.ai.agentserver.core.logger import get_logger

logger = get_logger()

ROOT = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Pipeline registry
# ---------------------------------------------------------------------------
PIPELINE_STEPS = [
    "scout_agent",
    "ingest_agent",
    "brain_v2",
    "generator_agent",
    "validator_agent",
    "publisher_agent",
]

HELP_TEXT = """\
CTOA Orchestrator — available commands:

  run pipeline              Run the full 6-step pipeline
  run <step_name>           Run a single step (e.g. "run scout_agent")
  status                    Show current task-state summary
  sprint                    Show active sprint backlog
  help                      Show this message

Pipeline steps: """ + ", ".join(PIPELINE_STEPS)


def _capture_step(module_path: str) -> str:
    """Run a single pipeline step and return captured stdout + result."""
    buf = io.StringIO()
    try:
        parts = module_path.rsplit(".", 1)
        mod = __import__(module_path, fromlist=[parts[-1]])
        with redirect_stdout(buf):
            mod.run_once()
        output = buf.getvalue().strip()
        return f"✓ {module_path}: OK\n{output}" if output else f"✓ {module_path}: OK"
    except Exception as exc:
        return f"✗ {module_path}: ERROR — {exc}"


def _run_full_pipeline() -> str:
    """Run the full orchestrator pipeline and return a text report."""
    sys.path.insert(0, str(ROOT))
    lines: list[str] = ["=== CTOA Pipeline Run ==="]
    for name, module_path in [(s, f"runner.agents.{s}") for s in PIPELINE_STEPS]:
        result = _capture_step(module_path)
        lines.append(result)
    return "\n".join(lines)


def _run_single_step(step: str) -> str:
    sys.path.insert(0, str(ROOT))
    if step not in PIPELINE_STEPS:
        return f"Unknown step '{step}'. Valid steps: {', '.join(PIPELINE_STEPS)}"
    return _capture_step(f"runner.agents.{step}")


def _get_status() -> str:
    state_file = ROOT / "runtime" / "task-state.yaml"
    if not state_file.exists():
        return "task-state.yaml not found. No pipeline runs recorded yet."
    try:
        import yaml
        with state_file.open(encoding="utf-8") as f:
            state = yaml.safe_load(f) or {}
        lines = ["=== CTOA Task State ==="]
        for task_id, info in list(state.items())[:20]:
            status = info.get("status", "?") if isinstance(info, dict) else str(info)
            lines.append(f"  {task_id}: {status}")
        if len(state) > 20:
            lines.append(f"  ... and {len(state) - 20} more tasks")
        return "\n".join(lines)
    except Exception as exc:
        return f"Error reading task-state: {exc}"


def _get_sprint_info() -> str:
    import glob
    pattern = str(ROOT / "workflows" / "backlog-sprint-*.yaml")
    files = sorted(glob.glob(pattern))
    if not files:
        return "No sprint backlog files found."
    try:
        import yaml
        latest = files[-1]
        with open(latest, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        sprint_id = data.get("sprint_id", Path(latest).stem)
        tasks = data.get("tasks", [])
        lines = [f"=== Sprint: {sprint_id} ({len(tasks)} tasks) ==="]
        for t in tasks[:10]:
            tid = t.get("id", "?")
            title = t.get("title", "?")
            status = t.get("status", "NEW")
            lines.append(f"  [{status}] {tid}: {title}")
        if len(tasks) > 10:
            lines.append(f"  ... and {len(tasks) - 10} more tasks")
        return "\n".join(lines)
    except Exception as exc:
        return f"Error reading sprint backlog: {exc}"


def _dispatch(user_message: str) -> str:
    msg = user_message.strip().lower()
    if msg in ("help", "?", "commands"):
        return HELP_TEXT
    if msg in ("run pipeline", "run full pipeline", "pipeline", "start pipeline"):
        return _run_full_pipeline()
    if msg.startswith("run "):
        step = msg[4:].strip()
        return _run_single_step(step)
    if msg in ("status", "get status", "state"):
        return _get_status()
    if msg in ("sprint", "backlog", "sprint info"):
        return _get_sprint_info()
    # Default: try to interpret as pipeline step or return help
    if msg in PIPELINE_STEPS:
        return _run_single_step(msg)
    return (
        f"Unknown command: '{user_message}'\n\n{HELP_TEXT}"
    )


# ---------------------------------------------------------------------------
# Foundry Hosted Agent
# ---------------------------------------------------------------------------

class CTOAOrchestrator(FoundryCBAgent):
    """CTOA AI Toolkit wrapped as a Foundry Hosted Agent."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        logger.info("CTOAOrchestrator initialized (ROOT=%s)", ROOT)

    async def agent_run(
        self,
        context: AgentRunContext,
    ) -> AsyncGenerator[ResponseStreamEvent, None]:
        # Extract last user message
        user_message = ""
        for item in reversed(context.request.input or []):
            role = getattr(item, "role", None)
            content = getattr(item, "content", None)
            if role == "user" and content:
                if isinstance(content, str):
                    user_message = content
                elif isinstance(content, list):
                    for part in content:
                        text = getattr(part, "text", None)
                        if text:
                            user_message = text
                            break
                break

        logger.info("Received message: %s", user_message[:120])
        response_text = _dispatch(user_message)
        logger.info("Dispatching complete (%d chars)", len(response_text))

        response_id = f"resp_{context.request_id[:8]}"
        item_id = f"item_{context.request_id[:8]}"

        yield ResponseCreatedEvent(
            response=OpenAIResponse(
                id=response_id,
                object="response",
                status="in_progress",
                output=[],
            )
        )

        yield ResponseOutputItemAddedEvent(
            item=ResponsesAssistantMessageItemResource(
                id=item_id,
                object="response.output_item",
                type="message",
                role="assistant",
                status="in_progress",
                content=[],
            ),
            output_index=0,
        )

        yield ResponseTextDeltaEvent(
            delta=response_text,
            content_index=0,
            output_index=0,
            item_id=item_id,
        )

        yield ResponseTextDoneEvent(
            text=response_text,
            content_index=0,
            output_index=0,
            item_id=item_id,
        )

        yield ResponseCompletedEvent(
            response=OpenAIResponse(
                id=response_id,
                object="response",
                status="completed",
                output=[
                    ResponsesAssistantMessageItemResource(
                        id=item_id,
                        object="response.output_item",
                        type="message",
                        role="assistant",
                        status="completed",
                        content=[
                            ItemContentOutputText(type="output_text", text=response_text)
                        ],
                    )
                ],
            )
        )


if __name__ == "__main__":
    agent = CTOAOrchestrator()
    agent.run()
