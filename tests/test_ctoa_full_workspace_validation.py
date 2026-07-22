from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "ops" / "ctoa_full_workspace_validation.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "ctoa_full_workspace_validation", SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def success_result(module, spec):
    if spec.kind == "brain_refresh":
        return module.ExecutionResult(
            0,
            json.dumps(
                {"doc_sync_status": "passed", "secret_guardrail_status": "passed"}
            ),
        )
    if spec.kind == "brain_doctor":
        return module.ExecutionResult(0, json.dumps({"overall_status": "warn"}))
    if spec.kind == "brain_pack_all":
        return module.ExecutionResult(
            0, json.dumps({"profile": "all", "included_count": 1})
        )
    if spec.kind == "p6_plugin_self_check":
        return module.ExecutionResult(0, json.dumps({"status": "ready"}))
    if spec.kind in {"p7_operator_brief", "p7_generated_brief"}:
        return module.ExecutionResult(
            0, json.dumps({"status": "ready", "hard_blockers": []})
        )
    if spec.kind == "p6_plugin_mcp":
        responses = [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"serverInfo": {"name": "ctoai-engine-brain"}},
            },
            {
                "jsonrpc": "2.0",
                "id": 2,
                "result": {
                    "tools": [
                        {"name": name} for name in sorted(module.MCP_REQUIRED_TOOLS)
                    ]
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 3,
                "result": {
                    "content": [
                        {"type": "text", "text": json.dumps({"status": "ready"})}
                    ],
                    "isError": False,
                },
            },
        ]
        return module.ExecutionResult(
            0, "\n".join(json.dumps(item) for item in responses)
        )
    return module.ExecutionResult(0, "completed")


def test_dry_run_never_executes_or_writes(monkeypatch, tmp_path: Path):
    module = load_module()
    calls = []

    def unexpected(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("dry-run must not execute or write")

    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "run_confirmed_validation", unexpected)
    monkeypatch.setattr(module, "write_evidence", unexpected)
    assert module.main(["--dry-run", "true", "--reason", "unit dry-run"]) == 0

    payload = module.build_dry_run_payload()

    assert payload["status"] == "dry_run"
    assert payload["summary"]["skipped"] == len(module.VALIDATION_REGISTRY)
    assert calls == []
    assert not (tmp_path / module.OUTPUT_RELATIVE_PATH).exists()
    assert {item["id"] for item in payload["commands"]} == {
        spec.identifier for spec in module.VALIDATION_REGISTRY
    }
    assert '"command":' not in json.dumps(payload)


def test_confirmed_run_writes_bounded_fixed_registry_evidence(tmp_path: Path):
    module = load_module()
    calls = []

    def executor(spec, root):
        calls.append((spec.identifier, root))
        return success_result(module, spec)

    payload = module.run_confirmed_validation(tmp_path, executor=executor)
    output = module.write_evidence(tmp_path, payload)
    stored = json.loads(output.read_text(encoding="utf-8"))

    assert calls == [(spec.identifier, tmp_path) for spec in module.VALIDATION_REGISTRY]
    assert output == tmp_path / module.OUTPUT_RELATIVE_PATH
    assert stored["schema_version"] == 2
    assert stored["status"] == "passed"
    assert stored["summary"] == {
        "command_count": len(module.VALIDATION_REGISTRY),
        "passed": len(module.VALIDATION_REGISTRY) - 1,
        "warn": 1,
        "failed": 0,
        "skipped": 0,
        "propagation": "passed",
    }
    assert [item["id"] for item in stored["commands"]] == [
        spec.identifier for spec in module.VALIDATION_REGISTRY
    ]
    assert all(
        set(item) == {"id", "status", "summary", "duration"}
        for item in stored["commands"]
    )
    assert len(output.read_bytes()) <= module.MAX_EVIDENCE_BYTES
    assert '"command":' not in json.dumps(stored)


def test_failed_entry_is_recorded_without_sensitive_output(tmp_path: Path):
    module = load_module()
    secret = "token=do-not-project-this-value"

    def executor(spec, root):
        if spec.identifier == "web_tests":
            return module.ExecutionResult(1, "", secret)
        return success_result(module, spec)

    payload = module.run_confirmed_validation(tmp_path, executor=executor)
    module.write_evidence(tmp_path, payload)
    serialized = json.dumps(payload)
    web_tests = next(item for item in payload["commands"] if item["id"] == "web_tests")

    assert payload["status"] == "failed"
    assert payload["summary"]["failed"] == 1
    assert web_tests["status"] == "failed"
    assert web_tests["summary"] == "nonzero_exit"
    assert secret not in serialized
    assert "stderr" not in serialized
    assert "stdout" not in serialized


def test_confirmed_run_requires_exact_confirmation(monkeypatch, tmp_path: Path):
    module = load_module()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    output = tmp_path / module.OUTPUT_RELATIVE_PATH

    with pytest.raises(SystemExit) as exc_info:
        module.main(
            [
                "--dry-run",
                "false",
                "--confirmation",
                "almost refresh full workspace validation",
                "--reason",
                "unit test",
            ]
        )

    assert exc_info.value.code == 2
    assert not output.exists()


def test_cli_rejects_command_and_path_overrides():
    module = load_module()

    with pytest.raises(SystemExit) as exc_info:
        module.main(
            [
                "--dry-run",
                "true",
                "--reason",
                "unit test",
                "--command",
                "untrusted",
            ]
        )

    assert exc_info.value.code == 2


@pytest.mark.parametrize("tools", [None, {}, "not-a-list"])
def test_mcp_handshake_rejects_non_list_tools_with_stable_error(tools):
    module = load_module()
    responses = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"serverInfo": {"name": "ctoai-engine-brain"}},
        },
        {"jsonrpc": "2.0", "id": 2, "result": {"tools": tools}},
        {
            "jsonrpc": "2.0",
            "id": 3,
            "result": {"content": [{"type": "text", "text": '{"status":"ready"}'}]},
        },
    ]

    ok, summary = module._mcp_handshake_ok(
        "\n".join(json.dumps(response) for response in responses)
    )

    assert ok is False
    assert summary == "invalid_mcp_tools_response"


@pytest.mark.parametrize(
    "missing_tool",
    [
        "ctoai_control_central",
        "ctoai_full_workspace_validation_refresh",
    ],
)
def test_mcp_handshake_requires_every_declared_read_only_and_safe_write_tool(
    missing_tool,
):
    module = load_module()
    responses = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"serverInfo": {"name": "ctoai-engine-brain"}},
        },
        {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "tools": [
                    {"name": name}
                    for name in sorted(module.MCP_REQUIRED_TOOLS - {missing_tool})
                ]
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 3,
            "result": {"content": [{"type": "text", "text": '{"status":"ready"}'}]},
        },
    ]

    ok, summary = module._mcp_handshake_ok(
        "\n".join(json.dumps(response) for response in responses)
    )

    assert ok is False
    assert summary == "mcp_required_tools_missing"


def test_mcp_handshake_rejects_forbidden_write_tool_even_when_required_tools_exist():
    module = load_module()
    responses = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"serverInfo": {"name": "ctoai-engine-brain"}},
        },
        {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "tools": [
                    {"name": name}
                    for name in sorted(
                        module.MCP_REQUIRED_TOOLS | {"ctoai_live_deploy"}
                    )
                ]
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 3,
            "result": {"content": [{"type": "text", "text": '{"status":"ready"}'}]},
        },
    ]

    ok, summary = module._mcp_handshake_ok(
        "\n".join(json.dumps(response) for response in responses)
    )

    assert ok is False
    assert summary == "mcp_forbidden_tools_present"


@pytest.mark.parametrize(
    "payload",
    [
        {"status": "ready"},
        {"status": "ready", "hard_blockers": None},
        {"status": "ready", "hard_blockers": {"blocked": False}},
        {"status": "ready", "hard_blockers": "none"},
        {"status": "ready", "hard_blockers": ["not_ready"]},
    ],
)
@pytest.mark.parametrize("kind", ["p7_operator_brief", "p7_generated_brief"])
def test_p7_briefs_require_an_explicit_empty_hard_blockers_list(payload, kind):
    module = load_module()
    spec = next(item for item in module.VALIDATION_REGISTRY if item.kind == kind)

    status, summary = module._classify_execution(
        spec,
        module.ExecutionResult(0, json.dumps(payload)),
    )

    assert status == "failed"
    assert summary in {"operator_brief_not_ready", "generated_operator_brief_not_ready"}
