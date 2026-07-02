"""
BRAVE(R) Prompt Template System
Background + Role + Action + Values + Examples + Result
"""

_COMPONENT_ALIASES = {
    "reasoning": "analysis",
}

BRAVER_TEMPLATES = {
    "task-execution": {
        "business": """
## Business Context
You are working on: {task_id}: {task_title}
Priority: {priority}
Assigned to agents: {agents}
Deadline: {deadline}
Success criteria: {success_criteria}
""",

        "analysis": """
## Task Analysis
Break down the task:
1. What must be accomplished?
2. What are the constraints?
3. What could go wrong?
4. What tools are available?

Decision inputs:
{user_reasoning}
""",

        "action": """
## Action Plan
Step-by-step execution:
{action_steps}

Tools to use:
{tool_list}

Fallback if tool fails:
{fallback_plan}
""",

        "value": """
## Expected Value & Impact
- Immediate impact: {immediate_impact}
- Long-term value: {long_term_value}
- Risk/benefit ratio: {risk_benefit}
- Success probability: {success_probability}
""",

        "evidence": """
## Supporting Evidence
Facts and data:
{evidence_list}

Similar completed tasks:
{precedent_tasks}

Tool reliability data:
{tool_reliability}
""",

        "reflection": """
## Reflection & Learning
What went well:
{what_went_well}

What could improve:
{improvements}

Lessons for next time:
{lessons}

Confidence in outcome: {confidence_level}/10
"""
    },

    "decision-making": {
        "business": """
## Business Decision
Decision: {decision_statement}
Stakeholders: {stakeholders}
Impact scope: {impact_scope}
Time sensitivity: {time_sensitivity}
""",

        "analysis": """
## Decision Analysis
Options considered:
{options}

Pros/cons analysis:
{pros_cons}

Why this option wins:
{why_chosen}
""",

        "action": """
## Implementation
First steps:
{first_steps}

Communication plan:
{communications}

Rollback plan if needed:
{rollback}
""",

        "value": """
## Value Proposition
Expected outcomes:
{outcomes}

Measurable metrics:
{metrics}
""",

        "evidence": """
## Decision Data
Historical precedent:
{precedent}

Supporting analysis:
{supporting_data}
""",

        "reflection": """
## Post-Decision Review
Was it the right call:
{review}

How to improve decisions next time:
{improvement_plan}
"""
    }
}


def get_template(template_type):
    """Get BRAVE(R) template for a type."""
    return BRAVER_TEMPLATES.get(template_type)


def normalize_component_name(component):
    """Map legacy component names to the canonical runtime component name."""
    return _COMPONENT_ALIASES.get(component, component)


def render_template(template_type, component, **variables):
    """Render a specific component with variables."""
    normalized = normalize_component_name(component)
    template = BRAVER_TEMPLATES.get(template_type, {}).get(normalized, "")
    return template.format(**variables, missing_var="[UNKNOWN]")


def get_all_components():
    """Get all BRAVE(R) runtime components."""
    return ["business", "analysis", "action", "value", "evidence", "reflection"]


API_COST_OPTIMIZER_BRAVER_TEMPLATE = """
[BACKGROUND]
The continuous evaluation run (evals/runs/) indicates an anomalous token usage spike. Current budget thresholds are approaching the maximum limits established in policies/.

[ROLE]
You are APICostOptimizerAgent. Operating strictly under STRATEGOS mode. You evaluate financial and prompt overheads, but you do not apply structural downgrades without explicit human permission.

[ACTIONS & TOOLS]
Query billing_metrics_provider to isolate the high-cost variant from evals/prompt-variants. Evaluate risk parameters before modifying config/ files.

[VALIDATION GATES]
Ensure the fallback model recommendation maintains compliance with active sprint product KPIs. Do not violate core accuracy constraints.

[EVIDENCE REQUIREMENTS]
Output JSON format ONLY:
{
  "anomalous_component": "string",
  "token_burn_reduction_pct": float,
  "suggested_model_matrix": {
    "primary": "string",
    "fallback": "string"
  },
  "estimated_scoring_impact": {"cost": float, "risk": float}
}
"""

BRAVER_TEMPLATES["api-cost-optimizer"] = {
    "business": """
## Business Context
API token usage has exceeded expected velocity.
Budget threshold: {budget_threshold}
Observed burn rate: {observed_burn_rate}
Affected eval run: {eval_run}
""",
    "analysis": """
## Cost Analysis
Identify the anomalous component, high-cost prompt variant, and expected token-burn reduction.
Decision inputs:
{cost_evidence}
""",
    "action": """
## Guarded Recommendation
Recommend model routing changes only. Do not apply config edits without explicit owner approval.
Candidate matrix:
{model_matrix}
""",
    "value": """
## Expected Value
Token burn reduction target: {token_burn_reduction_pct}
Estimated scoring impact:
{estimated_scoring_impact}
""",
    "evidence": """
## Evidence Requirements
Return JSON only with anomalous_component, token_burn_reduction_pct, suggested_model_matrix, and estimated_scoring_impact.
Evidence:
{evidence_list}
""",
    "reflection": """
## Guardrail Reflection
Confirm that no structural downgrade or config mutation is applied without human approval.
Confidence: {confidence_level}/10
""",
}
