from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent


class TestCopilotInstructions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = (ROOT / ".github" / "copilot-instructions.md").read_text(encoding="utf-8")

    def test_azure_activity_log_guidance_is_present(self):
        self.assertIn("Azure Activity Log", self.content)
        self.assertIn("operationName", self.content)
        self.assertIn("correlationId", self.content)
        self.assertIn("role assignments", self.content)
        self.assertIn("raw Azure Activity Log entry", self.content)

    def test_brave_r_components_are_canonical(self):
        """BRAVE(R) description must reference the canonical component names."""
        for component in ("Background", "Role", "Action", "Values", "Examples", "Result"):
            self.assertIn(
                component,
                self.content,
                f"BRAVE(R) component '{component}' missing from copilot-instructions.md",
            )
        self.assertIn("AGENT_PROMPT_DEFINITIVE.md", self.content)

    def test_architecture_defaults_section_is_present(self):
        """Architecture Defaults section must describe the four coordinated layers."""
        self.assertIn("Architecture Defaults", self.content)
        for layer in ("agents/", "prompts/", "runner/", "policies/"):
            self.assertIn(layer, self.content, f"Layer path '{layer}' not listed in Architecture Defaults")

    def test_ci_and_core_integrity_section_references_guard(self):
        """CI And Core Integrity section must reference core_guard.py."""
        self.assertIn("CI And Core Integrity", self.content)
        self.assertIn("core_guard.py", self.content)

    def test_canonical_commands_section_references_tasks_json(self):
        """Canonical Commands section must reference the VS Code tasks file."""
        self.assertIn("Canonical Commands", self.content)
        self.assertIn("tasks.json", self.content)

    def test_coding_conventions_references_status_flow(self):
        """Coding Conventions must reference the status/gate state machine."""
        self.assertIn("Coding Conventions", self.content)
        self.assertIn("IN_PROGRESS", self.content)
        self.assertIn("RELEASED", self.content)

    def test_link_do_not_embed_lists_canonical_docs(self):
        """Link, Do Not Embed section must reference key canonical doc files."""
        self.assertIn("Link, Do Not Embed", self.content)
        for doc in (
            "README.md",
            "docs/ARCHITECTURE.md",
            "docs/SPRINT_GOVERNANCE.md",
            "docs/CORE_GUARDRAILS.md",
            "docs/REPO_HYGIENE_POLICY.md",
        ):
            self.assertIn(doc, self.content, f"Canonical doc '{doc}' missing from Link, Do Not Embed section")

    def test_linked_canonical_docs_exist_on_disk(self):
        """Every canonical doc listed in Link, Do Not Embed must exist in the repository."""
        docs = [
            "README.md",
            "docs/ARCHITECTURE.md",
            "docs/LOCAL_SETUP.md",
            "docs/DEPLOYMENT.md",
            "docs/SPRINT_GOVERNANCE.md",
            "docs/CORE_GUARDRAILS.md",
            "docs/REPO_HYGIENE_POLICY.md",
            "docs/MOBILE_CONSOLE.md",
        ]
        for doc in docs:
            self.assertTrue(
                (ROOT / doc).exists(),
                f"Canonical doc '{doc}' listed in copilot-instructions.md does not exist on disk",
            )


if __name__ == "__main__":
    unittest.main()
