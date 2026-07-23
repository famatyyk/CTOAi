#!/usr/bin/env python3
"""Build and verify the signed, artifact-only P14 independent runner handoff."""

from __future__ import annotations

import argparse
import copy
import hashlib
import hmac
import json
import os
import re
import stat
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
REQUEST_SCHEMA_PATH = ROOT / "schemas" / "ctoa-p14-runner-request.schema.json"
RESULT_SCHEMA_PATH = ROOT / "schemas" / "ctoa-p14-runner-result.schema.json"
ROADMAP_STATE_PATH = ROOT / "AI" / "generated" / "ROADMAP_STATE.json"
HELPER_SOURCE_PATH = ROOT / "scripts" / "lua" / "otclient"
CHOOSER_SOURCE_PATH = ROOT / "scripts" / "lua" / "ctoa_chooser"
DEFAULT_ARTIFACT_ROOT = ROOT / "runtime" / "p14_independent_runner"

MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_HELPER_FILE_BYTES = 2 * 1024 * 1024
MAX_HELPER_FILES = 256
SIGNING_KEY_ENV = "CTOA_P14_RUNNER_SIGNING_KEY"
SIGNING_KEY_ID_ENV = "CTOA_P14_RUNNER_KEY_ID"
SAFE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
VERSION_RE = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+$")
SOURCE_PROVENANCE_SCHEMA = "ctoa.p14-source-provenance.v1"
SOURCE_PROVENANCE_FILENAME = ".ctoa-p14-source-provenance.json"
CHECK_IDS = [
    "request_schema",
    "bundle_signature",
    "roadmap_state_replay",
    "helper_manifest_replay",
    "rollback_manifest_replay",
]
AUTHORITY = {
    "runtime_executor_added": False,
    "runtime_actions": False,
    "live_authority": False,
    "promotion_approved": False,
    "mcp_write_tool_enabled": False,
    "p12_reopened": False,
}
LOCAL_SOURCE_ONLY_HELPER_FILES = frozenset(
    {
        "ctoa_native_combat.lua",
        "ctoa_native_heal.lua",
        "ctoa_native_loot.lua",
    }
)


class ContractError(ValueError):
    """Raised when a P14 artifact violates the fixed contract."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate_json_key:{key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ContractError(f"non_finite_json_number:{value}")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def raw_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _is_reparse(path: Path) -> bool:
    info = path.lstat()
    attributes = getattr(info, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return path.is_symlink() or bool(attributes & reparse_flag)


def _read_regular_file(path: Path, *, max_bytes: int = MAX_JSON_BYTES) -> bytes:
    if not path.exists() or not path.is_file() or _is_reparse(path):
        raise ContractError(f"regular_file_required:{path.name}")
    before = path.stat()
    if before.st_size > max_bytes:
        raise ContractError(f"file_too_large:{path.name}")
    raw = path.read_bytes()
    after = path.stat()
    stable = (
        before.st_size == after.st_size == len(raw)
        and before.st_mtime_ns == after.st_mtime_ns
        and getattr(before, "st_ino", 0) == getattr(after, "st_ino", 0)
    )
    if not stable:
        raise ContractError(f"file_changed_during_read:{path.name}")
    return raw


def load_strict_json(path: Path, *, max_bytes: int = MAX_JSON_BYTES) -> dict[str, Any]:
    raw = _read_regular_file(path, max_bytes=max_bytes)
    try:
        value = json.loads(
            raw.decode("utf-8-sig"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"invalid_json:{path.name}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"json_object_required:{path.name}")
    return value


def validate_schema(payload: dict[str, Any], schema_path: Path) -> None:
    # Emitting the bounded Docker provenance sidecar deliberately needs only the
    # standard library.  Full request/result validation still requires the
    # pinned jsonschema dependency at the point it is actually exercised.
    from jsonschema import Draft202012Validator, FormatChecker

    schema = load_strict_json(schema_path)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.path))
    if errors:
        location = ".".join(str(part) for part in errors[0].path) or "root"
        raise ContractError(f"schema_invalid:{schema_path.name}:{location}")


def _safe_relative_path(value: Any) -> str:
    if not isinstance(value, str) or not value or len(value) > 240 or "\\" in value:
        raise ContractError("helper_path_invalid")
    candidate = PurePosixPath(value)
    if candidate.is_absolute() or ".." in candidate.parts or "." in candidate.parts:
        raise ContractError("helper_path_invalid")
    if value != "ctoa_project_loader.lua" and (
        not candidate.parts or candidate.parts[0] != "mods"
    ):
        raise ContractError("helper_path_outside_allowlist")
    return candidate.as_posix()


def _safe_source_relative_path(value: Any) -> str:
    """Normalize an unambiguous path below the fixed source checkout root."""

    if not isinstance(value, str) or not value or len(value) > 240 or "\\" in value:
        raise ContractError("helper_provenance_invalid")
    candidate = PurePosixPath(value)
    if candidate.is_absolute() or "." in candidate.parts or ".." in candidate.parts:
        raise ContractError("helper_provenance_invalid")
    return candidate.as_posix()


def _package_source_index(
    sources: list[tuple[str, Path]],
) -> tuple[Path, dict[str, tuple[str, Path]]]:
    """Bind each fixed package target to one non-reparse source checkout path."""

    try:
        repository_root = ROOT.resolve(strict=True)
    except OSError as exc:
        raise ContractError("helper_tracking_unavailable") from exc

    indexed: dict[str, tuple[str, Path]] = {}
    for package_path, source_path in sources:
        package_relative = _safe_relative_path(package_path)
        if package_relative in indexed:
            raise ContractError("helper_file_duplicate")
        if _is_reparse(source_path):
            raise ContractError("helper_reparse_file_rejected")
        try:
            source_relative = source_path.resolve(strict=True).relative_to(repository_root)
        except (OSError, RuntimeError, ValueError) as exc:
            raise ContractError("helper_source_outside_repository") from exc
        indexed[package_relative] = (source_relative.as_posix(), source_path)

    if not indexed:
        raise ContractError("helper_file_count_invalid")
    return repository_root, indexed


def _git_metadata_is_present(repository_root: Path) -> bool:
    """Return whether this exact checkout has Git metadata, never probing a parent."""

    metadata_path = repository_root / ".git"
    try:
        metadata = metadata_path.lstat()
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise ContractError("helper_tracking_unavailable") from exc
    if _is_reparse(metadata_path):
        raise ContractError("helper_git_metadata_invalid")
    if not stat.S_ISDIR(metadata.st_mode) and not stat.S_ISREG(metadata.st_mode):
        raise ContractError("helper_git_metadata_invalid")
    return True


def _require_git_tracked_package_sources(
    repository_root: Path, relative_paths: set[str]
) -> None:
    """Use checkout Git metadata as the authoritative provenance source."""

    try:
        result = subprocess.run(
            [
                "git",
                "ls-files",
                "-z",
                "--error-unmatch",
                "--",
                *sorted(relative_paths),
            ],
            cwd=repository_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        # A checkout that contains metadata but cannot query it is never allowed
        # to downgrade to the Docker sidecar path.
        raise ContractError("helper_tracking_unavailable") from exc
    if result.returncode != 0:
        raise ContractError("helper_untracked_source_rejected")

    tracked_paths = {item for item in result.stdout.split("\0") if item}
    if tracked_paths != relative_paths:
        raise ContractError("helper_untracked_source_rejected")


def _load_source_provenance(repository_root: Path) -> dict[str, Any]:
    """Load the immutable CI-injected sidecar only when this checkout lacks Git."""

    sidecar_path = repository_root / SOURCE_PROVENANCE_FILENAME
    try:
        sidecar_path.lstat()
    except FileNotFoundError as exc:
        raise ContractError("helper_provenance_unavailable") from exc
    except OSError as exc:
        raise ContractError("helper_provenance_unavailable") from exc
    if _is_reparse(sidecar_path):
        raise ContractError("helper_provenance_invalid")
    try:
        return load_strict_json(sidecar_path)
    except ContractError as exc:
        raise ContractError("helper_provenance_invalid") from exc


def _require_sidecar_provenance(
    repository_root: Path, expected_sources: dict[str, tuple[str, Path]]
) -> None:
    """Bind the complete fixed package to a CI-generated tracked-source sidecar."""

    provenance = _load_source_provenance(repository_root)
    required = {"schema_version", "source_revision", "file_count", "files"}
    if (
        set(provenance) != required
        or provenance.get("schema_version") != SOURCE_PROVENANCE_SCHEMA
        or not isinstance(provenance.get("source_revision"), str)
        or not re.fullmatch(r"[a-f0-9]{40}", provenance["source_revision"])
    ):
        raise ContractError("helper_provenance_invalid")

    files = provenance.get("files")
    if (
        not isinstance(files, list)
        or not 1 <= len(files) <= MAX_HELPER_FILES
        or provenance.get("file_count") != len(files)
    ):
        raise ContractError("helper_provenance_invalid")

    entries: dict[str, dict[str, Any]] = {}
    package_paths: list[str] = []
    for entry in files:
        if not isinstance(entry, dict) or set(entry) != {
            "package_path",
            "source_path",
            "bytes",
            "sha256",
        }:
            raise ContractError("helper_provenance_invalid")
        try:
            package_path = _safe_relative_path(entry["package_path"])
            source_path = _safe_source_relative_path(entry["source_path"])
        except ContractError as exc:
            raise ContractError("helper_provenance_invalid") from exc
        size = entry.get("bytes")
        digest = entry.get("sha256")
        if (
            type(size) is not int
            or not 1 <= size <= MAX_HELPER_FILE_BYTES
            or not isinstance(digest, str)
            or not SHA256_RE.fullmatch(digest)
            or package_path in entries
        ):
            raise ContractError("helper_provenance_invalid")
        entries[package_path] = {
            "package_path": package_path,
            "source_path": source_path,
            "bytes": size,
            "sha256": digest,
        }
        package_paths.append(package_path)

    if package_paths != sorted(package_paths):
        raise ContractError("helper_provenance_order_invalid")
    if set(entries) != set(expected_sources):
        raise ContractError("helper_provenance_path_set_invalid")

    for package_path, (expected_source_path, source_path) in expected_sources.items():
        entry = entries[package_path]
        if entry["source_path"] != expected_source_path:
            raise ContractError("helper_provenance_path_set_invalid")
        raw = _read_regular_file(source_path, max_bytes=MAX_HELPER_FILE_BYTES)
        if len(raw) != entry["bytes"] or raw_sha256(raw) != entry["sha256"]:
            raise ContractError("helper_provenance_binding_invalid")


def _require_tracked_package_sources(sources: list[tuple[str, Path]]) -> None:
    """Reject untracked/reparse inputs; use sidecar only when Git is absent."""

    repository_root, indexed_sources = _package_source_index(sources)
    relative_paths = {source_path for source_path, _ in indexed_sources.values()}
    if _git_metadata_is_present(repository_root):
        _require_git_tracked_package_sources(repository_root, relative_paths)
        return
    _require_sidecar_provenance(repository_root, indexed_sources)


def _package_sources() -> list[tuple[str, Path]]:
    if not HELPER_SOURCE_PATH.is_dir() or _is_reparse(HELPER_SOURCE_PATH):
        raise ContractError("helper_source_root_invalid")
    if not CHOOSER_SOURCE_PATH.is_dir() or _is_reparse(CHOOSER_SOURCE_PATH):
        raise ContractError("chooser_source_root_invalid")
    sources = [
        ("ctoa_project_loader.lua", CHOOSER_SOURCE_PATH / "ctoa_chooser_loader.lua"),
        (
            "mods/ctoa_chooser/ctoa_chooser.otmod",
            CHOOSER_SOURCE_PATH / "ctoa_chooser.otmod",
        ),
        (
            "mods/ctoa_chooser/ctoa_chooser_loader.lua",
            CHOOSER_SOURCE_PATH / "ctoa_chooser_loader.lua",
        ),
    ]
    helper_files = sorted(
        (
            path
            for path in HELPER_SOURCE_PATH.iterdir()
            if path.suffix.lower() in {".lua", ".otmod"}
            and path.name not in LOCAL_SOURCE_ONLY_HELPER_FILES
        ),
        key=lambda path: path.name,
    )
    for path in helper_files:
        if _is_reparse(path):
            raise ContractError("helper_reparse_file_rejected")
        if not path.is_file():
            raise ContractError(f"regular_file_required:{path.name}")
    sources.extend((f"mods/ctoa_otclient/{path.name}", path) for path in helper_files)
    if not 1 <= len(sources) <= MAX_HELPER_FILES:
        raise ContractError("helper_file_count_invalid")
    _require_tracked_package_sources(sources)
    return sources


def _helper_version() -> str:
    metadata = _read_regular_file(HELPER_SOURCE_PATH / "ctoa_otclient.otmod").decode(
        "utf-8"
    )
    match = re.search(r"(?m)^\s*version:\s*v?([0-9]+\.[0-9]+\.[0-9]+)\s*$", metadata)
    if not match:
        raise ContractError("helper_version_invalid")
    return f"v{match.group(1)}"


def _sanitize_helper_manifest() -> dict[str, Any]:
    sanitized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for package_path, source_path in _package_sources():
        relative = _safe_relative_path(package_path)
        if relative in seen:
            raise ContractError("helper_file_duplicate")
        seen.add(relative)
        if _is_reparse(source_path):
            raise ContractError("helper_reparse_file_rejected")
        raw_file = _read_regular_file(source_path, max_bytes=MAX_HELPER_FILE_BYTES)
        sanitized.append(
            {
                "path": relative,
                "bytes": len(raw_file),
                "sha256": raw_sha256(raw_file),
            }
        )

    sanitized.sort(key=lambda item: item["path"])
    return {
        "schema_version": "ctoa.p14-helper-source-manifest.v1",
        "helper_version": _helper_version(),
        "file_count": len(sanitized),
        "files": sanitized,
    }


def _validate_roadmap_state(payload: dict[str, Any]) -> None:
    authority = payload.get("authority")
    summary = payload.get("summary")
    warnings = payload.get("warnings")
    if (
        payload.get("schema_version") != "ctoa.roadmap-state.v2"
        or payload.get("status") != "ready"
        or payload.get("readiness_status") not in {"ready", "awaiting_external"}
        or payload.get("phase") != "P13"
        or payload.get("phase_status") != "runtime_evidence_ready"
        or payload.get("next_phase") != "P14"
        or payload.get("freshness_status") != "current"
        or payload.get("tamper_status") != "passed"
        or payload.get("blockers") != []
        or not isinstance(warnings, list)
        or not isinstance(authority, dict)
        or not isinstance(summary, dict)
    ):
        raise ContractError("roadmap_state_not_p14_ready")
    if any(
        authority.get(key) is not expected
        for key, expected in {
            "runtime_executor_added": False,
            "runtime_actions": False,
            "live_authority": False,
            "p12_heal_friend_reopened": False,
            "runtime_mcp_write_tool_enabled": False,
            "roadmap_refresh_tool_enabled": True,
        }.items()
    ):
        raise ContractError("roadmap_state_authority_invalid")
    if authority.get("roadmap_refresh_risk_class") != "safe_write":
        raise ContractError("roadmap_state_refresh_risk_invalid")
    if authority.get("control_center_mode") != "read_only" or authority.get(
        "allowed_output_paths"
    ) != [
        "AI/generated/ROADMAP_STATE.json",
        "AI/generated/ROADMAP_STATE.md",
        "runtime/control-center/action-audit.jsonl",
    ]:
        raise ContractError("roadmap_state_refresh_boundary_invalid")
    allowed_warnings = {
        "control_center_preflight_pending",
        "runtime_module_gates_pending",
        "p14_runner_preflight_pending",
        "p14_runner_preflight_invalid",
    }
    if (
        any(item not in allowed_warnings for item in warnings)
        or (payload.get("readiness_status") == "ready" and warnings)
        or (payload.get("readiness_status") == "awaiting_external" and not warnings)
    ):
        raise ContractError("roadmap_state_readiness_invalid")
    if (
        summary.get("runtime_authority_count") != 0
        or summary.get("live_authority_count") != 0
    ):
        raise ContractError("roadmap_state_authority_count_invalid")
    expected_state_sha = payload.get("state_sha256")
    basis = {key: value for key, value in payload.items() if key != "state_sha256"}
    if not isinstance(
        expected_state_sha, str
    ) or expected_state_sha != canonical_sha256(basis):
        raise ContractError("roadmap_state_sha256_invalid")


def _embedded_artifact(
    name: str, schema_version: str, payload: dict[str, Any]
) -> dict[str, Any]:
    encoded = canonical_bytes(payload)
    return {
        "name": name,
        "schema_version": schema_version,
        "media_type": "application/json",
        "bytes": len(encoded),
        "sha256": raw_sha256(encoded),
        "payload": payload,
    }


def _git_state() -> tuple[str, bool]:
    revision = (
        subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
        .stdout.strip()
        .lower()
    )
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    ).stdout.strip()
    if not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ContractError("git_revision_invalid")
    return revision, not bool(dirty)


def build_source_provenance() -> dict[str, Any]:
    """Emit the fixed-package provenance sidecar for a clean Git checkout.

    Docker test images intentionally omit ``.git``.  The CI host creates this
    bounded sidecar before image construction, then injects it into the test
    stage only.  A guest or normal checkout must still use its Git index; it
    cannot select this fallback while its metadata exists.
    """

    try:
        repository_root = ROOT.resolve(strict=True)
    except OSError as exc:
        raise ContractError("helper_tracking_unavailable") from exc
    if not _git_metadata_is_present(repository_root):
        raise ContractError("helper_tracking_unavailable")

    sources = _package_sources()
    _, indexed_sources = _package_source_index(sources)
    revision, clean = _git_state()
    if not clean:
        raise ContractError("source_checkout_not_clean")

    files: list[dict[str, Any]] = []
    for package_path in sorted(indexed_sources):
        source_relative, source_path = indexed_sources[package_path]
        raw = _read_regular_file(source_path, max_bytes=MAX_HELPER_FILE_BYTES)
        files.append(
            {
                "package_path": package_path,
                "source_path": source_relative,
                "bytes": len(raw),
                "sha256": raw_sha256(raw),
            }
        )
    return {
        "schema_version": SOURCE_PROVENANCE_SCHEMA,
        "source_revision": revision,
        "file_count": len(files),
        "files": files,
    }


def _signing_material() -> tuple[bytes, str]:
    raw_key = os.environ.get(SIGNING_KEY_ENV, "")
    key_id = os.environ.get(SIGNING_KEY_ID_ENV, "")
    key = raw_key.encode("utf-8")
    if not 32 <= len(key) <= 4096:
        raise ContractError("signing_key_missing_or_too_short")
    if not SAFE_ID_RE.fullmatch(key_id):
        raise ContractError("signing_key_id_invalid")
    return key, key_id


def _signature_value(payload: dict[str, Any], key: bytes) -> str:
    unsigned = copy.deepcopy(payload)
    signature = unsigned.get("signature")
    if not isinstance(signature, dict):
        raise ContractError("signature_object_missing")
    signature["value"] = ""
    return hmac.new(key, canonical_bytes(unsigned), hashlib.sha256).hexdigest()


def _apply_signature(payload: dict[str, Any], key: bytes) -> None:
    payload["signature"]["value"] = _signature_value(payload, key)


def _verify_signature(payload: dict[str, Any], key: bytes, key_id: str) -> None:
    signature = payload.get("signature")
    if not isinstance(signature, dict) or signature.get("algorithm") != "hmac-sha256":
        raise ContractError("signature_contract_invalid")
    if signature.get("key_id") != key_id:
        raise ContractError("signature_key_id_mismatch")
    actual = signature.get("value")
    if not isinstance(actual, str) or not hmac.compare_digest(
        actual, _signature_value(payload, key)
    ):
        raise ContractError("signature_mismatch")


def build_request(
    *,
    revision: str,
    generated_at: str,
    key: bytes,
    key_id: str,
) -> dict[str, Any]:
    roadmap_raw = _read_regular_file(ROADMAP_STATE_PATH)
    roadmap = load_strict_json(ROADMAP_STATE_PATH)
    _validate_roadmap_state(roadmap)
    helper = _sanitize_helper_manifest()
    rollback = {
        "schema_version": "ctoa.p14-rollback-baseline.v1",
        "helper_version": helper["helper_version"],
        "file_count": helper["file_count"],
        "files": copy.deepcopy(helper["files"]),
    }
    helper_sha = canonical_sha256(helper)
    rollback_sha = canonical_sha256(rollback)
    request_seed = {
        "revision": revision,
        "helper_manifest_sha256": helper_sha,
        "roadmap_state_sha256": roadmap["state_sha256"],
        "rollback_manifest_sha256": rollback_sha,
    }
    request: dict[str, Any] = {
        "schema_version": "ctoa.p14-runner-request.v1",
        "generated_at": generated_at,
        "request_id": f"p14-{canonical_sha256(request_seed)[:16]}",
        "phase": "P14",
        "status": "ready_for_independent_runner",
        "source": {
            "revision": revision,
            "helper_version": helper["helper_version"],
            "helper_manifest_sha256": helper_sha,
            "roadmap_state_sha256": roadmap["state_sha256"],
            "roadmap_file_sha256": raw_sha256(roadmap_raw),
            "source_file_count": helper["file_count"],
        },
        "runner_contract": {
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
        },
        "replay_checks": CHECK_IDS,
        "artifacts": [
            _embedded_artifact("roadmap_state", "ctoa.roadmap-state.v2", roadmap),
            _embedded_artifact(
                "helper_source_manifest", "ctoa.p14-helper-source-manifest.v1", helper
            ),
            _embedded_artifact(
                "rollback_baseline", "ctoa.p14-rollback-baseline.v1", rollback
            ),
        ],
        "canary": {
            "mode": "artifact_manifest_only",
            "status": "planned_not_executed",
            "max_changed_files": 1,
            "promotion_approved": False,
            "external_approval_required": True,
        },
        "rollback": {
            "mode": "deterministic_manifest_replay",
            "status": "required",
            "baseline_manifest_sha256": rollback_sha,
            "live_rollback_allowed": False,
        },
        "authority": copy.deepcopy(AUTHORITY),
        "signature": {"algorithm": "hmac-sha256", "key_id": key_id, "value": "0" * 64},
    }
    _apply_signature(request, key)
    validate_schema(request, REQUEST_SCHEMA_PATH)
    return request


def _artifact_map(request: dict[str, Any]) -> dict[str, dict[str, Any]]:
    artifacts = request.get("artifacts")
    if not isinstance(artifacts, list):
        raise ContractError("artifacts_invalid")
    result: dict[str, dict[str, Any]] = {}
    for artifact in artifacts:
        if not isinstance(artifact, dict) or not isinstance(artifact.get("name"), str):
            raise ContractError("artifact_invalid")
        name = artifact["name"]
        if name in result:
            raise ContractError("artifact_duplicate")
        payload = artifact.get("payload")
        if not isinstance(payload, dict):
            raise ContractError("artifact_payload_invalid")
        encoded = canonical_bytes(payload)
        if artifact.get("bytes") != len(encoded) or artifact.get(
            "sha256"
        ) != raw_sha256(encoded):
            raise ContractError(f"artifact_hash_mismatch:{name}")
        result[name] = artifact
    return result


def _validate_manifest_payload(payload: dict[str, Any], schema_version: str) -> None:
    if payload.get("schema_version") != schema_version:
        raise ContractError("embedded_manifest_schema_invalid")
    version = payload.get("helper_version")
    entries = payload.get("files")
    if not isinstance(version, str) or not VERSION_RE.fullmatch(version):
        raise ContractError("embedded_manifest_version_invalid")
    if (
        not isinstance(entries, list)
        or payload.get("file_count") != len(entries)
        or not entries
    ):
        raise ContractError("embedded_manifest_count_invalid")
    paths: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"path", "bytes", "sha256"}:
            raise ContractError("embedded_manifest_entry_invalid")
        paths.append(_safe_relative_path(entry.get("path")))
        size = entry.get("bytes")
        digest = entry.get("sha256")
        if (
            not isinstance(size, int)
            or isinstance(size, bool)
            or not 1 <= size <= MAX_HELPER_FILE_BYTES
        ):
            raise ContractError("embedded_manifest_bytes_invalid")
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            raise ContractError("embedded_manifest_sha_invalid")
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise ContractError("embedded_manifest_order_invalid")


def _rollback_replay(payload: dict[str, Any]) -> tuple[str, str, str]:
    baseline_sha = canonical_sha256(payload)
    canary = copy.deepcopy(payload)
    original = canary["files"][0]["sha256"]
    canary["files"][0]["sha256"] = "0" * 64 if original != "0" * 64 else "1" * 64
    canary_sha = canonical_sha256(canary)
    restored = copy.deepcopy(payload)
    restored_sha = canonical_sha256(restored)
    if canary_sha == baseline_sha or restored_sha != baseline_sha:
        raise ContractError("rollback_manifest_replay_failed")
    return baseline_sha, canary_sha, restored_sha


def verify_request(
    request: dict[str, Any],
    *,
    key: bytes,
    key_id: str,
    runner_id: str,
    source_revision: str,
    clean_checkout: bool,
    generated_at: str,
) -> dict[str, Any]:
    if not SAFE_ID_RE.fullmatch(runner_id):
        raise ContractError("runner_id_invalid")
    validate_schema(request, REQUEST_SCHEMA_PATH)
    _verify_signature(request, key, key_id)
    artifacts = _artifact_map(request)

    roadmap = artifacts["roadmap_state"]["payload"]
    _validate_roadmap_state(roadmap)
    local_roadmap_raw = _read_regular_file(ROADMAP_STATE_PATH)
    local_roadmap = load_strict_json(ROADMAP_STATE_PATH)
    _validate_roadmap_state(local_roadmap)
    if (
        request["source"]["roadmap_state_sha256"] != roadmap["state_sha256"]
        or request["source"]["roadmap_file_sha256"] != raw_sha256(local_roadmap_raw)
        or local_roadmap != roadmap
    ):
        raise ContractError("roadmap_source_binding_invalid")

    helper = artifacts["helper_source_manifest"]["payload"]
    _validate_manifest_payload(helper, "ctoa.p14-helper-source-manifest.v1")
    local_helper = _sanitize_helper_manifest()
    if (
        request["source"]["helper_manifest_sha256"] != canonical_sha256(helper)
        or request["source"]["source_file_count"] != helper["file_count"]
        or request["source"]["helper_version"] != helper["helper_version"]
        or local_helper != helper
    ):
        raise ContractError("helper_source_binding_invalid")

    rollback = artifacts["rollback_baseline"]["payload"]
    _validate_manifest_payload(rollback, "ctoa.p14-rollback-baseline.v1")
    baseline_sha, canary_sha, restored_sha = _rollback_replay(rollback)
    if (
        request["rollback"]["baseline_manifest_sha256"] != baseline_sha
        or rollback["helper_version"] != helper["helper_version"]
        or rollback["files"] != helper["files"]
    ):
        raise ContractError("rollback_source_binding_invalid")

    revision_match = source_revision == request["source"]["revision"]
    blockers: list[str] = []
    if not revision_match:
        blockers.append("runner_revision_mismatch")
    if not clean_checkout:
        blockers.append("runner_checkout_not_clean")
    checks = [
        {
            "id": "request_schema",
            "status": "passed",
            "detail": "request matches the versioned P14 schema",
        },
        {
            "id": "bundle_signature",
            "status": "passed",
            "detail": "HMAC-SHA256 signature and trusted key id match",
        },
        {
            "id": "roadmap_state_replay",
            "status": "passed",
            "detail": "P13 terminal state permits only the P14 handoff",
        },
        {
            "id": "helper_manifest_replay",
            "status": "passed",
            "detail": "sanitized helper manifest is ordered and hash-bound",
        },
        {
            "id": "rollback_manifest_replay",
            "status": "passed",
            "detail": "simulated canary restores the exact baseline manifest hash",
        },
    ]
    request_sha = canonical_sha256(request)
    result_seed = {
        "request_sha256": request_sha,
        "runner_id": runner_id,
        "revision": source_revision,
    }
    result: dict[str, Any] = {
        "schema_version": "ctoa.p14-runner-result.v1",
        "generated_at": generated_at,
        "result_id": f"p14-result-{canonical_sha256(result_seed)[:16]}",
        "request_id": request["request_id"],
        "request_sha256": request_sha,
        "status": "passed" if not blockers else "blocked",
        "runner": {
            "runner_id": runner_id,
            "source_revision": source_revision,
            "revision_match": revision_match,
            "clean_checkout_proven": clean_checkout,
            "artifact_only": True,
            "isolated_display": True,
            "operator_workstation_focus_used": False,
            "operator_workstation_input_used": False,
            "network_dispatch_used": False,
            "live_client_accessed": False,
        },
        "checks": checks,
        "canary": {
            "status": "not_executed",
            "mode": "artifact_manifest_only",
            "changed_file_count": 0,
            "promotion_approved": False,
            "external_approval_required": True,
        },
        "rollback": {
            "status": "manifest_replay_passed",
            "baseline_manifest_sha256": baseline_sha,
            "simulated_canary_manifest_sha256": canary_sha,
            "restored_manifest_sha256": restored_sha,
            "live_rollback_tested": False,
        },
        "authority": copy.deepcopy(AUTHORITY),
        "blockers": blockers,
        "signature": {"algorithm": "hmac-sha256", "key_id": key_id, "value": "0" * 64},
    }
    _apply_signature(result, key)
    validate_schema(result, RESULT_SCHEMA_PATH)
    return result


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _artifact_root(value: str) -> Path:
    raw_candidate = Path(value)
    if not raw_candidate.is_absolute():
        raw_candidate = ROOT / raw_candidate
    current = Path(raw_candidate.anchor)
    for part in raw_candidate.parts[1:]:
        current /= part
        if current.exists() and _is_reparse(current):
            raise ContractError("artifact_root_reparse_rejected")
    if raw_candidate.exists() and (
        not raw_candidate.is_dir() or _is_reparse(raw_candidate)
    ):
        raise ContractError("artifact_root_invalid")
    return raw_candidate.resolve(strict=False)


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if _is_reparse(path.parent):
        raise ContractError("artifact_root_reparse_rejected")
    if path.exists() and (not path.is_file() or _is_reparse(path)):
        raise ContractError("artifact_output_invalid")
    encoded = (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True).encode(
            "utf-8"
        )
        + b"\n"
    )
    with tempfile.NamedTemporaryFile(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
    ) as handle:
        temporary = Path(handle.name)
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _print(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def _emit_source_provenance(_: argparse.Namespace) -> int:
    _print(build_source_provenance())
    return 0


def _prepare(args: argparse.Namespace) -> int:
    blockers: list[str] = []
    source_summary: dict[str, Any] = {}
    try:
        roadmap = load_strict_json(ROADMAP_STATE_PATH)
        _validate_roadmap_state(roadmap)
        helper = _sanitize_helper_manifest()
        source_summary = {
            "helper_version": helper["helper_version"],
            "source_file_count": helper["file_count"],
            "roadmap_state_sha256": roadmap["state_sha256"],
        }
    except ContractError as exc:
        blockers.append(str(exc))
    try:
        revision, clean = _git_state()
    except (ContractError, OSError, subprocess.SubprocessError):
        revision, clean = "", False
        blockers.append("git_state_unavailable")
    if not clean:
        blockers.append("source_checkout_not_clean")
    try:
        key, key_id = _signing_material()
    except ContractError as exc:
        key, key_id = b"", ""
        blockers.append(str(exc))

    if args.dry_run or blockers:
        _print(
            {
                "schema_version": 1,
                "action": "p14-independent-runner-prepare",
                "status": "dry_run" if args.dry_run else "blocked",
                "dry_run": bool(args.dry_run),
                "would_write": ["request.json"],
                "blockers": sorted(set(blockers)),
                "source": source_summary,
                "authority": AUTHORITY,
            }
        )
        return 0 if args.dry_run else 2

    request = build_request(
        revision=revision, generated_at=_utc_now(), key=key, key_id=key_id
    )
    root = _artifact_root(args.artifact_root)
    output = root / "request.json"
    _write_json_atomic(output, request)
    _print(
        {
            "schema_version": 1,
            "action": "p14-independent-runner-prepare",
            "status": "completed",
            "request_id": request["request_id"],
            "request_sha256": canonical_sha256(request),
            "output": "request.json",
            "authority": AUTHORITY,
        }
    )
    return 0


def _verify(args: argparse.Namespace) -> int:
    key, key_id = _signing_material()
    root = _artifact_root(args.artifact_root)
    request = load_strict_json(root / "request.json")
    revision, clean = _git_state()
    result = verify_request(
        request,
        key=key,
        key_id=key_id,
        runner_id=args.runner_id,
        source_revision=revision,
        clean_checkout=clean,
        generated_at=_utc_now(),
    )
    _write_json_atomic(root / "result.json", result)
    _print(
        {
            "schema_version": 1,
            "action": "p14-independent-runner-verify",
            "status": result["status"],
            "request_id": result["request_id"],
            "result_id": result["result_id"],
            "output": "result.json",
            "blockers": result["blockers"],
            "authority": AUTHORITY,
        }
    )
    return 0 if result["status"] == "passed" else 2


def verify_result_bundle(
    request: dict[str, Any], result: dict[str, Any], *, key: bytes, key_id: str
) -> None:
    validate_schema(request, REQUEST_SCHEMA_PATH)
    validate_schema(result, RESULT_SCHEMA_PATH)
    _verify_signature(request, key, key_id)
    _verify_signature(result, key, key_id)
    if (
        result.get("request_id") != request.get("request_id")
        or result.get("request_sha256") != canonical_sha256(request)
        or result.get("authority") != AUTHORITY
    ):
        raise ContractError("result_request_binding_invalid")
    checks = result.get("checks")
    if (
        not isinstance(checks, list)
        or [check.get("id") for check in checks] != CHECK_IDS
    ):
        raise ContractError("result_check_order_invalid")
    if result.get("status") == "passed" and (
        result.get("blockers") != []
        or any(check.get("status") != "passed" for check in checks)
        or result.get("runner", {}).get("revision_match") is not True
        or result.get("runner", {}).get("clean_checkout_proven") is not True
        or result.get("rollback", {}).get("status") != "manifest_replay_passed"
    ):
        raise ContractError("passed_result_contract_invalid")


def _verify_result(args: argparse.Namespace) -> int:
    key, key_id = _signing_material()
    root = _artifact_root(args.artifact_root)
    request = load_strict_json(root / "request.json")
    result = load_strict_json(root / "result.json")
    verify_result_bundle(request, result, key=key, key_id=key_id)
    _print(
        {
            "schema_version": 1,
            "action": "p14-independent-runner-verify-result",
            "status": result["status"],
            "request_id": result["request_id"],
            "result_id": result["result_id"],
            "blockers": result["blockers"],
            "authority": AUTHORITY,
        }
    )
    return 0 if result["status"] == "passed" else 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    provenance = subparsers.add_parser(
        "emit-source-provenance",
        help="Emit fixed tracked-source provenance for the Docker test stage.",
    )
    provenance.set_defaults(handler=_emit_source_provenance)

    prepare = subparsers.add_parser(
        "prepare", help="Create a signed fixed-scope runner request."
    )
    prepare.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    prepare.add_argument("--dry-run", action="store_true")
    prepare.set_defaults(handler=_prepare)

    verify = subparsers.add_parser(
        "verify", help="Verify request artifacts and emit a signed runner result."
    )
    verify.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    verify.add_argument("--runner-id", required=True)
    verify.set_defaults(handler=_verify)

    verify_result = subparsers.add_parser(
        "verify-result", help="Verify the signed result and its exact request binding."
    )
    verify_result.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    verify_result.set_defaults(handler=_verify_result)
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        return int(args.handler(args))
    except ContractError as exc:
        _print(
            {
                "schema_version": 1,
                "status": "blocked",
                "blockers": [str(exc)],
                "authority": AUTHORITY,
            }
        )
        return 2
    except (OSError, subprocess.SubprocessError):
        _print(
            {
                "schema_version": 1,
                "status": "blocked",
                "blockers": ["bounded_io_or_git_operation_failed"],
                "authority": AUTHORITY,
            }
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
