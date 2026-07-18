#!/usr/bin/env python3
"""Build sanitized product exports from ``config/repository-boundaries.json``.

The monorepo remains the source of truth during the transition.  This command
creates history-free, allowlist-first directories for the public product
repositories without copying private runtime data or following symlinks.

Examples:
    python scripts/ops/repository_export.py --list
    python scripts/ops/repository_export.py --repo control_center --dry-run
    python scripts/ops/repository_export.py --all --out C:/Users/zycie/CTOAi-exports/run --write
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]
BOUNDARIES = ROOT / "config" / "repository-boundaries.json"


class ExportError(RuntimeError):
    """Raised when an export would violate the repository boundary."""


@dataclass(frozen=True)
class ExportFile:
    source: Path
    relative: PurePosixPath


def _posix(path: Path) -> PurePosixPath:
    return PurePosixPath(path.as_posix())


def _matches_exclude(relative: PurePosixPath, patterns: Iterable[str]) -> bool:
    """Match path and path components against simple manifest exclusions."""

    text = relative.as_posix()
    parts = relative.parts
    for raw_pattern in patterns:
        pattern = raw_pattern.replace("\\", "/").rstrip("/")
        if not pattern:
            continue
        if "/" in pattern and fnmatch.fnmatch(text, pattern):
            return True
        if "/" not in pattern:
            if any(fnmatch.fnmatch(part, pattern) for part in parts):
                return True
            if fnmatch.fnmatch(relative.name, pattern):
                return True
    return False


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _iter_root_files(root: Path, relative_root: PurePosixPath) -> Iterable[ExportFile]:
    if root.is_symlink():
        raise ExportError(f"symlink root is forbidden: {relative_root}")
    if root.is_file():
        yield ExportFile(root, relative_root)
        return
    if not root.is_dir():
        raise ExportError(f"allowlisted root does not exist: {relative_root}")

    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ExportError(f"symlink is forbidden: {path.relative_to(ROOT)}")
        if path.is_file():
            yield ExportFile(path, relative_root / path.relative_to(root).as_posix())


def _load_manifest() -> dict:
    try:
        data = json.loads(BOUNDARIES.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExportError(f"cannot read boundary manifest: {exc}") from exc
    if data.get("policy") != "allowlist-first":
        raise ExportError("boundary manifest must use policy=allowlist-first")
    return data


def _collect(repo: str, spec: dict, root: Path = ROOT) -> list[ExportFile]:
    excludes = spec.get("exclude", [])
    collected: dict[str, ExportFile] = {}
    for raw_root in spec.get("roots", []):
        relative_root = PurePosixPath(raw_root.replace("\\", "/"))
        if any(char in raw_root for char in "*?["):
            matches = sorted(root.glob(raw_root.replace("/", os.sep)))
            if not matches:
                raise ExportError(f"allowlisted root does not match: {relative_root}")
        else:
            matches = [root.joinpath(*relative_root.parts)]
        for source in matches:
            if not _inside(source, root):
                raise ExportError(f"root escapes source repository: {raw_root}")
            match_relative = _posix(source.relative_to(root))
            for item in _iter_root_files(source, match_relative):
                if _matches_exclude(item.relative, excludes):
                    continue
                if not _inside(item.source, root):
                    raise ExportError(f"source escapes repository: {item.source}")
                collected[item.relative.as_posix()] = item
    if not collected:
        raise ExportError(f"repository has no exportable files: {repo}")
    return [collected[key] for key in sorted(collected)]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _generated_readme(repo: str, spec: dict) -> str:
    roots = "\n".join(f"- `{item}`" for item in spec.get("roots", []))
    return (
        f"# {spec['name']}\n\n"
        "This is a sanitized, history-free export generated from the CTOAi "
        "transition monorepo. It contains only the declared product boundary.\n\n"
        "## Export boundary\n\n"
        f"Product key: `{repo}`\n\n{roots}\n\n"
        "Private Engine Brain state, runtime evidence, credentials, databases, "
        "logs and deployment material are intentionally excluded.\n"
    )


def build_export(repo: str, spec: dict, out: Path, *, write: bool, root: Path = ROOT) -> dict:
    files = _collect(repo, spec, root)
    destination = out / spec["name"]
    if write and destination.exists():
        raise ExportError(f"destination already exists; choose a new --out path: {destination}")

    entries: list[dict[str, str]] = []
    for item in files:
        destination_file = destination / Path(*item.relative.parts)
        entries.append(
            {
                "path": item.relative.as_posix(),
                "sha256": _sha256(item.source),
            }
        )
        if write:
            destination_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item.source, destination_file)

    metadata = {
        "schema_version": 1,
        "repository": spec["name"],
        "source": "CTOAi transition monorepo",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "history_included": False,
        "file_count": len(entries),
        "boundary_roots": spec.get("roots", []),
        "files": entries,
    }
    if write:
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "README.md").write_text(
            _generated_readme(repo, spec), encoding="utf-8"
        )
        (destination / "EXPORT_MANIFEST.json").write_text(
            json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
        )
    return metadata


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="list public export keys")
    selector = parser.add_mutually_exclusive_group()
    selector.add_argument("--repo", choices=["control_center", "helper", "adapter"])
    selector.add_argument("--all", action="store_true", help="export every public product")
    parser.add_argument("--out", type=Path, default=ROOT / "_local_archive" / "exports")
    parser.add_argument("--write", action="store_true", help="write files; otherwise dry-run")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="explicitly select the default non-writing mode",
    )
    args = parser.parse_args(argv)

    try:
        manifest = _load_manifest()
        public = {
            key: value
            for key, value in manifest.get("repositories", {}).items()
            if value.get("public_export") is True
        }
        if args.list:
            for key in sorted(public):
                print(f"{key}\t{public[key]['name']}")
            return 0
        keys = [args.repo] if args.repo else sorted(public) if args.all else []
        if not keys:
            parser.error("choose --list, --repo KEY, or --all")
        for key in keys:
            metadata = build_export(key, public[key], args.out, write=args.write)
            mode = "written" if args.write else "dry-run"
            print(
                f"[repository-export] {mode} repo={key} "
                f"files={metadata['file_count']} out={args.out / public[key]['name']}"
            )
        return 0
    except ExportError as exc:
        print(f"[repository-export] ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
