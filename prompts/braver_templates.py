"""
BRAVE(R) Prompt Template System
Business + Reasoning + Action + Value + Evidence + Reflection
"""

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
        
        "reasoning": """
## Reasoning
Break down the task:
1. What must be accomplished?
2. What are the constraints?
3. What could go wrong?
4. What tools are available?

Your reasoning:
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
        
        "reasoning": """
## Decision Reasoning
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
    """Get BRAVE(R) template for a type"""
    return BRAVER_TEMPLATES.get(template_type)

def render_template(template_type, component, **variables):
    """Render a specific component with variables"""
    template = BRAVER_TEMPLATES.get(template_type, {}).get(component, "")
    return template.format(**variables, missing_var="[UNKNOWN]")

def get_all_components():
    """Get all BRAVE(R) components"""
    return ["business", "reasoning", "action", "value", "evidence", "reflection"]
