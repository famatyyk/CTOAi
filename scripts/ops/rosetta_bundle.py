#!/usr/bin/env python3
"""Build Rosetta Assembler bundles from repo-local presets.

This wrapper keeps CTOAi integration lightweight:
- preset definitions live in config/rosetta-presets.json
- bundles are written to runtime/rosetta-bundles/
- a small manifest is written alongside each bundle for traceability
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PRESETS_PATH = ROOT / "config" / "rosetta-presets.json"
OUTPUT_DIR = ROOT / "runtime" / "rosetta-bundles"
DEFAULT_IGNORES = ["runtime/**", "logs/**", "backups/**", "archived/**"]
LOCAL_ROSETTA_MAIN = ROOT / "tools" / "rosetta-assembler" / "src" / "main.py"


@dataclass(frozen=True)
class Preset:
    name: str
    description: str
    output_format: str
    target_size: str
    focus_on: list[str]
    include: list[str]
    exclude: list[str]


def _load_presets() -> dict[str, Preset]:
    if not PRESETS_PATH.exists():
        raise FileNotFoundError(f"Missing preset file: {PRESETS_PATH.relative_to(ROOT).as_posix()}")

    payload = json.loads(PRESETS_PATH.read_text(encoding="utf-8"))
    presets = payload.get("presets") if isinstance(payload, dict) else None
    if not isinstance(presets, dict):
        raise ValueError("Preset file must contain a top-level 'presets' object")

    result: dict[str, Preset] = {}
    for name, raw in presets.items():
        if not isinstance(raw, dict):
            continue
        result[name] = Preset(
            name=name,
            description=str(raw.get("description", "")),
            output_format=str(raw.get("output_format", "txt")),
            target_size=str(raw.get("target_size", "500k")),
            focus_on=[str(item) for item in raw.get("focus_on", []) if item],
            include=[str(item) for item in raw.get("include", []) if item],
            exclude=[str(item) for item in raw.get("exclude", []) if item],
        )
    return result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a Rosetta Assembler bundle from a CTOAi preset")
    parser.add_argument("preset", help="Preset name from config/rosetta-presets.json")
    parser.add_argument("--source", default=str(ROOT), help="Source path or repo URL for Rosetta Assembler")
    parser.add_argument(
        "--assembler",
        default=str(LOCAL_ROSETTA_MAIN) if LOCAL_ROSETTA_MAIN.exists() else "rosetta-assembler",
        help="Rosetta Assembler executable or a local source script path",
    )
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR), help="Directory for bundles and manifests")
    parser.add_argument("--dry-run", action="store_true", help="Print the command and manifest without running it")
    return parser


def _relative(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _manifest_path(output_dir: Path, preset: str, suffix: str) -> Path:
    return output_dir / f"{preset}-{suffix}.json"


def _bundle_path(output_dir: Path, preset: str, output_format: str) -> Path:
    extension = "json" if output_format.lower() == "json" else "txt"
    return output_dir / f"{preset}-bundle.{extension}"


def _reserve_unique_path(path: Path) -> Path:
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    counter = 2
    while True:
        candidate = path.with_name(f"{stem}_{counter}{suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def _build_command(args: argparse.Namespace, preset: Preset, bundle_path: Path) -> list[str]:
    cmd = [args.assembler, args.source, "-o", str(bundle_path), "--output-format", preset.output_format, "--target-size", preset.target_size]
    for item in preset.include:
        cmd.extend(["--include", item])
    for item in preset.exclude:
        cmd.extend(["--exclude", item])
    for item in preset.focus_on:
        cmd.extend(["--focus-on", item])
    return cmd


def _resolve_assembler(executable_name: str) -> list[str] | None:
    if executable_name.lower().endswith(".py"):
        script_path = Path(executable_name)
        if script_path.exists():
            return [sys.executable, str(script_path)]

    script_path = Path(executable_name)
    if script_path.exists() and script_path.suffix.lower() == ".py":
        return [sys.executable, str(script_path)]

    found = shutil.which(executable_name)
    if found is not None:
        return [found]

    python_dir = Path(sys.executable).resolve().parent
    scripts_dir = python_dir / "Scripts"
    candidate = scripts_dir / executable_name
    if candidate.exists():
        return [str(candidate)]

    windows_candidate = scripts_dir / f"{executable_name}.exe"
    if windows_candidate.exists():
        return [str(windows_candidate)]

    if LOCAL_ROSETTA_MAIN.exists():
        return [sys.executable, str(LOCAL_ROSETTA_MAIN)]

    return None


def _write_manifest(path: Path, preset: Preset, bundle_path: Path, command: list[str], source: str) -> None:
    manifest: dict[str, Any] = {
        "preset": preset.name,
        "description": preset.description,
        "generated_at": datetime.now(UTC).isoformat(),
        "source": source,
        "bundle_path": _relative(bundle_path),
        "bundle_exists": bundle_path.exists(),
        "output_format": preset.output_format,
        "target_size": preset.target_size,
        "focus_on": preset.focus_on,
        "include": preset.include,
        "exclude": preset.exclude,
        "command": command,
        "status": "DRY_RUN" if not bundle_path.exists() else "BUILT",
    }
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")


def main() -> int:
    args = _build_parser().parse_args()
    presets = _load_presets()
    preset = presets.get(args.preset)
    if preset is None:
        available = ", ".join(sorted(presets))
        print(f"Unknown preset: {args.preset}. Available presets: {available}", file=sys.stderr)
        return 2

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = _reserve_unique_path(_bundle_path(output_dir, preset.name, preset.output_format))
    manifest_path = _manifest_path(output_dir, preset.name, "manifest")
    command = _build_command(args, preset, bundle_path)

    if args.dry_run:
        _write_manifest(manifest_path, preset, bundle_path, command, args.source)
        print(json.dumps({"ok": True, "dry_run": True, "bundle_path": str(bundle_path), "manifest_path": str(manifest_path), "command": command}, indent=2))
        return 0

    assembler = _resolve_assembler(args.assembler)
    if assembler is None:
        print(
            f"Rosetta Assembler executable not found: {args.assembler}. Install it or pass --assembler with a full path.",
            file=sys.stderr,
        )
        return 1

    command = [*assembler, *command[1:]]
    completed = subprocess.run(command, cwd=ROOT)
    if completed.returncode != 0:
        return completed.returncode

    _write_manifest(manifest_path, preset, bundle_path, command, args.source)
    print(
        json.dumps(
            {
                "ok": True,
                "preset": preset.name,
                "bundle_path": str(bundle_path),
                "manifest_path": str(manifest_path),
                "output_format": preset.output_format,
                "target_size": preset.target_size,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
