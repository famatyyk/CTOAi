from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent


class TestCopilotInstructions(unittest.TestCase):
    def test_azure_activity_log_guidance_is_present(self):
        content = (ROOT / ".github" / "copilot-instructions.md").read_text(encoding="utf-8")

        self.assertIn("Azure Activity Log", content)
        self.assertIn("operationName", content)
        self.assertIn("correlationId", content)
        self.assertIn("role assignments", content)
        self.assertIn("raw Azure Activity Log entry", content)


if __name__ == "__main__":
    unittest.main()
