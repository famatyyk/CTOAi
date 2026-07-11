"""Helpers for reading generated manifest pointers without path escapes."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def resolve_latest_manifest_path(
    manifests_dir: Path, latest_payload: Mapping[str, Any]
) -> Path | None:
    """Resolve latest.json manifest_path while keeping reads under manifests_dir."""
    try:
        root = manifests_dir.resolve(strict=False)
    except (OSError, RuntimeError, ValueError):
        return None

    run_id = str(latest_payload.get("run_id", "")).strip()
    raw_manifest_path = str(latest_payload.get("manifest_path", "")).strip()
    candidates: list[Path] = []
    if raw_manifest_path:
        candidate = Path(raw_manifest_path)
        if not candidate.is_absolute():
            candidate = manifests_dir / candidate
        candidates.append(candidate)
    if run_id:
        candidates.append(manifests_dir / run_id / "manifest.json")

    for candidate in candidates:
        try:
            resolved = candidate.resolve(strict=True)
        except (OSError, RuntimeError, ValueError):
            continue
        if resolved.name != "manifest.json":
            continue
        if _is_relative_to(resolved, root):
            return resolved

    return None


def iter_safe_manifest_files(
    manifests_dir: Path,
    *,
    limit: int | None = None,
) -> list[Path]:
    """Return manifest files under manifests_dir, skipping symlink/path escapes."""
    if limit is not None and limit <= 0:
        return []

    try:
        root = manifests_dir.resolve(strict=False)
    except (OSError, RuntimeError, ValueError):
        return []

    safe_entries: list[tuple[float, Path]] = []
    seen: set[Path] = set()
    try:
        candidates = manifests_dir.glob("*/manifest.json")
        for candidate in candidates:
            try:
                resolved = candidate.resolve(strict=True)
            except (OSError, RuntimeError, ValueError):
                continue
            if resolved.name != "manifest.json":
                continue
            if not _is_relative_to(resolved, root):
                continue
            if resolved in seen:
                continue
            try:
                mtime = resolved.stat().st_mtime
            except OSError:
                continue
            seen.add(resolved)
            safe_entries.append((mtime, resolved))
    except (OSError, RuntimeError, ValueError):
        return []

    safe_entries.sort(key=lambda item: item[0], reverse=True)
    paths = [path for _, path in safe_entries]
    if limit is not None:
        return paths[:limit]
    return paths


def public_manifest_path(manifest_path: Path, manifests_dir: Path) -> str:
    """Return a generated-manifest display path without host-local parents."""
    try:
        root = manifests_dir.resolve(strict=False)
        resolved = manifest_path.resolve(strict=False)
        rel = resolved.relative_to(root)
    except (OSError, RuntimeError, ValueError):
        return manifest_path.name or "manifest.json"
    return (Path("generated") / "manifests" / rel).as_posix()
