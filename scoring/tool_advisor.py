"""
Tool Advisor - Intelligent Tool Selection & Scoring
Scores tools by efficacy, safety, cost, and latency
"""

TOOL_CATALOG = {
    "github-api": {
        "name": "GitHub API",
        "description": "Create issues, post comments, update repos",
        "endpoints": ["issues", "comments", "pulls", "repos"],
        "efficacy": 0.95,  # How well it does what it claims
        "safety": 0.90,    # No risk of destructive actions
        "cost": 0.05,      # API rate limit usage (0-1 scale)
        "latency": 0.10,   # Response time (0-1 scale, lower is better)
        "cost_per_call": 0.0001,
        "rate_limit": 5000,
        "timeout_sec": 10,
        "fallback": "github-graphql",
        "requires_auth": True,
        "auth_type": "PAT"
    },
    
    "ssh-command": {
        "name": "SSH Remote Execution",
        "description": "Run commands on VPS via SSH",
        "commands": ["bash", "python", "systemctl", "sysstat"],
        "efficacy": 0.88,
        "safety": 0.70,    # Higher risk (remote execution)
        "cost": 0.0,
        "latency": 0.30,   # Network latency
        "timeout_sec": 30,
        "fallback": "ssh-batch-mode",
        "requires_auth": True,
        "auth_type": "ed25519-key"
    },
    
    "prometheus": {
        "name": "Prometheus Metrics",
        "description": "Query system metrics from VPS monitoring",
        "queries": ["cpu_usage", "memory_usage", "disk_usage"],
        "efficacy": 0.92,
        "safety": 0.98,    # Read-only
        "cost": 0.01,
        "latency": 0.05,
        "timeout_sec": 5,
        "fallback": None,
        "requires_auth": False
    },
    
    "slack-webhook": {
        "name": "Slack Notifications",
        "description": "Send alerts to Slack channel",
        "actions": ["post-message", "thread-reply", "emoji-reaction"],
        "efficacy": 0.85,
        "safety": 0.95,
        "cost": 0.001,
        "latency": 0.20,
        "timeout_sec": 10,
        "fallback": "email",
        "requires_auth": True,
        "auth_type": "webhook-url"
    },
    
    "log-parser": {
        "name": "Local Log Parser",
        "description": "Parse and analyze local log files",
        "formats": ["json", "plaintext", "syslog"],
        "efficacy": 0.90,
        "safety": 0.99,
        "cost": 0.0,
        "latency": 0.02,
        "timeout_sec": 5,
        "fallback": None,
        "requires_auth": False
    }
}

def score_tool(tool_id, agent_weights=None):
    """
    Score a tool based on efficacy, safety, cost, latency.
    
    Default weights: efficacy=0.4, safety=0.3, cost=0.2, latency=0.1
    Agent can provide custom weights.
    """
    if agent_weights is None:
        agent_weights = {"efficacy": 0.4, "safety": 0.3, "cost": 0.2, "latency": 0.1}
    
    tool = TOOL_CATALOG.get(tool_id)
    if not tool:
        return None
    
    weighted_score = (
        tool["efficacy"] * agent_weights.get("efficacy", 0.4) +
        tool["safety"] * agent_weights.get("safety", 0.3) +
        (1 - tool["cost"]) * agent_weights.get("cost", 0.2) +
        (1 - tool["latency"]) * agent_weights.get("latency", 0.1)
    )
    
    return {
        "tool_id": tool_id,
        "name": tool["name"],
        "score": round(weighted_score, 3),
        "efficacy": tool["efficacy"],
        "safety": tool["safety"],
        "cost": tool["cost"],
        "latency": tool["latency"],
        "available": True,
        "fallback": tool.get("fallback")
    }

def rank_tools_for_task(task_type, agent_weights=None):
    """
    Rank all tools for a given task type, by score.
    Returns sorted list (highest score first).
    """
    scores = []
    for tool_id in TOOL_CATALOG.keys():
        score = score_tool(tool_id, agent_weights)
        scores.append(score)
    
    # Sort by score (descending)
    return sorted(scores, key=lambda x: x["score"], reverse=True)

def get_tool_config(tool_id):
    """Get tool configuration"""
    return TOOL_CATALOG.get(tool_id)

def list_available_tools():
    """List all tools"""
    return list(TOOL_CATALOG.keys())
