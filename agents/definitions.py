"""
Agent Framework - 10 Agent Definitions
CTOA AI Toolkit agent descriptions and tool assignments
"""

AGENTS = {
    "lua-scripter": {
        "name": "Lua Scripter Agent",
        "description": "Writes and optimizes Lua code for bot scripting",
        "capabilities": [
            "lua-syntax-validation",
            "code-generation",
            "performance-optimization",
            "library-integration"
        ],
        "assigned_tasks": ["CTOA-001", "CTOA-002", "CTOA-003", "CTOA-006"],
        "tool_score_weight": {"efficacy": 0.4, "safety": 0.3, "cost": 0.2, "latency": 0.1}
    },
    
    "bot-architect": {
        "name": "Bot Architecture Agent",
        "description": "Designs bot systems, pathing, and behavior trees",
        "capabilities": [
            "architecture-design",
            "pathfinding-algorithms",
            "state-machine-design",
            "system-integration"
        ],
        "assigned_tasks": ["CTOA-002", "CTOA-005", "CTOA-007"],
        "tool_score_weight": {"efficacy": 0.35, "safety": 0.25, "cost": 0.25, "latency": 0.15}
    },
    
    "qa-safety": {
        "name": "QA/Safety Agent",
        "description": "Tests bot safety, validates detection evasion, prevents bans",
        "capabilities": [
            "threat-modeling",
            "safety-validation",
            "anti-detection-testing",
            "regression-testing"
        ],
        "assigned_tasks": ["CTOA-001", "CTOA-003", "CTOA-008", "CTOA-009"],
        "tool_score_weight": {"efficacy": 0.3, "safety": 0.5, "cost": 0.1, "latency": 0.1}
    },
    
    "builder-engine": {
        "name": "Builder/Engine Agent",
        "description": "Implements core bot engine, resource management, state tracking",
        "capabilities": [
            "engine-development",
            "resource-management",
            "memory-optimization",
            "state-persistence"
        ],
        "assigned_tasks": ["CTOA-001", "CTOA-003", "CTOA-004", "CTOA-009"],
        "tool_score_weight": {"efficacy": 0.4, "safety": 0.2, "cost": 0.25, "latency": 0.15}
    },
    
    "mmo-intel": {
        "name": "MMO Intelligence Agent",
        "description": "Collects game intelligence, tracks enemies, identifies opportunities",
        "capabilities": [
            "data-collection",
            "pattern-recognition",
            "threat-assessment",
            "loot-analysis"
        ],
        "assigned_tasks": ["CTOA-005", "CTOA-007", "CTOA-008", "CTOA-010"],
        "tool_score_weight": {"efficacy": 0.35, "safety": 0.25, "cost": 0.2, "latency": 0.2}
    },
    
    "test-harness": {
        "name": "Test Harness Agent",
        "description": "Builds and runs automated tests for bot functionality",
        "capabilities": [
            "unit-testing",
            "integration-testing",
            "performance-benchmarking",
            "ci-cd-integration"
        ],
        "assigned_tasks": [],  # Owned by infrastructure
        "tool_score_weight": {"efficacy": 0.35, "safety": 0.3, "cost": 0.2, "latency": 0.15}
    },
    
    "evaluator": {
        "name": "Evaluator Agent",
        "description": "Measures bot performance, success rates, and compliance",
        "capabilities": [
            "metrics-collection",
            "performance-analysis",
            "reporting",
            "optimization-recommendations"
        ],
        "assigned_tasks": ["CTOA-010"],
        "tool_score_weight": {"efficacy": 0.3, "safety": 0.25, "cost": 0.2, "latency": 0.25}
    },
    
    "optimizer": {
        "name": "Optimizer Agent",
        "description": "Tunes bot performance, identifies bottlenecks, recommends improvements",
        "capabilities": [
            "profiling",
            "bottleneck-analysis",
            "tuning-recommendations",
            "cost-optimization"
        ],
        "assigned_tasks": ["CTOA-007"],
        "tool_score_weight": {"efficacy": 0.4, "safety": 0.15, "cost": 0.3, "latency": 0.15}
    },
    
    "debugger": {
        "name": "Debugger Agent",
        "description": "Diagnoses bot failures, traces execution, identifies root causes",
        "capabilities": [
            "error-diagnosis",
            "log-analysis",
            "trace-execution",
            "root-cause-analysis"
        ],
        "assigned_tasks": ["CTOA-009"],
        "tool_score_weight": {"efficacy": 0.45, "safety": 0.2, "cost": 0.15, "latency": 0.2}
    },
    
    "documenter": {
        "name": "Documentation Agent",
        "description": "Maintains runbooks, API docs, architecture diagrams",
        "capabilities": [
            "documentation-writing",
            "diagram-generation",
            "api-documentation",
            "runbook-creation"
        ],
        "assigned_tasks": [],  # Infrastructure-owned
        "tool_score_weight": {"efficacy": 0.3, "safety": 0.1, "cost": 0.1, "latency": 0.5}
    }
}

def get_agent_config(agent_id):
    """Get agent configuration"""
    return AGENTS.get(agent_id)

def list_agents():
    """List all agents"""
    return list(AGENTS.keys())

def get_agents_for_task(task_id):
    """Get agents assigned to a task"""
    agents = []
    for agent_id, config in AGENTS.items():
        if task_id in config.get("assigned_tasks", []):
            agents.append(agent_id)
    return agents
