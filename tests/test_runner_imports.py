import subprocess
import sys


def test_runner_help_works_as_script_and_module(project_root):
    commands = [
        [sys.executable, "runner/runner.py", "--help"],
        [sys.executable, "-m", "runner.runner", "--help"],
    ]

    for command in commands:
        result = subprocess.run(
            command,
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, result.stderr
        assert "CTOA VPS runner" in result.stdout


def test_agents_executor_imports_when_runner_dir_is_on_sys_path(project_root):
    runner_dir = project_root / "runner"
    script = (
        "import sys; "
        f"sys.path.insert(0, {str(runner_dir)!r}); "
        "from agents.executor import execute_agent_for_task; "
        "print(execute_agent_for_task.__name__)"
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "execute_agent_for_task"
