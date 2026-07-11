#!/usr/bin/env python3
"""Audit OTClient Helper Lua profiles for unsafe migration defaults."""

from __future__ import annotations

import argparse
import json
import os
import re
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROFILE = ROOT / "scripts" / "lua" / "otclient" / "ctoa_ek_profile.lua"
DEFAULT_SCHEMA = ROOT / "schemas" / "otclient-helper-config.schema.json"
EXPECTED_PROFILE_SCHEMA = "ctoa-helper-profile-v1"

SAFE_FALSE_KEYS = {
    "enabled",
    "auto_attack",
    "auto_exeta",
    "auto_haste",
    "spell_rotation",
    "rune_enabled",
    "cavebot_enabled",
    "cavebot_movement_enabled",
    "timer_enabled",
    "experimental_cavebot",
    "experimental_loot",
    "experimental_combat",
}


@dataclass(frozen=True)
class Finding:
    key: str
    status: str
    evidence: str
    reason: str


@dataclass(frozen=True)
class ProfileAudit:
    name: str
    status: str
    profile: str
    schema: str
    findings: list[Finding]
    live_safety: str


def _lua_bool(text: str, key: str) -> bool | None:
    match = re.search(rf"\b{re.escape(key)}\s*=\s*(true|false)\b", text)
    if not match:
        return None
    return match.group(1) == "true"


def _lua_string(text: str, key: str) -> str | None:
    match = re.search(rf'\b{re.escape(key)}\s*=\s*"([^"]+)"', text)
    return match.group(1) if match else None


def audit_profile(profile_path: Path = DEFAULT_PROFILE, schema_path: Path = DEFAULT_SCHEMA, *, allow_armed: bool = False) -> ProfileAudit:
    findings: list[Finding] = []
    if not schema_path.is_file():
        findings.append(Finding("schema", "blocked", str(schema_path), "HELPER_CONFIG schema is missing."))

    if not profile_path.is_file():
        findings.append(Finding("profile", "blocked", str(profile_path), "Profile file is missing."))
        return ProfileAudit(
            name="otclient-helper-profile-audit",
            status="blocked",
            profile=str(profile_path),
            schema=str(schema_path),
            findings=findings,
            live_safety="Profile audit reads repo files only; it does not touch the live Solteria client.",
        )

    text = profile_path.read_text(encoding="utf-8")
    schema_version = _lua_string(text, "schema_version")
    if schema_version != EXPECTED_PROFILE_SCHEMA:
        findings.append(
            Finding(
                "schema_version",
                "blocked",
                str(profile_path),
                f"Profile must declare schema_version = {EXPECTED_PROFILE_SCHEMA}.",
            )
        )
    safe_boot = _lua_bool(text, "safe_boot_runtime_disabled")
    if safe_boot is not True:
        findings.append(
            Finding(
                "safe_boot_runtime_disabled",
                "blocked",
                str(profile_path),
                "Profile must keep safe_boot_runtime_disabled = true.",
            )
        )

    for key in sorted(SAFE_FALSE_KEYS):
        value = _lua_bool(text, key)
        if value is None:
            findings.append(Finding(key, "blocked", str(profile_path), f"Profile is missing {key}."))
        elif value is True and not allow_armed:
            findings.append(Finding(key, "blocked", str(profile_path), f"Profile must not default {key} = true."))

    status = "passed" if not findings else "blocked"
    return ProfileAudit(
        name="otclient-helper-profile-audit",
        status=status,
        profile=str(profile_path),
        schema=str(schema_path),
        findings=findings,
        live_safety="Profile audit reads repo files only; it does not touch the live Solteria client.",
    )


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--allow-armed", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = audit_profile(args.profile.resolve(), args.schema.resolve(), allow_armed=args.allow_armed)
    payload = asdict(report)
    if args.json_out:
        write_json_atomic(args.json_out, payload)
        print(f"[otclient-helper-profile-audit] JSON: {args.json_out}")
    print(f"[otclient-helper-profile-audit] Status: {report.status}")
    for finding in report.findings:
        print(f"[otclient-helper-profile-audit] {finding.key}: {finding.reason}")
    return 0 if report.status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
