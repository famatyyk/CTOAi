#!/usr/bin/env python3
"""Create a full CTOAi workspace audit inventory and development plans.

The audit intentionally inventories every file under the workspace, including
Git internals. Files are grouped by role so local caches and runtime state remain
visible without being mistaken for canonical source.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import stat as stat_module
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runner import process_safety  # noqa: E402

DEFAULT_RUNTIME_OUT = ROOT / "runtime" / "audits" / "ctoai-full-workspace-audit.json"
DEFAULT_VALIDATION_IN = (
    ROOT / "runtime" / "audits" / "ctoai-full-workspace-validation.json"
)
DEFAULT_MARKDOWN_OUT = (
    ROOT / "docs" / "audits" / "CTOAI_FULL_WORKSPACE_AUDIT_2026-07-06.md"
)
DEFAULT_PLANS_OUT = (
    ROOT / "docs" / "roadmaps" / "CTOAI_THREE_DEVELOPMENT_PLANS_2026-07-06.md"
)

VENDOR_DIRS = {"node_modules", ".venv", ".pytest_cache", "__pycache__", ".next"}
LOCAL_STATE_DIRS = {
    "runtime",
    "logs",
    "data",
    ".tmp",
    "metrics",
    ".ctoa-local",
    ".agents",
    ".codex",
    "_local_archive",
}
SOURCE_DIRS = {
    "agents",
    "api",
    "bot",
    "config",
    "core",
    "deploy",
    "desktop_console",
    "docs",
    "evals",
    "mobile_console",
    "policies",
    "prompts",
    "releases",
    "runner",
    "schemas",
    "scoring",
    "scripts",
    "tests",
    "tools",
    "training",
    "web",
    "workflows",
    "AI",
}
SECRET_NAMES = {
    ".env",
    ".env.kingsvale",
    ".env.preview.local",
    ".env.production.local",
    ".env.local",
}
SECRET_PATTERNS = ("secret", "token", "credential", "password", ".env.")


@dataclass(frozen=True)
class FileRecord:
    path: str
    bytes: int
    modified_at: str
    category: str
    tracked: bool
    extension: str
    sha256: str
    note: str


def _run_git(args: list[str]) -> list[str]:
    try:
        git = process_safety.resolve_git()
        completed = process_safety.run_trusted(
            [git, *args],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
    except (
        process_safety.ExecutableUnavailableError,
        process_safety.ProcessExecutionError,
    ):
        return []
    return [
        line.strip().replace("\\", "/")
        for line in completed.stdout.splitlines()
        if line.strip()
    ]


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _is_git_internal(path: Path) -> bool:
    try:
        rel = _rel(path)
    except ValueError:
        return False
    return rel == ".git" or rel.startswith(".git/")


def _category(rel_path: str, tracked: bool) -> tuple[str, str]:
    parts = rel_path.split("/")
    root = parts[0]
    name = parts[-1]
    lowered = rel_path.lower()
    if root == ".git":
        return "git_internal", "Git internal repository storage"
    if root in VENDOR_DIRS or "/node_modules/" in rel_path or "/.venv/" in rel_path:
        return "vendor_or_cache", "local dependency/cache file"
    if name in SECRET_NAMES or (
        ".env." in lowered and not lowered.endswith(".example")
    ):
        return "local_secret_or_sensitive", "local environment or secret-style file"
    if root in LOCAL_STATE_DIRS:
        return "runtime_or_local_state", "local generated/runtime state"
    if tracked:
        return "tracked_source", "tracked by git"
    if any(pattern in lowered for pattern in SECRET_PATTERNS):
        return "local_secret_or_sensitive", "untracked sensitive-name file"
    if root in SOURCE_DIRS:
        return (
            "untracked_source_candidate",
            "inside source/doc/test tree but not tracked",
        )
    return "untracked_local", "not tracked by git"


def _safe_file_stat(path: Path) -> os.stat_result | None:
    try:
        file_stat = path.lstat()
    except OSError:
        return None
    if _file_kind(file_stat.st_mode) != "regular_file":
        return None
    return file_stat


def _file_kind(mode: int) -> str:
    if stat_module.S_ISLNK(mode):
        return "symlink"
    if stat_module.S_ISDIR(mode):
        return "directory"
    if stat_module.S_ISREG(mode):
        return "regular_file"
    if stat_module.S_ISCHR(mode):
        return "character_device"
    if stat_module.S_ISBLK(mode):
        return "block_device"
    if stat_module.S_ISFIFO(mode):
        return "fifo"
    if stat_module.S_ISSOCK(mode):
        return "socket"
    return "other"


def _same_file_stat(expected: os.stat_result, opened: os.stat_result) -> bool:
    expected_identity = (getattr(expected, "st_dev", 0), getattr(expected, "st_ino", 0))
    opened_identity = (getattr(opened, "st_dev", 0), getattr(opened, "st_ino", 0))
    if all(expected_identity) and all(opened_identity):
        return expected_identity == opened_identity
    return expected.st_size == opened.st_size and expected.st_mtime_ns == opened.st_mtime_ns


def _sha256_for_file(
    path: Path,
    category: str,
    max_hash_bytes: int,
    file_stat: os.stat_result | None = None,
) -> str:
    if category in {"vendor_or_cache", "local_secret_or_sensitive", "git_internal"}:
        return ""
    try:
        file_stat = file_stat or _safe_file_stat(path)
        if file_stat is None or file_stat.st_size > max_hash_bytes:
            return ""
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            opened_stat = os.fstat(handle.fileno())
            if _file_kind(opened_stat.st_mode) != "regular_file" or not _same_file_stat(
                file_stat, opened_stat
            ):
                return ""
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return ""


def build_inventory(max_hash_bytes: int = 2_000_000) -> dict[str, Any]:
    tracked = set(_run_git(["ls-files"]))
    dirty = _run_git(["status", "--short"])
    records: list[FileRecord] = []
    skipped_entries_by_kind: Counter[str] = Counter()

    for path in ROOT.rglob("*"):
        try:
            file_stat = path.lstat()
        except OSError:
            skipped_entries_by_kind["stat_error"] += 1
            continue
        kind = _file_kind(file_stat.st_mode)
        if kind != "regular_file":
            skipped_entries_by_kind[kind] += 1
            continue
        rel_path = _rel(path)
        is_tracked = rel_path in tracked
        category, note = _category(rel_path, is_tracked)
        records.append(
            FileRecord(
                path=rel_path,
                bytes=file_stat.st_size,
                modified_at=dt.datetime.fromtimestamp(
                    file_stat.st_mtime, tz=dt.UTC
                ).isoformat(timespec="seconds"),
                category=category,
                tracked=is_tracked,
                extension=path.suffix.lower() or "<none>",
                sha256=_sha256_for_file(path, category, max_hash_bytes, file_stat),
                note=note,
            )
        )

    records.sort(key=lambda item: item.path)
    by_category = Counter(record.category for record in records)
    bytes_by_category: Counter[str] = Counter()
    by_top_dir: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"files": 0, "bytes": 0}
    )
    by_extension = Counter(record.extension for record in records)
    hashed_file_count = 0
    sensitive_hash_count = 0
    for record in records:
        bytes_by_category[record.category] += record.bytes
        top = record.path.split("/", 1)[0]
        by_top_dir[top]["files"] += 1
        by_top_dir[top]["bytes"] += record.bytes
        if record.sha256:
            hashed_file_count += 1
            if record.category == "local_secret_or_sensitive":
                sensitive_hash_count += 1

    inventory = {
        "schema_version": 1,
        "generated_at_utc": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "root": str(ROOT),
        "coverage": {
            "scope": "All files under workspace root, including .git internals.",
            "file_count": len(records),
            "regular_file_count": len(records),
            "skipped_non_regular_count": sum(skipped_entries_by_kind.values()),
            "skipped_entries_by_kind": dict(sorted(skipped_entries_by_kind.items())),
            "tracked_file_count": len(tracked),
            "dirty_entry_count": len(dirty),
            "hashed_max_bytes": max_hash_bytes,
            "hashed_file_count": hashed_file_count,
            "sensitive_hash_count": sensitive_hash_count,
        },
        "counts_by_category": dict(sorted(by_category.items())),
        "bytes_by_category": dict(sorted(bytes_by_category.items())),
        "top_directories": dict(
            sorted(by_top_dir.items(), key=lambda item: item[1]["files"], reverse=True)
        ),
        "top_extensions": dict(by_extension.most_common(30)),
        "dirty_entries": dirty,
        "files": [asdict(record) for record in records],
    }
    inventory["audit_gate"] = _audit_gate(inventory)
    return inventory


def _audit_gate(inventory: dict[str, Any]) -> dict[str, Any]:
    coverage = inventory["coverage"]
    categories = inventory["counts_by_category"]
    skipped = coverage.get("skipped_entries_by_kind", {})
    checks = [
        {
            "name": "regular_file_inventory",
            "status": "passed" if coverage["regular_file_count"] > 0 else "failed",
            "evidence": f"{coverage['regular_file_count']} regular files inventoried.",
        },
        {
            "name": "non_regular_accounting",
            "status": "passed",
            "evidence": (
                f"{coverage['skipped_non_regular_count']} non-regular entries skipped "
                f"({skipped})."
            ),
        },
        {
            "name": "bounded_hashing",
            "status": "passed" if coverage["hashed_max_bytes"] > 0 else "failed",
            "evidence": (
                f"{coverage['hashed_file_count']} files hashed with max size "
                f"{coverage['hashed_max_bytes']} bytes."
            ),
        },
        {
            "name": "sensitive_content_omitted",
            "status": "passed" if coverage["sensitive_hash_count"] == 0 else "failed",
            "evidence": (
                f"{categories.get('local_secret_or_sensitive', 0)} sensitive-name "
                f"files inventoried; {coverage['sensitive_hash_count']} hashed."
            ),
        },
        {
            "name": "git_status_captured",
            "status": "passed" if isinstance(inventory["dirty_entries"], list) else "failed",
            "evidence": f"{coverage['dirty_entry_count']} git status entries captured.",
        },
    ]
    return {
        "status": (
            "evidence_ready"
            if all(check["status"] == "passed" for check in checks)
            else "needs_attention"
        ),
        "checks": checks,
        "completion_note": (
            "This gate proves the inventory mechanics for the current run. It does "
            "not by itself prove the whole repository objective complete; targeted "
            "and broad validation commands still need current run evidence."
        ),
    }


def _load_validation_evidence(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    commands = payload.get("commands")
    if not isinstance(commands, list):
        return None
    normalized_commands = []
    for command in commands:
        if not isinstance(command, dict):
            continue
        normalized_commands.append(
            {
                "id": str(command.get("id") or "unknown"),
                "command": str(command.get("command") or ""),
                "status": str(command.get("status") or "unknown"),
                "summary": str(command.get("summary") or ""),
                "duration": str(command.get("duration") or ""),
            }
        )
    return {
        "schema_version": payload.get("schema_version", 1),
        "generated_at_utc": str(payload.get("generated_at_utc") or ""),
        "commands": normalized_commands,
    }


def _validation_gate(validation: dict[str, Any] | None) -> dict[str, Any]:
    required_ids = {
        "python_non_e2e",
        "web_lint",
        "web_tests",
        "diff_check",
        "brain_refresh",
        "brain_doctor",
        "brain_pack_all",
    }
    if validation is None:
        return {
            "status": "missing",
            "missing": sorted(required_ids),
            "failed": [],
        }
    by_id = {command["id"]: command for command in validation["commands"]}
    missing = sorted(required_ids - set(by_id))
    failed = sorted(
        command_id
        for command_id, command in by_id.items()
        if command_id in required_ids and command["status"] not in {"passed", "warn"}
    )
    return {
        "status": "evidence_ready" if not missing and not failed else "needs_attention",
        "missing": missing,
        "failed": failed,
    }


def _mb(value: int) -> str:
    return f"{value / (1024 * 1024):.2f} MB"


def _audit_findings(inventory: dict[str, Any]) -> list[dict[str, str]]:
    categories = inventory["counts_by_category"]
    dirty = inventory["dirty_entries"]
    top_dirs = inventory["top_directories"]
    findings = [
        {
            "severity": "high",
            "area": "workspace-state",
            "finding": f"Worktree is dirty with {len(dirty)} status entries.",
            "evidence": "git status --short; see runtime audit JSON dirty_entries.",
            "action": "Package current Helper/Control Center changes into one reviewable change set before opening another lane.",
        },
        {
            "severity": "high",
            "area": "local-sensitive-state",
            "finding": f"{categories.get('local_secret_or_sensitive', 0)} sensitive-name files are present in the workspace inventory.",
            "evidence": ".env-style files are inventoried but content was not copied into docs.",
            "action": "Keep these ignored/local; never copy values into AI packs, docs, issues, or release evidence.",
        },
        {
            "severity": "medium",
            "area": "dependency-cache",
            "finding": f"Vendor/cache files dominate the workspace ({categories.get('vendor_or_cache', 0)} files).",
            "evidence": "Full inventory includes node_modules/.venv/cache paths so they are not hidden.",
            "action": "Keep audits category-aware; do not treat dependency cache churn as product source changes.",
        },
        {
            "severity": "medium",
            "area": "runtime-state",
            "finding": f"Runtime/local state is large and active ({categories.get('runtime_or_local_state', 0)} files).",
            "evidence": "runtime/log/data/local dirs are visible in the file inventory.",
            "action": "Continue writing release and Helper evidence to runtime, but keep canonical docs in docs/AI/release paths.",
        },
        {
            "severity": "medium",
            "area": "web-surface",
            "finding": f"Control Center/web is the largest source tree ({top_dirs.get('web', {}).get('files', 0)} files including local deps).",
            "evidence": "web/package.json exposes dev, build, lint, and vitest gates.",
            "action": "Keep Control Center panels read-only by default and extend tests whenever evidence payloads change.",
        },
        {
            "severity": "medium",
            "area": "helper-release",
            "finding": "OTClient Helper has a real release-gate pipeline, but live approval must remain explicit.",
            "evidence": "solteria_helper_test_env.ps1, release_gate/goal_audit scripts, Control Center Helper status.",
            "action": "Do not add shortcuts around PromoteLiveCtoa -ApproveLiveDeploy.",
        },
    ]
    return findings


def render_audit_markdown(
    inventory: dict[str, Any],
    validation_evidence: dict[str, Any] | None = None,
) -> str:
    findings = _audit_findings(inventory)
    validation_gate = _validation_gate(validation_evidence)
    lines = [
        "# CTOAi Full Workspace Audit",
        "",
        f"- Generated at UTC: `{inventory['generated_at_utc']}`",
        f"- Root: `{inventory['root']}`",
        f"- Coverage: `{inventory['coverage']['scope']}`",
        f"- Files inventoried: `{inventory['coverage']['file_count']}`",
        f"- Non-regular entries skipped: `{inventory['coverage']['skipped_non_regular_count']}`",
        f"- Git tracked files: `{inventory['coverage']['tracked_file_count']}`",
        f"- Dirty status entries: `{inventory['coverage']['dirty_entry_count']}`",
        "- Runtime JSON inventory: `runtime/audits/ctoai-full-workspace-audit.json`",
        "",
        "## Coverage Note",
        "",
        "The JSON inventory lists every file found under the workspace root, including `.git` internals. "
        "Sensitive-name files are listed by path, size, timestamp, and category only; secret contents are not copied. "
        "Symlinks and other non-regular entries are counted separately and are not opened or hashed.",
        "",
        "## Counts By Category",
        "",
        "| Category | Files | Size |",
        "| --- | ---: | ---: |",
    ]
    bytes_by_category = inventory["bytes_by_category"]
    for category, count in inventory["counts_by_category"].items():
        lines.append(
            f"| `{category}` | {count} | {_mb(int(bytes_by_category.get(category, 0)))} |"
        )

    lines.extend(
        [
            "",
            "## Largest Top-Level Areas",
            "",
            "| Path | Files | Size |",
            "| --- | ---: | ---: |",
        ]
    )
    for path, data in list(inventory["top_directories"].items())[:25]:
        lines.append(f"| `{path}` | {data['files']} | {_mb(int(data['bytes']))} |")

    gate = inventory["audit_gate"]
    lines.extend(
        [
            "",
            "## Audit Integrity Gate",
            "",
            f"- Status: `{gate['status']}`",
            f"- Note: {gate['completion_note']}",
            "",
            "| Check | Status | Evidence |",
            "| --- | --- | --- |",
        ]
    )
    for check in gate["checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['status']}` | {check['evidence']} |"
        )

    lines.extend(
        [
            "",
            "## Validation Evidence Gate",
            "",
            f"- Status: `{validation_gate['status']}`",
            f"- Missing command evidence: `{', '.join(validation_gate['missing']) or '<none>'}`",
            f"- Failed command evidence: `{', '.join(validation_gate['failed']) or '<none>'}`",
        ]
    )
    if validation_evidence is not None:
        lines.extend(
            [
                f"- Evidence generated at UTC: `{validation_evidence['generated_at_utc']}`",
                "",
                "| Command ID | Status | Duration | Summary |",
                "| --- | --- | ---: | --- |",
            ]
        )
        for command in validation_evidence["commands"]:
            lines.append(
                f"| `{command['id']}` | `{command['status']}` | `{command['duration']}` | {command['summary']} |"
            )

    lines.extend(["", "## Findings", ""])
    for finding in findings:
        lines.extend(
            [
                f"### {finding['severity'].upper()}: {finding['area']}",
                "",
                f"- Finding: {finding['finding']}",
                f"- Evidence: {finding['evidence']}",
                f"- Action: {finding['action']}",
                "",
            ]
        )

    lines.extend(
        [
            "## Required Completion Evidence",
            "",
            "The audit inventory and validation evidence gates must both be current before claiming "
            "the full repo-wide objective complete. Keep fresh command evidence for:",
            "",
            "- `python -m pytest tests\\ --ignore=tests\\e2e -q`",
            "- `cd web; npm run lint`",
            "- `cd web; npm test` or the scoped Control Center evidence/action suites changed by the wave",
            "- `git diff --check`",
            "- `.\\ctoa.ps1 brain refresh`",
            "- `.\\ctoa.ps1 brain doctor`",
            "- `.\\ctoa.ps1 brain pack all` or the scoped pack for the active lane",
            "",
            "## File Inventory",
            "",
            "The complete per-file inventory is intentionally stored in JSON instead of this Markdown file:",
            "",
            "- `runtime/audits/ctoai-full-workspace-audit.json`",
        ]
    )
    return "\n".join(lines) + "\n"


def render_plans_markdown(inventory: dict[str, Any]) -> str:
    file_count = inventory["coverage"]["file_count"]
    tracked_count = inventory["coverage"]["tracked_file_count"]
    lines = [
        "# CTOAi Three Development Plans",
        "",
        f"Basis: full workspace audit with `{file_count}` inventoried files and `{tracked_count}` git-tracked files.",
        "",
        "## Plan 1: Helper-First Productization",
        "",
        "Goal: turn the OTClient/Solteria Helper into a safe, repeatable product lane before broad expansion.",
        "",
        "### 0-30 Days",
        "",
        "- Keep `scripts/lua/otclient/` canonical and keep live Solteria protected.",
        "- Require `PrepareDev`, `ValidateDev`, `SmokePreflight`, in-world `SmokeAttachAll`, and explicit live approval.",
        "- Expand `otclient_helper_profile_audit.py` from text checks toward schema-backed migration validation.",
        "- Keep Control Center Helper status read-only and backed by runtime artifacts.",
        "",
        "### 31-60 Days",
        "",
        "- Split `ctoa_native_helper.lua` only along stable boundaries: config/schema, profile persistence, UI, runtime loops, diagnostics.",
        "- Preserve `ctoa_native_helper.lua` as the public loader entrypoint.",
        "- Add stable diagnostics export coverage for HP/MP, movement, combat, magic, container/loot, UI/resources.",
        "",
        "### 61-90 Days",
        "",
        "- Make `SmokeAttachAll` the final visual acceptance source with full in-world screenshots.",
        "- Block `releasable_to_live=true` unless staged package hashes match full in-world evidence.",
        "- Package Helper release notes and evidence as one reviewable artifact.",
        "",
        "## Plan 2: Control Center And Evidence Platform",
        "",
        "Goal: make Control Center the operator cockpit for status, evidence, safe commands, and release confidence.",
        "",
        "### 0-30 Days",
        "",
        "- Normalize evidence paths through `controlCenterEvidenceConfig.ts` and `.env.example`.",
        "- Add tests for every evidence payload shape before adding UI panels.",
        "- Keep Control Center markdown report reads physically size-bounded with file-handle reads of at most `max + 1` bytes, symlink rejection before `open`, `finally` cleanup, and no full-file `readFile` path.",
        "- Keep Control Center release-evidence drilldown metadata bounded too; title extraction must not full-read large markdown artifacts.",
        "- Keep Control Center configured JSON and action-audit reads physically bounded, symlink-rejecting, and fail-closed before any browser-visible evidence payload is built.",
        "- Keep release evidence pack generation on the same bounded, symlink-rejecting local-read contract for configured JSON, action-audit JSONL, release markdown discovery, and Helper dev status.",
        "- Keep Control Center API base URLs origin-only: reject path components, path separators, credentials, query strings, fragments, and non-local HTTP before proxy or browser API calls.",
        "- Keep panels read-only unless actions are explicitly risk-modeled and audited.",
        "- Keep API public registration fail-closed in production; privileged account creation must always require an authenticated owner token.",
        "- Keep production Intel launch targets protected from localhost/private/internal URLs unless `CTOA_ALLOW_PRIVATE_INTEL_TARGETS=true` is explicitly set.",
        "- Keep Intel client-sync write paths confined to `CTOA_CLIENT_SCRIPTS_DIR` and validate target/autoloader/init settings before copying files.",
        "- Keep the static security scan lane active: Bandit high and medium severity must remain zero, discovery TLS must verify by default, remote template sources must stay on public HTTP(S) hosts, and insecure legacy opt-ins must be explicit.",
        "- Keep operator script inputs fail-closed before network calls or child processes: runtime smoke base URLs and LAB003 base URLs stay on loopback HTTP(S), generic alert webhooks must be HTTP(S), Discord-native alert webhooks must stay on allowlisted Discord webhook URLs, Azure Activity listener binds default to loopback and requires `CTOA_AZURE_INGEST_SECRET` for non-loopback hosts, LAB003 child PowerShell launches use the current `$PSHOME` executable, GS reset API URLs/timing values are validated before shutdown or health probes, and direct GS API validator probes stay loopback-only before `urlopen`.",
        "",
        "### 31-60 Days",
        "",
        "- Add release-evidence drilldowns for Helper, repo hygiene, API cost, action audit, and VPS parity.",
        "- Add stale-artifact detection: manifest age, package hash mismatch with Helper dev-lane path containment, missing smoke, missing action audit.",
        "- Add one operator-safe `next` recommendation surface that never bypasses gates.",
        "",
        "### 61-90 Days",
        "",
        "- Turn evidence pack generation into a release prerequisite.",
        "- Add dashboard-level comparison between last released evidence and current runtime evidence.",
        "- Add CI checks for evidence schemas and docs links.",
        "",
        "## Plan 3: Engine Brain And CTOAi Platform",
        "",
        "Goal: make `AI/` the local, secret-safe planning/context layer and evolve it into a reusable CTOAi/Codex capability.",
        "",
        "### 0-30 Days",
        "",
        "- Keep `AI/FEATURE_ROADMAP.md`, `AI/ENGINE_BRAIN_STATUS.md`, and `AI/generated/*` fresh after workflow changes.",
        "- Use `ctoa.ps1 brain refresh`, `brain doctor`, and `brain pack` as the operator workflow.",
        "- Add this full workspace audit as a recurring Engine Brain input.",
        "",
        "### 31-60 Days",
        "",
        "- Generate ownership maps from inventory: path owner, source/runtime/vendor category, validation gate.",
        "- Add stale-doc detection between README, docs index, CLI docs, and command dictionary.",
        "- Add local-only secret guardrails for AI packs and generated context.",
        "",
        "### 61-90 Days",
        "",
        "- Convert the stabilized Engine Brain workflow into a Codex skill or CTOAi plugin.",
        "- Add repo context packs that can target Helper, Control Center, infra, or security lanes.",
        "- Gate plugin design through `AI/generated/P6_CODEX_INTEGRATION_READINESS.md`, generated by `brain refresh` from current local evidence.",
        "- Generate `AI/generated/P7_OPERATOR_WORKFLOW.md` as the read-only P7 risk gate before adding plugin actions.",
        "- Generate `AI/generated/P7_ACTION_READINESS.md` as the audited safe-write candidate gate before enabling plugin write tools.",
        "- Generate `AI/generated/P7_SAFE_WRITE_TOOL_DESIGN.md` as the primary safe-write tool contract and require enabled safe-write MCP tools to match audited evidence/reporting actions.",
        "- Generate `AI/generated/P7_OPERATOR_BRIEF.md` as the read-only daily operator handoff for Control Center and release evidence.",
        "- Keep the local `ctoai-engine-brain` plugin bounded to `ctoai_engine_brain_status`, `ctoai_engine_brain_self_check`, `ctoai_engine_brain_brief`, plus audited `ctoai_evidence_pack_refresh` and `ctoai_api_cost_refresh` safe-write tools.",
        "- Keep deploy/live actions out of the plugin MCP surface; only dry-run-first evidence/reporting refreshes may write, and they must append Control Center action-audit evidence.",
        "- Prepare a plugin-style operator surface for audit, release evidence, and roadmap generation.",
    ]
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_RUNTIME_OUT)
    parser.add_argument("--validation-json", type=Path, default=DEFAULT_VALIDATION_IN)
    parser.add_argument("--audit-md-out", type=Path, default=DEFAULT_MARKDOWN_OUT)
    parser.add_argument("--plans-md-out", type=Path, default=DEFAULT_PLANS_OUT)
    parser.add_argument("--max-hash-bytes", type=int, default=2_000_000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    inventory = build_inventory(max_hash_bytes=args.max_hash_bytes)
    validation_evidence = _load_validation_evidence(args.validation_json)

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(inventory, indent=2), encoding="utf-8")

    args.audit_md_out.parent.mkdir(parents=True, exist_ok=True)
    args.audit_md_out.write_text(
        render_audit_markdown(inventory, validation_evidence),
        encoding="utf-8",
    )

    args.plans_md_out.parent.mkdir(parents=True, exist_ok=True)
    args.plans_md_out.write_text(render_plans_markdown(inventory), encoding="utf-8")

    print(
        json.dumps(
            {
                k: inventory[k]
                for k in ["generated_at_utc", "root", "coverage", "counts_by_category"]
            },
            indent=2,
        )
    )
    print(f"JSON audit written to: {args.json_out}")
    print(f"Markdown audit written to: {args.audit_md_out}")
    print(f"Development plans written to: {args.plans_md_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
