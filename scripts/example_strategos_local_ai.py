#!/usr/bin/env python3
"""
STRATEGOS Integration Example: Using Local LLM for Strategic Decisions

This shows how your STRATEGOS agent and 10 sub-agents can use the local Qwen model
for real-time decision-making without Azure costs.
"""

from pathlib import Path
from typing import Any, Dict

# Add repo root to path
import sys
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from runner.llm_providers import get_provider


class StrategosLocalAI:
    """Strategist agent powered by local model."""

    def __init__(self):
        self.provider = get_provider()
        self.name = "STRATEGOS"

    def assess_sprint_blocker(self, blocker_desc: str, affected_agents: list) -> str:
        """Assess if blocker needs escalation to God Mode."""
        prompt = f"""
As STRATEGOS, analyze this sprint blocker and determine escalation:

Blocker: {blocker_desc}
Affected Agents: {', '.join(affected_agents)}

Respond with:
1. Severity (LOW/MEDIUM/HIGH/CRITICAL)
2. Escalate to God Mode? (YES/NO)
3. Immediate action

Keep response concise (5 lines max).
"""
        return self.provider.complete(
            system_prompt=(
                "You are STRATEGOS, the Supreme Commander. Make decisive calls. "
                "Escalate if >= 3 agents blocked or P0 risk detected."
            ),
            user_prompt=prompt,
            temperature=0.1,
            max_tokens=256,
        )

    def generate_daily_assignments(self, tasks: list) -> str:
        """Generate daily task assignments for agents 2-10."""
        task_str = "\n".join([f"- {t['id']}: {t['title']}" for t in tasks])
        prompt = f"""
STRATEGOS daily planning. Assign tasks to agents 2-10 with exit signals.

Available Tasks:
{task_str}

Agent specializations:
- Agent 2: Core Architecture
- Agent 3: Data Engineering
- Agent 4: ML Brain
- Agent 5: Security
- Agent 6: Game Logic
- Agent 7: Code Implementation
- Agent 8: QA
- Agent 9: DevOps
- Agent 10: Documentation

Generate assignment plan with clear exit criteria for each agent.
"""
        return self.provider.complete(
            system_prompt="You are a tactical sprint orchestrator.",
            user_prompt=prompt,
            temperature=0.05,
            max_tokens=512,
        )

    def evaluate_qa_report(self, qa_results: Dict[str, Any]) -> str:
        """Review QA results and recommend gate approval."""
        prompt = f"""
QA Report from Agent 8:
- Tests Passed: {qa_results.get('passed', 0)}
- Tests Failed: {qa_results.get('failed', 0)}
- Coverage: {qa_results.get('coverage_pct', 0)}%
- Critical Issues: {qa_results.get('critical', 0)}

Should we advance to release gate? Recommend APPROVE or BLOCK.
Rationale in 3 lines.
"""
        return self.provider.complete(
            system_prompt="You are QA gate keeper for sprint releases.",
            user_prompt=prompt,
            temperature=0.0,  # Deterministic for gate decisions
            max_tokens=256,
        )


class Agent7LocalAIIntegration:
    """CODE_SMITH (Agent 7) using local model for code generation."""

    def __init__(self):
        self.provider = get_provider()
        self.name = "CODE_SMITH"

    def generate_performance_profile(self) -> str:
        """Generate performance benchmarking code."""
        prompt = """
Generate Python code to benchmark a Tibia bot's performance:
- Screen capture latency
- Game state parsing time
- Decision loop time
- Action execution time
- Memory usage

Include timers and reporting. ~50 lines.
"""
        return self.provider.complete(
            system_prompt=(
                "You are CODE_SMITH, expert Python developer. "
                "Generate production-ready code with timing instrumentation."
            ),
            user_prompt=prompt,
            temperature=0.1,
            max_tokens=1024,
        )

    def refactor_legacy_module(self, module_description: str) -> str:
        """Suggest refactoring for older modules."""
        prompt = f"""
Module to refactor: {module_description}

Provide refactoring steps:
1. Identify tech debt
2. Suggest fixes (keep functionality)
3. Estimated effort (hours)

Keep concise, action-oriented.
"""
        return self.provider.complete(
            system_prompt="You are a code quality engineer.",
            user_prompt=prompt,
            temperature=0.1,
            max_tokens=512,
        )


def example_strategos_flow():
    """Example: STRATEGOS using local AI for daily planning."""
    print("="*60)
    print("STRATEGOS Local AI Integration Example")
    print("="*60)

    strategos = StrategosLocalAI()

    # Check provider health
    if not strategos.provider.health():
        print("ERROR: Local model not available, falling back to Azure (if configured)")
        return

    print("\n[STRATEGOS] Assessing sprint blocker...")
    blocker_result = strategos.assess_sprint_blocker(
        blocker_desc="ML model training OOM on VPS, blocking Agent 4",
        affected_agents=["Agent 4 (ML Brain)", "Agent 7 (Code Smith)"]
    )
    print(blocker_result)

    print("\n[STRATEGOS] Generating daily assignments...")
    assignments = strategos.generate_daily_assignments([
        {"id": "CTOA-041", "title": "Implement movement algorithm"},
        {"id": "CTOA-042", "title": "Add combat decision tree"},
        {"id": "CTOA-043", "title": "Write security audit"},
    ])
    print(assignments)

    print("\n[STRATEGOS] Evaluating QA gate...")
    qa_call = strategos.evaluate_qa_report({
        "passed": 45,
        "failed": 3,
        "coverage_pct": 87.5,
        "critical": 0,
    })
    print(qa_call)


def example_agent7_flow():
    """Example: Agent 7 (CODE_SMITH) using local AI for code generation."""
    print("\n" + "="*60)
    print("CODE_SMITH Local AI Integration Example")
    print("="*60)

    agent7 = Agent7LocalAIIntegration()

    if not agent7.provider.health():
        print("ERROR: Local model not available")
        return

    print("\n[CODE_SMITH] Generating performance benchmark code...")
    benchmark_code = agent7.generate_performance_profile()
    print(benchmark_code[:500] + "..." if len(benchmark_code) > 500 else benchmark_code)

    print("\n[CODE_SMITH] Refactoring legacy perception module...")
    refactor = agent7.refactor_legacy_module("Perception module: screen capture and state parsing")
    print(refactor)


if __name__ == "__main__":
    print("CTOAi Local AI Agent Integration Examples\n")

    # Run examples
    example_strategos_flow()
    example_agent7_flow()

    print("\n" + "="*60)
    print("Integration complete! Adapt these patterns to your agents.")
    print("="*60)
