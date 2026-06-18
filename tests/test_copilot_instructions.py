from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent


class TestCopilotInstructions(unittest.TestCase):
    def test_analyze_prompt_guidance_is_present(self):
        content = (ROOT / ".github" / "copilot-instructions.md").read_text(encoding="utf-8")

        self.assertIn("/analyze-prompt", content)
        self.assertIn("objective", content)
        self.assertIn("constraints", content)
        self.assertIn("ambiguities", content)
        self.assertIn("failure modes", content)
        self.assertIn("tightened prompt rewrite", content)

    def test_azure_activity_log_guidance_is_present(self):
        content = (ROOT / ".github" / "copilot-instructions.md").read_text(encoding="utf-8")

        self.assertIn("Azure Activity Log", content)
        self.assertIn("operationName", content)
        self.assertIn("correlationId", content)
        self.assertIn("role assignments", content)
        self.assertIn("raw Azure Activity Log entry", content)


if __name__ == "__main__":
    unittest.main()
