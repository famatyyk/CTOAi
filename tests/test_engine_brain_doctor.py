from __future__ import annotations

from scripts.ops import engine_brain_doctor as module
from scripts.ops.engine_brain_doctor import docker_status, parse_docker_ports, render_markdown


def test_parse_docker_ports_flags_broad_binds():
    ports = "127.0.0.1:5432->5432/tcp, 0.0.0.0:8001->8000/tcp, [::]:9090->9090/tcp"

    assert parse_docker_ports(ports) == [
        "0.0.0.0:8001->8000/tcp",
        "[::]:9090->9090/tcp",
    ]


def test_docker_status_warns_when_daemon_is_unavailable_but_compose_works():
    assert docker_status(version_ok=False, compose_ok=True, ps_ok=False, has_broad_binds=False) == "warn"


def test_docker_status_fails_when_compose_is_unavailable():
    assert docker_status(version_ok=True, compose_ok=False, ps_ok=True, has_broad_binds=False) == "fail"


def test_render_markdown_summarizes_key_risks():
    report = {
        "generated_at": "2026-07-06T00:00:00+00:00",
        "overall_status": "warn",
        "checks": {
            "git": {"status": "warn", "branch": "main", "dirty_count": 2, "git_path": "git.exe"},
            "docker": {
                "status": "warn",
                "container_count": 1,
                "broad_binds": [{"container": "ctoa-api", "bind": "0.0.0.0:8001->8000/tcp"}],
                "configured_broad_binds": [],
            },
            "vpn": {"status": "ok", "warp_connected": True},
            "vercel": {"status": "ok", "version": "1.0.0", "project": {"project_name": "ctoa-web"}},
            "vscode": {"status": "warn", "active_openai_extensions": ["openai.chatgpt@x"], "openai_extension_dirs": ["a", "b"]},
            "github": {
                "status": "warn",
                "open_pr_count": 1,
                "dirty_prs": [{"number": 1, "title": "Fix", "url": "https://example.test/pr/1"}],
                "failed_recent_runs": [],
            },
            "update_gate": {"status": "ok", "product": "CTOA Toolkit", "version": "1.1.1"},
        },
    }

    text = render_markdown(report)

    assert "Docker Broad Binds" in text
    assert "currently running container binds" in text
    assert "0.0.0.0:8001" in text
    assert "GitHub Dirty PRs" in text


def test_run_cmd_resolves_executable_before_launch(monkeypatch):
    captured = {}

    class FakeProc:
        returncode = 0
        stdout = "ok\n"
        stderr = ""

    def fake_resolve(name):
        captured["resolve"] = name
        return "/trusted/tool"

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return FakeProc()

    monkeypatch.setattr(module.process_safety, "resolve_executable", fake_resolve)
    monkeypatch.setattr(module.process_safety, "run_trusted", fake_run)

    result = module.run_cmd(["tool", "arg"], timeout=7)

    assert result.ok is True
    assert result.stdout == "ok"
    assert captured["resolve"] == "tool"
    assert captured["command"] == ["/trusted/tool", "arg"]
    assert captured["kwargs"]["timeout"] == 7
