"""Inspect external OTClient bot sources before CTOAi helper import."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_JSON = ROOT / "runtime" / "solteria_helper_dev" / "external_bot_intake.json"
DEFAULT_MARKDOWN = ROOT / "docs" / "otclient" / "vbot_import_intake.md"

TEXT_SUFFIXES = {
    ".lua",
    ".otui",
    ".otmod",
    ".json",
    ".yml",
    ".yaml",
    ".txt",
    ".md",
    ".cfg",
    ".conf",
    ".ini",
}
LICENSE_NAMES = {"license", "license.md", "license.txt", "copying", "copying.txt", "notice", "notice.txt"}
MAX_SCAN_BYTES = 512_000

CAPABILITY_PATTERNS = {
    "healing": re.compile(r"\b(heal|sio|uh|mana|health|hp|mp)\b", re.IGNORECASE),
    "targeting": re.compile(r"\b(target|attack|monster|creature|priority)\b", re.IGNORECASE),
    "cavebot": re.compile(r"\b(cavebot|waypoint|walk|route|path|label)\b", re.IGNORECASE),
    "looting": re.compile(r"\b(loot|container|corpse|pickup)\b", re.IGNORECASE),
    "hud": re.compile(r"\b(hud|overlay|label|widget|panel)\b", re.IGNORECASE),
    "hotkeys": re.compile(r"\b(hotkey|bindKey|keyboard|shortcut)\b", re.IGNORECASE),
    "conditions": re.compile(r"\b(condition|haste|paralyze|poison|burn|curse)\b", re.IGNORECASE),
    "equipment": re.compile(r"\b(equip|slot|ring|amulet|weapon|armor)\b", re.IGNORECASE),
    "scripting": re.compile(r"\b(macro|script|eval|loadstring|scheduleEvent|cycleEvent)\b", re.IGNORECASE),
    "diagnostics": re.compile(r"\b(log|debug|trace|diagnostic|export)\b", re.IGNORECASE),
}

RUNTIME_ACTION_PATTERNS = {
    "movement": re.compile(r"\b(autoWalk|walk|findPath|goto|moveTo)\b"),
    "attack": re.compile(r"\b(g_game\.attack|attack\(|setTarget)\b"),
    "spell_cast": re.compile(r"\b(say|talk|cast|exori|exura|utani|utevo|exeta)\b", re.IGNORECASE),
    "rune_or_item_use": re.compile(r"\b(useInventoryItem|useWith|g_game\.use|useItem|useRune)\b"),
    "item_move": re.compile(r"\b(moveItem|g_game\.move|moveToParentContainer)\b"),
    "keyboard_binding": re.compile(r"\b(bindKey|g_keyboard|pressKey)\b"),
    "filesystem_write": re.compile(r"\b(io\.open|writefile|save|g_resources\.writeFileContents)\b"),
    "dynamic_code": re.compile(r"\b(loadstring|dofile|require|assert\(load)\b"),
}

SECRET_PATTERNS = {
    "token_like": re.compile(r"(?i)\b(token|secret|api[_-]?key)\b\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}"),
    "password_like": re.compile(r"(?i)\b(pass|password)\b\s*[:=]\s*['\"]?[^'\"\s]{6,}"),
    "bearer": re.compile(r"(?i)\bbearer\s+[A-Za-z0-9_\-.]{20,}"),
    "ipv4": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
}

CAPABILITY_TARGETS = {
    "healing": "ctoa_helper_heal_friend.lua",
    "targeting": "ctoa_helper_targeting.lua",
    "cavebot": "ctoa_helper_route.lua",
    "looting": "ctoa_helper_loot_runtime.lua",
    "hud": "ctoa_helper_hud.lua",
    "hotkeys": "ctoa_helper_hotkeys.lua",
    "conditions": "ctoa_helper_conditions.lua",
    "equipment": "ctoa_helper_equipment.lua",
    "scripting": "ctoa_helper_scripting.lua",
    "diagnostics": "ctoa_helper_diagnostics.lua",
}

RUNTIME_ACTION_GATES = {
    "movement": "cavebot_runtime",
    "attack": "combat_runtime",
    "spell_cast": "combat_runtime",
    "rune_or_item_use": "combat_runtime",
    "item_move": "loot_runtime",
    "keyboard_binding": "hotkeys",
    "filesystem_write": "profile_schema",
    "dynamic_code": "scripting",
}


@dataclass(frozen=True)
class SourceFileReport:
    path: str
    bytes: int
    sha256: str
    capabilities: list[str]
    runtime_actions: list[str]
    secret_hits: list[str]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_limited(path: Path) -> bytes:
    with path.open("rb") as handle:
        return handle.read(MAX_SCAN_BYTES + 1)


def _is_text_candidate(path: str) -> bool:
    return Path(path).suffix.lower() in TEXT_SUFFIXES or Path(path).name.lower() in LICENSE_NAMES


def _decode(data: bytes) -> str:
    return data[:MAX_SCAN_BYTES].decode("utf-8", errors="replace")


def _matches(patterns: dict[str, re.Pattern[str]], haystack: str) -> list[str]:
    return [name for name, pattern in patterns.items() if pattern.search(haystack)]


def _directory_snapshot_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    for file_path in sorted(item for item in path.rglob("*") if item.is_file()):
        rel = file_path.relative_to(path).as_posix()
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        with file_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest()


def _zip_text_entries(path: Path) -> Iterable[tuple[str, bytes]]:
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if info.is_dir() or not _is_text_candidate(info.filename):
                continue
            with archive.open(info) as handle:
                yield info.filename, handle.read(MAX_SCAN_BYTES + 1)


def _directory_text_entries(path: Path) -> Iterable[tuple[str, bytes]]:
    for file_path in sorted(item for item in path.rglob("*") if item.is_file()):
        rel = file_path.relative_to(path).as_posix()
        if _is_text_candidate(rel):
            yield rel, _read_limited(file_path)


def _source_entries(path: Path) -> Iterable[tuple[str, bytes]]:
    if path.is_dir():
        return _directory_text_entries(path)
    if zipfile.is_zipfile(path):
        return _zip_text_entries(path)
    if _is_text_candidate(path.name):
        return [(path.name, _read_limited(path))]
    return []


def _source_sha256(path: Path) -> str:
    if path.is_dir():
        return _directory_snapshot_sha256(path)
    return _sha256_bytes(path.read_bytes())


def inspect_source_file(name: str, data: bytes) -> SourceFileReport:
    text = _decode(data)
    haystack = f"{name}\n{text}"
    return SourceFileReport(
        path=name,
        bytes=len(data),
        sha256=_sha256_bytes(data),
        capabilities=_matches(CAPABILITY_PATTERNS, haystack),
        runtime_actions=_matches(RUNTIME_ACTION_PATTERNS, haystack),
        secret_hits=_matches(SECRET_PATTERNS, haystack),
    )


def build_import_gate(report: dict) -> dict:
    """Convert intake findings into an explicit CTOAi import decision."""
    if report.get("status") == "source_missing":
        decision = "source_required"
    elif report.get("blockers"):
        decision = "review_required"
    else:
        decision = "capability_mapping_only"

    capability_mapping = {}
    for capability, paths in report.get("capability_inventory", {}).items():
        if paths:
            capability_mapping[capability] = {
                "target_module": CAPABILITY_TARGETS.get(capability, "manual_review_required"),
                "source_files": sorted(paths),
                "import_rule": "map concepts only; no direct code copy; runtime behavior remains gated",
            }

    runtime_gate_mapping = {}
    for action, paths in report.get("runtime_action_inventory", {}).items():
        if paths:
            runtime_gate_mapping[action] = {
                "required_gate": RUNTIME_ACTION_GATES.get(action, "manual_review_required"),
                "source_files": sorted(paths),
                "allowed_now": False,
            }

    blockers = list(report.get("blockers") or [])
    if decision == "capability_mapping_only" and runtime_gate_mapping:
        blockers.append("runtime actions detected; map as passive module plans before any execution path")

    return {
        "decision": decision,
        "runtime_import_allowed": False,
        "direct_copy_allowed": False,
        "capability_mapping": capability_mapping,
        "runtime_gate_mapping": runtime_gate_mapping,
        "blockers": blockers,
        "next_action": (
            "Provide vBot source with origin and license notes."
            if decision == "source_required"
            else "Resolve provenance, license, secret, and review blockers."
            if decision == "review_required"
            else "Map detected capabilities into CTOAi passive module contracts and sandbox gates."
        ),
    }


def build_report(source: Path, *, origin: str = "", license_note: str = "") -> dict:
    source = source.expanduser()
    generated_at = datetime.now().replace(microsecond=0).isoformat()
    if not source.exists():
        report = {
            "schema_version": 1,
            "generated_at": generated_at,
            "source": str(source),
            "status": "source_missing",
            "blockers": ["source path does not exist"],
            "warnings": [],
            "source_sha256": "",
            "origin": origin,
            "license_note": license_note,
            "files": [],
            "capability_inventory": {},
            "runtime_action_inventory": {},
            "secret_scan_status": "not_run",
        }
        report["import_gate"] = build_import_gate(report)
        return report

    files = [inspect_source_file(name, data) for name, data in _source_entries(source)]
    capability_inventory = {
        capability: sorted(report.path for report in files if capability in report.capabilities)
        for capability in CAPABILITY_PATTERNS
    }
    runtime_action_inventory = {
        action: sorted(report.path for report in files if action in report.runtime_actions)
        for action in RUNTIME_ACTION_PATTERNS
    }
    secret_files = sorted(report.path for report in files if report.secret_hits)
    license_files = sorted(report.path for report in files if Path(report.path).name.lower() in LICENSE_NAMES)

    blockers: list[str] = []
    warnings: list[str] = []
    if not origin:
        blockers.append("origin/provenance note missing")
    if not license_note and not license_files:
        blockers.append("license note or license file missing")
    if secret_files:
        blockers.append("secret-like values require review")
    if not files:
        blockers.append("no scan-compatible text files found")
    for action, action_files in runtime_action_inventory.items():
        if action_files:
            warnings.append(f"runtime action path detected: {action}")

    status = "ready_for_capability_mapping" if not blockers else "review_required"
    report = {
        "schema_version": 1,
        "generated_at": generated_at,
        "source": str(source),
        "status": status,
        "blockers": blockers,
        "warnings": warnings,
        "source_sha256": _source_sha256(source),
        "origin": origin,
        "license_note": license_note,
        "license_files": license_files,
        "files": [asdict(report) for report in files],
        "capability_inventory": capability_inventory,
        "runtime_action_inventory": runtime_action_inventory,
        "secret_scan_status": "needs_review" if secret_files else "passed",
        "secret_files": secret_files,
    }
    report["import_gate"] = build_import_gate(report)
    return report


def render_markdown(report: dict) -> str:
    lines = [
        "# External Bot Intake Report",
        "",
        "## Decision",
        "",
        f"- Status: `{report['status']}`",
        f"- Source: `{report['source']}`",
        f"- Source SHA256: `{report['source_sha256'] or 'missing'}`",
        f"- Secret scan: `{report['secret_scan_status']}`",
        "",
        "## Blockers",
        "",
    ]
    blockers = report.get("blockers") or ["none"]
    lines.extend(f"- {item}" for item in blockers)
    lines.extend(["", "## Runtime Action Warnings", ""])
    warnings = report.get("warnings") or ["none"]
    lines.extend(f"- {item}" for item in warnings)
    lines.extend(["", "## Capability Inventory", ""])
    for capability, paths in report.get("capability_inventory", {}).items():
        value = ", ".join(paths[:20]) if paths else "none"
        suffix = " ..." if len(paths) > 20 else ""
        lines.append(f"- `{capability}`: {value}{suffix}")
    gate = report.get("import_gate", {})
    lines.extend(
        [
            "",
            "## CTOAi Import Gate",
            "",
            f"- Decision: `{gate.get('decision', 'unknown')}`",
            f"- Runtime import allowed: `{str(gate.get('runtime_import_allowed', False)).lower()}`",
            f"- Direct copy allowed: `{str(gate.get('direct_copy_allowed', False)).lower()}`",
            f"- Next action: {gate.get('next_action', 'Review source before import.')}",
            "",
            "## Runtime Gate Mapping",
            "",
        ]
    )
    runtime_gate_mapping = gate.get("runtime_gate_mapping") or {}
    if runtime_gate_mapping:
        for action, item in runtime_gate_mapping.items():
            lines.append(
                f"- `{action}` -> `{item['required_gate']}`: {', '.join(item['source_files'][:20])}"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Import Rule", ""])
    lines.append(
        "Use this report as a capability checklist only. Runtime behavior must still be mapped into passive CTOAi helper modules and proven by sandbox smoke before live promotion."
    )
    return "\n".join(lines) + "\n"


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{id(text)}.tmp")
    try:
        tmp.write_text(text if text.endswith("\n") else f"{text}\n", encoding="utf-8", newline="\n")
        tmp.replace(path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect external OTClient bot sources before helper import")
    parser.add_argument("source", type=Path)
    parser.add_argument("--origin", default="", help="Origin URL or owner-provided provenance note")
    parser.add_argument("--license-note", default="", help="License text reference or explicit permission note")
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()

    report = build_report(args.source, origin=args.origin, license_note=args.license_note)
    write_text_atomic(args.json_out, json.dumps(report, indent=2))
    write_text_atomic(args.markdown_out, render_markdown(report))
    print(f"[otclient-external-bot-intake] JSON: {args.json_out}")
    print(f"[otclient-external-bot-intake] Markdown: {args.markdown_out}")
    print(f"[otclient-external-bot-intake] Status: {report['status']}")
    return 0 if report["status"] != "source_missing" else 2


if __name__ == "__main__":
    raise SystemExit(main())
