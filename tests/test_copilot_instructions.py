from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent


class TestCopilotInstructions(unittest.TestCase):
    def _content(self) -> str:
        return (ROOT / ".github" / "copilot-instructions.md").read_text(encoding="utf-8")

    # ── Agent Response Rules ────────────────────────────────────────────────
    def test_azure_activity_log_guidance_is_present(self):
        content = self._content()

        self.assertIn("Azure Activity Log", content)
        self.assertIn("operationName", content)
        self.assertIn("correlationId", content)
        self.assertIn("role assignments", content)
        self.assertIn("raw Azure Activity Log entry", content)

    # ── Required sections ───────────────────────────────────────────────────
    def test_all_required_sections_present(self):
        """Every top-level section defined in the scope priority list must appear."""
        content = self._content()
        sections = [
            "## Architecture Defaults",
            "## Canonical Commands",
            "## Coding Conventions",
            "## CI And Core Integrity",
            "## Operational Pitfalls",
            "## Link, Do Not Embed",
            "## Agent Response Rules",
        ]
        for section in sections:
            self.assertIn(section, content, f"Required section '{section}' is missing from copilot-instructions.md")

    # ── Architecture Defaults ───────────────────────────────────────────────
    def test_architecture_layer_directories_exist(self):
        """The four architectural layers referenced in instructions must be present."""
        layers = ["agents", "prompts", "scoring", "runner", "policies", "workflows"]
        for layer in layers:
            self.assertTrue(
                (ROOT / layer).is_dir(),
                f"Architecture layer directory '{layer}/' referenced in copilot-instructions.md is missing",
            )

    def test_agent_prompt_definitive_doc_exists(self):
        """The BRAVE(R) canonical doc referenced in Architecture Defaults must exist."""
        self.assertTrue(
            (ROOT / "docs" / "AGENT_PROMPT_DEFINITIVE.md").exists(),
            "docs/AGENT_PROMPT_DEFINITIVE.md referenced in Architecture Defaults is missing",
        )

    # ── Canonical Commands ──────────────────────────────────────────────────
    def test_canonical_tasks_in_vscode(self):
        """All canonical task labels listed in the instructions must be in .vscode/tasks.json."""
        tasks_path = ROOT / ".vscode" / "tasks.json"
        self.assertTrue(tasks_path.exists(), ".vscode/tasks.json is missing")
        tasks_content = tasks_path.read_text(encoding="utf-8")
        canonical_tasks = [
            "CTOA: Bootstrap Product Config",
            "CTOA: Check Update Gate",
            "CTOA: Run All Tests",
            "CTOA: Launch Pack",
        ]
        for task in canonical_tasks:
            self.assertIn(
                task,
                tasks_content,
                f"Canonical task '{task}' not found in .vscode/tasks.json",
            )

    # ── CI And Core Integrity / Operational Pitfalls ────────────────────────
    def test_core_ops_scripts_exist(self):
        """Operational scripts referenced in the instructions must exist."""
        scripts = [
            "scripts/ops/core_guard.py",
            "scripts/ops/ctoa-vps.ps1",
        ]
        for script in scripts:
            self.assertTrue(
                (ROOT / script).exists(),
                f"Referenced script '{script}' does not exist",
            )

    # ── Link, Do Not Embed ──────────────────────────────────────────────────
    def test_linked_docs_exist(self):
        """Every doc linked in the 'Link, Do Not Embed' section must exist in the repo."""
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
                f"Referenced doc '{doc}' listed in 'Link, Do Not Embed' does not exist",
            )


if __name__ == "__main__":
    unittest.main()
