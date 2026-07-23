#!/usr/bin/env python3
"""Run the fixed, file-only P14 sandbox canary and rollback rehearsal.

This module deliberately operates on the package paths declared by the signed
P14 helper manifest.  It does not accept a client path, a command, a promotion
flag, or a caller-selected output path.  The public CLI has one action only:
``run --run-id <safe-id>``.  A one-time, fixed ``stage-bundle`` command can
build the reviewed package before the appliance is snapshotted; it takes no
paths, commands, revisions, or external input.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
if os.name == "nt":
    # The guest broker never stages, mutates, or emits evidence under the source
    # checkout.  These roots are provisioned with separate ACLs in the golden VM.
    DEFAULT_RUNS_ROOT = Path(r"C:\P14Runner\runs")
    DEFAULT_EVIDENCE_ROOT = Path(r"C:\P14Runner\evidence")
    DEFAULT_STAGED_PACKAGE_ROOT = Path(r"C:\P14Runner\bundle")
    DEFAULT_SOURCE_MANIFEST_PATH = Path(r"C:\P14Runner\bundle\helper-manifest.json")
else:
    # Non-Windows defaults keep local fixtures isolated from the checked-in helper
    # source while allowing the pure-Python contract tests to run anywhere.
    DEFAULT_RUNS_ROOT = ROOT / "runtime" / "p14_sandbox_runs"
    DEFAULT_EVIDENCE_ROOT = ROOT / "runtime" / "p14_sandbox_evidence"
    DEFAULT_STAGED_PACKAGE_ROOT = ROOT / "runtime" / "p14_staged_helper_package"
    DEFAULT_SOURCE_MANIFEST_PATH = ROOT / "runtime" / "p14_staged_helper_manifest.json"

RUN_ID_RE = re.compile(r"^[a-f0-9]{16}$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
VERSION_RE = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+$")

MAX_FILES = 256
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_JSON_BYTES = 2 * 1024 * 1024
SOURCE_MANIFEST_SCHEMA = "ctoa.p14-helper-source-manifest.v1"
SANDBOX_MANIFEST_SCHEMA = "ctoa.p14-sandbox-manifest.v1"
STATE_SCHEMA = "ctoa.p14-sandbox-state.v1"
REHEARSAL_SCHEMA = "ctoa.p14-sandbox-rehearsal.v1"
CANARY_MARKER_RELATIVE_PATH = ".ctoa-p14-canary.json"


class SandboxError(ValueError):
    """Raised when the fixed P14 sandbox boundary is violated."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise SandboxError(f"duplicate_json_key:{key}")
        value[key] = item
    return value


def _reject_constant(value: str) -> None:
    raise SandboxError(f"non_finite_json_number:{value}")


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


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _is_reparse(path: Path) -> bool:
    info = path.lstat()
    attributes = getattr(info, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return path.is_symlink() or bool(attributes & reparse_flag)


def _require_no_reparse(path: Path, code: str) -> None:
    try:
        if _is_reparse(path):
            raise SandboxError(f"reparse_point_rejected:{code}")
    except FileNotFoundError as exc:
        raise SandboxError(f"path_missing:{code}") from exc


def _require_directory(path: Path, code: str, *, create: bool = False) -> Path:
    if create:
        path.mkdir(parents=True, exist_ok=True)
    if not path.exists() or not path.is_dir():
        raise SandboxError(f"directory_required:{code}")
    _require_no_reparse(path, code)
    return path.resolve(strict=True)


def _require_regular_unlinked_file(path: Path, code: str) -> bytes:
    try:
        info = path.lstat()
    except FileNotFoundError as exc:
        raise SandboxError(f"file_missing:{code}") from exc
    if _is_reparse(path):
        raise SandboxError(f"reparse_point_rejected:{code}")
    if not stat.S_ISREG(info.st_mode):
        raise SandboxError(f"regular_file_required:{code}")
    if getattr(info, "st_nlink", 1) != 1:
        raise SandboxError(f"hardlink_rejected:{code}")
    if info.st_size < 1 or info.st_size > MAX_FILE_BYTES:
        raise SandboxError(f"file_size_invalid:{code}")
    raw = path.read_bytes()
    after = path.lstat()
    stable = (
        after.st_size == info.st_size == len(raw)
        and after.st_mtime_ns == info.st_mtime_ns
        and getattr(after, "st_ino", 0) == getattr(info, "st_ino", 0)
    )
    if not stable:
        raise SandboxError(f"file_changed_during_read:{code}")
    return raw


def _require_existing_components_no_reparse(path: Path, code: str) -> None:
    """Reject a link/reparse point in every existing path component."""

    absolute = Path(path).absolute()
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        if current.exists():
            _require_no_reparse(current, code)


def _safe_run_id(value: str) -> str:
    if not isinstance(value, str) or not RUN_ID_RE.fullmatch(value):
        raise SandboxError("run_id_invalid")
    return value


def _safe_helper_relative_path(value: Any) -> str:
    if not isinstance(value, str) or not value or len(value) > 240 or "\\" in value:
        raise SandboxError("helper_path_invalid")
    candidate = PurePosixPath(value)
    if candidate.is_absolute() or "." in candidate.parts or ".." in candidate.parts:
        raise SandboxError("helper_path_invalid")
    if value == "ctoa_project_loader.lua":
        return value
    if (
        len(candidate.parts) != 3
        or candidate.parts[0] != "mods"
        or candidate.parts[1] not in {"ctoa_chooser", "ctoa_otclient"}
        or candidate.suffix.lower() not in {".lua", ".otmod"}
    ):
        raise SandboxError("helper_path_outside_allowlist")
    return candidate.as_posix()


def validate_source_manifest(value: Mapping[str, Any]) -> dict[str, Any]:
    """Strictly normalize the current P14 helper source manifest."""

    if not isinstance(value, Mapping) or set(value) != {
        "schema_version",
        "helper_version",
        "file_count",
        "files",
    }:
        raise SandboxError("source_manifest_invalid")
    if value.get("schema_version") != SOURCE_MANIFEST_SCHEMA:
        raise SandboxError("source_manifest_schema_invalid")
    helper_version = value.get("helper_version")
    files = value.get("files")
    if not isinstance(helper_version, str) or not VERSION_RE.fullmatch(helper_version):
        raise SandboxError("source_manifest_version_invalid")
    if (
        not isinstance(files, list)
        or not 1 <= len(files) <= MAX_FILES
        or value.get("file_count") != len(files)
    ):
        raise SandboxError("source_manifest_file_count_invalid")

    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in files:
        if not isinstance(item, Mapping) or set(item) != {"path", "bytes", "sha256"}:
            raise SandboxError("source_manifest_entry_invalid")
        relative = _safe_helper_relative_path(item.get("path"))
        size = item.get("bytes")
        digest = item.get("sha256")
        if (
            type(size) is not int
            or not 1 <= size <= MAX_FILE_BYTES
            or not isinstance(digest, str)
            or not SHA256_RE.fullmatch(digest)
            or relative in seen
        ):
            raise SandboxError("source_manifest_entry_invalid")
        seen.add(relative)
        normalized.append({"path": relative, "bytes": size, "sha256": digest})
    if [item["path"] for item in normalized] != sorted(seen):
        raise SandboxError("source_manifest_order_invalid")
    return {
        "schema_version": SOURCE_MANIFEST_SCHEMA,
        "helper_version": helper_version,
        "file_count": len(normalized),
        "files": normalized,
    }


def _path_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=True))
    except (OSError, RuntimeError, ValueError):
        return False
    return True


def _run_paths(runs_root: Path, run_id: str) -> tuple[Path, Path, Path]:
    run_id = _safe_run_id(run_id)
    _require_existing_components_no_reparse(runs_root, "runs_root")
    runs = _require_directory(runs_root, "runs_root", create=True)
    run_root = runs / run_id
    if not _path_within(run_root, runs) or run_root.parent != runs:
        raise SandboxError("run_root_outside_allowlist")
    sandbox_root = run_root / "sandbox"
    state_path = run_root / "state.json"
    return run_root, sandbox_root, state_path


def _relative_path(root: Path, value: str) -> Path:
    relative = PurePosixPath(value)
    destination = root.joinpath(*relative.parts)
    if not _path_within(destination, root):
        raise SandboxError("helper_path_outside_allowlist")
    return destination


def _write_bytes_atomic(path: Path, raw: bytes) -> None:
    parent = path.parent
    _require_directory(parent, "output_parent", create=True)
    _require_existing_components_no_reparse(parent, "output_parent")
    if path.exists() and (not path.is_file() or _is_reparse(path)):
        raise SandboxError("output_path_invalid")
    with tempfile.NamedTemporaryFile(
        mode="wb", dir=parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
    ) as handle:
        temporary = Path(handle.name)
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        if temporary.lstat().st_nlink != 1 or _is_reparse(temporary):
            raise SandboxError("temporary_output_invalid")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    _require_regular_unlinked_file(path, "output")


def _write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    _write_bytes_atomic(
        path,
        json.dumps(
            value, ensure_ascii=False, allow_nan=False, indent=2, sort_keys=True
        ).encode("utf-8")
        + b"\n",
    )


def _load_json(path: Path, code: str) -> dict[str, Any]:
    raw = _require_regular_unlinked_file(path, code)
    if len(raw) > MAX_JSON_BYTES:
        raise SandboxError(f"json_too_large:{code}")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SandboxError(f"json_invalid:{code}") from exc
    if not isinstance(value, dict):
        raise SandboxError(f"json_object_required:{code}")
    return value


def _walk_regular_files(root: Path) -> dict[str, dict[str, Any]]:
    """Return an exact manifest while refusing every link and special file."""

    _require_directory(root, "sandbox_root")
    result: dict[str, dict[str, Any]] = {}
    stack = [root]
    while stack:
        directory = stack.pop()
        _require_no_reparse(directory, "sandbox_directory")
        with os.scandir(directory) as entries:
            for entry in entries:
                path = Path(entry.path)
                try:
                    info = path.lstat()
                except FileNotFoundError as exc:
                    raise SandboxError("sandbox_entry_changed_during_walk") from exc
                if _is_reparse(path):
                    raise SandboxError("reparse_point_rejected:sandbox_entry")
                if stat.S_ISDIR(info.st_mode):
                    stack.append(path)
                    continue
                if not stat.S_ISREG(info.st_mode):
                    raise SandboxError("regular_file_required:sandbox_entry")
                if getattr(info, "st_nlink", 1) != 1:
                    raise SandboxError("hardlink_rejected:sandbox_entry")
                relative = path.relative_to(root).as_posix()
                raw = _require_regular_unlinked_file(path, "sandbox_entry")
                result[relative] = {
                    "path": relative,
                    "bytes": len(raw),
                    "sha256": _sha256(raw),
                }
    return result


def _sandbox_manifest(
    sandbox_root: Path,
    *,
    source_manifest_sha256: str,
    allowed_paths: set[str],
) -> dict[str, Any]:
    entries = _walk_regular_files(sandbox_root)
    if set(entries) != allowed_paths:
        raise SandboxError("sandbox_manifest_path_set_invalid")
    files = [entries[path] for path in sorted(entries)]
    return {
        "schema_version": SANDBOX_MANIFEST_SCHEMA,
        "source_manifest_sha256": source_manifest_sha256,
        "file_count": len(files),
        "files": files,
    }


def _read_state(run_root: Path, state_path: Path) -> dict[str, Any]:
    state = _load_json(state_path, "state")
    required = {
        "schema_version",
        "run_id",
        "status",
        "source_manifest_sha256",
        "baseline_manifest_sha256",
        "rollback_baseline_manifest_sha256",
        "changed_manifest_sha256",
        "marker_sha256",
    }
    if set(state) != required or state.get("schema_version") != STATE_SCHEMA:
        raise SandboxError("state_invalid")
    if not RUN_ID_RE.fullmatch(str(state.get("run_id") or "")):
        raise SandboxError("state_invalid")
    if not _path_within(run_root, run_root.parent):
        raise SandboxError("state_invalid")
    for field in (
        "source_manifest_sha256",
        "baseline_manifest_sha256",
        "rollback_baseline_manifest_sha256",
    ):
        if not isinstance(state.get(field), str) or not SHA256_RE.fullmatch(
            state[field]
        ):
            raise SandboxError("state_invalid")
    for field in ("changed_manifest_sha256", "marker_sha256"):
        if state.get(field) is not None and (
            not isinstance(state[field], str) or not SHA256_RE.fullmatch(state[field])
        ):
            raise SandboxError("state_invalid")
    if state.get("status") not in {"prepared", "canary_applied", "rollback_verified"}:
        raise SandboxError("state_invalid")
    return state


def _baseline_path(run_root: Path) -> Path:
    return run_root / "baseline-manifest.json"


def _rollback_baseline_manifest(source_manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Recreate the signed foundation baseline without trusting a copied hash."""

    return {
        "schema_version": "ctoa.p14-rollback-baseline.v1",
        "helper_version": source_manifest["helper_version"],
        "file_count": source_manifest["file_count"],
        "files": [dict(item) for item in source_manifest["files"]],
    }


def _changed_path(run_root: Path) -> Path:
    return run_root / "changed-manifest.json"


def _read_manifest(path: Path, code: str) -> dict[str, Any]:
    manifest = _load_json(path, code)
    if (
        set(manifest)
        != {"schema_version", "source_manifest_sha256", "file_count", "files"}
        or manifest.get("schema_version") != SANDBOX_MANIFEST_SCHEMA
        or not isinstance(manifest.get("source_manifest_sha256"), str)
        or not SHA256_RE.fullmatch(manifest["source_manifest_sha256"])
    ):
        raise SandboxError(f"manifest_invalid:{code}")
    files = manifest.get("files")
    if not isinstance(files, list) or manifest.get("file_count") != len(files):
        raise SandboxError(f"manifest_invalid:{code}")
    paths: list[str] = []
    for item in files:
        if not isinstance(item, Mapping) or set(item) != {"path", "bytes", "sha256"}:
            raise SandboxError(f"manifest_invalid:{code}")
        path_value = item.get("path")
        if path_value == CANARY_MARKER_RELATIVE_PATH:
            normalized = path_value
        else:
            normalized = _safe_helper_relative_path(path_value)
        if (
            type(item.get("bytes")) is not int
            or not 1 <= item["bytes"] <= MAX_FILE_BYTES
            or not isinstance(item.get("sha256"), str)
            or not SHA256_RE.fullmatch(item["sha256"])
        ):
            raise SandboxError(f"manifest_invalid:{code}")
        paths.append(normalized)
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise SandboxError(f"manifest_invalid:{code}")
    return {
        "schema_version": SANDBOX_MANIFEST_SCHEMA,
        "source_manifest_sha256": manifest["source_manifest_sha256"],
        "file_count": len(files),
        "files": [dict(item) for item in files],
    }


def prepare_sandbox(
    *,
    runs_root: Path,
    run_id: str,
    source_root: Path,
    source_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Create the immutable baseline as a complete, link-free package copy."""

    normalized_source_manifest = validate_source_manifest(source_manifest)
    source_manifest_sha256 = canonical_sha256(normalized_source_manifest)
    run_root, sandbox_root, state_path = _run_paths(Path(runs_root), run_id)
    if run_root.exists():
        raise SandboxError("run_already_exists")

    _require_existing_components_no_reparse(source_root, "source_root")
    source = _require_directory(Path(source_root), "source_root")
    if _path_within(source, run_root.parent) or _path_within(run_root.parent, source):
        raise SandboxError("source_root_overlaps_runs_root")

    run_root.mkdir(mode=0o700)
    _require_directory(run_root, "run_root")
    sandbox_root.mkdir(mode=0o700)
    _require_directory(sandbox_root, "sandbox_root")

    allowed_paths = {entry["path"] for entry in normalized_source_manifest["files"]}
    for entry in normalized_source_manifest["files"]:
        relative = entry["path"]
        source_path = _relative_path(source, relative)
        _require_existing_components_no_reparse(source_path.parent, "source_package")
        raw = _require_regular_unlinked_file(source_path, "source_package_file")
        if len(raw) != entry["bytes"] or _sha256(raw) != entry["sha256"]:
            raise SandboxError("source_manifest_binding_invalid")
        destination = _relative_path(sandbox_root, relative)
        _write_bytes_atomic(destination, raw)
        copied = _require_regular_unlinked_file(destination, "sandbox_copy")
        if copied != raw:
            raise SandboxError("sandbox_copy_binding_invalid")

    baseline = _sandbox_manifest(
        sandbox_root,
        source_manifest_sha256=source_manifest_sha256,
        allowed_paths=allowed_paths,
    )
    baseline_sha256 = canonical_sha256(baseline)
    rollback_baseline_sha256 = canonical_sha256(
        _rollback_baseline_manifest(normalized_source_manifest)
    )
    _write_json_atomic(_baseline_path(run_root), baseline)
    state = {
        "schema_version": STATE_SCHEMA,
        "run_id": run_id,
        "status": "prepared",
        "source_manifest_sha256": source_manifest_sha256,
        "baseline_manifest_sha256": baseline_sha256,
        "rollback_baseline_manifest_sha256": rollback_baseline_sha256,
        "changed_manifest_sha256": None,
        "marker_sha256": None,
    }
    _write_json_atomic(state_path, state)
    return {
        "run_id": run_id,
        "status": "prepared",
        "baseline_manifest_sha256": rollback_baseline_sha256,
        "sandbox_baseline_manifest_sha256": baseline_sha256,
        "source_manifest_sha256": source_manifest_sha256,
        "file_count": baseline["file_count"],
    }


def _load_baseline_for_run(
    runs_root: Path, run_id: str
) -> tuple[Path, Path, Path, dict[str, Any], dict[str, Any]]:
    run_root, sandbox_root, state_path = _run_paths(Path(runs_root), run_id)
    _require_directory(run_root, "run_root")
    _require_directory(sandbox_root, "sandbox_root")
    state = _read_state(run_root, state_path)
    if state["run_id"] != run_id:
        raise SandboxError("state_run_id_mismatch")
    baseline = _read_manifest(_baseline_path(run_root), "baseline_manifest")
    if (
        canonical_sha256(baseline) != state["baseline_manifest_sha256"]
        or baseline["source_manifest_sha256"] != state["source_manifest_sha256"]
    ):
        raise SandboxError("baseline_manifest_binding_invalid")
    return run_root, sandbox_root, state_path, state, baseline


def _manifest_paths(manifest: Mapping[str, Any]) -> set[str]:
    return {str(item["path"]) for item in manifest["files"]}


def _assert_current_manifest(
    sandbox_root: Path, *, expected: Mapping[str, Any], allow_marker: bool
) -> None:
    allowed = _manifest_paths(expected)
    if allow_marker:
        allowed.add(CANARY_MARKER_RELATIVE_PATH)
    observed = _sandbox_manifest(
        sandbox_root,
        source_manifest_sha256=str(expected["source_manifest_sha256"]),
        allowed_paths=allowed,
    )
    if canonical_sha256(observed) != canonical_sha256(expected):
        raise SandboxError("sandbox_manifest_drift")


def _marker_bytes(run_id: str, source_manifest_sha256: str) -> bytes:
    return canonical_bytes(
        {
            "run_id": run_id,
            "schema_version": "ctoa.p14-canary-marker.v1",
            "source_manifest_sha256": source_manifest_sha256,
        }
    ) + b"\n"


def apply_canary(*, runs_root: Path, run_id: str) -> dict[str, Any]:
    """Apply exactly one benign, sandbox-only marker file."""

    run_root, sandbox_root, state_path, state, baseline = _load_baseline_for_run(
        runs_root, run_id
    )
    if state["status"] != "prepared":
        raise SandboxError("canary_state_invalid")
    _assert_current_manifest(sandbox_root, expected=baseline, allow_marker=False)

    marker = sandbox_root / CANARY_MARKER_RELATIVE_PATH
    if marker.exists():
        raise SandboxError("canary_marker_already_exists")
    marker_raw = _marker_bytes(run_id, state["source_manifest_sha256"])
    _write_bytes_atomic(marker, marker_raw)
    changed = _sandbox_manifest(
        sandbox_root,
        source_manifest_sha256=state["source_manifest_sha256"],
        allowed_paths=_manifest_paths(baseline) | {CANARY_MARKER_RELATIVE_PATH},
    )
    changed_sha256 = canonical_sha256(changed)
    if changed_sha256 == state["baseline_manifest_sha256"]:
        raise SandboxError("canary_manifest_unchanged")
    changed_paths = _manifest_paths(changed) ^ _manifest_paths(baseline)
    if changed_paths != {CANARY_MARKER_RELATIVE_PATH}:
        raise SandboxError("canary_changed_path_invalid")
    baseline_files = {item["path"]: item for item in baseline["files"]}
    changed_files = {item["path"]: item for item in changed["files"]}
    if any(changed_files[path] != item for path, item in baseline_files.items()):
        raise SandboxError("canary_changed_file_invalid")
    _write_json_atomic(_changed_path(run_root), changed)
    state.update(
        {
            "status": "canary_applied",
            "changed_manifest_sha256": changed_sha256,
            "marker_sha256": _sha256(marker_raw),
        }
    )
    _write_json_atomic(state_path, state)
    return {
        "run_id": run_id,
        "status": "canary_applied",
        "baseline_manifest_sha256": state["rollback_baseline_manifest_sha256"],
        "sandbox_baseline_manifest_sha256": state["baseline_manifest_sha256"],
        "changed_manifest_sha256": changed_sha256,
        "changed_file_count": 1,
    }


def canary_health_check(*, runs_root: Path, run_id: str) -> dict[str, Any]:
    """Verify the physical sandbox state without launching or controlling a client."""

    run_root, sandbox_root, _, state, baseline = _load_baseline_for_run(
        runs_root, run_id
    )
    if state["status"] != "canary_applied" or not state["changed_manifest_sha256"]:
        raise SandboxError("canary_health_state_invalid")
    changed = _read_manifest(_changed_path(run_root), "changed_manifest")
    if (
        canonical_sha256(changed) != state["changed_manifest_sha256"]
        or changed["source_manifest_sha256"] != baseline["source_manifest_sha256"]
    ):
        raise SandboxError("changed_manifest_binding_invalid")
    _assert_current_manifest(sandbox_root, expected=changed, allow_marker=False)
    marker = sandbox_root / CANARY_MARKER_RELATIVE_PATH
    marker_raw = _require_regular_unlinked_file(marker, "canary_marker")
    if _sha256(marker_raw) != state["marker_sha256"]:
        raise SandboxError("canary_marker_binding_invalid")
    return {
        "run_id": run_id,
        "status": "passed",
        "changed_manifest_sha256": state["changed_manifest_sha256"],
        "artifact_count": 1,
    }


def apply_rollback(*, runs_root: Path, run_id: str) -> dict[str, Any]:
    """Remove only the verified marker and prove exact baseline restoration."""

    run_root, sandbox_root, state_path, state, baseline = _load_baseline_for_run(
        runs_root, run_id
    )
    if state["status"] != "canary_applied" or not state["changed_manifest_sha256"]:
        raise SandboxError("rollback_state_invalid")
    canary_health_check(runs_root=runs_root, run_id=run_id)
    marker = sandbox_root / CANARY_MARKER_RELATIVE_PATH
    _require_regular_unlinked_file(marker, "canary_marker")
    marker.unlink()
    restored = _sandbox_manifest(
        sandbox_root,
        source_manifest_sha256=state["source_manifest_sha256"],
        allowed_paths=_manifest_paths(baseline),
    )
    restored_sha256 = canonical_sha256(restored)
    if restored_sha256 != state["baseline_manifest_sha256"]:
        raise SandboxError("rollback_baseline_restore_failed")
    state.update(
        {
            "status": "rollback_verified",
            "changed_manifest_sha256": state["changed_manifest_sha256"],
            "marker_sha256": state["marker_sha256"],
        }
    )
    _write_json_atomic(state_path, state)
    return {
        "run_id": run_id,
        "status": "rollback_verified",
        "baseline_manifest_sha256": state["rollback_baseline_manifest_sha256"],
        "changed_manifest_sha256": state["changed_manifest_sha256"],
        "restored_manifest_sha256": state["rollback_baseline_manifest_sha256"],
        "sandbox_restored_manifest_sha256": restored_sha256,
        "changed_file_count": 1,
    }


def run_sandbox_rehearsal(
    *,
    runs_root: Path,
    run_id: str,
    source_root: Path,
    source_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Execute the fixed prepare -> canary -> health -> rollback sequence."""

    prepared = prepare_sandbox(
        runs_root=runs_root,
        run_id=run_id,
        source_root=source_root,
        source_manifest=source_manifest,
    )
    canary = apply_canary(runs_root=runs_root, run_id=run_id)
    health = canary_health_check(runs_root=runs_root, run_id=run_id)
    rollback = apply_rollback(runs_root=runs_root, run_id=run_id)
    return {
        "schema_version": REHEARSAL_SCHEMA,
        "status": "passed",
        "run_id": run_id,
        "source_manifest_sha256": prepared["source_manifest_sha256"],
        "baseline_manifest_sha256": rollback["baseline_manifest_sha256"],
        "changed_manifest_sha256": rollback["changed_manifest_sha256"],
        "restored_manifest_sha256": rollback["restored_manifest_sha256"],
        "changed_file_count": 1,
        "canary_health": health["status"],
        "rollback": rollback["status"],
    }


def write_execution_evidence(
    *, evidence_root: Path, run_id: str, result: Mapping[str, Any]
) -> Path:
    """Write one compact, immutable execution receipt under the fixed evidence root."""

    run_id = _safe_run_id(run_id)
    if (
        not isinstance(result, Mapping)
        or result.get("schema_version") != REHEARSAL_SCHEMA
        or result.get("status") != "passed"
        or result.get("run_id") != run_id
    ):
        raise SandboxError("execution_result_invalid")
    _require_existing_components_no_reparse(evidence_root, "evidence_root")
    root = _require_directory(Path(evidence_root), "evidence_root", create=True)
    run_evidence = root / run_id
    if not _path_within(run_evidence, root) or run_evidence.parent != root:
        raise SandboxError("evidence_root_outside_allowlist")
    if run_evidence.exists():
        raise SandboxError("evidence_run_already_exists")
    run_evidence.mkdir(mode=0o700)
    _require_directory(run_evidence, "evidence_run")
    output = run_evidence / "sandbox-execution.json"
    _write_json_atomic(output, dict(result))
    return output


def run(*, run_id: str) -> dict[str, Any]:
    """Broker-facing fixed-root API; it exposes no source, client, or output path."""

    safe_run_id = _safe_run_id(run_id)
    result = run_sandbox_rehearsal(
        runs_root=DEFAULT_RUNS_ROOT,
        run_id=safe_run_id,
        source_root=DEFAULT_STAGED_PACKAGE_ROOT,
        source_manifest=_load_fixed_source_manifest(),
    )
    write_execution_evidence(
        evidence_root=DEFAULT_EVIDENCE_ROOT,
        run_id=safe_run_id,
        result=result,
    )
    return result


def _load_fixed_source_manifest() -> dict[str, Any]:
    return validate_source_manifest(
        _load_json(DEFAULT_SOURCE_MANIFEST_PATH, "fixed_source_manifest")
    )


def stage_fixed_bundle() -> dict[str, Any]:
    """Stage the tracked P14 helper package at the only permitted guest root.

    This is intentionally a provisioning operation, not a runtime command.  It
    derives both the source list and manifest from the checked-out revision via
    the existing P14 contract code, rejects a non-empty destination, and copies
    only verified regular files.  No caller-controlled source or destination is
    accepted.
    """

    try:
        from otclient_p14_independent_runner import (
            ContractError,
            _package_sources,
            _sanitize_helper_manifest,
        )

        source_manifest = validate_source_manifest(_sanitize_helper_manifest())
        package_sources = _package_sources()
    except (ImportError, ContractError) as exc:
        raise SandboxError("bundle_source_manifest_invalid") from exc

    source_by_relative = {relative: path for relative, path in package_sources}
    expected_paths = [entry["path"] for entry in source_manifest["files"]]
    if set(source_by_relative) != set(expected_paths):
        raise SandboxError("bundle_source_path_set_invalid")

    _require_existing_components_no_reparse(DEFAULT_STAGED_PACKAGE_ROOT, "bundle_root")
    if DEFAULT_STAGED_PACKAGE_ROOT.exists():
        bundle_root = _require_directory(DEFAULT_STAGED_PACKAGE_ROOT, "bundle_root")
        if any(bundle_root.iterdir()):
            raise SandboxError("bundle_root_not_empty")
    else:
        DEFAULT_STAGED_PACKAGE_ROOT.mkdir(parents=True, mode=0o700)
        bundle_root = _require_directory(DEFAULT_STAGED_PACKAGE_ROOT, "bundle_root")

    for entry in source_manifest["files"]:
        relative = entry["path"]
        source_path = source_by_relative[relative]
        _require_existing_components_no_reparse(source_path.parent, "bundle_source")
        raw = _require_regular_unlinked_file(source_path, "bundle_source")
        if len(raw) != entry["bytes"] or _sha256(raw) != entry["sha256"]:
            raise SandboxError("bundle_source_manifest_binding_invalid")
        destination = _relative_path(bundle_root, relative)
        _write_bytes_atomic(destination, raw)
        if _require_regular_unlinked_file(destination, "bundle_copy") != raw:
            raise SandboxError("bundle_copy_binding_invalid")

    manifest_path = bundle_root / "helper-manifest.json"
    _write_json_atomic(manifest_path, source_manifest)
    if DEFAULT_SOURCE_MANIFEST_PATH != manifest_path:
        # The Windows guest uses the manifest inside the bundle.  Keeping this
        # explicit avoids accidentally widening the production output boundary
        # when non-Windows tests override the default roots.
        raise SandboxError("bundle_manifest_location_invalid")
    return {
        "schema_version": "ctoa.p14-guest-bundle-stage.v1",
        "status": "staged",
        "helper_manifest_sha256": canonical_sha256(source_manifest),
        "file_count": source_manifest["file_count"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser(
        "run", help="Run the fixed P14 package canary and rollback rehearsal."
    )
    run.add_argument("--run-id", required=True)
    subparsers.add_parser(
        "stage-bundle",
        help="Provision the fixed P14 helper bundle; accepts no caller input.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        if args.command == "run":
            result = run(run_id=args.run_id)
        elif args.command == "stage-bundle":
            result = stage_fixed_bundle()
        else:
            raise SandboxError("command_invalid")
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, SandboxError) as exc:
        print(
            json.dumps(
                {
                    "schema_version": REHEARSAL_SCHEMA,
                    "status": "blocked",
                    "blockers": [str(exc)],
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
