#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

SAFE_TARGET_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _resolve_directory(path: Path | str, *, create: bool) -> Path:
    raw = Path(path).expanduser()
    if create:
        raw.mkdir(parents=True, exist_ok=True)
    resolved = raw.resolve()
    if not resolved.is_dir():
        raise ValueError(f"Path must be a directory: {raw}")
    return resolved


def _validate_target_name(name: str) -> str:
    if not SAFE_TARGET_NAME.fullmatch(name):
        raise ValueError("Live target directory names must be safe slugs")
    return name


def _assert_target_child(target_root: Path, candidate: Path) -> Path:
    resolved_root = target_root.resolve()
    resolved_candidate = candidate.resolve(strict=False)
    if resolved_candidate == resolved_root or not _is_relative_to(
        resolved_candidate, resolved_root
    ):
        raise ValueError("Refusing to write outside live target root")
    return resolved_candidate


def _assert_relative_child(target_root: Path, candidate: Path) -> None:
    if not _is_relative_to(candidate.resolve(strict=False), target_root.resolve()):
        raise ValueError("Refusing to write outside live target root")


def _copy_tree(source: Path, target: Path, target_root: Path) -> int:
    count = 0
    _assert_target_child(target_root, target)
    if target.exists():
        if target.is_symlink() or not target.is_dir():
            raise ValueError("Refusing to replace unsafe live target path")
        shutil.rmtree(target)
    for path in source.rglob("*"):
        if path.is_symlink():
            raise ValueError("Refusing to sync symlinked live target content")
        rel = path.relative_to(source)
        if any(part in {"", ".", ".."} for part in rel.parts):
            raise ValueError("Refusing to sync unsafe live target relative path")
        dst = target / rel
        _assert_relative_child(target_root, dst)
        if path.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dst)
        count += 1
    return count


def sync_live_targets(source: Path | str, target: Path | str) -> dict[str, object]:
    source_root = _resolve_directory(source, create=True)
    target_root = _resolve_directory(target, create=True)
    if source_root == target_root or _is_relative_to(target_root, source_root):
        raise ValueError("Live target root must not be the source root or inside it")

    synced: list[dict[str, object]] = []
    for item in sorted(source_root.iterdir()):
        if item.is_symlink() or not item.is_dir():
            continue
        target_name = _validate_target_name(item.name)
        target_dir = target_root / target_name
        file_count = _copy_tree(item, target_dir, target_root)
        synced.append(
            {
                "name": target_name,
                "source": str(item),
                "target": str(target_dir),
                "files": file_count,
            }
        )

    return {
        "ok": True,
        "source_root": str(source_root),
        "target_root": str(target_root),
        "synced_count": len(synced),
        "targets": synced,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync CTOA live targets into bot runtime root"
    )
    parser.add_argument("--source", required=True)
    parser.add_argument("--target", required=True)
    args = parser.parse_args()

    try:
        report = sync_live_targets(args.source, args.target)
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=True, indent=2))
        raise SystemExit(2) from exc
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
