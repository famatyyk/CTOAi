"""
Agent Framework Tests
Tests for agent definitions, BRAVE(R) templates, and tool advisor
"""

import unittest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "agents"))
sys.path.insert(0, str(Path(__file__).parent.parent / "prompts"))
sys.path.insert(0, str(Path(__file__).parent.parent / "scoring"))


class TestAgentDefinitions(unittest.TestCase):
    """Test agent framework definitions"""
    
    def test_agent_count(self):
        """Verify 10 agents are defined"""
        from definitions import list_agents
        agents = list_agents()
        self.assertEqual(len(agents), 10, f"Expected 10 agents, got {len(agents)}")
    
    def test_agent_properties(self):
        """Verify each agent has required properties"""
        from definitions import AGENTS
        required_props = ["name", "description", "capabilities", "assigned_tasks", "tool_score_weight"]
        
        for agent_id, config in AGENTS.items():
            for prop in required_props:
                self.assertIn(prop, config, f"Agent {agent_id} missing {prop}")
    
    def test_task_assignments(self):
        """Verify CTOA-001..010 are assigned to agents"""
        from definitions import get_agents_for_task
        
        for task_id in [f"CTOA-{i:03d}" for i in range(1, 11)]:
            agents = get_agents_for_task(task_id)
            self.assertGreater(len(agents), 0, f"{task_id} has no assigned agents")
    
    def test_tool_weights_sum(self):
        """Verify tool score weights sum to ~1.0"""
        from definitions import AGENTS
        
        for agent_id, config in AGENTS.items():
            weights = config.get("tool_score_weight", {})
            total = sum(weights.values())
            self.assertAlmostEqual(total, 1.0, places=1, 
                msg=f"Agent {agent_id} weights don't sum to 1.0: {total}")


class TestBraverTemplates(unittest.TestCase):
    """Test BRAVE(R) prompt templates"""
    
    def test_template_components(self):
        """Verify all BRAVE(R) components present"""
        from braver_templates import get_all_components
        components = get_all_components()
        self.assertEqual(len(components), 6)  # Business, Reasoning, Action, Value, Evidence, Reflection
        self.assertIn("business", components)
        self.assertIn("reflection", components)
    
    def test_template_types(self):
        """Verify template types exist"""
        from braver_templates import BRAVER_TEMPLATES
        self.assertIn("task-execution", BRAVER_TEMPLATES)
        self.assertIn("decision-making", BRAVER_TEMPLATES)
    
    def test_template_rendering(self):
        """Verify template variables can be substituted"""
        from braver_templates import render_template
        
        result = render_template(
            "task-execution",
            "business",
            task_id="CTOA-001",
            task_title="Test Task",
            priority="P0",
            agents=["agent1", "agent2"],
            deadline="2026-03-25",
            success_criteria="All tests pass"
        )
        
        self.assertIn("CTOA-001", result)
        self.assertIn("Test Task", result)
        self.assertNotIn("{", result)  # No unsubstituted variables


class TestToolAdvisor(unittest.TestCase):
    """Test tool advisor scoring system"""
    
    def test_tool_count(self):
        """Verify tools are defined"""
        from tool_advisor import list_available_tools
        tools = list_available_tools()
        self.assertGreater(len(tools), 0)
    
    def test_tool_properties(self):
        """Verify each tool has required properties"""
        from tool_advisor import TOOL_CATALOG
        required_props = ["name", "description", "efficacy", "safety", "cost", "latency"]
        
        for tool_id, config in TOOL_CATALOG.items():
            for prop in required_props:
                self.assertIn(prop, config, f"Tool {tool_id} missing {prop}")
            
            # Verify scores are 0-1
            self.assertGreaterEqual(config["efficacy"], 0)
            self.assertLessEqual(config["efficacy"], 1)
            self.assertGreaterEqual(config["safety"], 0)
            self.assertLessEqual(config["safety"], 1)
    
    def test_tool_scoring(self):
        """Verify tool scoring works"""
        from tool_advisor import score_tool
        
        score = score_tool("github-api", {"efficacy": 0.4, "safety": 0.3, "cost": 0.2, "latency": 0.1})
        self.assertIsNotNone(score)
        self.assertIn("score", score)
        self.assertGreater(score["score"], 0)
        self.assertLess(score["score"], 1)
    
    def test_tool_ranking(self):
        """Verify tools can be ranked"""
        from tool_advisor import rank_tools_for_task
        
        ranked = rank_tools_for_task("test-task")
        self.assertGreater(len(ranked), 0)
        
        # Verify sorted by score (descending)
        scores = [t["score"] for t in ranked]
        self.assertEqual(scores, sorted(scores, reverse=True))


if __name__ == "__main__":
    unittest.main(verbosity=2)
