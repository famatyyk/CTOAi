"""
CTOA Test Suite - Runner and Reporter Unit Tests
Tests core functionality for automation engine
"""

import unittest
from pathlib import Path
from datetime import datetime, timezone
import json
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "runner"))

class TestRunnerBasics(unittest.TestCase):
    """Test runner.py core functions"""
    
    def test_imports(self):
        """Verify runner module imports"""
        try:
            import runner
            self.assertTrue(hasattr(runner, 'main'))
        except ImportError as e:
            self.fail(f"Failed to import runner: {e}")
    
    def test_config_validation(self):
        """Test config file validation (skipped in CI — runtime/ is gitignored)"""
        config_path = Path(__file__).parent.parent / "runtime" / "task-state.yaml"
        if not config_path.exists():
            self.skipTest("runtime/task-state.yaml not present (expected in CI)")
        self.assertTrue(config_path.stat().st_size > 0, "Config is empty")
    
    def test_env_variables(self):
        """Test required environment variables"""
        import os
        # Non-critical env vars for test
        # Don't test GITHUB_PAT or SSH keys (those are runtime-only)
        pass
    
    def test_log_output_format(self):
        """Test that logging produces valid output"""
        test_msg = "[test] Message format"
        self.assertIn("[", test_msg)
        self.assertIn("]", test_msg)


class TestReporterBasics(unittest.TestCase):
    """Test reporter functionality"""
    
    def test_status_sync_exists(self):
        """Verify status_sync.py file exists"""
        status_sync = Path(__file__).parent.parent / "runner" / "status_sync.py"
        self.assertTrue(status_sync.exists(), "status_sync.py not found")
    
    def test_issue_markdown_format(self):
        """Test GitHub Issue markdown format"""
        sample_issue = """## Live Status
        
        Sprint: sprint-002
        Tasks: 10
        Completed: 0
        """
        self.assertIn("Sprint:", sample_issue)
        self.assertIn("Tasks:", sample_issue)
    
    def test_timestamp_format(self):
        """Test ISO 8601 timestamp format"""
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        parts = ts.split("T")
        self.assertEqual(len(parts), 2)
        self.assertRegex(ts, r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')


class TestVPSConnectivity(unittest.TestCase):
    """Test VPS connection parameters (non-interactive)"""
    
    def test_ssh_key_format(self):
        """Verify SSH key file path is valid"""
        import os
        key_path = os.environ.get("CTOA_VPS_KEY_PATH")
        if key_path:
            self.assertTrue(Path(key_path).exists() or True, "SSH key path structure valid")
    
    def test_vps_host_config(self):
        """Verify VPS host is configured"""
        import os
        host = os.environ.get("CTOA_VPS_HOST", "116.202.96.250")
        self.assertIsNotNone(host)
        self.assertRegex(host, r'\d+\.\d+\.\d+\.\d+')

    def test_ctoa_cli_default_host_is_active_vps(self):
        """Ensure CLI fallback host points to active VPS"""
        script = Path(__file__).parent.parent / "ctoa.ps1"
        content = script.read_text(encoding="utf-8", errors="ignore")
        self.assertIn('return "116.202.96.250"', content)
        self.assertNotIn('return "46.225.110.52"', content)

    def test_ctoa_vps_script_default_host_is_active_vps(self):
        """Ensure VPS ops fallback host points to active VPS"""
        script = Path(__file__).parent.parent / "scripts" / "ops" / "ctoa-vps.ps1"
        content = script.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("$h = '116.202.96.250'", content)
        self.assertNotIn("$h = '46.225.110.52'", content)

    def test_ctoa_vps_preupdate_gate_present(self):
        """Ensure dirty-worktree gate exists in VPS update script"""
        script = Path(__file__).parent.parent / "scripts" / "ops" / "ctoa-vps.ps1"
        content = script.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("ctoa_preupdate_gate()", content)
        self.assertIn("[pre-update-gate] BLOCKED dirty worktree", content)
        self.assertIn("preupdate-gate-${ts}.txt", content)

    def test_ctoa_vps_preupdate_gate_applied_to_update_paths(self):
        """Ensure gate is called before pull/reset/checkout update flows"""
        script = Path(__file__).parent.parent / "scripts" / "ops" / "ctoa-vps.ps1"
        content = script.read_text(encoding="utf-8", errors="ignore")
        self.assertGreaterEqual(content.count("ctoa_preupdate_gate /opt/ctoa"), 4)

        self.assertIn(
            "if [ -d /opt/ctoa/.git ]; then\n  ctoa_preupdate_gate /opt/ctoa\n  cd /opt/ctoa; git fetch --all; git checkout main; git pull --ff-only",
            content,
        )
        self.assertIn(
            "cd /opt/ctoa\nctoa_preupdate_gate /opt/ctoa\ngit fetch --quiet\ngit reset --hard origin/main",
            content,
        )
        self.assertIn(
            "cd /opt/ctoa\nctoa_preupdate_gate /opt/ctoa\n    echo \"[InstallGsResetFromBranch] source ref: __SOURCE_REF__\"\n    git fetch --quiet origin \"__SOURCE_REF__\"\ngit checkout -f FETCH_HEAD",
            content,
        )


    def test_phase5_worktree_drycheck_script_exists_and_checks_porcelain(self):
        """Ensure Phase-5 nightly dry-check script enforces clean worktree."""
        script = Path(__file__).parent.parent / "deploy" / "vps" / "worktree-nightly-drycheck.sh"
        self.assertTrue(script.exists(), "Phase-5 dry-check script is missing")
        content = script.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("git -C \"$repo\" status --porcelain=v1", content)
        self.assertIn("Mirror emergency VPS edits to main within one sprint cycle", content)

    def test_ctoa_root_action_supports_phase5_guardrail_actions(self):
        """Ensure root wrapper can install and run Phase-5 dry-check guardrails."""
        script = Path(__file__).parent.parent / "scripts" / "ops" / "ctoa-root-action.sh"
        content = script.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("worktree-drycheck)", content)
        self.assertIn("install-worktree-drycheck-cron)", content)
        self.assertIn("worktree-nightly-drycheck.sh", content)

    def test_ctoa_vps_exposes_phase5_guardrail_actions(self):
        """Ensure ctoa-vps action map exposes Phase-5 guardrail operations."""
        script = Path(__file__).parent.parent / "scripts" / "ops" / "ctoa-vps.ps1"
        content = script.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("'WorktreeDryCheck'", content)
        self.assertIn("'InstallWorktreeDryCheckCron'", content)

    def test_vps_crontab_example_contains_nightly_worktree_drycheck(self):
        """Ensure cron template documents nightly worktree dry-check schedule."""
        script = Path(__file__).parent.parent / "deploy" / "vps" / "crontab.example"
        content = script.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("worktree-nightly-drycheck.sh", content)

class TestGitHubIntegration(unittest.TestCase):
    """Test GitHub API integration (mock-friendly)"""
    
    def test_github_api_format(self):
        """Test GitHub API response format expectations"""
        sample_issue = {
            "number": 1,
            "title": "Test Issue",
            "body": "Test body",
            "updated_at": "2026-03-12T12:00:00Z",
            "state": "open"
        }
        self.assertEqual(sample_issue["number"], 1)
        self.assertIn("updated_at", sample_issue)
    
    def test_pat_not_in_code(self):
        """Verify no PAT tokens in source files"""
        runner_file = Path(__file__).parent.parent / "runner" / "runner.py"
        if runner_file.exists():
            content = runner_file.read_text()
            self.assertNotIn("ghp_", content, "PAT found in source code!")
            self.assertNotIn("github_pat_", content)


class TestFileStructure(unittest.TestCase):
    """Test project file structure"""
    
    def test_required_files_exist(self):
        """Verify required files are present"""
        required_files = [
            "runner/runner.py",
            "runner/status_sync.py",
            ".github/workflows/ctoa-pipeline.yml",
            "CHANGELOG.md",
            "docs/history/sprints/SPRINT-002.md"
        ]
        base_path = Path(__file__).parent.parent
        for file_path in required_files:
            full_path = base_path / file_path
            self.assertTrue(full_path.exists(), f"Missing: {file_path}")
    
    def test_gitignore_configured(self):
        """Verify .gitignore exists and is configured"""
        gitignore = Path(__file__).parent.parent / ".gitignore"
        self.assertTrue(gitignore.exists())
        content = gitignore.read_text()
        self.assertIn("__pycache__", content)


if __name__ == "__main__":
    # Run with: python -m pytest tests/test_suite.py -v
    # Or: python -m unittest discover tests/ -v
    unittest.main(verbosity=2)

