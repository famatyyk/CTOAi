#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def _copy_tree(source: Path, target: Path) -> int:
    count = 0
    if target.exists():
        shutil.rmtree(target)
    for path in source.rglob("*"):
        rel = path.relative_to(source)
        dst = target / rel
        if path.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dst)
        count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync CTOA live targets into bot runtime root")
    parser.add_argument("--source", required=True)
    parser.add_argument("--target", required=True)
    args = parser.parse_args()

    source_root = Path(args.source)
    target_root = Path(args.target)
    source_root.mkdir(parents=True, exist_ok=True)
    target_root.mkdir(parents=True, exist_ok=True)

    synced: list[dict[str, object]] = []
    for item in sorted(source_root.iterdir()):
        if not item.is_dir():
            continue
        target_dir = target_root / item.name
        file_count = _copy_tree(item, target_dir)
        synced.append(
            {
                "name": item.name,
                "source": str(item),
                "target": str(target_dir),
                "files": file_count,
            }
        )

    report = {
        "ok": True,
        "source_root": str(source_root),
        "target_root": str(target_root),
        "synced_count": len(synced),
        "targets": synced,
    }
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()