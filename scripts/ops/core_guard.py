#!/usr/bin/env python3
"""Core integrity guard for CTOAi.

- `--update`: regenerate `core/core-manifest.sha256` from protected-files list
- `--check` : verify protected files match manifest hashes (default)
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROTECTED_LIST = ROOT / "core" / "protected-files.txt"
MANIFEST = ROOT / "core" / "core-manifest.sha256"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk.replace(b"\r\n", b"\n"))
    return h.hexdigest()


def read_protected_paths() -> list[Path]:
    if not PROTECTED_LIST.exists():
        raise FileNotFoundError(f"Missing protected list: {PROTECTED_LIST}")

    out: list[Path] = []
    for raw in PROTECTED_LIST.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        p = (ROOT / line).resolve()
        out.append(p)
    return out


def write_manifest(paths: list[Path]) -> int:
    lines: list[str] = []
    missing: list[str] = []

    for p in paths:
        rel = p.relative_to(ROOT).as_posix()
        if not p.exists():
            missing.append(rel)
            continue
        lines.append(f"{sha256_file(p)}  {rel}")

    if missing:
        print("Cannot update manifest. Missing protected files:")
        for m in missing:
            print(f" - {m}")
        return 2

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Updated manifest: {MANIFEST.relative_to(ROOT).as_posix()} ({len(lines)} files)")
    return 0


def parse_manifest() -> dict[str, str]:
    if not MANIFEST.exists():
        raise FileNotFoundError(f"Missing manifest: {MANIFEST}")

    expected: dict[str, str] = {}
    for raw in MANIFEST.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("  ", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid manifest line: {line}")
        expected[parts[1]] = parts[0]
    return expected


def check_manifest(paths: list[Path]) -> int:
    expected = parse_manifest()
    failed = False

    for p in paths:
        rel = p.relative_to(ROOT).as_posix()
        if rel not in expected:
            print(f"[FAIL] Missing entry in manifest: {rel}")
            failed = True
            continue
        if not p.exists():
            print(f"[FAIL] Missing file: {rel}")
            failed = True
            continue

        actual = sha256_file(p)
        if actual != expected[rel]:
            print(f"[FAIL] Hash mismatch: {rel}")
            print(f"       expected={expected[rel]}")
            print(f"       actual  ={actual}")
            failed = True
        else:
            print(f"[OK]   {rel}")

    for rel in sorted(expected):
        if not (ROOT / rel).resolve() in paths:
            print(f"[WARN] Manifest contains file not in protected list: {rel}")

    if failed:
        print("\nCore integrity check FAILED.")
        print("If the change was intentional, run:")
        print("  python scripts/ops/core_guard.py --update")
        return 1

    print("\nCore integrity check PASSED.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="CTOA core integrity guard")
    parser.add_argument("--update", action="store_true", help="Regenerate manifest from current files")
    parser.add_argument("--check", action="store_true", help="Check manifest integrity (default)")
    args = parser.parse_args()

    paths = read_protected_paths()

    if args.update:
        return write_manifest(paths)

    return check_manifest(paths)


if __name__ == "__main__":
    sys.exit(main())
