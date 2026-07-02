import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agents"))
sys.path.insert(0, str(ROOT / "prompts"))


def test_api_cost_optimizer_registered():
    from definitions import get_agent_config, list_agents

    assert "api-cost-optimizer" in list_agents()
    config = get_agent_config("api-cost-optimizer")
    assert config is not None
    assert config["name"] == "APICostOptimizerAgent"
    assert "analyze_token_velocity" in config["capabilities"]
    assert "calculate_burn_rate" in config["capabilities"]
    assert "propose_model_fallback" in config["capabilities"]
    assert abs(sum(config["tool_score_weight"].values()) - 1.0) < 0.01


def test_api_cost_optimizer_facade_risk_scores():
    from definitions import APICostOptimizerAgent

    agent = APICostOptimizerAgent()
    assert agent.score_action_risk("billing_metrics_provider", {}) == 0.05
    assert agent.score_action_risk("token_counter_service", {}) == 0.05
    assert agent.score_action_risk("local_file_patcher", {}) == 0.28
    assert agent.score_action_risk("unknown_tool", {}) == agent.risk_threshold
    assert agent.registry_config()["name"] == "APICostOptimizerAgent"


def test_api_cost_optimizer_braver_template_registered():
    from braver_templates import API_COST_OPTIMIZER_BRAVER_TEMPLATE, BRAVER_TEMPLATES, get_template

    assert "APICostOptimizerAgent" in API_COST_OPTIMIZER_BRAVER_TEMPLATE
    assert '"anomalous_component"' in API_COST_OPTIMIZER_BRAVER_TEMPLATE
    assert "api-cost-optimizer" in BRAVER_TEMPLATES
    assert get_template("api-cost-optimizer")["evidence"]
