from __future__ import annotations

import copy
import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ops" / "otclient_p14_independent_runner.py"
WORKFLOW = ROOT / ".github" / "workflows" / "p14-independent-runner-contract.yml"
CONTRACT_DOC = ROOT / "docs" / "otclient" / "P14_INDEPENDENT_RUNNER_CONTRACT.md"
DOCKERFILE = ROOT / "Dockerfile"
DOCKER_BUILD_WORKFLOW = ROOT / ".github" / "workflows" / "docker-build.yml"
SPEC = importlib.util.spec_from_file_location("otclient_p14_independent_runner", SCRIPT)
assert SPEC and SPEC.loader
p14 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(p14)

REVISION = "a" * 40
KEY = b"p14-contract-test-key-material-32-bytes-minimum"
KEY_ID = "p14-contract-test"
GENERATED_AT = "2026-07-15T14:00:00Z"


def roadmap_state() -> dict[str, object]:
    basis: dict[str, object] = {
        "schema_version": "ctoa.roadmap-state.v2",
        "generated_at": "2026-07-15T13:25:55Z",
        "status": "ready",
        "readiness_status": "awaiting_external",
        "phase": "P13",
        "phase_status": "runtime_evidence_ready",
        "next_phase": "P14",
        "freshness_status": "current",
        "tamper_status": "passed",
        "blockers": [],
        "warnings": ["runtime_module_gates_pending"],
        "authority": {
            "control_center_mode": "read_only",
            "runtime_executor_added": False,
            "runtime_actions": False,
            "live_authority": False,
            "p12_heal_friend_reopened": False,
            "runtime_mcp_write_tool_enabled": False,
            "roadmap_refresh_tool_enabled": True,
            "roadmap_refresh_risk_class": "safe_write",
            "allowed_output_paths": [
                "AI/generated/ROADMAP_STATE.json",
                "AI/generated/ROADMAP_STATE.md",
                "runtime/control-center/action-audit.jsonl",
            ],
        },
        "summary": {"runtime_authority_count": 0, "live_authority_count": 0},
    }
    return {**basis, "state_sha256": p14.canonical_sha256(basis)}


@pytest.mark.parametrize(
    "warning",
    [
        "control_center_preflight_pending",
        "runtime_module_gates_pending",
        "p14_runner_preflight_pending",
        "p14_runner_preflight_invalid",
    ],
)
def test_runner_accepts_only_bounded_roadmap_advisories(warning: str) -> None:
    state = roadmap_state()
    state["warnings"] = [warning]
    state["state_sha256"] = p14.canonical_sha256(
        {key: value for key, value in state.items() if key != "state_sha256"}
    )

    p14._validate_roadmap_state(state)


def test_runner_rejects_unknown_roadmap_advisory() -> None:
    state = roadmap_state()
    state["warnings"] = ["private_unclassified_warning"]
    state["state_sha256"] = p14.canonical_sha256(
        {key: value for key, value in state.items() if key != "state_sha256"}
    )

    with pytest.raises(p14.ContractError, match="roadmap_state_readiness_invalid"):
        p14._validate_roadmap_state(state)


def configure_sources(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    helper_source = tmp_path / "scripts" / "lua" / "otclient"
    chooser_source = tmp_path / "scripts" / "lua" / "ctoa_chooser"
    helper_source.mkdir(parents=True)
    chooser_source.mkdir(parents=True)
    helper_file = helper_source / "helper.lua"
    metadata_file = helper_source / "ctoa_otclient.otmod"
    chooser_loader = chooser_source / "ctoa_chooser_loader.lua"
    chooser_metadata = chooser_source / "ctoa_chooser.otmod"
    helper_file.write_text("return { safe_boot = true }\n", encoding="utf-8")
    metadata_file.write_text(
        "Module\n  name: CTOAi\n  version: v2.4.1\n", encoding="utf-8"
    )
    chooser_loader.write_text("return true\n", encoding="utf-8")
    chooser_metadata.write_text("Module\n  name: CTOAi chooser\n", encoding="utf-8")
    roadmap_path = tmp_path / "ROADMAP_STATE.json"
    roadmap_path.write_text(json.dumps(roadmap_state()), encoding="utf-8")

    subprocess.run(
        ["git", "init", "--quiet"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "add", "scripts/lua/otclient", "scripts/lua/ctoa_chooser"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    monkeypatch.setattr(p14, "ROOT", tmp_path)
    monkeypatch.setattr(p14, "HELPER_SOURCE_PATH", helper_source)
    monkeypatch.setattr(p14, "CHOOSER_SOURCE_PATH", chooser_source)
    monkeypatch.setattr(p14, "ROADMAP_STATE_PATH", roadmap_path)


def build_request(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, object]:
    configure_sources(monkeypatch, tmp_path)
    return p14.build_request(
        revision=REVISION, generated_at=GENERATED_AT, key=KEY, key_id=KEY_ID
    )


def test_builds_schema_valid_signed_secret_safe_artifact_only_request(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    request = build_request(monkeypatch, tmp_path)

    p14.validate_schema(request, p14.REQUEST_SCHEMA_PATH)
    p14._verify_signature(request, KEY, KEY_ID)
    serialized = json.dumps(request)
    assert str(tmp_path) not in serialized
    assert request["status"] == "ready_for_independent_runner"
    assert request["replay_checks"] == p14.CHECK_IDS
    assert request["runner_contract"] == {
        "client_family": "mehah-redemption",
        "required_capabilities": [
            "module_discovery",
            "otmod_metadata",
            "g_ui_load_ui",
            "g_ui_create_widget",
        ],
        "artifact_only_handoff": True,
        "clean_checkout_required": True,
        "isolated_display_required": True,
        "operator_workstation_focus_allowed": False,
        "operator_workstation_input_allowed": False,
        "network_dispatch_allowed": False,
        "live_client_access_allowed": False,
    }
    assert request["authority"] == p14.AUTHORITY
    assert request["canary"]["promotion_approved"] is False
    assert request["rollback"]["live_rollback_allowed"] is False


def test_clean_matching_runner_emits_signed_passed_result_with_manifest_rollback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    request = build_request(monkeypatch, tmp_path)

    result = p14.verify_request(
        request,
        key=KEY,
        key_id=KEY_ID,
        runner_id="ci-independent-01",
        source_revision=REVISION,
        clean_checkout=True,
        generated_at=GENERATED_AT,
    )

    p14.validate_schema(result, p14.RESULT_SCHEMA_PATH)
    p14._verify_signature(result, KEY, KEY_ID)
    assert result["status"] == "passed"
    assert result["blockers"] == []
    assert [check["id"] for check in result["checks"]] == p14.CHECK_IDS
    assert all(check["status"] == "passed" for check in result["checks"])
    assert result["rollback"]["status"] == "manifest_replay_passed"
    assert (
        result["rollback"]["baseline_manifest_sha256"]
        == result["rollback"]["restored_manifest_sha256"]
    )
    assert (
        result["rollback"]["simulated_canary_manifest_sha256"]
        != result["rollback"]["baseline_manifest_sha256"]
    )
    assert result["rollback"]["live_rollback_tested"] is False
    assert result["canary"]["status"] == "not_executed"
    assert result["authority"] == p14.AUTHORITY
    p14.verify_result_bundle(request, result, key=KEY, key_id=KEY_ID)


def test_controller_rejects_result_rebound_to_another_request(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    request = build_request(monkeypatch, tmp_path)
    result = p14.verify_request(
        request,
        key=KEY,
        key_id=KEY_ID,
        runner_id="ci-independent-01",
        source_revision=REVISION,
        clean_checkout=True,
        generated_at=GENERATED_AT,
    )
    result["request_id"] = "p14-ffffffffffffffff"
    p14._apply_signature(result, KEY)

    with pytest.raises(p14.ContractError, match="result_request_binding_invalid"):
        p14.verify_result_bundle(request, result, key=KEY, key_id=KEY_ID)


@pytest.mark.parametrize(
    ("revision", "clean", "blocker"),
    [
        ("b" * 40, True, "runner_revision_mismatch"),
        (REVISION, False, "runner_checkout_not_clean"),
    ],
)
def test_runner_fails_closed_on_revision_or_clean_checkout_drift(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    revision: str,
    clean: bool,
    blocker: str,
) -> None:
    request = build_request(monkeypatch, tmp_path)

    result = p14.verify_request(
        request,
        key=KEY,
        key_id=KEY_ID,
        runner_id="ci-independent-01",
        source_revision=revision,
        clean_checkout=clean,
        generated_at=GENERATED_AT,
    )

    assert result["status"] == "blocked"
    assert blocker in result["blockers"]
    assert result["authority"] == p14.AUTHORITY


def test_signature_detects_payload_tamper(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    request = build_request(monkeypatch, tmp_path)
    request["canary"]["promotion_approved"] = True

    with pytest.raises(p14.ContractError, match="signature_mismatch"):
        p14._verify_signature(request, KEY, KEY_ID)


def test_embedded_artifact_hash_detects_post_signature_payload_drift(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    request = build_request(monkeypatch, tmp_path)
    request["artifacts"][1]["payload"]["files"][0]["sha256"] = "f" * 64
    p14._apply_signature(request, KEY)

    with pytest.raises(p14.ContractError, match="artifact_hash_mismatch"):
        p14.verify_request(
            request,
            key=KEY,
            key_id=KEY_ID,
            runner_id="ci-independent-01",
            source_revision=REVISION,
            clean_checkout=True,
            generated_at=GENERATED_AT,
        )


def test_source_manifest_rejects_path_escape(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configure_sources(monkeypatch, tmp_path)
    source = p14.HELPER_SOURCE_PATH / "helper.lua"
    monkeypatch.setattr(
        p14, "_package_sources", lambda: [("../operator-secret.txt", source)]
    )

    with pytest.raises(p14.ContractError, match="helper_path_invalid"):
        p14._sanitize_helper_manifest()


def test_source_manifest_excludes_local_only_legacy_runtime_references() -> None:
    package_names = {
        path.name
        for path in p14.HELPER_SOURCE_PATH.iterdir()
        if path.suffix.lower() in {".lua", ".otmod"}
        and path.name not in p14.LOCAL_SOURCE_ONLY_HELPER_FILES
    }

    assert p14.LOCAL_SOURCE_ONLY_HELPER_FILES == {
        "ctoa_native_combat.lua",
        "ctoa_native_heal.lua",
        "ctoa_native_loot.lua",
    }
    assert package_names.isdisjoint(p14.LOCAL_SOURCE_ONLY_HELPER_FILES)
    assert all(
        (p14.HELPER_SOURCE_PATH / name).is_file()
        for name in p14.LOCAL_SOURCE_ONLY_HELPER_FILES
    )


def test_source_manifest_rejects_reparse_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configure_sources(monkeypatch, tmp_path)
    target = p14.HELPER_SOURCE_PATH / "helper.lua"
    original = target.with_suffix(".real.lua")
    target.replace(original)
    try:
        target.symlink_to(original)
    except OSError:
        pytest.skip("symlink creation is unavailable on this Windows host")

    with pytest.raises(p14.ContractError, match="helper_reparse_file_rejected"):
        p14._sanitize_helper_manifest()


def test_source_manifest_rejects_untracked_package_source(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configure_sources(monkeypatch, tmp_path)
    (p14.HELPER_SOURCE_PATH / "untracked.lua").write_text(
        "return { unexpected = true }\n", encoding="utf-8"
    )

    with pytest.raises(p14.ContractError, match="helper_untracked_source_rejected"):
        p14._sanitize_helper_manifest()


def test_source_manifest_rejects_when_git_tracking_is_unavailable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "scripts" / "lua" / "otclient" / "helper.lua"
    source.parent.mkdir(parents=True)
    source.write_text("return true\n", encoding="utf-8")
    monkeypatch.setattr(p14, "ROOT", tmp_path)

    def missing_git(*_args: object, **_kwargs: object) -> object:
        raise FileNotFoundError("git unavailable")

    monkeypatch.setattr(p14.subprocess, "run", missing_git)

    with pytest.raises(p14.ContractError, match="helper_tracking_unavailable"):
        p14._require_tracked_package_sources([("helper.lua", source)])


def test_source_manifest_checks_reparse_before_regular_file_status(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configure_sources(monkeypatch, tmp_path)
    target = p14.HELPER_SOURCE_PATH / "helper.lua"
    original_is_reparse = p14._is_reparse
    monkeypatch.setattr(
        p14,
        "_is_reparse",
        lambda path: path == target or original_is_reparse(path),
    )

    with pytest.raises(p14.ContractError, match="helper_reparse_file_rejected"):
        p14._sanitize_helper_manifest()


def test_strict_json_rejects_duplicate_keys(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.json"
    path.write_text('{"schema_version":1,"schema_version":2}', encoding="utf-8")

    with pytest.raises(p14.ContractError, match="duplicate_json_key"):
        p14.load_strict_json(path)


def test_schema_files_are_valid_draft_2020_12() -> None:
    for path in [p14.REQUEST_SCHEMA_PATH, p14.RESULT_SCHEMA_PATH]:
        schema = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)


def test_tracked_source_derivation_matches_current_official_stage_manifest() -> None:
    runtime_manifest = ROOT / "runtime" / "solteria_helper_dev" / "manifest.json"
    if not runtime_manifest.exists():
        pytest.skip("local official stage manifest is not available")
    official = json.loads(runtime_manifest.read_text(encoding="utf-8-sig"))
    derived = p14._sanitize_helper_manifest()
    official_files = sorted(official["files"], key=lambda item: item["path"])

    assert derived["helper_version"] == official["helper_version"]
    assert derived["file_count"] == len(official_files)
    assert derived["file_count"] > 0
    assert derived["files"] == official_files


def test_result_schema_rejects_any_runtime_or_live_authority(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    request = build_request(monkeypatch, tmp_path)
    result = p14.verify_request(
        request,
        key=KEY,
        key_id=KEY_ID,
        runner_id="ci-independent-01",
        source_revision=REVISION,
        clean_checkout=True,
        generated_at=GENERATED_AT,
    )
    unsafe = copy.deepcopy(result)
    unsafe["authority"]["live_authority"] = True

    with pytest.raises(p14.ContractError, match="schema_invalid"):
        p14.validate_schema(unsafe, p14.RESULT_SCHEMA_PATH)


def test_cli_has_no_request_controlled_command_or_live_promotion_surface() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "shell=True" not in source
    assert "subprocess.Popen" not in source
    assert "Start-Process" not in source
    assert "solteria-client.exe" not in source
    assert "Promote" not in source
    assert '"promotion_approved": False' in source


def test_workflow_separates_pr_and_protected_github_hosted_execution() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")

    assert "runs-on: windows-latest" in source
    assert "runs-on: [self-hosted" not in source
    assert (
        "if: github.event_name == 'workflow_dispatch' && "
        "inputs.run_protected_replay == true" in source
    )
    assert "name: p14-independent-runner" in source
    assert "${{ secrets.CTOA_P14_RUNNER_SIGNING_KEY }}" in source
    assert "${{ vars.CTOA_P14_RUNNER_KEY_ID }}" in source
    assert "persist-credentials: false" in source
    assert "name: p14-protected-contract-${{ github.run_id }}" in source
    assert "pull_request_target" not in source


def test_contract_does_not_hardcode_derived_helper_file_count() -> None:
    source = CONTRACT_DOC.read_text(encoding="utf-8")

    assert "63-file" not in source
    assert "current tracked" in source


def test_p14_bundle_uses_the_chooser_as_its_only_autoload_and_hides_safe() -> None:
    chooser_metadata = (
        ROOT / "scripts" / "lua" / "ctoa_chooser" / "ctoa_chooser.otmod"
    ).read_text(encoding="utf-8")
    helper_metadata = (
        ROOT / "scripts" / "lua" / "otclient" / "ctoa_otclient.otmod"
    ).read_text(encoding="utf-8")
    chooser_loader = (
        ROOT / "scripts" / "lua" / "ctoa_chooser" / "ctoa_chooser_loader.lua"
    ).read_text(encoding="utf-8")

    assert "autoLoad: true" in chooser_metadata
    assert "autoLoadPriority: 900" in chooser_metadata
    assert "autoload:" not in chooser_metadata
    assert "autoload-priority:" not in chooser_metadata
    assert "autoLoad: false" in helper_metadata
    assert "ctoa_safe" not in chooser_loader
    assert "CTOA SAFE" not in chooser_loader


def test_p14_chooser_activates_helper_through_its_explicit_safe_loader_api() -> None:
    chooser_loader = (
        ROOT / "scripts" / "lua" / "ctoa_chooser" / "ctoa_chooser_loader.lua"
    ).read_text(encoding="utf-8")

    assert "activation = function(api)" in chooser_loader
    assert 'type(api.loadHelperOnly) ~= "function"' in chooser_loader
    assert "pcall(api.loadHelperOnly)" in chooser_loader
    assert "api.loaded ~= true" in chooser_loader
    assert "project.activation" in chooser_loader
    assert "api.init" not in chooser_loader
    assert "loadRuntimeModules" not in chooser_loader


def test_p14_chooser_allows_noninteractive_activation_only_for_the_complete_guest_capture_context() -> (
    None
):
    chooser_loader = (
        ROOT / "scripts" / "lua" / "ctoa_chooser" / "ctoa_chooser_loader.lua"
    ).read_text(encoding="utf-8")

    assert "local P14_CAPTURE_FLAGS" in chooser_loader
    assert 'CTOA_P14_CAPTURE_HELPER_ACTIVATION = "helper-ui-only"' in chooser_loader
    for flag, value in (
        ("CTOA_P14_ISOLATED_ENVIRONMENT", "true"),
        ("CTOA_P14_CAPTURE_CONTEXT", "guest"),
        ("CTOA_P14_OPERATOR_WORKSTATION_FOCUS_USED", "false"),
        ("CTOA_P14_OPERATOR_WORKSTATION_INPUT_USED", "false"),
        ("CTOA_P14_NETWORK_DISPATCH_USED", "false"),
        ("CTOA_P14_LIVE_CLIENT_ACCESSED", "false"),
        ("CTOA_P14_PROMOTION_ATTEMPTED", "false"),
    ):
        assert f'{flag} = "{value}"' in chooser_loader
    assert "p14CaptureActivationRequested" in chooser_loader
    assert "scheduleP14CaptureHelperActivation" in chooser_loader
    assert "if p14CaptureActivationRequested() then" in chooser_loader
    assert 'Loader.activate("helper")' in chooser_loader
    assert "showChooser()" in chooser_loader


def test_p14_chooser_runtime_requires_every_guest_capture_flag(tmp_path: Path) -> None:
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for P14 chooser validation"
    chooser = ROOT / "scripts" / "lua" / "ctoa_chooser" / "ctoa_chooser_loader.lua"
    probe = tmp_path / "p14_chooser_probe.lua"
    probe.write_text(
        """
local chooserPath = arg[1]
local expected = arg[2]
local realDofile = dofile
local activationCalls = 0
local chooserCalls = 0

g_game = {isOnline = function() return true end}
g_resources = {fileExists = function() return true end}
g_ui = {getRootWidget = function()
    chooserCalls = chooserCalls + 1
    return nil
end}
connect = function() end
scheduleEvent = function(callback)
    callback()
    return nil
end
dofile = function(path)
    if string.find(path, "ctoa_otclient_loader.lua", 1, true) then
        local api = {loaded = false}
        api.loadHelperOnly = function()
            activationCalls = activationCalls + 1
            api.loaded = true
            return true
        end
        _G.CTOA_OTCLIENT = api
        return api
    end
    return realDofile(path)
end

local loader = realDofile(chooserPath)
assert(loader.init() == true)
if expected == "capture" then
    assert(activationCalls == 1)
    assert(chooserCalls == 0)
    assert(loader.active_project == "helper")
else
    assert(activationCalls == 0)
    assert(chooserCalls == 1)
    assert(loader.active_project == nil)
end
""",
        encoding="utf-8",
    )
    capture_environment = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith("CTOA_P14_")
    }
    capture_environment.update(
        {
            "CTOA_P14_CAPTURE_HELPER_ACTIVATION": "helper-ui-only",
            "CTOA_P14_ISOLATED_ENVIRONMENT": "true",
            "CTOA_P14_CAPTURE_CONTEXT": "guest",
            "CTOA_P14_OPERATOR_WORKSTATION_FOCUS_USED": "false",
            "CTOA_P14_OPERATOR_WORKSTATION_INPUT_USED": "false",
            "CTOA_P14_NETWORK_DISPATCH_USED": "false",
            "CTOA_P14_LIVE_CLIENT_ACCESSED": "false",
            "CTOA_P14_PROMOTION_ATTEMPTED": "false",
        }
    )

    def run_probe(environment: dict[str, str], expected: str) -> None:
        completed = subprocess.run(
            [lua, str(probe), str(chooser), expected],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
            env=environment,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr

    run_probe(capture_environment, "capture")

    missing_flag = capture_environment.copy()
    missing_flag.pop("CTOA_P14_OPERATOR_WORKSTATION_INPUT_USED")
    run_probe(missing_flag, "chooser")

    bad_flag = capture_environment.copy()
    bad_flag["CTOA_P14_NETWORK_DISPATCH_USED"] = "true"
    run_probe(bad_flag, "chooser")


def test_docker_build_tests_use_a_git_capable_nonproduction_stage() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    workflow = DOCKER_BUILD_WORKFLOW.read_text(encoding="utf-8")

    assert "FROM runtime AS test" in dockerfile
    assert "apt-get install -y --no-install-recommends git" in dockerfile
    assert dockerfile.index("FROM runtime AS test") < dockerfile.index(
        "FROM runtime AS production"
    )
    assert dockerfile.rstrip().endswith("FROM runtime AS production")
    assert (
        "apt-get install -y --no-install-recommends git"
        not in dockerfile.split("FROM runtime AS test", maxsplit=1)[0]
    )
    assert "target: test" in workflow
