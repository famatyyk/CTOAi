from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from scripts.ops import otclient_headless_evidence as evidence
from scripts.ops import otclient_headless_status as status


ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "scripts" / "windows" / "solteria_helper_test_env.ps1"
CLI = ROOT / "ctoa.ps1"
REPORTER = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_client_reporter.lua"
SANDBOX_SMOKE = (
    ROOT / "scripts" / "ops" / "otclient_runtime_module_gates_sandbox_smoke.py"
)
NOW = datetime(2026, 7, 11, 16, 0, tzinfo=timezone.utc)
NOW_MS = int(NOW.timestamp() * 1_000)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _resign_promotion(dev: Path, client: Path) -> None:
    manifest_path = dev / "live_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _write_json(
        dev / "live_promotion.json",
        {
            "name": "solteria-helper-live-promotion",
            "created_at": manifest.get("generated_at_utc"),
            "approval_switch": "ApproveLiveDeploy",
            "verification": "stage_live_sha256_match",
            "helper_version": manifest.get("helper_version"),
            "verified_file_count": len(manifest.get("files", [])),
            "live_manifest": str(manifest_path.resolve()),
            "live_manifest_sha256": _sha256(manifest_path),
            "live_client": str(client.resolve()),
        },
    )


def _fixture(
    tmp_path: Path,
    *,
    observed_at_ms: int = NOW_MS - 1_000,
) -> tuple[Path, Path, Path]:
    local_app_data = tmp_path / "LocalAppData"
    client = local_app_data / "Solteria" / "client"
    dev = tmp_path / "runtime" / "solteria_helper_dev"
    target = client / "mods" / "ctoa_otclient" / "sample.lua"
    target.parent.mkdir(parents=True)
    target.write_text("return true\n", encoding="utf-8")
    dev.mkdir(parents=True)

    _write_json(
        dev / "live_manifest.json",
        {
            "schema_version": status.LIVE_MANIFEST_SCHEMA,
            "origin": status.LIVE_MANIFEST_ORIGIN,
            "generated_at_utc": "2026-07-11T15:55:00+00:00",
            "helper_version": "v2.2.1",
            "files": [
                {
                    "path": "mods/ctoa_otclient/sample.lua",
                    "sha256": _sha256(target),
                    "bytes": target.stat().st_size,
                }
            ],
        },
    )
    _resign_promotion(dev, client)

    capability = client / "mods" / "ctoa_otclient" / "ctoa_client_capabilities.json"
    _write_json(
        capability,
        {
            "schema_version": evidence.CAPABILITY_SCHEMA,
            "observed_at_unix_ms": observed_at_ms,
            "heartbeat_interval_ms": evidence.EXPECTED_HEARTBEAT_INTERVAL_MS,
            "heartbeat_status": "online",
            "online": True,
            "helper_version": "v2.2.1",
            "protocol_status": "pending_protocol_source",
            "safe_fallback": True,
            "runtime_actions": False,
            "runtime_session_armed": False,
            "runtime_state": "disarmed",
            "runtime_enabled": False,
            "supported_modules": ["client_reporter"],
            "runtime_core": {
                "status": "available",
                "mode": "passive",
                "runtime_actions": False,
            },
        },
    )
    (client / "ctoa_local.log").write_text(
        "\n".join(
            [
                "old Lua exception",
                "Initialized successfully v2.2.1",
                "[CTOA-OTC-HELPER] Runtime disarmed",
                "[CTOA-OTC-HELPER] API probe (manual): core[online=yes localPlayer=yes] player[hp=100/100 pz=no]",
            ]
        ),
        encoding="utf-8",
    )
    return local_app_data, client, dev


def _build(
    client: Path,
    dev: Path,
    *,
    process_count: int = 1,
    process_start_unix_ms: int = NOW_MS - 10_000,
    explicit_report: Path | None = None,
) -> dict[str, object]:
    return status.build_status(
        client_root=client,
        live_manifest_path=dev / "live_manifest.json",
        live_promotion_path=dev / "live_promotion.json",
        process_count=process_count,
        process_start_unix_ms=process_start_unix_ms,
        explicit_report=explicit_report,
        now=NOW,
    )


def _mutate_capability(client: Path, mutation: str) -> None:
    path = client / "mods" / "ctoa_otclient" / "ctoa_client_capabilities.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if mutation == "heartbeat_offline":
        payload["heartbeat_status"] = "offline"
    elif mutation == "game_offline":
        payload["online"] = False
    elif mutation == "missing_runtime_actions":
        payload.pop("runtime_actions")
    elif mutation == "missing_runtime_core_actions":
        payload["runtime_core"].pop("runtime_actions")
    elif mutation == "wrong_interval":
        payload["heartbeat_interval_ms"] = 60_000
    elif mutation == "version_mismatch":
        payload["helper_version"] = "v9.9.9"
    else:
        raise AssertionError(f"unknown mutation: {mutation}")
    _write_json(path, payload)


def test_bounded_tail_and_session_parser_ignore_old_errors(tmp_path: Path):
    log = tmp_path / "client.log"
    log.write_text(
        "X" * 1_000
        + "\nInitialized successfully v2.2.1\n"
        + "[CTOA-OTC-HELPER] Runtime armed\n"
        + "[CTOA-OTC-HELPER] Runtime disarmed\n",
        encoding="utf-8",
    )

    tail = evidence.bounded_tail_text(log, 256)
    session = evidence.current_session(tail)

    assert len(tail.encode("utf-8")) <= 256
    assert evidence.latest_runtime_state(session) == "disarmed"
    assert evidence.summarize_log(log)["lua_exception_count"] == 0


def test_background_status_is_ready_only_from_trusted_live_evidence(
    tmp_path: Path,
):
    _, client, dev = _fixture(tmp_path)

    report = _build(client, dev)

    assert report["status"] == "ready"
    assert report["mode"] == "background_no_screen"
    assert report["advisory_only"] is True
    assert report["safe_to_run_while_playing"] is True
    assert report["promotion_allowed"] is False
    assert report["dispatch_allowed"] is False
    assert report["runtime_actions"] is False
    assert report["process_count"] == 1
    assert report["integrity"]["pin_status"] == "trusted"
    assert report["integrity"]["matched_file_count"] == 1
    assert report["integrity"]["baseline_recorded"] is False
    assert report["capability"]["fresh"] is True
    assert report["capability"]["version_match"] is True
    assert report["capability"]["heartbeat_after_process_start"] is True
    assert report["intrusive_actions_performed"] == []
    assert report["blockers"] == []


@pytest.mark.parametrize(
    ("mutation", "expected_status"),
    [
        ("heartbeat_offline", "heartbeat_offline"),
        ("game_offline", "game_offline"),
        ("missing_runtime_actions", "invalid_contract"),
        ("missing_runtime_core_actions", "invalid_contract"),
        ("wrong_interval", "invalid_heartbeat"),
        ("version_mismatch", "version_mismatch"),
    ],
)
def test_heartbeat_contract_fails_closed(
    tmp_path: Path, mutation: str, expected_status: str
):
    _, client, dev = _fixture(tmp_path)
    _mutate_capability(client, mutation)

    report = _build(client, dev)

    assert report["status"] != "ready"
    assert report["capability"]["status"] == expected_status
    assert report["dispatch_allowed"] is False


def test_heartbeat_must_be_newer_than_process_and_no_more_than_15_seconds_old(
    tmp_path: Path,
):
    _, client, dev = _fixture(tmp_path, observed_at_ms=NOW_MS - 15_001)
    stale = _build(
        client,
        dev,
        process_start_unix_ms=NOW_MS - 30_000,
    )

    _, client2, dev2 = _fixture(tmp_path / "second", observed_at_ms=NOW_MS - 1_000)
    before_process = _build(
        client2,
        dev2,
        process_start_unix_ms=NOW_MS - 1_000,
    )

    assert stale["status"] != "ready"
    assert stale["capability"]["status"] == "stale"
    assert before_process["status"] == "blocked"
    assert before_process["capability"]["status"] == "heartbeat_before_process"


@pytest.mark.parametrize(
    ("process_count", "process_start_unix_ms"),
    [(0, NOW_MS - 10_000), (2, NOW_MS - 10_000), (1, 0)],
)
def test_ready_requires_one_active_process_with_positive_start_time(
    tmp_path: Path,
    process_count: int,
    process_start_unix_ms: int,
):
    _, client, dev = _fixture(tmp_path)

    report = _build(
        client,
        dev,
        process_count=process_count,
        process_start_unix_ms=process_start_unix_ms,
    )

    assert report["status"] != "ready"
    assert report["checks"]["exact_active_client_process"] is (process_count == 1)
    assert report["dispatch_allowed"] is False


def test_missing_or_untrusted_pin_blocks_and_observer_never_creates_one(
    tmp_path: Path,
):
    _, client, dev = _fixture(tmp_path)
    live_manifest = dev / "live_manifest.json"
    live_manifest.unlink()
    _write_json(dev / "manifest.json", {"files": []})

    report = _build(client, dev)

    assert report["status"] == "blocked"
    assert "live_manifest_pin_untrusted" in report["blockers"]
    assert report["integrity"]["baseline"] == "live_manifest"
    assert report["integrity"]["baseline_recorded"] is False
    assert not live_manifest.exists()


@pytest.mark.parametrize(
    ("field", "value", "expected_error"),
    [
        ("name", "wrong", "live_promotion_name_invalid"),
        ("created_at", "wrong", "live_promotion_timestamp_mismatch"),
        ("approval_switch", "no", "live_promotion_approval_invalid"),
        ("verification", "unchecked", "live_promotion_verification_invalid"),
        ("helper_version", "v0", "live_promotion_helper_version_mismatch"),
        ("verified_file_count", 99, "live_promotion_file_count_mismatch"),
        ("live_manifest", "wrong.json", "live_promotion_manifest_path_mismatch"),
        (
            "live_manifest_sha256",
            "0" * 64,
            "live_promotion_manifest_sha256_mismatch",
        ),
    ],
)
def test_live_promotion_cross_check_is_strict(
    tmp_path: Path, field: str, value: object, expected_error: str
):
    _, client, dev = _fixture(tmp_path)
    promotion_path = dev / "live_promotion.json"
    promotion = json.loads(promotion_path.read_text(encoding="utf-8"))
    promotion[field] = value
    _write_json(promotion_path, promotion)

    report = _build(client, dev)

    assert report["status"] == "blocked"
    assert expected_error in report["integrity"]["pin_errors"]
    assert report["integrity"]["pin_trusted"] is False


def test_live_manifest_requires_official_origin_and_schema(tmp_path: Path):
    _, client, dev = _fixture(tmp_path)
    manifest_path = dev / "live_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["origin"] = "background_verified_current_live"
    manifest["schema_version"] = "legacy"
    _write_json(manifest_path, manifest)
    _resign_promotion(dev, client)

    report = _build(client, dev)

    assert report["status"] == "blocked"
    assert "live_manifest_origin_invalid" in report["integrity"]["pin_errors"]
    assert "live_manifest_schema_invalid" in report["integrity"]["pin_errors"]


@pytest.mark.parametrize(
    "invalid_kind", ["nested", "entry_limit", "file_size", "total_size"]
)
def test_manifest_scope_and_size_limits_fail_before_live_reads(
    tmp_path: Path, invalid_kind: str
):
    _, client, dev = _fixture(tmp_path)
    manifest_path = dev / "live_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if invalid_kind == "nested":
        manifest["files"][0]["path"] = "mods/ctoa_otclient/nested/sample.lua"
    elif invalid_kind == "entry_limit":
        manifest["files"] = [
            {
                "path": f"mods/ctoa_otclient/file_{index}.lua",
                "sha256": "0" * 64,
                "bytes": 1,
            }
            for index in range(status.MAX_MANIFEST_ENTRIES + 1)
        ]
    elif invalid_kind == "file_size":
        manifest["files"][0]["bytes"] = status.MAX_LIVE_FILE_BYTES + 1
    elif invalid_kind == "total_size":
        manifest["files"] = [
            {
                "path": f"mods/ctoa_otclient/file_{index}.lua",
                "sha256": "0" * 64,
                "bytes": status.MAX_LIVE_FILE_BYTES,
            }
            for index in range(9)
        ]
    _write_json(manifest_path, manifest)
    _resign_promotion(dev, client)

    report = _build(client, dev)

    assert report["status"] == "blocked"
    assert report["integrity"]["pin_trusted"] is False
    assert report["integrity"]["actual_total_bytes"] == 0


def test_live_file_hashing_stops_at_two_mib(tmp_path: Path):
    _, client, dev = _fixture(tmp_path)
    target = client / "mods" / "ctoa_otclient" / "sample.lua"
    target.write_bytes(b"x" * (status.MAX_LIVE_FILE_BYTES + 1))

    report = _build(client, dev)

    assert report["status"] == "blocked"
    assert report["integrity"]["oversize_count"] == 1
    assert report["integrity"]["actual_total_bytes"] == 0


def test_case_insensitive_manifest_alias_is_rejected(tmp_path: Path):
    _, client, dev = _fixture(tmp_path)
    manifest_path = dev / "live_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    alias = dict(manifest["files"][0])
    alias["path"] = "mods/ctoa_otclient/SAMPLE.lua"
    manifest["files"].append(alias)
    _write_json(manifest_path, manifest)
    _resign_promotion(dev, client)

    report = _build(client, dev)

    assert report["status"] == "blocked"
    assert report["integrity"]["pin_trusted"] is False
    assert "manifest_entry_1_duplicate" in report["integrity"]["pin_errors"]


def test_executable_profile_drift_never_passes_parity(tmp_path: Path):
    _, client, dev = _fixture(tmp_path)
    profile = client / "mods" / "ctoa_otclient" / "ctoa_ek_profile.lua"
    profile.write_text("return true\n", encoding="utf-8")
    manifest_path = dev / "live_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"] = [
        {
            "path": "mods/ctoa_otclient/ctoa_ek_profile.lua",
            "sha256": _sha256(profile),
            "bytes": profile.stat().st_size,
        }
    ]
    _write_json(manifest_path, manifest)
    _resign_promotion(dev, client)
    profile.write_text("return false\n", encoding="utf-8")

    report = _build(client, dev)

    assert report["status"] == "blocked"
    assert report["integrity"]["status"] == "failed"
    assert report["integrity"]["profile_drift_count"] == 1
    assert report["integrity"]["mutable_drift_count"] == 1
    assert "live_manifest_parity_failed" in report["blockers"]


def test_actual_hashing_stops_at_remaining_aggregate_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _, client, dev = _fixture(tmp_path)
    first = client / "mods" / "ctoa_otclient" / "first.lua"
    second = client / "mods" / "ctoa_otclient" / "second.lua"
    first.write_bytes(b"a" * 10)
    second.write_bytes(b"b" * 10)
    manifest_path = dev / "live_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"] = [
        {
            "path": "mods/ctoa_otclient/first.lua",
            "sha256": _sha256(first),
            "bytes": 8,
        },
        {
            "path": "mods/ctoa_otclient/second.lua",
            "sha256": _sha256(second),
            "bytes": 8,
        },
    ]
    _write_json(manifest_path, manifest)
    _resign_promotion(dev, client)
    monkeypatch.setattr(status, "MAX_LIVE_TOTAL_BYTES", 16)

    report = _build(client, dev)

    assert report["status"] == "blocked"
    assert report["integrity"]["actual_total_bytes"] == 10
    assert report["integrity"]["oversize_count"] == 1
    assert report["integrity"]["matched_file_count"] == 0
    first_fingerprint, first_status = status._file_fingerprint(first)
    second_fingerprint, second_status = status._file_fingerprint(second)
    assert first_status == second_status == "loaded"
    assert first_fingerprint is not None and second_fingerprint is not None
    assert not status._fingerprints_unchanged(
        {
            "mods/ctoa_otclient/first.lua": first_fingerprint,
            "mods/ctoa_otclient/second.lua": second_fingerprint,
        },
        client,
    )


def test_only_deterministic_capability_path_is_accepted(tmp_path: Path):
    local_app_data, client, dev = _fixture(tmp_path)
    alternate = (
        local_app_data
        / "ctoa_helper_client_ui_preview"
        / "ctoa_client_capabilities.json"
    )
    alternate.parent.mkdir(parents=True)
    deterministic = client / "mods" / "ctoa_otclient" / "ctoa_client_capabilities.json"
    alternate.write_bytes(deterministic.read_bytes())

    report = _build(client, dev, explicit_report=alternate)

    assert report["status"] == "blocked"
    assert report["capability"]["status"] == "explicit_path_mismatch"
    assert "capability_explicit_path_mismatch" in report["blockers"]


def test_bounded_json_reader_rejects_oversize_and_symlink(tmp_path: Path):
    oversized = tmp_path / "oversized.json"
    oversized.write_bytes(b"{" + b" " * evidence.MAX_CAPABILITY_BYTES)
    assert evidence.load_json_bounded(oversized)[1] == "oversize"

    target = tmp_path / "target.json"
    target.write_text("{}", encoding="utf-8")
    linked = tmp_path / "linked.json"
    try:
        os.symlink(target, linked)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable on this platform")
    assert evidence.load_json_bounded(linked)[1] == "symlink_rejected"


def test_main_no_write_does_not_create_a_missing_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    local_app_data = tmp_path / "LocalAppData"
    client = local_app_data / "Solteria" / "client"
    dev = tmp_path / "runtime" / "solteria_helper_dev"
    client.mkdir(parents=True)
    dev.mkdir(parents=True)
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))
    monkeypatch.setattr(status, "RUNTIME_ROOT", tmp_path / "runtime")

    result = status.main(
        [
            "--client-root",
            str(client),
            "--dev-dir",
            str(dev),
            "--json-out",
            str(dev / "background_status.json"),
            "--process-count",
            "1",
            "--process-start-unix-ms",
            str(NOW_MS - 10_000),
            "--no-write",
        ]
    )

    assert result == 1
    assert not (dev / "live_manifest.json").exists()
    assert not (dev / "background_status.json").exists()
    assert "live_manifest_pin_untrusted" in capsys.readouterr().out


def test_main_rejects_a_non_live_localappdata_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    local_app_data = tmp_path / "LocalAppData"
    wrong_client = local_app_data / "OtherApp"
    dev = tmp_path / "runtime" / "solteria_helper_dev"
    wrong_client.mkdir(parents=True)
    dev.mkdir(parents=True)
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))
    monkeypatch.setattr(status, "RUNTIME_ROOT", tmp_path / "runtime")

    result = status.main(
        [
            "--client-root",
            str(wrong_client),
            "--dev-dir",
            str(dev),
            "--json-out",
            str(dev / "background_status.json"),
            "--process-count",
            "1",
            "--process-start-unix-ms",
            str(NOW_MS - 10_000),
            "--no-write",
        ]
    )

    assert result == 2
    assert not (dev / "background_status.json").exists()


@pytest.mark.parametrize("invalid_target", ["dev_dir", "json_out"])
def test_main_requires_exact_repo_runtime_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid_target: str,
):
    local_app_data = tmp_path / "LocalAppData"
    client = local_app_data / "Solteria" / "client"
    runtime_root = tmp_path / "runtime"
    exact_dev = runtime_root / "solteria_helper_dev"
    client.mkdir(parents=True)
    exact_dev.mkdir(parents=True)
    dev = runtime_root / "other" if invalid_target == "dev_dir" else exact_dev
    output = (
        exact_dev / "other.json"
        if invalid_target == "json_out"
        else dev / "background_status.json"
    )
    dev.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))
    monkeypatch.setattr(status, "RUNTIME_ROOT", runtime_root)

    result = status.main(
        [
            "--client-root",
            str(client),
            "--dev-dir",
            str(dev),
            "--json-out",
            str(output),
            "--process-count",
            "1",
            "--process-start-unix-ms",
            str(NOW_MS - 10_000),
            "--no-write",
        ]
    )

    assert result == 2
    assert not output.exists()


def test_background_wrapper_has_positive_allowlist_and_guarded_primitives():
    wrapper = WRAPPER.read_text(encoding="utf-8")
    cli = CLI.read_text(encoding="utf-8")
    reporter = REPORTER.read_text(encoding="utf-8")
    smoke = SANDBOX_SMOKE.read_text(encoding="utf-8")

    allowlist = wrapper[
        wrapper.index("function Get-BackgroundAllowedActions") : wrapper.index(
            "function Assert-InteractiveOperatorMode"
        )
    ]
    background = wrapper[
        wrapper.index("function Invoke-BackgroundStatus") : wrapper.index(
            "Assert-OperatorModeAction\n\nswitch"
        )
    ]
    assert 'return @("BackgroundStatus")' in allowlist
    assert "CTOA_OPERATOR_MODE=background_no_screen cannot be downgraded" in wrapper
    assert "BackgroundNoScreen rejects live approval" in wrapper
    assert '"BackgroundStatus" {' in wrapper
    assert '"otbg" { Invoke-OtBackgroundStatus; break }' in cli
    assert '"-OperatorMode"' in cli and '"BackgroundNoScreen"' in cli
    assert '"--process-count"' in background
    assert '"--process-start-unix-ms"' in background
    for forbidden in (
        "Start-Process",
        "Stop-Process",
        "Capture-Screenshot",
        "SetForegroundWindow",
        "SendKeys",
        "mouse_event",
        "Copy-Item",
        "PromoteLiveCtoa",
    ):
        assert forbidden not in background
    for function_name in (
        "Write-SmokeCommand",
        "Sync-CtoaRuntimeFiles",
        "Start-LiveClientAfterPromotion",
        "Initialize-Sandbox",
        "Start-SandboxClient",
        "Stop-SandboxClient",
        "Set-LiveCtoaEnabled",
        "Set-LiveCtoaUiOnly",
        "New-LiveCtoaBackup",
        "Invoke-LivePromotion",
        "Invoke-LiveEmergencyRepair",
        "Capture-Screenshot",
    ):
        start = wrapper.index(f"function {function_name}")
        assert "Assert-InteractiveOperatorMode" in wrapper[start : start + 700]
    assert "deterministic_work_dir_path = true" in reporter
    assert "no_screen_safe = true" in reporter
    assert "bounded_tail_text(log_path)" in smoke
    assert "function Write-LiveManifestSnapshot" in wrapper
    assert 'schema_version = "ctoa.solteria-live-manifest.v1"' in wrapper
    assert "live_manifest_sha256 = $liveManifestSha256" in wrapper
    live_snapshot = wrapper[
        wrapper.index("function Write-LiveManifestSnapshot") : wrapper.index(
            "function Invoke-LivePromotion"
        )
    ]
    assert 'Join-Path $OutRoot "manifest.json"' not in live_snapshot
    assert "Get-Content" not in live_snapshot
    assert "$VerifiedEntries" in live_snapshot
    assert "$HelperVersion" in live_snapshot


def test_background_wrapper_publishes_only_after_external_invariants():
    wrapper = WRAPPER.read_text(encoding="utf-8")
    background = wrapper[
        wrapper.index("function Invoke-BackgroundStatus") : wrapper.index(
            "Assert-OperatorModeAction\n\nswitch"
        )
    ]

    assert "Assert-ExactLiveClientPath -Path $SourceClient" in background
    assert "BackgroundNoScreen requires the trusted repo interpreter" in background
    assert "Get-Command python" not in background
    assert '"--no-write"' in background
    assert background.index("$rawPayload = @(& $python @arguments)") < background.index(
        "$afterProcesses = Get-BackgroundProcessSample"
    )
    assert background.index(
        "$afterProcesses = Get-BackgroundProcessSample"
    ) < background.index("Write-JsonAtomic -InputObject $payload")
    assert "client_process_changed_during_observation" in background
    assert "screenshot_count_changed_during_observation" in background
    assert "stored a blocked sample" in background
    assert background.count("Assert-ExactBackgroundOutputPath") >= 2
    assert "publication escaped the exact runtime output path" in background
    output_guard = wrapper[
        wrapper.index("function Assert-ExactBackgroundOutputPath") : wrapper.index(
            "function Assert-SandboxClientPath"
        )
    ]
    assert "ReparsePoint" in output_guard
    assert 'Join-Path $runtimeRoot "solteria_helper_dev"' in output_guard
