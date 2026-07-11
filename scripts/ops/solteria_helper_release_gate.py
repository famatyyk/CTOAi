#!/usr/bin/env python3
"""Audit Solteria Helper release gates without touching the live client."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DEV_DIR = ROOT / "runtime" / "solteria_helper_dev"
DEFAULT_SCREENSHOT_DIR = ROOT / "runtime" / "otclient_ui_preview"
EXPECTED_SMOKE_VIEWS = {
    "overview",
    "healing",
    "heal_friend",
    "conditions",
    "hunting",
    "hunting_magic",
    "cavebot",
    "equipment",
    "tools",
    "tools_pvp",
    "tools_hud",
    "tools_timer",
    "tools_diag",
    "scripting",
    "profile",
    "ui",
}
LAUNCH_COMMAND = (
    "powershell -NoProfile -ExecutionPolicy Bypass -File "
    "scripts\\windows\\solteria_helper_test_env.ps1 -Action Launch"
)
READY_CHECK_COMMAND = (
    "powershell -NoProfile -ExecutionPolicy Bypass -File "
    "scripts\\windows\\solteria_helper_test_env.ps1 -Action ReadyCheck"
)
SMOKE_ATTACH_ALL_COMMAND = (
    "powershell -NoProfile -ExecutionPolicy Bypass -File "
    "scripts\\windows\\solteria_helper_test_env.ps1 -Action SmokeAttachAll"
)
SMOKE_ATTACH_MODULES_COMMAND = (
    "powershell -NoProfile -ExecutionPolicy Bypass -File "
    "scripts\\windows\\solteria_helper_test_env.ps1 -Action SmokeAttachModules"
)
MODULE_STATIC_GATES_COMMAND = (
    "powershell -NoProfile -ExecutionPolicy Bypass -File "
    "scripts\\windows\\solteria_helper_test_env.ps1 -Action ModuleStaticGates"
)
LIVE_FORBIDDEN_ROOT_FALLBACKS = ("ctoa_native_helper.lua",)


@dataclass(frozen=True)
class Gate:
    name: str
    status: str
    evidence: str
    reason: str = ""


@dataclass(frozen=True)
class GateReport:
    name: str
    status: str
    releasable_to_live: bool
    gates: list[Gate]
    next_action: str
    next_command: str


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        with tmp.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        tmp.replace(path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def _file_gate(name: str, path: Path | None, reason: str) -> Gate:
    if path is None:
        return Gate(name=name, status="blocked", evidence="not provided", reason=reason)
    if path.is_file():
        return Gate(name=name, status="passed", evidence=str(path))
    return Gate(name=name, status="blocked", evidence=str(path), reason=reason)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _zip_gate(path: Path | None, expected_sha256: str) -> Gate:
    base = _file_gate("zip", path, "Missing versioned ZIP evidence; run PrepareDev or ValidateDev.")
    if base.status != "passed" or path is None:
        return base
    actual_sha256 = _sha256(path)
    if expected_sha256 and actual_sha256.lower() != expected_sha256.lower():
        return Gate(
            name="zip",
            status="blocked",
            evidence=str(path),
            reason="ZIP SHA256 does not match release_readiness.json; rerun PrepareDev or ValidateDev.",
        )
    return Gate(name="zip", status="passed", evidence=str(path))


def _manifest_gate(manifest_path: Path, manifest: dict) -> Gate:
    base = _file_gate("manifest", manifest_path, "Missing manifest.json; run PrepareDev.")
    if base.status != "passed":
        return base
    files = manifest.get("files")
    stage_value = manifest.get("stage")
    if not isinstance(files, list) or not files:
        return Gate(
            name="manifest",
            status="blocked",
            evidence=str(manifest_path),
            reason="Manifest has no staged file hash evidence; run PrepareDev or ValidateDev.",
        )
    if not stage_value:
        return Gate(
            name="manifest",
            status="blocked",
            evidence=str(manifest_path),
            reason="Manifest is missing stage path; run PrepareDev or ValidateDev.",
        )
    stage = Path(stage_value)
    mismatches: list[str] = []
    for item in files:
        relative = item.get("path") if isinstance(item, dict) else None
        expected_sha256 = item.get("sha256") if isinstance(item, dict) else None
        if not relative or not expected_sha256:
            mismatches.append(str(relative or "<missing path>"))
            continue
        path = stage / str(relative)
        if not path.is_file() or _sha256(path).lower() != str(expected_sha256).lower():
            mismatches.append(str(relative))
    if mismatches:
        preview = ", ".join(mismatches[:3])
        if len(mismatches) > 3:
            preview += f", +{len(mismatches) - 3} more"
        return Gate(
            name="manifest",
            status="blocked",
            evidence=str(manifest_path),
            reason=f"Manifest staged file hashes do not match latest package: {preview}.",
        )
    return Gate(name="manifest", status="passed", evidence=str(manifest_path))


def find_latest_inworld_smoke_report(screenshot_dir: Path) -> Path | None:
    candidates = [
        path
        for path in screenshot_dir.glob("solteria-helper-smokeall-inworld-*.json")
        if path.is_file()
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: (path.stat().st_mtime, path.name))


def _resolve_report_screenshot(smoke_report: Path, screenshot_value: str) -> Path:
    path = Path(screenshot_value)
    if path.is_absolute():
        return path
    candidates = [ROOT / path, smoke_report.parent / path]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]


def _smoke_gate(smoke_report: Path | None, manifest_path: Path | None = None) -> Gate:
    if not smoke_report:
        return Gate(
            name="SmokeAttachAll",
            status="pending",
            evidence="not provided",
            reason="Run SmokeAttachAll after sandbox character is in-world.",
        )
    if manifest_path and manifest_path.is_file() and smoke_report.stat().st_mtime < manifest_path.stat().st_mtime:
        return Gate(
            name="SmokeAttachAll",
            status="blocked",
            evidence=str(smoke_report),
            reason="SmokeAttachAll is stale for the current dev manifest; rerun SmokeAttachAll after sandbox character is in-world.",
        )
    data = _load_json(smoke_report)
    complete = data.get("covered_count") == data.get("expected_count") and not data.get("missing")
    in_world = data.get("acceptance_status") == "ready_for_visual_review" and data.get("modal_limited") is False
    views = data.get("views") if isinstance(data.get("views"), list) else []
    by_view = {item.get("view"): item for item in views if isinstance(item, dict)}
    missing_views = sorted(EXPECTED_SMOKE_VIEWS - set(by_view))
    missing_screenshots: list[str] = []
    for view in sorted(EXPECTED_SMOKE_VIEWS):
        item = by_view.get(view) or {}
        screenshot = item.get("screenshot")
        if not screenshot or not _resolve_report_screenshot(smoke_report, str(screenshot)).is_file():
            missing_screenshots.append(view)
    expected_shape = data.get("expected_count") == len(EXPECTED_SMOKE_VIEWS)
    view_evidence = not missing_views and not missing_screenshots
    if complete and in_world and expected_shape and view_evidence:
        return Gate(name="SmokeAttachAll", status="passed", evidence=str(smoke_report))
    if not expected_shape or not view_evidence:
        details = missing_views or missing_screenshots
        preview = ", ".join(details[:3])
        if len(details) > 3:
            preview += f", +{len(details) - 3} more"
        return Gate(
            name="SmokeAttachAll",
            status="blocked",
            evidence=str(smoke_report),
            reason=f"Smoke report is missing required view screenshot evidence: {preview}.",
        )
    return Gate(
        name="SmokeAttachAll",
        status="blocked",
        evidence=str(smoke_report),
        reason="Smoke report is missing views or is still modal-limited.",
    )


def _smoke_preflight_gate(preflight_path: Path, manifest_path: Path, manifest: dict) -> Gate:
    data = _load_json(preflight_path)
    if not data:
        return Gate(
            name="SmokePreflight",
            status="pending",
            evidence=str(preflight_path),
            reason="Run SmokePreflight before Launch or SmokeAttachModules.",
        )
    manifest_created_at = manifest.get("created_at")
    preflight_manifest = data.get("manifest") or {}
    preflight_manifest_created_at = preflight_manifest.get("created_at")
    preflight_manifest_sha256 = str(preflight_manifest.get("sha256") or "").lower()
    if data.get("status") != "passed":
        return Gate(
            name="SmokePreflight",
            status="blocked",
            evidence=str(preflight_path),
            reason="SmokePreflight did not pass; sandbox files do not match staged package.",
        )
    current_manifest_sha256 = _sha256(manifest_path) if manifest_path.is_file() else ""
    manifest_matches = bool(
        preflight_manifest_sha256
        and current_manifest_sha256
        and preflight_manifest_sha256 == current_manifest_sha256.lower()
    )
    if not manifest_matches and manifest_created_at and preflight_manifest_created_at != manifest_created_at:
        return Gate(
            name="SmokePreflight",
            status="blocked",
            evidence=str(preflight_path),
            reason="SmokePreflight is stale for the current dev manifest; rerun SmokePreflight.",
        )
    return Gate(name="SmokePreflight", status="passed", evidence=str(preflight_path))


def _module_static_gates_gate(gates_path: Path, manifest_path: Path) -> Gate:
    data = _load_json(gates_path)
    if not data:
        return Gate(
            name="ModuleStaticGates",
            status="pending",
            evidence=str(gates_path),
            reason="Run ModuleStaticGates before sandbox attach smoke.",
        )
    if manifest_path.is_file() and gates_path.stat().st_mtime < manifest_path.stat().st_mtime:
        return Gate(
            name="ModuleStaticGates",
            status="blocked",
            evidence=str(gates_path),
            reason="ModuleStaticGates is stale for the current dev manifest; rerun ModuleStaticGates.",
        )
    gate_count = int(data.get("gate_count") or 0)
    passed_count = int(data.get("passed_count") or 0)
    failed_count = int(data.get("failed_count") or 0)
    if data.get("status") == "passed" and gate_count >= 5 and passed_count == gate_count and failed_count == 0:
        return Gate(name="ModuleStaticGates", status="passed", evidence=str(gates_path))
    return Gate(
        name="ModuleStaticGates",
        status="blocked",
        evidence=str(gates_path),
        reason="ModuleStaticGates did not pass all prototype module gates.",
    )


def _module_attach_smoke_gate(gates_path: Path, manifest_path: Path) -> Gate:
    data = _load_json(gates_path)
    if not data:
        return Gate(
            name="ModuleAttachSmoke",
            status="pending",
            evidence=str(gates_path),
            reason="Run SmokeAttachModules after sandbox character is in-world.",
        )
    if manifest_path.is_file() and gates_path.stat().st_mtime < manifest_path.stat().st_mtime:
        return Gate(
            name="ModuleAttachSmoke",
            status="blocked",
            evidence=str(gates_path),
            reason="ModuleAttachSmoke is stale for the current dev manifest; rerun SmokeAttachModules after sandbox character is in-world.",
        )
    module_count = int(data.get("module_count") or 0)
    passed_count = int(data.get("passed_count") or 0)
    failed_count = int(data.get("failed_count") or 0)
    if data.get("status") == "passed" and module_count == 4 and passed_count == module_count and failed_count == 0:
        return Gate(name="ModuleAttachSmoke", status="passed", evidence=str(gates_path))
    return Gate(
        name="ModuleAttachSmoke",
        status="blocked",
        evidence=str(gates_path),
        reason="ModuleAttachSmoke did not pass all prototype module attach tabs.",
    )


def _live_root_from_manifest(manifest: dict) -> Path | None:
    live_client = manifest.get("live_client")
    if isinstance(live_client, dict):
        source_client = live_client.get("source_client")
        if source_client:
            return Path(str(source_client))
    return None


def _live_package_matches_manifest(live_root: Path, manifest: dict) -> tuple[bool, str]:
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        return False, "Manifest has no file hashes to verify against live client."
    mismatches: list[str] = []
    for item in files:
        relative = item.get("path") if isinstance(item, dict) else None
        expected_sha256 = item.get("sha256") if isinstance(item, dict) else None
        if not relative or not expected_sha256:
            mismatches.append(str(relative or "<missing path>"))
            continue
        live_path = live_root / str(relative)
        if not live_path.is_file() or _sha256(live_path).lower() != str(expected_sha256).lower():
            mismatches.append(str(relative))
    if mismatches:
        preview = ", ".join(mismatches[:3])
        if len(mismatches) > 3:
            preview += f", +{len(mismatches) - 3} more"
        return False, f"Live promoted files do not match current manifest: {preview}."
    forbidden = [name for name in LIVE_FORBIDDEN_ROOT_FALLBACKS if (live_root / name).is_file()]
    if forbidden:
        preview = ", ".join(forbidden)
        return False, f"Live client still contains forbidden root helper fallback files: {preview}."
    return True, ""


def _live_approval_gate(dev_dir: Path, manifest_path: Path, manifest: dict, approved: bool) -> Gate:
    if approved:
        return Gate(name="live_approval", status="passed", evidence="-ApproveLiveDeploy")
    promotion_path = dev_dir / "live_promotion.json"
    if not promotion_path.is_file():
        return Gate(
            "live_approval",
            "pending",
            "not approved",
            "Live deployment requires explicit user approval.",
        )
    promotion = _load_json(promotion_path)
    if promotion.get("approval_switch") != "ApproveLiveDeploy":
        return Gate(
            "live_approval",
            "blocked",
            str(promotion_path),
            "Live promotion report does not contain the approval switch evidence.",
        )
    if manifest_path.is_file() and promotion_path.stat().st_mtime < manifest_path.stat().st_mtime:
        return Gate(
            "live_approval",
            "blocked",
            str(promotion_path),
            "Live promotion report is older than the current dev manifest; rerun promotion after the current gates pass.",
        )
    live_root_value = promotion.get("live_client") or _live_root_from_manifest(manifest)
    if not live_root_value:
        return Gate(
            "live_approval",
            "blocked",
            str(promotion_path),
            "Live promotion report is missing live client path evidence.",
        )
    live_root = Path(str(live_root_value))
    matches, reason = _live_package_matches_manifest(live_root, manifest)
    if not matches:
        return Gate("live_approval", "blocked", str(promotion_path), reason)
    return Gate(name="live_approval", status="passed", evidence=str(promotion_path))


def _command_for_attach_gate(dev_dir: Path, ready_command: str) -> str:
    smoke_status = _load_json(dev_dir / "smoke_status.json")
    smoke_status_value = str(smoke_status.get("status") or "").strip()
    smoke_command = str(smoke_status.get("next_command") or "").strip()
    if smoke_command and smoke_status_value in {
        "not_running",
        "running_without_window",
        "character_modal",
        "helper_log_missing",
    }:
        return smoke_command
    ready_check = _load_json(dev_dir / "ready_check.json")
    if ready_check.get("status") == "ready" and smoke_status_value in {"", "ready_for_readycheck"}:
        return ready_command
    if smoke_command:
        return smoke_command
    ready_command = str(ready_check.get("next_command") or "").strip()
    if ready_command:
        return ready_command
    return LAUNCH_COMMAND


def _command_for_smokeattach_gate(dev_dir: Path) -> str:
    return _command_for_attach_gate(dev_dir, SMOKE_ATTACH_ALL_COMMAND)


def _command_for_module_attach_gate(dev_dir: Path) -> str:
    return _command_for_attach_gate(dev_dir, SMOKE_ATTACH_MODULES_COMMAND)


def _command_for_next_gate(gates: list[Gate], approved: bool, dev_dir: Path) -> str:
    promote_command = (
        "powershell -NoProfile -ExecutionPolicy Bypass -File "
        "scripts\\windows\\solteria_helper_test_env.ps1 -Action PromoteLiveCtoa -ApproveLiveDeploy"
    )
    blocked = next((gate for gate in gates if gate.status != "passed"), None)
    if not blocked:
        return promote_command
    if blocked.name == "SmokePreflight":
        return (
            "powershell -NoProfile -ExecutionPolicy Bypass -File "
            "scripts\\windows\\solteria_helper_test_env.ps1 -Action SmokePreflight"
        )
    if blocked.name == "ModuleStaticGates":
        return MODULE_STATIC_GATES_COMMAND
    if blocked.name == "ModuleAttachSmoke":
        return _command_for_module_attach_gate(dev_dir)
    if blocked.name == "SmokeAttachAll":
        return _command_for_smokeattach_gate(dev_dir)
    if blocked.name == "live_approval" and not approved:
        return promote_command
    return (
        "powershell -NoProfile -ExecutionPolicy Bypass -File "
        "scripts\\windows\\solteria_helper_test_env.ps1 -Action ValidateDev"
    )


def build_report(dev_dir: Path, smoke_report: Path | None = None, *, approved: bool = False) -> GateReport:
    manifest_path = dev_dir / "manifest.json"
    validation_path = dev_dir / "validation.json"
    readiness_path = dev_dir / "release_readiness.json"
    changelog_path = dev_dir / "CHANGELOG.md"
    smoke_preflight_path = dev_dir / "smoke_preflight.json"
    module_static_gates_path = dev_dir / "module_static_gates.json"
    module_attach_smoke_path = dev_dir / "module_attach_smoke.json"

    manifest = _load_json(manifest_path)
    validation = _load_json(validation_path)
    readiness = _load_json(readiness_path)
    zip_info = readiness.get("zip") or {}
    zip_value = zip_info.get("path")
    zip_expected_sha256 = str(zip_info.get("sha256") or "")
    zip_path = Path(zip_value) if zip_value else None

    gates = [
        _manifest_gate(manifest_path, manifest),
        _file_gate("changelog", changelog_path, "Missing CHANGELOG.md; run PrepareDev or ValidateDev."),
        Gate("validation", "passed" if validation.get("status") == "passed" else "blocked", str(validation_path)),
        Gate("release_readiness", "passed" if readiness.get("status") == "static-passed" else "blocked", str(readiness_path)),
        _zip_gate(zip_path, zip_expected_sha256),
        _smoke_preflight_gate(smoke_preflight_path, manifest_path, manifest),
        _module_static_gates_gate(module_static_gates_path, manifest_path),
        _module_attach_smoke_gate(module_attach_smoke_path, manifest_path),
        _smoke_gate(smoke_report, manifest_path),
        _live_approval_gate(dev_dir, manifest_path, manifest, approved),
    ]
    releasable = all(gate.status == "passed" for gate in gates)
    if releasable:
        live_gate = next((gate for gate in gates if gate.name == "live_approval"), None)
        if live_gate and live_gate.evidence.endswith("live_promotion.json"):
            next_action = "Live promotion is complete for the current staged package."
        else:
            next_action = "Run PromoteLiveCtoa -ApproveLiveDeploy if the user still wants live promotion."
    else:
        next_action = next((gate.reason for gate in gates if gate.status != "passed" and gate.reason), "Resolve pending gates.")
    next_command = "" if releasable and next_action.startswith("Live promotion is complete") else _command_for_next_gate(gates, approved, dev_dir)
    return GateReport(
        name="solteria-helper-release-gate",
        status="passed" if releasable else "blocked",
        releasable_to_live=releasable,
        gates=gates,
        next_action=next_action,
        next_command=next_command,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dev-dir", type=Path, default=DEFAULT_DEV_DIR)
    parser.add_argument("--smoke-report", type=Path, default=None)
    parser.add_argument("--screenshot-dir", type=Path, default=DEFAULT_SCREENSHOT_DIR)
    parser.add_argument("--approved", action="store_true")
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--allow-blocked", action="store_true", help="Return 0 even when release gates are blocked.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    smoke_report = args.smoke_report.resolve() if args.smoke_report else find_latest_inworld_smoke_report(args.screenshot_dir.resolve())
    report = build_report(args.dev_dir.resolve(), smoke_report, approved=args.approved)
    out = args.json_out or args.dev_dir / "release_gate.json"
    write_json_atomic(out, asdict(report))
    print(f"[solteria-helper-release-gate] JSON: {out}")
    print(f"[solteria-helper-release-gate] Status: {report.status}")
    print(f"[solteria-helper-release-gate] Next: {report.next_action}")
    if report.next_command:
        print(f"[solteria-helper-release-gate] Next command: {report.next_command}")
    return 0 if report.releasable_to_live or args.allow_blocked else 1


if __name__ == "__main__":
    raise SystemExit(main())
