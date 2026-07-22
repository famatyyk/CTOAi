"""Generate secret-safe Engine Brain repository indexes."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import stat
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = ROOT / "AI" / "generated"
DEFAULT_AUDIT_PATH = ROOT / "runtime" / "audits" / "ctoai-full-workspace-audit.json"
DEFAULT_VALIDATION_PATH = (
    ROOT / "runtime" / "audits" / "ctoai-full-workspace-validation.json"
)
DEFAULT_ACTION_AUDIT_PATH = ROOT / "runtime" / "control-center" / "action-audit.jsonl"
DEFAULT_P7_COCKPIT_SMOKE_PATH = ROOT / "runtime" / "control-center" / "p7-cockpit-smoke.json"
DEFAULT_P7_EVIDENCE_REVIEW_PATH = ROOT / "runtime" / "control-center" / "p7-evidence-review.json"
DEFAULT_RELEASE_EVIDENCE_DIR = ROOT / "releases" / "evidence"
DEFAULT_RELEASE_EVIDENCE_LATEST_PATH = ROOT / "runtime" / "evidence" / "latest.json"
DEFAULT_FRESHNESS_POLICY_PATH = ROOT / "AI" / "control-central-freshness-policy.json"
DEFAULT_ACTION_AUDIT_MAX_AGE_SECONDS = 86_400
MIN_ACTION_AUDIT_MAX_AGE_SECONDS = 300
MAX_ACTION_AUDIT_MAX_AGE_SECONDS = 604_800
ACTION_AUDIT_FUTURE_SKEW_SECONDS = 300
MAX_VALIDATION_EVIDENCE_BYTES = 64 * 1024
MAX_ACTION_AUDIT_BYTES = 1024 * 1024
MAX_ACTION_AUDIT_LINE_BYTES = 20_000
VALIDATION_EVIDENCE_SCHEMA_VERSION = 2
VALIDATION_EVIDENCE_MAX_AGE_SECONDS = 86_400
VALIDATION_EVIDENCE_FUTURE_SKEW_SECONDS = 300
ROADMAP_MAX_BYTES = 256 * 1024
ROADMAP_GENERATION_DOCS = {
    "feature_roadmap": {
        "path": "AI/FEATURE_ROADMAP.md",
        "needles": [
            "P6: Codex Integration",
            "P7_OPERATOR_BRIEF.json",
            "Expand the CTOAi plugin beyond these seven registered safe-write MCP tools only after",
            "Registration does not imply readiness: each",
            "candidate remains fail-closed until current plugin, preflight, and audit",
        ],
    },
    "engine_brain_status": {
        "path": "AI/ENGINE_BRAIN_STATUS.md",
        "needles": [
            "P6 Codex Integration",
            "P7 operator brief",
            "plugin-style operator surface",
        ],
    },
    "plan3_roadmap": {
        "path": "docs/roadmaps/CTOAI_THREE_DEVELOPMENT_PLANS_2026-07-06.md",
        "needles": [
            "Prepare a plugin-style operator surface for audit, release evidence, and roadmap generation.",
            "Keep deploy/live actions out of the plugin MCP surface",
        ],
    },
}

EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "__pycache__",
    "node_modules",
    "runtime",
    "logs",
    "data",
    ".pytest_cache",
    ".next",
    "dist",
    "build",
    ".tmp",
}

EXCLUDED_FILES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.preview",
    "auth.json",
}

SECRET_NAME_PATTERNS = (
    ".env.",
    ".env-",
    "secret",
    "token",
    "credential",
    "password",
)

SYMBOL_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx", ".lua", ".ps1"}
TREE_EXTENSIONS = SYMBOL_EXTENSIONS | {
    ".md",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".txt",
    ".otmod",
}

OWNER_RULES = {
    "AI": ("Engine Brain", "brain refresh; brain pack"),
    "agents": ("Agent governance", "pytest tests/ --ignore=tests/e2e"),
    "api": ("API runtime", "pytest tests/ --ignore=tests/e2e"),
    "bot": ("Bot runtime", "pytest tests/ --ignore=tests/e2e"),
    "deploy": ("VPS/deploy", "engine_brain_doctor; deployment smoke"),
    "docs": ("Documentation", "doc sync guard"),
    "mobile_console": ("Mobile console", "pytest tests/ --ignore=tests/e2e"),
    "releases": ("Release evidence", "release_evidence_pack.py"),
    "runner": ("Runner runtime", "pytest tests/ --ignore=tests/e2e"),
    "schemas": ("Contracts", "schema consumers and pytest"),
    "scripts": ("Operator automation", "pytest targeted script tests"),
    "tests": ("Regression suite", "pytest tests/ --ignore=tests/e2e"),
    "web": ("Control Center", "cd web; npm run lint; npm test"),
    "workflows": ("Sprint workflows", "sprint validators"),
}

DOC_SYNC_CHECKS = [
    {
        "name": "brain_cli_docs",
        "path": "docs/CTOA_CLI.md",
        "needles": ["brain refresh", "brain doctor", "brain pack"],
    },
    {
        "name": "otclient_cli_docs",
        "path": "docs/CTOA_CLI.md",
        "needles": ["otprofile", "otdeploy", "otest"],
    },
    {
        "name": "command_dictionary_brain",
        "path": "schemas/ctoa-command-dictionary.json",
        "needles": ['"command": "brain"', "refresh|doctor|pack"],
    },
    {
        "name": "command_dictionary_otclient",
        "path": "schemas/ctoa-command-dictionary.json",
        "needles": [
            '"command": "otprofile"',
            '"command": "otdeploy"',
            '"command": "otest"',
        ],
    },
    {
        "name": "docs_index_plan3_artifacts",
        "path": "docs/INDEX.md",
        "needles": ["Full Workspace Audit", "Three Development Plans"],
    },
    {
        "name": "roadmap_plan3",
        "path": "docs/roadmaps/CTOAI_THREE_DEVELOPMENT_PLANS_2026-07-06.md",
        "needles": [
            "Plan 3: Engine Brain And CTOAi Platform",
            "secret-safe planning/context layer",
        ],
    },
]

P6_REQUIRED_VALIDATION_IDS = {
    "python_non_e2e",
    "web_lint",
    "web_tests",
    "diff_check",
    "brain_refresh",
    "brain_doctor",
    "brain_pack_all",
    "p6_plugin_self_check",
    "p6_plugin_mcp",
    "p7_operator_brief",
    "p7_generated_brief",
}
P6_PLUGIN_NAME = "ctoai-engine-brain"

P7_SAFE_WRITE_ACTION_CANDIDATES = [
    {
        "id": "repo-hygiene-refresh",
        "risk_class": "safe_write",
        "control_center_label": "Refresh repo hygiene snapshot",
        "source": "web/src/lib/controlCenterActions.ts",
        "risk_model": "docs/CTOAI_COMMAND_RISK_MODEL.md",
    },
    {
        "id": "api-cost-refresh",
        "risk_class": "safe_write",
        "control_center_label": "Refresh API cost report",
        "source": "web/src/lib/controlCenterActions.ts",
        "risk_model": "docs/CTOAI_COMMAND_RISK_MODEL.md",
    },
    {
        "id": "evidence-pack-refresh",
        "risk_class": "safe_write",
        "control_center_label": "Rebuild evidence pack",
        "source": "web/src/lib/controlCenterActions.ts",
        "risk_model": "docs/CTOAI_COMMAND_RISK_MODEL.md",
    },
    {
        "id": "engine-brain-refresh",
        "risk_class": "safe_write",
        "control_center_label": "Refresh Engine Brain context",
        "source": "web/src/lib/controlCenterActions.ts",
        "risk_model": "docs/CTOAI_COMMAND_RISK_MODEL.md",
    },
    {
        "id": "p7-cockpit-smoke-refresh",
        "risk_class": "safe_write",
        "control_center_label": "Refresh P7 cockpit smoke",
        "source": "web/src/lib/controlCenterActions.ts",
        "risk_model": "docs/CTOAI_COMMAND_RISK_MODEL.md",
    },
    {
        "id": "roadmap-state-refresh",
        "risk_class": "safe_write",
        "control_center_label": "Refresh adaptive roadmap state",
        "source": "web/src/lib/controlCenterActions.ts",
        "risk_model": "docs/CTOAI_COMMAND_RISK_MODEL.md",
        "native_dry_run": True,
    },
    {
        "id": "full-workspace-validation-refresh",
        "risk_class": "safe_write",
        "control_center_label": "Refresh full workspace validation",
        "source": "web/src/lib/controlCenterActions.ts",
        "risk_model": "docs/CTOAI_COMMAND_RISK_MODEL.md",
        "native_dry_run": True,
    },
]
P7_SELECTED_SAFE_WRITE_ACTION_ID = "evidence-pack-refresh"
P7_SELECTED_SAFE_WRITE_MCP_TOOL = "ctoai_evidence_pack_refresh"
P7_SELECTED_SAFE_WRITE_CONFIRM_TEXT = "refresh evidence pack"
P7_ROADMAP_STATE_ACTION_ID = "roadmap-state-refresh"
P7_ROADMAP_STATE_MCP_TOOL = "ctoai_roadmap_state_refresh"
P7_ROADMAP_STATE_CONFIRM_TEXT = "refresh roadmap state"
P7_FULL_WORKSPACE_VALIDATION_ACTION_ID = "full-workspace-validation-refresh"
P7_FULL_WORKSPACE_VALIDATION_MCP_TOOL = "ctoai_full_workspace_validation_refresh"
P7_FULL_WORKSPACE_VALIDATION_CONFIRM_TEXT = "refresh full workspace validation"
P7_ENABLED_SAFE_WRITE_MCP_TOOLS = {
    "repo-hygiene-refresh": "ctoai_repo_hygiene_refresh",
    "api-cost-refresh": "ctoai_api_cost_refresh",
    "evidence-pack-refresh": "ctoai_evidence_pack_refresh",
    "engine-brain-refresh": "ctoai_engine_brain_refresh",
    "p7-cockpit-smoke-refresh": "ctoai_p7_cockpit_smoke_refresh",
    "roadmap-state-refresh": "ctoai_roadmap_state_refresh",
    "full-workspace-validation-refresh": "ctoai_full_workspace_validation_refresh",
}


@dataclass(frozen=True)
class FileEntry:
    path: Path
    size: int

    @property
    def rel(self) -> str:
        return self.path.relative_to(ROOT).as_posix()


def _is_excluded(path: Path) -> bool:
    parts = set(path.relative_to(ROOT).parts)
    if parts & EXCLUDED_DIRS:
        return True
    name = path.name.lower()
    if name in EXCLUDED_FILES:
        return True
    return any(pattern in name for pattern in SECRET_NAME_PATTERNS)


def iter_files() -> list[FileEntry]:
    files: list[FileEntry] = []
    for dirpath, dirnames, filenames in os.walk(
        ROOT, topdown=True, onerror=lambda _error: None
    ):
        current = Path(dirpath)
        dirnames[:] = [name for name in dirnames if name not in EXCLUDED_DIRS]
        if current != ROOT and _is_excluded(current):
            dirnames[:] = []
            continue
        for filename in filenames:
            path = current / filename
            if _is_excluded(path) or path.suffix.lower() not in TREE_EXTENSIONS:
                continue
            try:
                if not path.is_file():
                    continue
                size = path.stat().st_size
            except OSError:
                continue
            files.append(FileEntry(path=path, size=size))
    return sorted(files, key=lambda item: item.rel.lower())


def python_symbols(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return []

    symbols: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            symbols.append(f"L{node.lineno}: class {node.name}")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = [arg.arg for arg in node.args.args]
            prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
            symbols.append(f"L{node.lineno}: {prefix} {node.name}({', '.join(args)})")
    return sorted(symbols, key=lambda item: int(item.split(":", 1)[0][1:]))


TS_SYMBOL_RE = re.compile(
    r"^\s*(?:export\s+)?(?:async\s+)?(?:function|class|interface|type)\s+([A-Za-z_$][\w$]*)",
)
LUA_SYMBOL_RE = re.compile(
    r"^\s*(?:local\s+function|function)\s+([A-Za-z_][\w_.:]*)|^\s*([A-Za-z_][\w_]*)\s*=\s*\{",
)
PS_SYMBOL_RE = re.compile(r"^\s*function\s+([A-Za-z_][\w-]*)")


def regex_symbols(path: Path, pattern: re.Pattern[str], label: str) -> list[str]:
    symbols: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return symbols
    for lineno, line in enumerate(lines, 1):
        match = pattern.search(line)
        if not match:
            continue
        name = next((group for group in match.groups() if group), "")
        if name:
            symbols.append(f"L{lineno}: {label} {name}")
    return symbols


def symbols_for(path: Path) -> list[str]:
    suffix = path.suffix.lower()
    if suffix == ".py":
        return python_symbols(path)
    if suffix in {".ts", ".tsx", ".js", ".jsx"}:
        return regex_symbols(path, TS_SYMBOL_RE, "symbol")
    if suffix == ".lua":
        return regex_symbols(path, LUA_SYMBOL_RE, "lua")
    if suffix == ".ps1":
        return regex_symbols(path, PS_SYMBOL_RE, "function")
    return []


def render_file_tree(files: list[FileEntry], generated_at: str) -> str:
    lines = [
        "# Engine Brain File Tree",
        "",
        f"Generated at: `{generated_at}`",
        "",
        "Excluded: `.env*`, secrets/tokens/credentials, `.git`, `.venv`,",
        "`node_modules`, `runtime`, `logs`, `data`, `.tmp`, build outputs.",
        "",
        "| Path | Bytes |",
        "|---|---:|",
    ]
    for entry in files:
        lines.append(f"| `{entry.rel}` | {entry.size} |")
    lines.append("")
    return "\n".join(lines)


def render_symbol_map(files: list[FileEntry], generated_at: str) -> str:
    lines = [
        "# Engine Brain Symbol Map",
        "",
        f"Generated at: `{generated_at}`",
        "",
        "This is a lightweight map for navigation, not a full source dump.",
        "",
    ]
    symbol_files = 0
    for entry in files:
        symbols = symbols_for(entry.path)
        if not symbols:
            continue
        symbol_files += 1
        lines.append(f"## `{entry.rel}`")
        lines.append("")
        lines.extend(f"- {symbol}" for symbol in symbols[:80])
        if len(symbols) > 80:
            lines.append(f"- ... {len(symbols) - 80} more symbols omitted")
        lines.append("")
    if symbol_files == 0:
        lines.append("No symbols found.")
        lines.append("")
    return "\n".join(lines)


def read_audit_inventory(audit_path: Path = DEFAULT_AUDIT_PATH) -> dict[str, Any]:
    if not audit_path.exists():
        return {}
    try:
        payload = json.loads(audit_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def top_level_owner(path_name: str) -> tuple[str, str]:
    return OWNER_RULES.get(path_name, ("Local/uncategorized", "manual review"))


def build_ownership_payload(audit: dict[str, Any], generated_at: str) -> dict[str, Any]:
    top_directories = (
        audit.get("top_directories")
        if isinstance(audit.get("top_directories"), dict)
        else {}
    )
    files = audit.get("files") if isinstance(audit.get("files"), list) else []
    category_by_top: dict[str, Counter[str]] = {}
    for item in files:
        if not isinstance(item, dict):
            continue
        path_value = str(item.get("path", ""))
        if not path_value:
            continue
        top = path_value.split("/", 1)[0]
        category = str(item.get("category", "unknown"))
        category_by_top.setdefault(top, Counter())[category] += 1

    areas: list[dict[str, Any]] = []
    for path_name, data in sorted(top_directories.items()):
        if not isinstance(data, dict):
            continue
        categories = dict(sorted(category_by_top.get(path_name, Counter()).items()))
        if set(categories) == {"local_secret_or_sensitive"}:
            continue
        owner, validation_gate = top_level_owner(path_name)
        areas.append(
            {
                "path": path_name,
                "owner": owner,
                "validation_gate": validation_gate,
                "files": int(data.get("files", 0)),
                "bytes": int(data.get("bytes", 0)),
                "categories": categories,
            }
        )

    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "source": display_path(DEFAULT_AUDIT_PATH),
        "status": "ready" if areas else "missing_audit",
        "areas": areas,
    }


def render_ownership_map(payload: dict[str, Any]) -> str:
    lines = [
        "# Engine Brain Ownership Map",
        "",
        f"Generated at: `{payload['generated_at']}`",
        f"Source audit: `{payload['source']}`",
        f"Status: `{payload['status']}`",
        "",
        "| Path | Owner | Validation gate | Files | Categories |",
        "|---|---|---|---:|---|",
    ]
    for area in payload["areas"]:
        categories = ", ".join(
            f"{key}:{value}" for key, value in area["categories"].items()
        )
        lines.append(
            f"| `{area['path']}` | {area['owner']} | `{area['validation_gate']}` | {area['files']} | {categories} |"
        )
    lines.append("")
    return "\n".join(lines)


def build_doc_sync_payload(generated_at: str) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    for check in DOC_SYNC_CHECKS:
        path = ROOT / check["path"]
        text = (
            path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
        )
        missing = [needle for needle in check["needles"] if needle not in text]
        checks.append(
            {
                "name": check["name"],
                "path": check["path"],
                "status": "passed" if path.exists() and not missing else "blocked",
                "missing": missing,
            }
        )
    status = (
        "passed" if all(check["status"] == "passed" for check in checks) else "blocked"
    )
    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "status": status,
        "checks": checks,
    }


def render_doc_sync(payload: dict[str, Any]) -> str:
    lines = [
        "# Engine Brain Doc Sync",
        "",
        f"Generated at: `{payload['generated_at']}`",
        f"Status: `{payload['status']}`",
        "",
        "| Check | Path | Status | Missing |",
        "|---|---|---|---|",
    ]
    for check in payload["checks"]:
        missing = ", ".join(f"`{item}`" for item in check["missing"]) or "-"
        lines.append(
            f"| `{check['name']}` | `{check['path']}` | `{check['status']}` | {missing} |"
        )
    lines.append("")
    return "\n".join(lines)


def build_secret_guardrail_payload(
    generated_at: str, audit: dict[str, Any], generated_paths: list[Path]
) -> dict[str, Any]:
    files = audit.get("files") if isinstance(audit.get("files"), list) else []
    sensitive_paths = [
        str(item.get("path", ""))
        for item in files
        if isinstance(item, dict)
        and item.get("category") == "local_secret_or_sensitive"
    ]
    scanned: list[dict[str, Any]] = []
    leaks: list[dict[str, str]] = []
    for path in generated_paths:
        if not path.exists() or path.suffix.lower() not in {".md", ".json"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        hits = [
            secret_path
            for secret_path in sensitive_paths
            if secret_path and exact_path_appears(text, secret_path)
        ]
        scanned.append({"path": display_path(path), "hits": len(hits)})
        for hit in hits:
            leaks.append({"generated_path": display_path(path), "sensitive_path": hit})

    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "status": "passed" if not leaks else "blocked",
        "sensitive_path_count": len(sensitive_paths),
        "scanned": scanned,
        "leaks": leaks,
        "policy": "Generated Engine Brain context must not include exact local sensitive/env paths or secret contents.",
    }


def exact_path_appears(text: str, path_value: str) -> bool:
    escaped = re.escape(path_value)
    pattern = rf"(?<![A-Za-z0-9_./\\-]){escaped}(?![A-Za-z0-9_*./\\-])"
    return re.search(pattern, text) is not None


def render_secret_guardrail(payload: dict[str, Any]) -> str:
    lines = [
        "# Engine Brain Secret Guardrail",
        "",
        f"Generated at: `{payload['generated_at']}`",
        f"Status: `{payload['status']}`",
        f"Sensitive/local env path count in audit: `{payload['sensitive_path_count']}`",
        "",
        payload["policy"],
        "",
        "| Generated path | Exact sensitive path hits |",
        "|---|---:|",
    ]
    for item in payload["scanned"]:
        lines.append(f"| `{item['path']}` | {item['hits']} |")
    if payload["leaks"]:
        lines.extend(["", "## Leaks", ""])
        for leak in payload["leaks"]:
            lines.append(
                f"- `{leak['generated_path']}` includes `{leak['sensitive_path']}`"
            )
    lines.append("")
    return "\n".join(lines)


class _EvidenceReadError(ValueError):
    """A bounded local-evidence read failed without exposing source contents."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in payload:
            raise ValueError("duplicate_json_key")
        payload[key] = value
    return payload


def _reject_non_finite_json_number(value: str) -> None:
    raise ValueError(f"non_finite_json_number:{value}")


def _is_reparse_path(path: Path) -> bool:
    """Reject symlinks and Windows reparse points before reading evidence."""

    try:
        info = path.lstat()
    except OSError:
        return True
    attributes = getattr(info, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(info.st_mode) or bool(attributes & reparse_flag)


def _read_bounded_regular_file(path: Path, *, max_bytes: int) -> bytes:
    """Read one stable regular evidence file without following a link."""

    try:
        before = path.lstat()
    except FileNotFoundError as exc:
        raise _EvidenceReadError("missing") from exc
    except OSError as exc:
        raise _EvidenceReadError("unreadable") from exc
    if _is_reparse_path(path) or not stat.S_ISREG(before.st_mode):
        raise _EvidenceReadError("regular_file_required")
    if before.st_size > max_bytes:
        raise _EvidenceReadError("file_too_large")
    try:
        raw = path.read_bytes()
        after = path.lstat()
    except OSError as exc:
        raise _EvidenceReadError("unreadable") from exc
    if (
        _is_reparse_path(path)
        or not stat.S_ISREG(after.st_mode)
        or before.st_size != after.st_size
        or after.st_size != len(raw)
        or before.st_mtime_ns != after.st_mtime_ns
        or getattr(before, "st_ino", 0) != getattr(after, "st_ino", 0)
    ):
        raise _EvidenceReadError("file_changed_during_read")
    if len(raw) > max_bytes:
        raise _EvidenceReadError("file_too_large")
    return raw


def _strict_json_object(raw: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(
            raw.decode("utf-8-sig"),
            object_pairs_hook=_reject_duplicate_json_keys,
            parse_constant=_reject_non_finite_json_number,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise _EvidenceReadError("invalid_json") from exc
    if not isinstance(payload, dict):
        raise _EvidenceReadError("json_object_required")
    return payload


def _parse_utc_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _as_utc(value: datetime | None = None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        return current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc)


def _validation_evidence_policy(
    payload: dict[str, Any], *, now: datetime | None = None
) -> tuple[bool, str]:
    """Require current, successful evidence before P6/P7 can consume it."""

    if payload.get("schema_version") != VALIDATION_EVIDENCE_SCHEMA_VERSION:
        return False, "schema_version_invalid"
    if payload.get("status") != "passed":
        return False, "top_level_status_not_passed"
    if not isinstance(payload.get("commands"), list):
        return False, "commands_invalid"
    generated_at = _parse_utc_timestamp(payload.get("generated_at_utc"))
    if generated_at is None:
        return False, "generated_at_invalid"
    age_seconds = (_as_utc(now) - generated_at).total_seconds()
    if age_seconds < -VALIDATION_EVIDENCE_FUTURE_SKEW_SECONDS:
        return False, "generated_at_future"
    if age_seconds > VALIDATION_EVIDENCE_MAX_AGE_SECONDS:
        return False, "generated_at_stale"
    return True, "passed"


def read_validation_evidence(
    validation_path: Path = DEFAULT_VALIDATION_PATH,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    try:
        payload = _strict_json_object(
            _read_bounded_regular_file(
                validation_path,
                max_bytes=MAX_VALIDATION_EVIDENCE_BYTES,
            )
        )
    except _EvidenceReadError:
        return {}
    valid, _reason = _validation_evidence_policy(payload, now=now)
    return payload if valid else {}


def _path_check(name: str, path: str) -> dict[str, str]:
    exists = (ROOT / path).exists()
    return {
        "name": name,
        "status": "passed" if exists else "blocked",
        "evidence": path if exists else f"missing: {path}",
    }


def _source_needles_check(name: str, path: str, needles: list[str]) -> dict[str, Any]:
    source_path = ROOT / path
    try:
        text = source_path.read_text(encoding="utf-8")
    except OSError:
        return {
            "name": name,
            "status": "blocked",
            "evidence": f"missing: {path}",
            "missing": needles,
        }

    missing = [needle for needle in needles if needle not in text]
    return {
        "name": name,
        "status": "passed" if not missing else "blocked",
        "evidence": path if not missing else f"{path} missing contract markers",
        "missing": missing,
    }


def _local_codex_skill_check() -> dict[str, str]:
    path = Path.home() / ".codex" / "skills" / "ctoa-engine-brain" / "SKILL.md"
    exists = path.exists()
    return {
        "name": "engine_brain_skill_source",
        "status": "passed" if exists else "blocked",
        "evidence": "codex_home/skills/ctoa-engine-brain/SKILL.md"
        if exists
        else "missing local ctoa-engine-brain skill",
    }


def _local_plugin_file_check(name: str, relative_path: str) -> dict[str, str]:
    path = Path.home() / "plugins" / P6_PLUGIN_NAME / relative_path
    exists = path.exists()
    return {
        "name": name,
        "status": "passed" if exists else "blocked",
        "evidence": (
            f"home/plugins/{P6_PLUGIN_NAME}/{relative_path}"
            if exists
            else f"missing home/plugins/{P6_PLUGIN_NAME}/{relative_path}"
        ),
    }


def _local_plugin_source_needles_check(
    name: str, relative_path: str, needles: list[str]
) -> dict[str, Any]:
    plugin_path = Path.home() / "plugins" / P6_PLUGIN_NAME / relative_path
    try:
        text = plugin_path.read_text(encoding="utf-8")
    except OSError:
        return {
            "name": name,
            "status": "blocked",
            "evidence": f"missing home/plugins/{P6_PLUGIN_NAME}/{relative_path}",
            "missing": needles,
        }
    missing = [needle for needle in needles if needle not in text]
    return {
        "name": name,
        "status": "passed" if not missing else "blocked",
        "evidence": (
            f"home/plugins/{P6_PLUGIN_NAME}/{relative_path}"
            if not missing
            else f"home/plugins/{P6_PLUGIN_NAME}/{relative_path} missing contract markers"
        ),
        "missing": missing,
    }


def _read_local_plugin_manifest() -> dict[str, Any]:
    manifest_path = (
        Path.home() / "plugins" / P6_PLUGIN_NAME / ".codex-plugin" / "plugin.json"
    )
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _installed_plugin_cache_check() -> dict[str, str]:
    manifest = _read_local_plugin_manifest()
    version = str(manifest.get("version") or "").strip()
    if not version:
        return {
            "name": "ctoai_plugin_installed_cache",
            "status": "blocked",
            "evidence": "missing local plugin version",
        }
    cache_manifest_path = (
        Path.home()
        / ".codex"
        / "plugins"
        / "cache"
        / "personal"
        / P6_PLUGIN_NAME
        / version
        / ".codex-plugin"
        / "plugin.json"
    )
    try:
        cached = json.loads(cache_manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "name": "ctoai_plugin_installed_cache",
            "status": "blocked",
            "evidence": f"missing installed cache for {version}",
        }
    cache_root = cache_manifest_path.parents[1]
    required_files = [
        ".mcp.json",
        ".codex-plugin/plugin.json",
        "skills/ctoai-engine-brain-operator/SKILL.md",
        "scripts/ctoai_control_center_cockpit.py",
        "scripts/ctoai_engine_brain_brief.py",
        "scripts/ctoai_engine_brain_mcp.py",
        "scripts/ctoai_engine_brain_status.py",
        "scripts/ctoai_engine_brain_self_check.py",
    ]
    missing = [
        relative for relative in required_files if not (cache_root / relative).exists()
    ]
    ok = (
        cached.get("name") == P6_PLUGIN_NAME
        and cached.get("version") == version
        and not missing
    )
    return {
        "name": "ctoai_plugin_installed_cache",
        "status": "passed" if ok else "blocked",
        "evidence": f"installed personal cache version {version}"
        if ok
        else "installed cache manifest or files mismatch",
    }


def _plugin_mcp_absolute_script_check() -> dict[str, str]:
    plugin_root = Path.home() / "plugins" / P6_PLUGIN_NAME
    mcp_path = plugin_root / ".mcp.json"
    expected_script = plugin_root / "scripts" / "ctoai_engine_brain_mcp.py"
    try:
        payload = json.loads(mcp_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "name": "ctoai_plugin_mcp_absolute_script",
            "status": "blocked",
            "evidence": "missing or invalid home/plugins/ctoai-engine-brain/.mcp.json",
        }
    servers = payload.get("mcpServers") if isinstance(payload, dict) else {}
    server = (
        servers.get(P6_PLUGIN_NAME)
        if isinstance(servers, dict) and isinstance(servers.get(P6_PLUGIN_NAME), dict)
        else {}
    )
    args = server.get("args") if isinstance(server.get("args"), list) else []
    try:
        expected_resolved = expected_script.resolve(strict=True)
    except OSError:
        expected_resolved = None
    has_absolute_script = False
    if expected_resolved is not None:
        for arg in args:
            if not isinstance(arg, str):
                continue
            arg_path = Path(arg)
            if not arg_path.is_absolute():
                continue
            try:
                has_absolute_script = arg_path.resolve(strict=True) == expected_resolved
            except OSError:
                has_absolute_script = False
            if has_absolute_script:
                break
    ok = (
        server.get("type") == "stdio"
        and server.get("command") == "python"
        and has_absolute_script
    )
    return {
        "name": "ctoai_plugin_mcp_absolute_script",
        "status": "passed" if ok else "blocked",
        "evidence": "absolute MCP script path is runnable"
        if ok
        else "MCP config must use an absolute runnable ctoai_engine_brain_mcp.py path",
    }


def _personal_marketplace_plugin_check() -> dict[str, str]:
    marketplace_path = Path.home() / ".agents" / "plugins" / "marketplace.json"
    evidence = "personal marketplace entry"
    try:
        payload = json.loads(marketplace_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "name": "ctoai_plugin_marketplace_entry",
            "status": "blocked",
            "evidence": "missing or invalid personal marketplace",
        }
    plugins = payload.get("plugins") if isinstance(payload, dict) else None
    if not isinstance(plugins, list):
        return {
            "name": "ctoai_plugin_marketplace_entry",
            "status": "blocked",
            "evidence": "personal marketplace has no plugins array",
        }
    expected_path = f"./plugins/{P6_PLUGIN_NAME}"
    for entry in plugins:
        if not isinstance(entry, dict) or entry.get("name") != P6_PLUGIN_NAME:
            continue
        source = entry.get("source") if isinstance(entry.get("source"), dict) else {}
        policy = entry.get("policy") if isinstance(entry.get("policy"), dict) else {}
        ok = (
            source.get("source") == "local"
            and source.get("path") == expected_path
            and policy.get("installation") == "AVAILABLE"
            and policy.get("authentication") == "ON_INSTALL"
        )
        return {
            "name": "ctoai_plugin_marketplace_entry",
            "status": "passed" if ok else "blocked",
            "evidence": evidence if ok else "marketplace entry policy/source mismatch",
        }
    return {
        "name": "ctoai_plugin_marketplace_entry",
        "status": "blocked",
        "evidence": f"missing {P6_PLUGIN_NAME} entry",
    }


def _validation_evidence_check(validation: dict[str, Any]) -> dict[str, Any]:
    evidence_valid, evidence_error = _validation_evidence_policy(validation)
    commands = (
        validation.get("commands")
        if isinstance(validation.get("commands"), list)
        else []
    )
    by_id = {
        str(command.get("id")): command
        for command in commands
        if isinstance(command, dict) and command.get("id")
    }
    missing = sorted(P6_REQUIRED_VALIDATION_IDS - set(by_id))
    failed = sorted(
        command_id
        for command_id, command in by_id.items()
        if command_id in P6_REQUIRED_VALIDATION_IDS
        and command.get("status") not in {"passed", "warn"}
    )
    status = "passed" if evidence_valid and not missing and not failed else "blocked"
    return {
        "name": "full_workspace_validation_evidence",
        "status": status,
        "evidence": display_path(DEFAULT_VALIDATION_PATH)
        if status == "passed"
        else "missing, invalid, or failed command evidence",
        "missing": missing,
        "failed": failed,
        "evidence_error": "" if evidence_valid else evidence_error,
    }


def build_p6_readiness_payload(
    generated_at: str,
    manifest_payload: dict[str, object],
    validation: dict[str, Any],
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = [
        _path_check("ai_agents_instruction", "AI/AGENTS.md"),
        _path_check("lua_agents_instruction", "scripts/lua/AGENTS.md"),
        _local_codex_skill_check(),
        _local_plugin_file_check("ctoai_plugin_manifest", ".codex-plugin/plugin.json"),
        _local_plugin_file_check(
            "ctoai_plugin_brief_script",
            "scripts/ctoai_engine_brain_brief.py",
        ),
        _local_plugin_file_check("ctoai_plugin_mcp_config", ".mcp.json"),
        _plugin_mcp_absolute_script_check(),
        _local_plugin_file_check(
            "ctoai_plugin_mcp_server",
            "scripts/ctoai_engine_brain_mcp.py",
        ),
        _local_plugin_file_check(
            "ctoai_plugin_operator_skill",
            "skills/ctoai-engine-brain-operator/SKILL.md",
        ),
        _local_plugin_file_check(
            "ctoai_plugin_status_script",
            "scripts/ctoai_engine_brain_status.py",
        ),
        _local_plugin_file_check(
            "ctoai_plugin_control_center_cockpit_script",
            "scripts/ctoai_control_center_cockpit.py",
        ),
        _local_plugin_file_check(
            "ctoai_plugin_control_central_script",
            "scripts/ctoai_control_central.py",
        ),
        _local_plugin_file_check(
            "ctoai_plugin_self_check_script",
            "scripts/ctoai_engine_brain_self_check.py",
        ),
        _local_plugin_source_needles_check(
            "ctoai_plugin_p7_workflow_status_contract",
            "scripts/ctoai_engine_brain_status.py",
            [
                "P7_OPERATOR_WORKFLOW.json",
                "p7_operator_workflow",
                "p7_operator_workflow_status",
            ],
        ),
        _local_plugin_source_needles_check(
            "ctoai_plugin_p7_workflow_brief_contract",
            "scripts/ctoai_engine_brain_brief.py",
            ["operator_workflow", "blocked_action_classes", "allowed_tool_count"],
        ),
        _local_plugin_source_needles_check(
            "ctoai_plugin_operator_brief_cockpit_handoff_contract",
            "scripts/ctoai_engine_brain_brief.py",
            [
                "ctoai_control_center_cockpit.build_cockpit",
                "cockpit_handoff",
                "p7_cockpit_smoke",
                "p7_safe_write_dry_run_smoke",
                "release_evidence",
                "action_audit",
                "roadmap_generation",
                "recommended_tool_order",
                "ctoai_evidence_pack_refresh dry_run=true",
            ],
        ),
        _local_plugin_source_needles_check(
            "ctoai_plugin_control_center_cockpit_mcp_contract",
            "scripts/ctoai_engine_brain_mcp.py",
            [
                "ctoai_control_center_cockpit",
                "ctoai_control_center_cockpit.build_cockpit",
                "cockpit_preflight",
                "Control Center cockpit preflight",
                "operator_next",
                "runtime evidence",
                "action audit",
                "p7_cockpit_smoke",
                "p7_safe_write_dry_run_smoke",
            ],
        ),
        _local_plugin_source_needles_check(
            "ctoai_plugin_control_central_mcp_contract",
            "scripts/ctoai_engine_brain_mcp.py",
            [
                "ctoai_control_central",
                "ctoai_control_central.build_control_central",
                "control_central_schema",
                "profile",
                "detail",
            ],
        ),
        _local_plugin_source_needles_check(
            "ctoai_plugin_control_center_cockpit_drilldown_contract",
            "scripts/ctoai_control_center_cockpit.py",
            [
                "release_evidence_drilldown",
                "action_audit_drilldown",
                "ACTION_AUDIT_MAX_BYTES",
                "MARKDOWN_TITLE_MAX_BYTES",
                "recent_files",
                "recent_records",
                "source_bytes",
                "sampled_bytes",
                "roadmap_generation_status",
                "build_operator_next_recommendation",
                "operator_next",
                "is_guarded_live_command",
                "DOC_SYNC.json",
                "AI/FEATURE_ROADMAP.md",
                "CTOAI_THREE_DEVELOPMENT_PLANS_2026-07-06.md",
                "blocked_until",
            ],
        ),
        _local_plugin_source_needles_check(
            "ctoai_plugin_control_center_cockpit_self_check_contract",
            "scripts/ctoai_engine_brain_self_check.py",
            [
                "scripts/ctoai_control_center_cockpit.py",
                "control_center_cockpit_script",
                "p7_cockpit_smoke",
                "p7_safe_write_dry_run_smoke",
                "runtime/control-center/p7-cockpit-smoke.json",
                "runtime/control-center/p7-safe-write-dry-run-smoke.json",
            ],
        ),
        _local_plugin_source_needles_check(
            "ctoai_plugin_p7_action_readiness_status_contract",
            "scripts/ctoai_engine_brain_status.py",
            [
                "P7_ACTION_READINESS.json",
                "p7_action_readiness",
                "mcp_write_tool_count",
                "enabled_safe_write_tools",
            ],
        ),
        _local_plugin_source_needles_check(
            "ctoai_plugin_p7_action_readiness_brief_contract",
            "scripts/ctoai_engine_brain_brief.py",
            [
                "action_readiness",
                "candidate_count",
                "mcp_write_tool_count",
                "enabled_safe_write_tools",
            ],
        ),
        _local_plugin_source_needles_check(
            "ctoai_plugin_p7_safe_write_design_status_contract",
            "scripts/ctoai_engine_brain_status.py",
            [
                "P7_SAFE_WRITE_TOOL_DESIGN.json",
                "p7_safe_write_tool_design",
                "mcp_enabled",
            ],
        ),
        _local_plugin_source_needles_check(
            "ctoai_plugin_p7_safe_write_design_brief_contract",
            "scripts/ctoai_engine_brain_brief.py",
            ["safe_write_tool_design", "selected_action_id", "proposed_mcp_tool"],
        ),
        _local_plugin_source_needles_check(
            "ctoai_plugin_repo_hygiene_refresh_mcp_contract",
            "scripts/ctoai_engine_brain_mcp.py",
            [
                "REPO_HYGIENE_TOOL_NAME",
                "ctoai_repo_hygiene_refresh",
                "run_repo_hygiene_refresh",
                "repo_hygiene_audit.py",
                "dry_run",
                "refresh repo hygiene snapshot",
            ],
        ),
        _local_plugin_source_needles_check(
            "ctoai_plugin_evidence_pack_refresh_mcp_contract",
            "scripts/ctoai_engine_brain_mcp.py",
            [
                "EVIDENCE_TOOL_NAME",
                "ctoai_evidence_pack_refresh",
                "run_evidence_pack_refresh",
                "append_action_audit",
                "dry_run",
                "refresh evidence pack",
            ],
        ),
        _local_plugin_source_needles_check(
            "ctoai_plugin_api_cost_refresh_mcp_contract",
            "scripts/ctoai_engine_brain_mcp.py",
            [
                "API_COST_TOOL_NAME",
                "ctoai_api_cost_refresh",
                "run_api_cost_refresh",
                "api_cost_report.py",
                "dry_run",
                "refresh api cost report",
            ],
        ),
        _local_plugin_source_needles_check(
            "ctoai_plugin_engine_brain_refresh_mcp_contract",
            "scripts/ctoai_engine_brain_mcp.py",
            [
                "ENGINE_BRAIN_TOOL_NAME",
                "ctoai_engine_brain_refresh",
                "run_engine_brain_refresh",
                "engine_brain_index.py",
                "dry_run",
                "refresh engine brain context",
            ],
        ),
        _local_plugin_source_needles_check(
            "ctoai_plugin_p7_cockpit_smoke_refresh_mcp_contract",
            "scripts/ctoai_engine_brain_mcp.py",
            [
                "P7_COCKPIT_SMOKE_TOOL_NAME",
                "ctoai_p7_cockpit_smoke_refresh",
                "run_p7_cockpit_smoke_refresh",
                "control_center_p7_cockpit_smoke.py",
                "dry_run",
                "refresh p7 cockpit smoke",
            ],
        ),
        _local_plugin_source_needles_check(
            "ctoai_plugin_roadmap_state_refresh_mcp_contract",
            "scripts/ctoai_engine_brain_mcp.py",
            [
                "ROADMAP_STATE_TOOL_NAME",
                "ctoai_roadmap_state_refresh",
                "run_roadmap_state_refresh",
                "ctoai_roadmap_state.py",
                '"native_dry_run": True',
                "refresh roadmap state",
            ],
        ),
        _local_plugin_source_needles_check(
            "ctoai_plugin_full_workspace_validation_refresh_mcp_contract",
            "scripts/ctoai_engine_brain_mcp.py",
            [
                "FULL_VALIDATION_TOOL_NAME",
                "ctoai_full_workspace_validation_refresh",
                "run_full_workspace_validation_refresh",
                "ctoa_full_workspace_validation.py",
                '"native_dry_run": True',
                "refresh full workspace validation",
            ],
        ),
        _local_plugin_source_needles_check(
            "ctoai_plugin_p6_handoff_smoke_status_contract",
            "scripts/ctoai_engine_brain_status.py",
            [
                "p6_plugin_handoff_smoke_path",
                "p6-plugin-handoff-smoke.json",
                "p6_plugin_handoff_smoke",
                "current_thread_tool_discovery_status",
            ],
        ),
        _local_plugin_source_needles_check(
            "ctoai_plugin_p6_handoff_smoke_cockpit_contract",
            "scripts/ctoai_control_center_cockpit.py",
            [
                "summarize_p6_plugin_handoff_smoke",
                "p6_plugin_handoff_smoke",
                "missing_p6_plugin_handoff_smoke",
                "p6_plugin_handoff_smoke_not_ready",
                "p6-plugin-handoff-smoke.json",
            ],
        ),
        _local_plugin_source_needles_check(
            "ctoai_plugin_p6_handoff_smoke_brief_contract",
            "scripts/ctoai_engine_brain_brief.py",
            [
                "p6_plugin_handoff_smoke",
                "current_thread_tool_discovery_status",
                "fresh_thread_verification_status",
                "ctoai_engine_brain_self_check",
            ],
        ),
        _local_plugin_source_needles_check(
            "ctoai_plugin_p6_handoff_smoke_self_check_contract",
            "scripts/ctoai_engine_brain_self_check.py",
            [
                "p6_plugin_handoff_smoke_status",
                "p6_plugin_handoff_smoke",
                "missing_p6_plugin_handoff_smoke",
                "contracts={passed_mcp_contract_count}/{mcp_contract_count}",
            ],
        ),
        _local_plugin_source_needles_check(
            "ctoai_plugin_bounded_write_policy_contract",
            "scripts/ctoai_engine_brain_self_check.py",
            ["bounded_write_policy", "safe-write", "audit"],
        ),
        _source_needles_check(
            "ctoai_plugin_p7_cockpit_smoke_contract_tests",
            "tests/test_engine_brain_index.py",
            [
                "p7_cockpit_smoke",
                "missing_p7_cockpit_smoke",
                "p7_safe_write_dry_run_smoke",
                "missing_p7_safe_write_dry_run_smoke",
                "engine-brain-refresh",
                "ctoai_engine_brain_refresh",
                "p7-cockpit-smoke-refresh",
                "ctoai_p7_cockpit_smoke_refresh",
                "roadmap-state-refresh",
                "ctoai_roadmap_state_refresh",
                "full-workspace-validation-refresh",
                "ctoai_full_workspace_validation_refresh",
                "preflight",
                "runtime/control-center/p7-cockpit-smoke.json",
                "runtime/control-center/p7-safe-write-dry-run-smoke.json",
            ],
        ),
        _personal_marketplace_plugin_check(),
        _installed_plugin_cache_check(),
        _path_check(
            "control_center_evidence_contract", "web/src/lib/controlCenterEvidence.ts"
        ),
        _path_check(
            "control_center_evidence_tests",
            "web/src/lib/__tests__/controlCenterEvidence.test.ts",
        ),
        _path_check(
            "control_center_p7_cockpit_smoke_script",
            "scripts/ops/control_center_p7_cockpit_smoke.py",
        ),
        _source_needles_check(
            "control_center_p7_cockpit_smoke_tests",
            "tests/test_control_center_p7_cockpit_smoke.py",
            [
                "test_p7_cockpit_smoke_reports_ready",
                "action_audit_missing_ready_safe_write_record",
                "workflow_tool_policy_mismatch",
                "missing_or_invalid_operator_brief",
            ],
        ),
        _path_check(
            "control_center_p7_safe_write_dry_run_smoke_script",
            "scripts/ops/control_center_p7_safe_write_dry_run_smoke.py",
        ),
        _source_needles_check(
            "control_center_p7_safe_write_dry_run_smoke_tests",
            "tests/test_control_center_p7_safe_write_dry_run_smoke.py",
            [
                "test_safe_write_dry_run_smoke_reports_ready",
                "test_safe_write_dry_run_smoke_blocks_forbidden_tool",
                "dry_run_ready_count",
                "mcp_tool_policy_mismatch",
            ],
        ),
        _path_check(
            "control_center_full_workspace_validation_script",
            "scripts/ops/ctoa_full_workspace_validation.py",
        ),
        _source_needles_check(
            "control_center_full_workspace_validation_tests",
            "tests/test_ctoa_full_workspace_validation.py",
            [
                "test_dry_run_never_executes_or_writes",
                "test_confirmed_run_writes_bounded_fixed_registry_evidence",
                "test_failed_entry_is_recorded_without_sensitive_output",
                "test_confirmed_run_requires_exact_confirmation",
            ],
        ),
        _path_check(
            "control_center_p7_evidence_review_script",
            "scripts/ops/control_center_p7_evidence_review.py",
        ),
        _source_needles_check(
            "control_center_p7_evidence_review_tests",
            "tests/test_control_center_p7_evidence_review.py",
            [
                "test_p7_evidence_review_reports_ready",
                "missing_confirmed_evidence_pack_audit",
                "ready_to_design_next_p7_plugin_action",
            ],
        ),
        _path_check(
            "control_center_p6_plugin_handoff_smoke_script",
            "scripts/ops/control_center_p6_plugin_handoff_smoke.py",
        ),
        _source_needles_check(
            "control_center_p6_plugin_handoff_smoke_tests",
            "tests/test_control_center_p6_plugin_handoff_smoke.py",
            [
                "test_p6_plugin_handoff_smoke_reports_ready",
                "test_p6_plugin_handoff_smoke_blocks_version_mismatch",
                "current_thread_tool_discovery_status",
                "plugin_manifest_version_mismatch",
            ],
        ),
        _source_needles_check(
            "control_center_safe_write_action_catalog",
            "web/src/lib/controlCenterActions.ts",
            [
                'id: "repo-hygiene-refresh"',
                'id: "api-cost-refresh"',
                'id: "evidence-pack-refresh"',
                'id: "engine-brain-refresh"',
                'id: "p7-cockpit-smoke-refresh"',
                'id: "roadmap-state-refresh"',
                'id: "full-workspace-validation-refresh"',
                'riskClass: "safe_write"',
                "appendAuditRecord",
            ],
        ),
        _source_needles_check(
            "control_center_p7_operator_brief_config",
            "web/src/lib/controlCenterEvidenceConfig.ts",
            [
                "engineBrainP6ReadinessPath",
                "CTOA_ENGINE_BRAIN_P6_READINESS_PATH",
                "AI/generated/P6_CODEX_INTEGRATION_READINESS.json",
                "engineBrainP6PluginHandoffSmokePath",
                "CTOA_ENGINE_BRAIN_P6_PLUGIN_HANDOFF_SMOKE_PATH",
                "runtime/control-center/p6-plugin-handoff-smoke.json",
                "engineBrainOperatorBriefPath",
                "CTOA_ENGINE_BRAIN_OPERATOR_BRIEF_PATH",
                "AI/generated/P7_OPERATOR_BRIEF.json",
                "engineBrainP7CockpitSmokePath",
                "CTOA_ENGINE_BRAIN_P7_COCKPIT_SMOKE_PATH",
                "runtime/control-center/p7-cockpit-smoke.json",
                "engineBrainP7SafeWriteDryRunSmokePath",
                "CTOA_ENGINE_BRAIN_P7_SAFE_WRITE_DRY_RUN_SMOKE_PATH",
                "runtime/control-center/p7-safe-write-dry-run-smoke.json",
            ],
        ),
        _source_needles_check(
            "control_center_p7_operator_brief_payload",
            "web/src/lib/controlCenterEvidence.ts",
            [
                "config.engineBrainP6ReadinessPath",
                "config.engineBrainP6PluginHandoffSmokePath",
                "collectP6PluginHandoff",
                "p6PluginHandoff",
                "p6PluginHandoffSmokePayload",
                "smokeStatus",
                "freshThreadRecommendedToolOrder",
                "currentThreadToolDiscoveryStatus",
                "config.engineBrainOperatorBriefPath",
                "p7OperatorBriefStatus",
                "p7NextSafeCommand",
                "p7ActionReadinessStatus",
                "p7SafeWriteToolDesignStatus",
                "p7SafeWriteAudit",
                "p7McpWriteToolCount",
                "p7EnabledSafeWriteToolCount",
                "p7ReadySafeWriteAuditCount",
                "p7OperatorCockpitSummary",
                "p7EnabledSafeWriteTools",
                "p7CockpitSmoke",
                "p7SafeWriteDryRunSmoke",
                "operatorBrief",
                "cockpitHandoff",
                "operatorNext",
                "sourcePaths",
            ],
        ),
        _source_needles_check(
            "control_center_p7_operator_brief_ops",
            "web/src/lib/controlCenterOps.ts",
            [
                "engine-brain",
                "summarizeEngineBrain",
                "p6PluginHandoff",
                "P6 smoke",
                "p7OperatorBriefStatus",
                "p7ActionAuditedCandidateCount",
                "p7SafeWriteAudit",
                "p7EnabledSafeWriteToolCount",
                "p7ReadySafeWriteAuditCount",
                "p7OperatorCockpitSummary",
                "p7CockpitSmoke",
                "operatorNext",
            ],
        ),
        _source_needles_check(
            "control_center_p7_operator_brief_ui",
            "web/src/components/ControlCenterEvidencePanel.tsx",
            [
                "Operator next",
                "P6 plugin",
                "P6 plugin handoff",
                "P6 plugin handoff smoke",
                "freshThreadRequired",
                "freshThreadRecommendedToolOrder",
                "currentThreadToolDiscoveryStatus",
                "runtime/control-center/p6-plugin-handoff-smoke.json",
                "AI/generated/P6_CODEX_INTEGRATION_READINESS.json",
                "P7 operator brief",
                "AI/generated/P7_OPERATOR_BRIEF.json",
                "Recommended tool order",
                "cockpitHandoff",
                "P7 operator handoff",
                "p7OperatorBriefStatus",
                "p7NextSafeCommand",
                "P7 action gate",
                "P7 cockpit status",
                "Safe-write design",
                "Safe-write audit",
                "P7 cockpit smoke",
                "Dry-run smoke",
                "p7SafeWriteDryRunSmoke",
                "p7ActionReadinessStatus",
                "p7OperatorCockpitSummary",
                "p7EnabledSafeWriteTools",
                "p7SafeWriteAudit",
                "p7CockpitSmoke",
                "p7SafeWriteDryRunSmoke",
                "operatorNext",
            ],
        ),
        _source_needles_check(
            "control_center_p7_operator_brief_detail_ui",
            "web/src/components/ControlCenterDetailPanels.tsx",
            [
                "OperatorNextPanel",
                "Operator next",
                "EngineBrainPanel",
                "P7 cockpit status",
                "p7OperatorCockpitSummary",
                "p7EnabledSafeWriteTools",
                "p7EnabledSafeWriteToolCount",
                "p7ReadySafeWriteAuditCount",
                "p7CockpitSmoke",
                "p7SafeWriteDryRunSmoke",
                "operatorNext",
            ],
        ),
        _path_check("release_evidence_pack", "scripts/ops/release_evidence_pack.py"),
        _source_needles_check(
            "release_evidence_p7_operator_brief",
            "scripts/ops/release_evidence_pack.py",
            [
                "p7_operator_brief",
                "CTOA_ENGINE_BRAIN_OPERATOR_BRIEF_PATH",
                "P7_OPERATOR_BRIEF.json",
            ],
        ),
        _validation_evidence_check(validation),
    ]

    manifest_ok = (
        manifest_payload.get("doc_sync_status") == "passed"
        and manifest_payload.get("secret_guardrail_status") == "passed"
    )
    checks.append(
        {
            "name": "engine_brain_generated_context",
            "status": "passed" if manifest_ok else "blocked",
            "evidence": (
                "doc_sync_status=passed; secret_guardrail_status=passed"
                if manifest_ok
                else "manifest doc sync or secret guardrail is not passed"
            ),
        }
    )

    blocking = [check for check in checks if check["status"] != "passed"]
    recommended_next = (
        "Operate the plugin as five read-only Control Central/status/cockpit tools. Seven safe-write candidates are registered; invoke only a candidate whose current plugin, preflight, and audit evidence pass."
        if not blocking
        else "Fix blocked readiness checks before creating a CTOAi plugin."
    )
    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "status": "ready_for_plugin_design" if not blocking else "blocked",
        "policy": "P6 registers five read-only Control Central/status/cockpit tools and seven bounded safe-write candidates. Each candidate remains fail-closed until current plugin, preflight, and audit evidence pass. Do not add deploy/live shortcuts or bypass Control Center evidence gates.",
        "recommended_next": recommended_next,
        "checks": checks,
    }


def render_p6_readiness(payload: dict[str, Any]) -> str:
    lines = [
        "# P6 Codex Integration Readiness",
        "",
        f"Generated at: `{payload['generated_at']}`",
        f"Status: `{payload['status']}`",
        "",
        payload["policy"],
        "",
        f"Recommended next: {payload['recommended_next']}",
        "",
        "| Check | Status | Evidence |",
        "|---|---|---|",
    ]
    for check in payload["checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['status']}` | {check['evidence']} |"
        )
    lines.append("")
    return "\n".join(lines)


def _validation_statuses(validation: dict[str, Any]) -> dict[str, str]:
    commands = (
        validation.get("commands")
        if isinstance(validation.get("commands"), list)
        else []
    )
    statuses: dict[str, str] = {}
    for command in commands:
        if not isinstance(command, dict):
            continue
        command_id = str(command.get("id") or "").strip()
        if command_id:
            statuses[command_id] = str(command.get("status") or "unknown")
    return statuses


def _action_audit_max_age_seconds() -> int:
    policy = read_json_object(DEFAULT_FRESHNESS_POLICY_PATH)
    artifacts = policy.get("artifacts") if isinstance(policy.get("artifacts"), dict) else {}
    configured = artifacts.get("action_audit")
    if (
        policy.get("schema_version") == 1
        and isinstance(configured, int)
        and not isinstance(configured, bool)
        and MIN_ACTION_AUDIT_MAX_AGE_SECONDS
        <= configured
        <= MAX_ACTION_AUDIT_MAX_AGE_SECONDS
    ):
        return configured
    return DEFAULT_ACTION_AUDIT_MAX_AGE_SECONDS


def _classify_action_audit_freshness(
    value: Any,
    *,
    now: datetime,
    max_age_seconds: int,
) -> str:
    text = str(value or "").strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return "invalid"
    if parsed.tzinfo is None:
        return "invalid"
    parsed = parsed.astimezone(timezone.utc)
    age_seconds = int((now - parsed).total_seconds())
    if age_seconds < -ACTION_AUDIT_FUTURE_SKEW_SECONDS:
        return "future"
    return "fresh" if age_seconds <= max_age_seconds else "stale"


def _empty_action_audit_summary(
    action_audit_path: Path,
    freshness_max_age: int,
    *,
    integrity_status: str,
) -> dict[str, Any]:
    return {
        "path": display_path(action_audit_path),
        "record_count": 0,
        "invalid_record_count": 0,
        "latest_at": "",
        "risk_counts": {},
        "by_action": {},
        "integrity_status": integrity_status,
        "source_valid": False,
        "action_audit_freshness_max_age_seconds": freshness_max_age,
    }


def read_action_audit_summary(
    action_audit_path: Path = DEFAULT_ACTION_AUDIT_PATH,
    *,
    now: datetime | None = None,
    max_age_seconds: int | None = None,
) -> dict[str, Any]:
    """Summarize append-only P7 audits without letting old success mask failure."""
    by_action: dict[str, dict[str, Any]] = {}
    risk_counts: Counter[str] = Counter()
    record_count = 0
    invalid_record_count = 0
    latest_at = ""
    current_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    freshness_max_age = (
        max_age_seconds
        if isinstance(max_age_seconds, int)
        and not isinstance(max_age_seconds, bool)
        and MIN_ACTION_AUDIT_MAX_AGE_SECONDS
        <= max_age_seconds
        <= MAX_ACTION_AUDIT_MAX_AGE_SECONDS
        else _action_audit_max_age_seconds()
    )
    try:
        raw = _read_bounded_regular_file(
            action_audit_path,
            max_bytes=MAX_ACTION_AUDIT_BYTES,
        )
    except _EvidenceReadError as exc:
        return _empty_action_audit_summary(
            action_audit_path,
            freshness_max_age,
            integrity_status="missing" if exc.code == "missing" else "invalid",
        )

    if raw and not raw.endswith(b"\n"):
        return _empty_action_audit_summary(
            action_audit_path,
            freshness_max_age,
            integrity_status="invalid",
        )

    for raw_line in raw.splitlines():
        record_count += 1
        if len(raw_line) > MAX_ACTION_AUDIT_LINE_BYTES:
            invalid_record_count += 1
            continue
        try:
            record = _strict_json_object(raw_line)
        except _EvidenceReadError:
            invalid_record_count += 1
            continue
        created_at = str(record.get("at") or record.get("created_at") or "")
        if created_at:
            latest_at = created_at
        risk_class = str(record.get("risk_class") or "").strip()
        if risk_class:
            risk_counts[risk_class] += 1
        action_id = str(record.get("action") or "").strip()
        if not action_id:
            continue
        entry = by_action.setdefault(
            action_id,
            {
                "record_count": 0,
                "dry_run_count": 0,
                "authorized_count": 0,
                "ok_count": 0,
                "qualifying_dry_run": False,
                "confirmed_ok_count": 0,
                "current": {},
                "risk_classes": Counter(),
            },
        )
        entry["record_count"] += 1
        dry_run = record.get("dry_run") is True
        authorized = record.get("authorized") is True
        ok = record.get("ok") is True
        preflight_status_present = "preflight_status" in record
        preflight_status = str(record.get("preflight_status") or "").strip()
        if dry_run:
            entry["dry_run_count"] += 1
        if authorized:
            entry["authorized_count"] += 1
        if ok:
            entry["ok_count"] += 1
        if (
            risk_class == "safe_write"
            and dry_run
            and authorized
            and ok
            and preflight_status_present
            and preflight_status == "ready"
        ):
            entry["qualifying_dry_run"] = True
        if risk_class == "safe_write" and not dry_run and authorized and ok:
            entry["confirmed_ok_count"] += 1
        entry["current"] = {
            "at": created_at,
            "dry_run": dry_run,
            "authorized": authorized,
            "ok": ok,
            "risk_class": risk_class,
            "preflight_status": preflight_status,
            "preflight_status_present": preflight_status_present,
        }
        if risk_class:
            entry["risk_classes"][risk_class] += 1

    source_valid = invalid_record_count == 0
    sanitized_by_action: dict[str, dict[str, Any]] = {}
    for action_id, entry in by_action.items():
        risk_classes = entry["risk_classes"]
        current_record = entry["current"]
        timestamp_seen = bool(str(current_record.get("at") or "").strip())
        freshness_status = (
            _classify_action_audit_freshness(
                current_record.get("at"),
                now=current_time,
                max_age_seconds=freshness_max_age,
            )
            if timestamp_seen
            else "missing"
        )
        preflight_status_seen = bool(current_record.get("preflight_status_present"))
        current_preflight_ready = (
            preflight_status_seen and current_record.get("preflight_status") == "ready"
        )
        current_successful = bool(
            current_record.get("risk_class") == "safe_write"
            and current_record.get("authorized") is True
            and current_record.get("ok") is True
        )
        audit_ready = bool(
            source_valid
            and entry["record_count"] > 0
            and entry["dry_run_count"] > 0
            and entry["authorized_count"] > 0
            and entry["ok_count"] > 0
            and entry["qualifying_dry_run"]
            and current_successful
            and current_preflight_ready
            and freshness_status == "fresh"
        )
        sanitized_by_action[action_id] = {
            "record_count": entry["record_count"],
            "dry_run_count": entry["dry_run_count"],
            "authorized_count": entry["authorized_count"],
            "ok_count": entry["ok_count"],
            "confirmed_ok_count": entry["confirmed_ok_count"],
            "preflight_status_seen": preflight_status_seen,
            "current_preflight_status": str(
                current_record.get("preflight_status") or ""
            ),
            "current_preflight_ready": current_preflight_ready,
            "timestamp_seen": timestamp_seen,
            "current_at": str(current_record.get("at") or ""),
            "freshness_status": freshness_status,
            "current_successful": current_successful,
            "audit_ready": audit_ready,
            "risk_classes": sorted(risk_classes.keys()),
        }
    return {
        "path": display_path(action_audit_path),
        "record_count": record_count,
        "invalid_record_count": invalid_record_count,
        "latest_at": latest_at,
        "risk_counts": dict(sorted(risk_counts.items())),
        "by_action": sanitized_by_action,
        "integrity_status": "valid" if source_valid else "invalid",
        "source_valid": source_valid,
        "action_audit_freshness_max_age_seconds": freshness_max_age,
    }


def read_json_object(path: Path) -> dict[str, Any]:
    try:
        if path.is_symlink() or not path.is_file():
            return {}
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def read_roadmap_text(path: Path) -> tuple[str, int]:
    try:
        if path.is_symlink() or not path.is_file():
            return "", 0
        size = path.stat().st_size
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "", 0
    return text[:ROADMAP_MAX_BYTES], size


def build_roadmap_generation_payload(
    generated_at: str,
    doc_sync_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    doc_sync = doc_sync_payload or {}
    doc_sync_checks = (
        doc_sync.get("checks") if isinstance(doc_sync.get("checks"), list) else []
    )
    plan3_sync = next(
        (
            check
            for check in doc_sync_checks
            if isinstance(check, dict) and check.get("name") == "roadmap_plan3"
        ),
        {},
    )
    doc_sync_status = str(doc_sync.get("status") or "missing")
    plan3_sync_status = str(plan3_sync.get("status") or "missing")

    docs: list[dict[str, Any]] = []
    hard_blockers: list[str] = []
    for name, config in ROADMAP_GENERATION_DOCS.items():
        rel_path = str(config["path"])
        path = ROOT / rel_path
        text, source_bytes = read_roadmap_text(path)
        exists = bool(text)
        needles = [str(item) for item in config["needles"]]
        missing = [needle for needle in needles if needle not in text]
        status = "passed" if exists and not missing else "blocked"
        if not exists:
            hard_blockers.append(f"missing_doc:{rel_path}")
        for needle in missing:
            hard_blockers.append(f"missing_marker:{rel_path}:{needle}")
        docs.append(
            {
                "name": name,
                "path": rel_path,
                "status": status,
                "missing_markers": missing,
                "required_marker_count": len(needles),
                "source_bytes": source_bytes,
                "checked_bytes": min(source_bytes, ROADMAP_MAX_BYTES),
            }
        )

    if doc_sync_status != "passed":
        hard_blockers.append("doc_sync_status")
    if plan3_sync_status != "passed":
        hard_blockers.append("doc_sync:roadmap_plan3")

    ready_doc_count = sum(1 for doc in docs if doc["status"] == "passed")
    ready = not hard_blockers and ready_doc_count == len(docs)
    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "status": "ready" if ready else "blocked",
        "hard_blockers": hard_blockers,
        "doc_sync_status": doc_sync_status,
        "doc_sync_roadmap_plan3_status": plan3_sync_status,
        "doc_count": len(docs),
        "ready_doc_count": ready_doc_count,
        "docs": docs,
        "next_action": (
            "Keep roadmap generation read-only in Control Center Evidence and plugin cockpit before adding any new MCP action."
            if ready
            else "Fix roadmap_generation hard_blockers before expanding plugin actions."
        ),
        "blocked_until": (
            "risk model coverage, audit replay evidence, Control Center gates, and tests exist before adding any new MCP write tool."
        ),
    }


def read_release_evidence_summary(
    release_root: Path = DEFAULT_RELEASE_EVIDENCE_DIR,
    latest_path: Path = DEFAULT_RELEASE_EVIDENCE_LATEST_PATH,
) -> dict[str, Any]:
    file_count = 0
    sprint_dirs: set[str] = set()
    latest_markdown_path = ""
    latest_modified_ts = -1.0

    try:
        markdown_files = list(release_root.rglob("*.md"))
    except OSError:
        markdown_files = []

    for item in markdown_files:
        if item.is_symlink() or not item.is_file():
            continue
        try:
            file_stat = item.stat()
        except OSError:
            continue
        file_count += 1
        try:
            relative_parts = item.relative_to(release_root).parts
        except ValueError:
            relative_parts = ()
        if relative_parts and relative_parts[0].startswith("sprint-"):
            sprint_dirs.add(relative_parts[0])
        if file_stat.st_mtime > latest_modified_ts:
            latest_modified_ts = file_stat.st_mtime
            latest_markdown_path = display_path(item)

    latest_payload = read_json_object(latest_path)
    helper = latest_payload.get("otclient_helper")
    if not isinstance(helper, dict):
        helper = {}
    queue = helper.get("sandbox_smoke_queue")
    if not isinstance(queue, dict):
        queue = {}
    module_contract = helper.get("module_contract")
    if not isinstance(module_contract, dict):
        module_contract = {}
    next_steps = queue.get("next_steps")
    if not isinstance(next_steps, list):
        next_steps = []

    return {
        "status": "ready" if file_count else "missing",
        "file_count": file_count,
        "sprint_count": len(sprint_dirs),
        "latest_path": latest_markdown_path,
        "release_evidence_generated_at": str(latest_payload.get("generated_at_utc") or ""),
        "otclient_helper_status": str(helper.get("status") or ""),
        "otclient_helper_release_gate_status": str(helper.get("release_gate_status") or ""),
        "otclient_helper_next_action": str(helper.get("next_action") or ""),
        "otclient_helper_module_contract": {
            "status": str(module_contract.get("status") or ""),
            "passed_count": int(module_contract.get("passed_count") or 0),
            "check_count": int(module_contract.get("check_count") or 0),
            "forbidden_count": int(module_contract.get("forbidden_count") or 0),
        },
        "sandbox_smoke_queue": {
            "status": str(queue.get("status") or ""),
            "runtime_status": str(queue.get("runtime_status") or ""),
            "next_action": str(queue.get("next_action") or ""),
            "required_count": int(queue.get("required_count") or 0),
            "queued_count": int(queue.get("queued_count") or 0),
            "first_step": str((next_steps[0] if next_steps and isinstance(next_steps[0], dict) else {}).get("step_id") or ""),
        },
    }


def read_p7_cockpit_smoke_summary(
    smoke_path: Path = DEFAULT_P7_COCKPIT_SMOKE_PATH,
) -> dict[str, Any]:
    payload = read_json_object(smoke_path)
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    hard_blockers = (
        payload.get("hard_blockers") if isinstance(payload.get("hard_blockers"), list) else []
    )
    warnings = payload.get("warnings") if isinstance(payload.get("warnings"), list) else []
    return {
        "status": str(payload.get("status") or "missing"),
        "checks": int(summary.get("checks") or 0),
        "passed": int(summary.get("passed") or 0),
        "blocked": int(summary.get("blocked") or 0),
        "action_audit_line_count": int(summary.get("action_audit_line_count") or 0),
        "hard_blockers": [str(item) for item in hard_blockers[:8]],
        "warnings": [str(item) for item in warnings[:8]],
        "source_path": display_path(smoke_path),
    }


def read_p7_evidence_review_summary(
    review_path: Path = DEFAULT_P7_EVIDENCE_REVIEW_PATH,
) -> dict[str, Any]:
    payload = read_json_object(review_path)
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    hard_blockers = (
        payload.get("hard_blockers") if isinstance(payload.get("hard_blockers"), list) else []
    )
    warnings = payload.get("warnings") if isinstance(payload.get("warnings"), list) else []
    return {
        "status": str(payload.get("status") or "missing"),
        "outcome": str(payload.get("outcome") or ""),
        "selected_action_id": str(payload.get("selected_action_id") or ""),
        "selected_mcp_tool": str(payload.get("selected_mcp_tool") or ""),
        "checks": int(summary.get("checks") or 0),
        "passed": int(summary.get("passed") or 0),
        "blocked": int(summary.get("blocked") or 0),
        "confirmed_audit_id": str(summary.get("confirmed_audit_id") or ""),
        "confirmed_audit_at": str(summary.get("confirmed_audit_at") or ""),
        "release_evidence_generated_at": str(
            summary.get("release_evidence_generated_at") or ""
        ),
        "hard_blockers": [str(item) for item in hard_blockers[:8]],
        "warnings": [str(item) for item in warnings[:8]],
        "source_path": display_path(review_path),
    }


def build_p7_cockpit_handoff_payload(
    action_readiness_payload: dict[str, Any] | None,
    action_audit: dict[str, Any],
    *,
    smoke_summary: dict[str, Any] | None = None,
    release_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    action_readiness = action_readiness_payload or {}
    action_audit_integrity = str(action_audit.get("integrity_status") or "invalid")
    enabled_tools = (
        action_readiness.get("enabled_safe_write_tools")
        if isinstance(action_readiness.get("enabled_safe_write_tools"), list)
        else []
    )
    enabled_tool_count = len(enabled_tools)
    audit_record_count = int(action_audit.get("record_count") or 0)
    ready_audit_count = 0
    for tool in enabled_tools:
        if not isinstance(tool, dict):
            continue
        action_id = str(tool.get("action_id") or "")
        audit_entry = (action_audit.get("by_action") or {}).get(action_id, {})
        if isinstance(audit_entry, dict) and audit_entry.get("audit_ready") is True:
            ready_audit_count += 1

    smoke = smoke_summary or read_p7_cockpit_smoke_summary()
    release = release_evidence or read_release_evidence_summary()
    blockers: list[str] = []
    warnings: list[str] = []
    if smoke["status"] != "ready" or smoke["blocked"]:
        warnings.append("p7_cockpit_smoke_not_ready")
    if release["status"] != "ready":
        warnings.append("release_evidence_missing")
    if not audit_record_count:
        warnings.append("action_audit_missing")
    if action_audit_integrity != "valid":
        blockers.append("action_audit_integrity_invalid")
    if action_readiness.get("status") not in {
        "first_safe_write_enabled",
        "safe_write_tools_enabled",
    } and int(action_readiness.get("mcp_write_tool_count") or 0):
        blockers.append("p7_action_readiness_not_ready")
    if enabled_tool_count and ready_audit_count != enabled_tool_count:
        blockers.append("safe_write_audit_not_ready")

    ready = not blockers
    next_safe_mode = str(action_readiness.get("next_safe_mode") or "")
    if next_safe_mode == "design_next_p7_plugin_action":
        next_operator_step = "design next P7 plugin action"
    elif next_safe_mode == "review_confirmed_safe_write_evidence":
        next_operator_step = "review confirmed evidence-pack-refresh audit"
    elif next_safe_mode == "confirmed_selected_safe_write":
        next_operator_step = (
            f"{P7_SELECTED_SAFE_WRITE_MCP_TOOL} dry_run=false "
            f"confirm={P7_SELECTED_SAFE_WRITE_CONFIRM_TEXT!r}"
        )
    else:
        next_operator_step = "ctoai_evidence_pack_refresh dry_run=true"
    return {
        "status": "ready" if ready else "needs_attention",
        "ready": ready,
        "hard_blockers": blockers,
        "warnings": warnings,
        "p7_cockpit": {
            "status": str(action_readiness.get("status") or "missing"),
            "enabled_safe_write_tool_count": enabled_tool_count,
            "ready_audit_count": ready_audit_count,
            "audit_count": enabled_tool_count,
            "mcp_write_tool_count": int(action_readiness.get("mcp_write_tool_count") or 0),
        },
        "p7_cockpit_smoke": smoke,
        "release_evidence": release,
        "action_audit": {
            "status": "ready" if audit_record_count else "missing",
            "record_count": audit_record_count,
            "latest_at": str(action_audit.get("latest_at") or ""),
            "invalid_record_count": int(action_audit.get("invalid_record_count") or 0),
            "integrity_status": action_audit_integrity,
            "risk_counts": action_audit.get("risk_counts") or {},
        },
        "recommended_tool_order": [
            "ctoai_engine_brain_brief",
            "ctoai_control_center_cockpit",
            next_operator_step,
        ]
        if ready
        else [
            "ctoai_engine_brain_self_check",
            "ctoai_control_center_cockpit",
        ],
    }


def _source_has_needles(relative_path: str, needles: list[str]) -> bool:
    path = ROOT / relative_path
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return all(needle in text for needle in needles)


def build_p7_action_readiness_payload(
    generated_at: str,
    workflow_payload: dict[str, Any],
    action_audit: dict[str, Any],
    p7_evidence_review: dict[str, Any] | None = None,
) -> dict[str, Any]:
    evidence_review = p7_evidence_review or {}
    allowed_tools = workflow_payload.get("allowed_mcp_tools")
    allowed_tools = allowed_tools if isinstance(allowed_tools, list) else []
    mcp_write_tools = [
        str(tool.get("name") or "unknown")
        for tool in allowed_tools
        if isinstance(tool, dict) and tool.get("risk_class") != "read_only"
    ]
    enabled_tool_names = set(P7_ENABLED_SAFE_WRITE_MCP_TOOLS.values())
    unexpected_mcp_write_tools = [
        tool for tool in mcp_write_tools if tool not in enabled_tool_names
    ]
    selected_mcp_enabled = P7_SELECTED_SAFE_WRITE_MCP_TOOL in mcp_write_tools
    action_audit_integrity = str(action_audit.get("integrity_status") or "invalid")
    action_audit_valid = action_audit_integrity == "valid"
    audit_by_action = (
        action_audit.get("by_action")
        if isinstance(action_audit.get("by_action"), dict)
        else {}
    )
    candidates: list[dict[str, Any]] = []
    for candidate in P7_SAFE_WRITE_ACTION_CANDIDATES:
        action_id = candidate["id"]
        expected_mcp_tool = P7_ENABLED_SAFE_WRITE_MCP_TOOLS.get(action_id, "")
        plugin_mcp_allowed = bool(
            expected_mcp_tool and expected_mcp_tool in mcp_write_tools
        )
        source_needles = [
            f'id: "{action_id}"',
            'riskClass: "safe_write"',
            "dryRunAvailable: true",
            "appendAuditRecord",
        ]
        if candidate.get("native_dry_run"):
            source_needles.append("nativeDryRun: true")
        source_ok = _source_has_needles(candidate["source"], source_needles)
        risk_model_ok = _source_has_needles(
            candidate["risk_model"],
            [
                action_id,
                "`safe_write`",
                "runtime/control-center/action-audit.jsonl",
            ],
        )
        audit_entry = (
            audit_by_action.get(action_id)
            if isinstance(audit_by_action.get(action_id), dict)
            else {}
        )
        audit_seen = bool(audit_entry.get("record_count", 0))
        audit_ready = bool(
            action_audit_valid and audit_entry.get("audit_ready") is True
        )
        missing_gates: list[str] = []
        if not source_ok:
            missing_gates.append("control_center_action_source_contract")
        if not risk_model_ok:
            missing_gates.append("risk_model_entry")
        if not audit_seen:
            missing_gates.append("control_center_action_audit_evidence")
        if audit_seen and not audit_entry.get("preflight_status_seen"):
            missing_gates.append("control_center_action_current_preflight_missing")
        elif audit_seen and not audit_entry.get("current_preflight_ready"):
            missing_gates.append("control_center_action_current_preflight")
        freshness_status = str(audit_entry.get("freshness_status") or "")
        if audit_seen and not audit_entry.get("timestamp_seen"):
            missing_gates.append("control_center_action_audit_freshness_missing")
        elif audit_seen and freshness_status != "fresh":
            missing_gates.append(
                "control_center_action_audit_"
                f"freshness_{freshness_status or 'invalid'}"
            )
        if audit_seen and not audit_entry.get("current_successful"):
            missing_gates.append("control_center_action_current_success")
        if audit_seen and not audit_ready:
            missing_gates.append("control_center_action_audit_not_ready")
        if not action_audit_valid:
            missing_gates.append("control_center_action_audit_integrity_invalid")
        if not plugin_mcp_allowed:
            missing_gates.append("plugin_write_tool_not_enabled_by_policy")
        candidates.append(
            {
                "id": action_id,
                "risk_class": candidate["risk_class"],
                "control_center_label": candidate["control_center_label"],
                "control_center_enabled": source_ok,
                "risk_model_present": risk_model_ok,
                "audit_seen": audit_seen,
                "audit_ready": audit_ready,
                "audit_record_count": int(audit_entry.get("record_count", 0) or 0),
                "audit_dry_run_count": int(audit_entry.get("dry_run_count", 0) or 0),
                "audit_confirmed_count": int(
                    audit_entry.get("confirmed_ok_count", 0) or 0
                ),
                "expected_mcp_tool": expected_mcp_tool,
                "plugin_mcp_allowed": plugin_mcp_allowed,
                "missing_gates": missing_gates,
            }
        )

    audited_count = sum(1 for candidate in candidates if candidate["audit_ready"])
    source_ready_count = sum(
        1
        for candidate in candidates
        if candidate["control_center_enabled"] and candidate["risk_model_present"]
    )
    selected_candidate = next(
        (
            candidate
            for candidate in candidates
            if candidate["id"] == P7_SELECTED_SAFE_WRITE_ACTION_ID
        ),
        {},
    )
    selected_ready = bool(
        selected_candidate
        and selected_candidate.get("control_center_enabled")
        and selected_candidate.get("risk_model_present")
        and selected_candidate.get("audit_ready")
    )
    all_candidates_audited = source_ready_count == len(
        candidates
    ) and audited_count == len(candidates)
    ready_to_design = not mcp_write_tools and all_candidates_audited
    registered_safe_write_tools = [
        {
            "action_id": candidate["id"],
            "mcp_tool": candidate["expected_mcp_tool"],
            "risk_class": candidate["risk_class"],
        }
        for candidate in candidates
        if candidate["plugin_mcp_allowed"]
    ]
    enabled_safe_write_tool_count = sum(
        1 for candidate in candidates if candidate["plugin_mcp_allowed"]
    )
    enabled_safe_write_tools_ready = all(
        candidate["control_center_enabled"]
        and candidate["risk_model_present"]
        and candidate["audit_ready"]
        for candidate in candidates
        if candidate["plugin_mcp_allowed"]
    ) and bool(registered_safe_write_tools)
    safe_write_tools_enabled = (
        selected_mcp_enabled
        and selected_ready
        and enabled_safe_write_tool_count == len(mcp_write_tools)
        and enabled_safe_write_tools_ready
        and not unexpected_mcp_write_tools
    )
    if unexpected_mcp_write_tools:
        status = "unsafe_write_tools_present"
        decision = "remove_unexpected_mcp_write_tools"
    elif safe_write_tools_enabled:
        status = (
            "safe_write_tools_enabled"
            if enabled_safe_write_tool_count > 1
            else "first_safe_write_enabled"
        )
        decision = (
            "monitor_enabled_safe_write_tools"
            if enabled_safe_write_tool_count > 1
            else "monitor_first_safe_write_tool"
        )
    else:
        status = "write_tools_blocked"
        decision = (
            "ready_to_design_first_safe_write_tool"
            if ready_to_design
            else "collect_control_center_action_audit_evidence"
        )
    enabled_safe_write_tools = (
        registered_safe_write_tools if safe_write_tools_enabled else []
    )
    enabled_dry_run_ready_count = sum(
        1
        for candidate in candidates
        if candidate["plugin_mcp_allowed"] and candidate["audit_ready"]
    )
    enabled_dry_run_ready = bool(
        registered_safe_write_tools
        and enabled_dry_run_ready_count == len(registered_safe_write_tools)
    )
    selected_confirmed_ready = bool(
        selected_candidate and int(selected_candidate.get("audit_confirmed_count") or 0)
    )
    selected_evidence_review_ready = (
        evidence_review.get("status") == "ready"
        and evidence_review.get("outcome") == "ready_to_design_next_p7_plugin_action"
        and evidence_review.get("selected_action_id") == P7_SELECTED_SAFE_WRITE_ACTION_ID
        and evidence_review.get("selected_mcp_tool") == P7_SELECTED_SAFE_WRITE_MCP_TOOL
    )
    selected_confirmed_command = (
        f"Run {P7_SELECTED_SAFE_WRITE_MCP_TOOL} with dry_run=false "
        f"confirm={P7_SELECTED_SAFE_WRITE_CONFIRM_TEXT!r} after reviewing "
        "runtime/control-center/action-audit.jsonl."
    )
    selected_design_command = (
        "Design the next P7 plugin action only after risk model coverage, "
        "audit logging, Control Center gates, and targeted MCP tests exist; "
        "keep deploy/live actions outside the plugin surface."
    )
    selected_review_command = (
        "Review confirmed evidence-pack-refresh audit evidence in "
        "runtime/control-center/action-audit.jsonl and runtime/evidence/latest.json; "
        "design the next P7 plugin action only after risk model coverage, audit "
        "logging, Control Center gates, and targeted MCP tests exist."
    )
    enabled_tool_names = [item["mcp_tool"] for item in enabled_safe_write_tools]
    if (
        safe_write_tools_enabled
        and selected_confirmed_ready
        and selected_evidence_review_ready
    ):
        safe_write_next = selected_design_command
        next_safe_mode = "design_next_p7_plugin_action"
    elif safe_write_tools_enabled and selected_confirmed_ready:
        safe_write_next = selected_review_command
        next_safe_mode = "review_confirmed_safe_write_evidence"
    elif safe_write_tools_enabled and enabled_dry_run_ready:
        safe_write_next = selected_confirmed_command
        next_safe_mode = "confirmed_selected_safe_write"
    elif len(enabled_tool_names) > 1:
        enabled_tools_text = (
            ", ".join(enabled_tool_names[:-1]) + f", and {enabled_tool_names[-1]}"
        )
        safe_write_next = (
            f"Run {enabled_tools_text} with dry_run=true before any confirmed refresh."
        )
        next_safe_mode = "dry_run_all_enabled_safe_write"
    elif enabled_tool_names:
        safe_write_next = (
            f"Run {enabled_tool_names[0]} with dry_run=true, verify action audit evidence, "
            "then decide on confirmed execution."
        )
        next_safe_mode = "dry_run_first_safe_write"
    else:
        safe_write_next = "Design bounded safe_write MCP tools behind Control Center audit replay; keep live/deploy actions blocked."
        next_safe_mode = "design_safe_write"
    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "status": status,
        "decision": decision,
        "policy": "P7 action readiness is evidence-only. MCP write tools stay disabled until every candidate has audit evidence and explicit enablement.",
        "risk_model": "docs/CTOAI_COMMAND_RISK_MODEL.md",
        "action_audit_path": action_audit.get(
            "path", display_path(DEFAULT_ACTION_AUDIT_PATH)
        ),
        "action_audit_record_count": action_audit.get("record_count", 0),
        "action_audit_integrity_status": action_audit_integrity,
        "candidate_count": len(candidates),
        "source_ready_count": source_ready_count,
        "audited_candidate_count": audited_count,
        "enabled_dry_run_ready_count": enabled_dry_run_ready_count,
        "enabled_safe_write_tools_ready": enabled_safe_write_tools_ready,
        "p7_evidence_review": evidence_review,
        "next_safe_mode": next_safe_mode,
        "mcp_write_tool_count": len(mcp_write_tools),
        "mcp_write_tools": mcp_write_tools,
        "unexpected_mcp_write_tools": unexpected_mcp_write_tools,
        "registered_safe_write_tools": registered_safe_write_tools,
        "enabled_safe_write_tools": enabled_safe_write_tools,
        "safe_write_candidates": candidates,
        "next_safe_command": (
            safe_write_next
            if safe_write_tools_enabled
            else "Remove unexpected MCP write tools before continuing P7 operator workflow."
            if unexpected_mcp_write_tools
            else safe_write_next
            if ready_to_design
            else "Run Control Center dry-runs for missing safe_write candidates, then refresh release evidence and brain."
        ),
    }


def render_p7_action_readiness(payload: dict[str, Any]) -> str:
    lines = [
        "# P7 Action Readiness",
        "",
        f"Generated at: `{payload['generated_at']}`",
        f"Status: `{payload['status']}`",
        f"Decision: `{payload['decision']}`",
        "",
        payload["policy"],
        "",
        f"Risk model: `{payload['risk_model']}`",
        f"Action audit: `{payload['action_audit_path']}` with `{payload['action_audit_record_count']}` records.",
        f"MCP write tools: `{payload['mcp_write_tool_count']}`",
        f"Next safe command: {payload['next_safe_command']}",
        "",
        "## Safe Write Candidates",
        "",
        "| Action | Source | Risk model | Audit seen | Audit ready | MCP allowed | Missing gates |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for candidate in payload["safe_write_candidates"]:
        missing = (
            ", ".join(f"`{item}`" for item in candidate["missing_gates"]) or "`none`"
        )
        lines.append(
            "| "
            f"`{candidate['id']}` | "
            f"`{candidate['control_center_enabled']}` | "
            f"`{candidate['risk_model_present']}` | "
            f"`{candidate['audit_seen']}` | "
            f"`{candidate['audit_ready']}` | "
            f"`{candidate['plugin_mcp_allowed']}` | "
            f"{missing} |"
        )
    lines.append("")
    return "\n".join(lines)


def build_p7_safe_write_tool_design_payload(
    generated_at: str,
    action_readiness_payload: dict[str, Any],
) -> dict[str, Any]:
    candidates = (
        action_readiness_payload.get("safe_write_candidates")
        if isinstance(action_readiness_payload.get("safe_write_candidates"), list)
        else []
    )
    selected_candidate = next(
        (
            candidate
            for candidate in candidates
            if isinstance(candidate, dict)
            and candidate.get("id") == P7_SELECTED_SAFE_WRITE_ACTION_ID
        ),
        {},
    )
    selected_ready = bool(
        selected_candidate
        and selected_candidate.get("control_center_enabled")
        and selected_candidate.get("risk_model_present")
        and selected_candidate.get("audit_ready")
    )
    mcp_write_tools = (
        action_readiness_payload.get("mcp_write_tools")
        if isinstance(action_readiness_payload.get("mcp_write_tools"), list)
        else []
    )
    unexpected_write_tools = (
        action_readiness_payload.get("unexpected_mcp_write_tools")
        if isinstance(action_readiness_payload.get("unexpected_mcp_write_tools"), list)
        else []
    )
    selected_tool_enabled = P7_SELECTED_SAFE_WRITE_MCP_TOOL in {
        str(tool) for tool in mcp_write_tools
    }
    action_gate_ready = (
        action_readiness_payload.get("decision")
        == "ready_to_design_first_safe_write_tool"
        and int(action_readiness_payload.get("mcp_write_tool_count", 0) or 0) == 0
    )
    implemented = (
        selected_ready
        and selected_tool_enabled
        and action_readiness_payload.get("status")
        in {"first_safe_write_enabled", "safe_write_tools_enabled"}
        and not unexpected_write_tools
    )
    design_ready = bool(selected_ready and (action_gate_ready or implemented))
    blocked_reasons: list[str] = []
    if unexpected_write_tools:
        blocked_reasons.append("unexpected_mcp_write_tools")
    if not action_gate_ready and not implemented:
        blocked_reasons.append("p7_action_readiness_not_ready")
    if not selected_candidate:
        blocked_reasons.append("selected_candidate_missing")
    elif not selected_ready:
        blocked_reasons.extend(
            str(item) for item in selected_candidate.get("missing_gates", [])
        )

    implementation_contract = [
        "Reuse Control Center action semantics for evidence-pack-refresh or an equivalent audited runner.",
        "Default to dry-run before any write and expose the dry-run result in the MCP response.",
        "Append a sanitized action audit record before returning.",
        "Accept no arbitrary command, path, shell, live-deploy, or Solteria Helper promotion arguments.",
        "Do not read .env, logs, databases, runtime client state, or private client data into AI/generated context.",
        "Keep live, deploy, guarded_write, dangerous, and forbidden_ui actions out of this tool.",
        "Keep MCP tool listing read-only until implementation tests and audit parity pass in a later turn.",
    ]
    required_tests = [
        "MCP tools/list still exposes only read-only tools while this design artifact is design-only.",
        "Dry-run call returns planned evidence-pack refresh output without mutating release artifacts.",
        "Real execution requires explicit safe_write intent and appends a sanitized action audit record.",
        "Denied or malformed arguments return blocked status without running a command.",
        "Release evidence and Control Center panels show the tool status without secret leakage.",
    ]
    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "status": "implemented"
        if implemented
        else "design_ready"
        if design_ready
        else "blocked",
        "decision": (
            "ready_for_dry_run_operation"
            if implemented
            else "ready_to_implement_dry_run_first_tool"
            if design_ready
            else "keep_collecting_action_gate_evidence"
        ),
        "mode": "dry_run_first" if implemented else "design_only",
        "mcp_enabled": implemented,
        "selected_action_id": P7_SELECTED_SAFE_WRITE_ACTION_ID,
        "selected_action_label": str(
            selected_candidate.get("control_center_label") or "Rebuild evidence pack"
        ),
        "proposed_mcp_tool": P7_SELECTED_SAFE_WRITE_MCP_TOOL,
        "risk_class": "safe_write",
        "control_center_source": "web/src/lib/controlCenterActions.ts",
        "risk_model": "docs/CTOAI_COMMAND_RISK_MODEL.md",
        "audit_sink": "runtime/control-center/action-audit.jsonl",
        "selected_candidate": selected_candidate,
        "implementation_contract": implementation_contract,
        "required_tests": required_tests,
        "blocked_reasons": blocked_reasons,
        "blocked_until": ""
        if implemented
        else "Explicit implementation turn after this design contract is current and accepted.",
        "next_safe_command": (
            "Run ctoai_evidence_pack_refresh with dry_run=true and verify runtime/control-center/action-audit.jsonl before confirmed execution."
            if implemented
            else "Implement dry-run-first safe_write MCP tools with Control Center audit parity."
            if design_ready
            else action_readiness_payload.get(
                "next_safe_command",
                "Refresh P7 action readiness before designing a write tool.",
            )
        ),
        "policy": (
            "Primary safe-write MCP design remains evidence-pack refresh; repo hygiene, API cost, and Engine Brain refreshes are allowed as additional bounded evidence/context tools. Deploy/live actions remain blocked."
            if implemented
            else "Design-only P7 artifact. It selects bounded safe-write MCP candidates but does not enable them."
        ),
    }


def render_p7_safe_write_tool_design(payload: dict[str, Any]) -> str:
    blocked_reasons = (
        ", ".join(f"`{item}`" for item in payload["blocked_reasons"]) or "`none`"
    )
    lines = [
        "# P7 Safe Write Tool Design",
        "",
        f"Generated at: `{payload['generated_at']}`",
        f"Status: `{payload['status']}`",
        f"Decision: `{payload['decision']}`",
        "",
        payload["policy"],
        "",
        f"Mode: `{payload['mode']}`",
        f"MCP enabled: `{payload['mcp_enabled']}`",
        f"Selected action: `{payload['selected_action_id']}`",
        f"Proposed MCP tool: `{payload['proposed_mcp_tool']}`",
        f"Risk class: `{payload['risk_class']}`",
        f"Control Center source: `{payload['control_center_source']}`",
        f"Risk model: `{payload['risk_model']}`",
        f"Audit sink: `{payload['audit_sink']}`",
        f"Blocked reasons: {blocked_reasons}",
        f"Next safe command: {payload['next_safe_command']}",
        "",
        "## Implementation Contract",
        "",
    ]
    for item in payload["implementation_contract"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Required Tests", ""])
    for item in payload["required_tests"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def build_p7_operator_brief_payload(
    generated_at: str,
    p6_payload: dict[str, Any],
    validation: dict[str, Any],
    workflow_payload: dict[str, Any] | None = None,
    action_readiness_payload: dict[str, Any] | None = None,
    safe_write_tool_design_payload: dict[str, Any] | None = None,
    action_audit: dict[str, Any] | None = None,
    roadmap_generation_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validation_statuses = _validation_statuses(validation)
    failed = sorted(
        key
        for key, value in validation_statuses.items()
        if value not in {"passed", "warn"}
    )
    warnings = sorted(
        key for key, value in validation_statuses.items() if value == "warn"
    )
    p6_checks = (
        p6_payload.get("checks") if isinstance(p6_payload.get("checks"), list) else []
    )
    blocked_p6 = [
        str(check.get("name") or "unknown")
        for check in p6_checks
        if isinstance(check, dict) and check.get("status") != "passed"
    ]
    hard_blockers = []
    if p6_payload.get("status") != "ready_for_plugin_design":
        hard_blockers.append("p6_readiness_status")
    hard_blockers.extend(f"p6:{name}" for name in blocked_p6)
    hard_blockers.extend(f"validation:{name}" for name in failed)
    if workflow_payload and workflow_payload.get("status") not in {
        "read_only_ready",
        "safe_write_ready",
    }:
        hard_blockers.append("p7_operator_workflow_status")
    if (
        action_readiness_payload
        and action_readiness_payload.get("status") == "unsafe_write_tools_present"
    ):
        hard_blockers.append("p7_action_readiness_unsafe_write_tools")
    if (
        safe_write_tool_design_payload
        and safe_write_tool_design_payload.get("status") == "blocked"
    ):
        hard_blockers.append("p7_safe_write_tool_design")
    design_ready = (safe_write_tool_design_payload or {}).get("status") in {
        "design_ready",
        "implemented",
    }
    enabled_safe_write_tool_count = len(
        (action_readiness_payload or {}).get("enabled_safe_write_tools") or []
    )
    action_next_safe_command = (action_readiness_payload or {}).get(
        "next_safe_command", ""
    )
    design_next_safe_command = (safe_write_tool_design_payload or {}).get(
        "next_safe_command", ""
    )
    cockpit_handoff = build_p7_cockpit_handoff_payload(
        action_readiness_payload,
        action_audit or read_action_audit_summary(),
    )
    hard_blockers.extend(
        f"cockpit_handoff:{name}" for name in cockpit_handoff["hard_blockers"]
    )
    roadmap_generation = roadmap_generation_payload or {
        "status": "missing",
        "hard_blockers": ["roadmap_generation_missing"],
        "doc_sync_status": "missing",
        "doc_sync_roadmap_plan3_status": "missing",
        "doc_count": 0,
        "ready_doc_count": 0,
        "docs": [],
        "next_action": "Generate roadmap_generation before expanding P7 operator workflow.",
        "blocked_until": "risk model coverage, audit replay evidence, Control Center gates, and tests exist before adding any new MCP write tool.",
    }
    if roadmap_generation.get("status") != "ready":
        hard_blockers.append("roadmap_generation_status")
    hard_blockers.extend(
        f"roadmap_generation:{name}"
        for name in roadmap_generation.get("hard_blockers", [])
        if isinstance(name, str)
    )
    warnings.extend(
        f"cockpit_handoff:{name}"
        for name in cockpit_handoff["warnings"]
        if f"cockpit_handoff:{name}" not in warnings
    )
    ready = not hard_blockers
    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "decision": "ready_for_p7_operator_workflow" if ready else "needs_attention",
        "status": "ready" if ready else "needs_attention",
        "hard_blockers": hard_blockers,
        "warnings": warnings,
        "p6_readiness": {
            "status": p6_payload.get("status", "missing"),
            "checks": len(p6_checks),
            "blocked_checks": blocked_p6,
        },
        "validation": {
            "generated_at_utc": validation.get("generated_at_utc", ""),
            "count": len(validation_statuses),
            "failed": failed,
            "warn": warnings,
        },
        "operator_workflow": {
            "status": (workflow_payload or {}).get("status", "missing"),
            "allowed_tool_count": len(
                (workflow_payload or {}).get("allowed_mcp_tools", [])
            ),
            "safe_write_tool_count": len(
                [
                    tool
                    for tool in (workflow_payload or {}).get("allowed_mcp_tools", [])
                    if isinstance(tool, dict) and tool.get("risk_class") == "safe_write"
                ]
            ),
            "blocked_action_classes": (workflow_payload or {}).get(
                "blocked_action_classes", []
            ),
            "risk_model": (workflow_payload or {}).get("risk_model", ""),
        },
        "action_readiness": {
            "status": (action_readiness_payload or {}).get("status", "missing"),
            "decision": (action_readiness_payload or {}).get("decision", "missing"),
            "candidate_count": (action_readiness_payload or {}).get(
                "candidate_count", 0
            ),
            "audited_candidate_count": (action_readiness_payload or {}).get(
                "audited_candidate_count", 0
            ),
            "enabled_dry_run_ready_count": (action_readiness_payload or {}).get(
                "enabled_dry_run_ready_count", 0
            ),
            "next_safe_mode": (action_readiness_payload or {}).get(
                "next_safe_mode", ""
            ),
            "mcp_write_tool_count": (action_readiness_payload or {}).get(
                "mcp_write_tool_count", 0
            ),
            "enabled_safe_write_tools": (action_readiness_payload or {}).get(
                "enabled_safe_write_tools", []
            ),
            "next_safe_command": (action_readiness_payload or {}).get(
                "next_safe_command", ""
            ),
        },
        "safe_write_tool_design": {
            "status": (safe_write_tool_design_payload or {}).get("status", "missing"),
            "decision": (safe_write_tool_design_payload or {}).get(
                "decision", "missing"
            ),
            "selected_action_id": (safe_write_tool_design_payload or {}).get(
                "selected_action_id", ""
            ),
            "proposed_mcp_tool": (safe_write_tool_design_payload or {}).get(
                "proposed_mcp_tool", ""
            ),
            "risk_class": (safe_write_tool_design_payload or {}).get("risk_class", ""),
            "mode": (safe_write_tool_design_payload or {}).get("mode", "missing"),
            "mcp_enabled": (safe_write_tool_design_payload or {}).get(
                "mcp_enabled", False
            ),
            "next_safe_command": (safe_write_tool_design_payload or {}).get(
                "next_safe_command", ""
            ),
        },
        "cockpit_handoff": cockpit_handoff,
        "roadmap_generation": {
            "status": str(roadmap_generation.get("status") or "missing"),
            "doc_sync_status": str(
                roadmap_generation.get("doc_sync_status") or "missing"
            ),
            "doc_sync_roadmap_plan3_status": str(
                roadmap_generation.get("doc_sync_roadmap_plan3_status") or "missing"
            ),
            "doc_count": int(roadmap_generation.get("doc_count") or 0),
            "ready_doc_count": int(roadmap_generation.get("ready_doc_count") or 0),
            "hard_blockers": [
                str(item)
                for item in roadmap_generation.get("hard_blockers", [])
                if isinstance(item, str)
            ][:12],
            "docs": [
                {
                    "name": str(item.get("name", "")),
                    "path": str(item.get("path", "")),
                    "status": str(item.get("status", "missing")),
                    "missing_markers": [
                        str(marker)
                        for marker in item.get("missing_markers", [])
                        if isinstance(marker, str)
                    ][:8],
                }
                for item in roadmap_generation.get("docs", [])
                if isinstance(item, dict)
            ],
            "next_action": str(roadmap_generation.get("next_action") or ""),
            "blocked_until": str(roadmap_generation.get("blocked_until") or ""),
        },
        "next_safe_command": (
            str(roadmap_generation.get("next_action") or "")
            if not ready and roadmap_generation.get("status") != "ready"
            else action_next_safe_command
            if ready
            and enabled_safe_write_tool_count > 1
            and action_next_safe_command
            else design_next_safe_command
            if ready and design_ready
            else "Design bounded safe_write MCP tools behind Control Center audit replay; keep live/deploy actions blocked."
            if ready
            and (action_readiness_payload or {}).get("decision")
            == "ready_to_design_first_safe_write_tool"
            else "Run Control Center P7 cockpit smoke and review cockpit_handoff before expanding P7 operator workflow."
            if ready
            else "Fix hard_blockers before expanding P7 operator workflow."
        ),
        "policy": "Generated operator brief. P7 registers seven bounded safe_write candidates; each remains fail-closed until current source, plugin, preflight, and audit evidence pass. Deploy/live actions remain blocked.",
    }


def build_p7_operator_workflow_payload(
    generated_at: str,
    p6_payload: dict[str, Any],
    action_readiness_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    p6_ready = p6_payload.get("status") == "ready_for_plugin_design"
    allowed_tools = [
        {
            "name": "ctoai_control_central",
            "risk_class": "read_only",
            "allowed": True,
            "purpose": "Return token-efficient brain, Control Center, plugin-management, and sites status with lane-specific drilldown.",
        },
        {
            "name": "ctoai_engine_brain_status",
            "risk_class": "read_only",
            "allowed": True,
            "purpose": "Summarize generated Engine Brain, validation, doctor, and pack status.",
        },
        {
            "name": "ctoai_engine_brain_self_check",
            "risk_class": "read_only",
            "allowed": True,
            "purpose": "Verify plugin install state and generated workspace evidence.",
        },
        {
            "name": "ctoai_engine_brain_brief",
            "risk_class": "read_only",
            "allowed": True,
            "purpose": "Return the generated P7 operator decision and next safe command.",
        },
        {
            "name": "ctoai_control_center_cockpit",
            "risk_class": "read_only",
            "allowed": True,
            "purpose": "Return read-only Control Center runtime evidence, P7 cockpit, and action-audit status.",
        },
        {
            "name": P7_ENABLED_SAFE_WRITE_MCP_TOOLS["repo-hygiene-refresh"],
            "risk_class": "safe_write",
            "allowed": True,
            "action_id": "repo-hygiene-refresh",
            "dry_run_default": True,
            "audit_sink": "runtime/control-center/action-audit.jsonl",
            "purpose": "Dry-run-first refresh of repo hygiene evidence with Control Center-compatible audit logging.",
        },
        {
            "name": P7_ENABLED_SAFE_WRITE_MCP_TOOLS["api-cost-refresh"],
            "risk_class": "safe_write",
            "allowed": True,
            "action_id": "api-cost-refresh",
            "dry_run_default": True,
            "audit_sink": "runtime/control-center/action-audit.jsonl",
            "purpose": "Dry-run-first refresh of API cost evidence with Control Center-compatible audit logging.",
        },
        {
            "name": P7_SELECTED_SAFE_WRITE_MCP_TOOL,
            "risk_class": "safe_write",
            "allowed": True,
            "action_id": P7_SELECTED_SAFE_WRITE_ACTION_ID,
            "dry_run_default": True,
            "audit_sink": "runtime/control-center/action-audit.jsonl",
            "purpose": "Dry-run-first refresh of release evidence with Control Center-compatible audit logging.",
        },
        {
            "name": P7_ENABLED_SAFE_WRITE_MCP_TOOLS["engine-brain-refresh"],
            "risk_class": "safe_write",
            "allowed": True,
            "action_id": "engine-brain-refresh",
            "dry_run_default": True,
            "audit_sink": "runtime/control-center/action-audit.jsonl",
            "purpose": "Dry-run-first refresh of Engine Brain generated context with Control Center-compatible audit logging.",
        },
        {
            "name": P7_ENABLED_SAFE_WRITE_MCP_TOOLS["p7-cockpit-smoke-refresh"],
            "risk_class": "safe_write",
            "allowed": True,
            "action_id": "p7-cockpit-smoke-refresh",
            "dry_run_default": True,
            "audit_sink": "runtime/control-center/action-audit.jsonl",
            "purpose": "Dry-run-first refresh of P7 cockpit smoke evidence with Control Center-compatible audit logging.",
        },
        {
            "name": P7_ENABLED_SAFE_WRITE_MCP_TOOLS["roadmap-state-refresh"],
            "risk_class": "safe_write",
            "allowed": True,
            "action_id": "roadmap-state-refresh",
            "dry_run_default": True,
            "audit_sink": "runtime/control-center/action-audit.jsonl",
            "purpose": "Registered native dry-run-first P13 roadmap-state candidate; current source, plugin, preflight, and audit evidence remain required.",
        },
        {
            "name": P7_ENABLED_SAFE_WRITE_MCP_TOOLS[
                "full-workspace-validation-refresh"
            ],
            "risk_class": "safe_write",
            "allowed": True,
            "action_id": "full-workspace-validation-refresh",
            "dry_run_default": True,
            "audit_sink": "runtime/control-center/action-audit.jsonl",
            "purpose": "Registered native dry-run-first full-workspace-validation candidate; current plugin, preflight, and audit evidence remain required.",
        },
    ]
    blocked_action_classes = [
        {
            "risk_class": "guarded_write",
            "blocked_until": "Risk metadata, confirmation modal, operator/owner role gate, and audit evidence exist.",
        },
        {
            "risk_class": "dangerous",
            "blocked_until": "Owner-only typed confirmation, dry-run path, rollback evidence, and audit review exist.",
        },
        {
            "risk_class": "forbidden_ui",
            "blocked_until": "Never expose through plugin or Control Center UI.",
        },
    ]
    gates_before_actions = [
        "Every plugin tool must have a stable risk class from docs/CTOAI_COMMAND_RISK_MODEL.md.",
        "Every write-capable tool must be represented in Control Center action audit before enablement.",
        "The seven registered safe-write candidates (ctoai_repo_hygiene_refresh, ctoai_api_cost_refresh, ctoai_evidence_pack_refresh, ctoai_engine_brain_refresh, ctoai_p7_cockpit_smoke_refresh, ctoai_roadmap_state_refresh, and ctoai_full_workspace_validation_refresh) may be exposed only when their individual current source, plugin, preflight, and audit evidence pass.",
        "Every safe-write MCP tool must default to dry-run and append runtime/control-center/action-audit.jsonl.",
        "No tool may bypass PromoteLiveCtoa -ApproveLiveDeploy for Solteria Helper live promotion.",
        "No tool may read .env, logs, databases, runtime client state, or private Solteria client data into generated context.",
        "P6 readiness, P7 operator brief, release evidence pack, doc sync, and secret guardrail must all be current.",
    ]
    action_readiness = action_readiness_payload or {}
    safe_write_ready = (
        p6_ready
        and action_readiness.get("status")
        in {"first_safe_write_enabled", "safe_write_tools_enabled"}
        and action_readiness.get("enabled_safe_write_tools_ready") is True
        and int(action_readiness.get("audited_candidate_count") or 0)
        == len(P7_SAFE_WRITE_ACTION_CANDIDATES)
        and len(action_readiness.get("enabled_safe_write_tools") or [])
        == len(P7_SAFE_WRITE_ACTION_CANDIDATES)
    )
    status = (
        "safe_write_ready"
        if safe_write_ready
        else "registered_fail_closed"
        if p6_ready
        else "blocked"
    )
    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "status": status,
        "decision": (
            "allow_bounded_safe_write_tools"
            if safe_write_ready
            else "retain_registered_safe_write_candidates"
            if p6_ready
            else "fix_p6_before_operator_workflow"
        ),
        "risk_model": "docs/CTOAI_COMMAND_RISK_MODEL.md",
        "allowed_mcp_tools": allowed_tools,
        "blocked_action_classes": blocked_action_classes,
        "gates_before_actions": gates_before_actions,
        "next_safe_command": (
            "Monitor current bounded safe-write evidence; any failed, denied, or stale current audit/preflight record returns the workflow to registered_fail_closed."
            if safe_write_ready
            else "Assess each registered safe-write candidate with dry_run=true; a missing, failed, or stale current preflight/audit record keeps that candidate blocked."
            if p6_ready
            else "Fix P6 readiness before exposing the P7 operator workflow."
        ),
        "policy": "P7 registers seven bounded safe_write candidates. Registration alone is registered_fail_closed; safe_write_ready requires every current source, plugin, preflight, and audit gate to pass. Deploy/live actions stay blocked.",
    }


def render_p7_operator_workflow(payload: dict[str, Any]) -> str:
    lines = [
        "# P7 Operator Workflow",
        "",
        f"Generated at: `{payload['generated_at']}`",
        f"Status: `{payload['status']}`",
        f"Decision: `{payload['decision']}`",
        "",
        payload["policy"],
        "",
        f"Risk model: `{payload['risk_model']}`",
        f"Next safe command: {payload['next_safe_command']}",
        "",
        "## Allowed MCP Tools",
        "",
        "| Tool | Risk | Purpose |",
        "|---|---|---|",
    ]
    for tool in payload["allowed_mcp_tools"]:
        lines.append(
            f"| `{tool['name']}` | `{tool['risk_class']}` | {tool['purpose']} |"
        )
    lines.extend(
        [
            "",
            "## Blocked Action Classes",
            "",
            "| Risk class | Blocked until |",
            "|---|---|",
        ]
    )
    for item in payload["blocked_action_classes"]:
        lines.append(f"| `{item['risk_class']}` | {item['blocked_until']} |")
    lines.extend(["", "## Gates Before Actions", ""])
    for gate in payload["gates_before_actions"]:
        lines.append(f"- {gate}")
    lines.append("")
    return "\n".join(lines)


def render_p7_operator_brief(payload: dict[str, Any]) -> str:
    p6 = payload["p6_readiness"]
    validation = payload["validation"]
    workflow = payload["operator_workflow"]
    action_readiness = payload["action_readiness"]
    safe_write_design = payload["safe_write_tool_design"]
    cockpit_handoff = payload.get("cockpit_handoff", {})
    roadmap_generation = payload.get("roadmap_generation", {})
    p7_cockpit = (
        cockpit_handoff.get("p7_cockpit")
        if isinstance(cockpit_handoff.get("p7_cockpit"), dict)
        else {}
    )
    p7_smoke = (
        cockpit_handoff.get("p7_cockpit_smoke")
        if isinstance(cockpit_handoff.get("p7_cockpit_smoke"), dict)
        else {}
    )
    release_evidence = (
        cockpit_handoff.get("release_evidence")
        if isinstance(cockpit_handoff.get("release_evidence"), dict)
        else {}
    )
    sandbox_queue = (
        release_evidence.get("sandbox_smoke_queue")
        if isinstance(release_evidence.get("sandbox_smoke_queue"), dict)
        else {}
    )
    module_contract = (
        release_evidence.get("otclient_helper_module_contract")
        if isinstance(release_evidence.get("otclient_helper_module_contract"), dict)
        else {}
    )
    action_audit = (
        cockpit_handoff.get("action_audit")
        if isinstance(cockpit_handoff.get("action_audit"), dict)
        else {}
    )
    warnings = ", ".join(f"`{item}`" for item in payload["warnings"]) or "`none`"
    blockers = ", ".join(f"`{item}`" for item in payload["hard_blockers"]) or "`none`"
    lines = [
        "# P7 Operator Brief",
        "",
        f"Generated at: `{payload['generated_at']}`",
        f"Decision: `{payload['decision']}`",
        f"Status: `{payload['status']}`",
        "",
        payload["policy"],
        "",
        f"Next safe command: {payload['next_safe_command']}",
        "",
        "## Evidence",
        "",
        f"- P6 readiness: `{p6['status']}` with `{p6['checks']}` checks.",
        (
            f"- P7 workflow: `{workflow['status']}` with `{workflow['allowed_tool_count']}` MCP tools "
            f"and `{workflow.get('safe_write_tool_count', 0)}` safe-write tools."
        ),
        (
            f"- P7 action readiness: `{action_readiness['status']}` with "
            f"`{action_readiness['audited_candidate_count']}/{action_readiness['candidate_count']}` audited candidates "
            f"and `{action_readiness['mcp_write_tool_count']}` MCP write tools."
        ),
        (
            f"- P7 safe-write design: `{safe_write_design['status']}` for "
            f"`{safe_write_design['proposed_mcp_tool'] or 'n/a'}` "
            f"with MCP enabled `{safe_write_design['mcp_enabled']}`."
        ),
        (
            f"- P7 cockpit handoff: `{cockpit_handoff.get('status', 'missing')}`; "
            f"smoke `{p7_smoke.get('passed', 0)}/{p7_smoke.get('checks', 0)}`; "
            f"safe-write audits `{p7_cockpit.get('ready_audit_count', 0)}/{p7_cockpit.get('audit_count', 0)}`; "
            f"release files `{release_evidence.get('file_count', 0)}`; "
            f"action audit records `{action_audit.get('record_count', 0)}`."
        ),
        (
            f"- OTClient helper: `{release_evidence.get('otclient_helper_status', 'missing')}`; "
            f"release gate `{release_evidence.get('otclient_helper_release_gate_status', 'missing')}`; "
            f"module contract `{module_contract.get('status', 'missing')}` "
            f"({module_contract.get('passed_count', 0)}/{module_contract.get('check_count', 0)}); "
            f"sandbox queue `{sandbox_queue.get('status', 'missing')}`; "
            f"runtime `{sandbox_queue.get('runtime_status', 'missing')}`; "
            f"first step `{sandbox_queue.get('first_step', 'n/a')}`."
        ),
        (
            f"- Roadmap generation: `{roadmap_generation.get('status', 'missing')}`; "
            f"docs `{roadmap_generation.get('ready_doc_count', 0)}/{roadmap_generation.get('doc_count', 0)}`; "
            f"doc sync `{roadmap_generation.get('doc_sync_status', 'missing')}`."
        ),
        f"- Validation evidence: `{validation['count']}` commands from `{validation['generated_at_utc']}`.",
        f"- Hard blockers: {blockers}.",
        f"- Warnings: {warnings}.",
        "",
    ]
    return "\n".join(lines)


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def build_indexes(out_dir: Path) -> dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    files = iter_files()

    file_tree = out_dir / "FILE_TREE.md"
    symbol_map = out_dir / "SYMBOL_MAP.md"
    ownership_map = out_dir / "OWNERSHIP_MAP.md"
    ownership_json = out_dir / "OWNERSHIP_MAP.json"
    doc_sync = out_dir / "DOC_SYNC.md"
    doc_sync_json = out_dir / "DOC_SYNC.json"
    secret_guardrail = out_dir / "SECRET_GUARDRAIL.md"
    secret_guardrail_json = out_dir / "SECRET_GUARDRAIL.json"
    p6_readiness = out_dir / "P6_CODEX_INTEGRATION_READINESS.md"
    p6_readiness_json = out_dir / "P6_CODEX_INTEGRATION_READINESS.json"
    p7_operator_workflow = out_dir / "P7_OPERATOR_WORKFLOW.md"
    p7_operator_workflow_json = out_dir / "P7_OPERATOR_WORKFLOW.json"
    p7_action_readiness = out_dir / "P7_ACTION_READINESS.md"
    p7_action_readiness_json = out_dir / "P7_ACTION_READINESS.json"
    p7_safe_write_tool_design = out_dir / "P7_SAFE_WRITE_TOOL_DESIGN.md"
    p7_safe_write_tool_design_json = out_dir / "P7_SAFE_WRITE_TOOL_DESIGN.json"
    p7_operator_brief = out_dir / "P7_OPERATOR_BRIEF.md"
    p7_operator_brief_json = out_dir / "P7_OPERATOR_BRIEF.json"
    manifest = out_dir / "manifest.json"

    file_tree.write_text(render_file_tree(files, generated_at), encoding="utf-8")
    symbol_map.write_text(render_symbol_map(files, generated_at), encoding="utf-8")
    audit = read_audit_inventory()

    ownership_payload = build_ownership_payload(audit, generated_at)
    ownership_map.write_text(render_ownership_map(ownership_payload), encoding="utf-8")
    ownership_json.write_text(json.dumps(ownership_payload, indent=2), encoding="utf-8")

    doc_sync_payload = build_doc_sync_payload(generated_at)
    doc_sync.write_text(render_doc_sync(doc_sync_payload), encoding="utf-8")
    doc_sync_json.write_text(json.dumps(doc_sync_payload, indent=2), encoding="utf-8")

    secret_payload = build_secret_guardrail_payload(
        generated_at,
        audit,
        [file_tree, symbol_map, ownership_map, ownership_json, doc_sync, doc_sync_json],
    )
    secret_guardrail.write_text(
        render_secret_guardrail(secret_payload), encoding="utf-8"
    )
    secret_guardrail_json.write_text(
        json.dumps(secret_payload, indent=2), encoding="utf-8"
    )

    validation = read_validation_evidence()
    p6_payload = build_p6_readiness_payload(
        generated_at,
        {
            "doc_sync_status": doc_sync_payload["status"],
            "secret_guardrail_status": secret_payload["status"],
        },
        validation,
    )
    p6_readiness.write_text(render_p6_readiness(p6_payload), encoding="utf-8")
    p6_readiness_json.write_text(json.dumps(p6_payload, indent=2), encoding="utf-8")
    p7_workflow_registration_payload = build_p7_operator_workflow_payload(
        generated_at, p6_payload
    )
    action_audit = read_action_audit_summary()
    p7_evidence_review = read_p7_evidence_review_summary()
    p7_action_payload = build_p7_action_readiness_payload(
        generated_at,
        p7_workflow_registration_payload,
        action_audit,
        p7_evidence_review,
    )
    p7_workflow_payload = build_p7_operator_workflow_payload(
        generated_at, p6_payload, p7_action_payload
    )
    p7_operator_workflow.write_text(
        render_p7_operator_workflow(p7_workflow_payload), encoding="utf-8"
    )
    p7_operator_workflow_json.write_text(
        json.dumps(p7_workflow_payload, indent=2), encoding="utf-8"
    )
    p7_action_readiness.write_text(
        render_p7_action_readiness(p7_action_payload), encoding="utf-8"
    )
    p7_action_readiness_json.write_text(
        json.dumps(p7_action_payload, indent=2), encoding="utf-8"
    )
    p7_safe_write_tool_design_payload = build_p7_safe_write_tool_design_payload(
        generated_at, p7_action_payload
    )
    p7_safe_write_tool_design.write_text(
        render_p7_safe_write_tool_design(p7_safe_write_tool_design_payload),
        encoding="utf-8",
    )
    p7_safe_write_tool_design_json.write_text(
        json.dumps(p7_safe_write_tool_design_payload, indent=2),
        encoding="utf-8",
    )
    roadmap_generation_payload = build_roadmap_generation_payload(
        generated_at, doc_sync_payload
    )
    p7_payload = build_p7_operator_brief_payload(
        generated_at,
        p6_payload,
        validation,
        p7_workflow_payload,
        p7_action_payload,
        p7_safe_write_tool_design_payload,
        action_audit,
        roadmap_generation_payload,
    )
    p7_operator_brief.write_text(render_p7_operator_brief(p7_payload), encoding="utf-8")
    p7_operator_brief_json.write_text(
        json.dumps(p7_payload, indent=2), encoding="utf-8"
    )

    payload: dict[str, object] = {
        "schema_version": 1,
        "generated_at": generated_at,
        "root": str(ROOT),
        "file_count": len(files),
        "outputs": {
            "file_tree": display_path(file_tree),
            "symbol_map": display_path(symbol_map),
            "ownership_map": display_path(ownership_map),
            "ownership_json": display_path(ownership_json),
            "doc_sync": display_path(doc_sync),
            "doc_sync_json": display_path(doc_sync_json),
            "secret_guardrail": display_path(secret_guardrail),
            "secret_guardrail_json": display_path(secret_guardrail_json),
            "p6_readiness": display_path(p6_readiness),
            "p6_readiness_json": display_path(p6_readiness_json),
            "p7_operator_workflow": display_path(p7_operator_workflow),
            "p7_operator_workflow_json": display_path(p7_operator_workflow_json),
            "p7_action_readiness": display_path(p7_action_readiness),
            "p7_action_readiness_json": display_path(p7_action_readiness_json),
            "p7_safe_write_tool_design": display_path(p7_safe_write_tool_design),
            "p7_safe_write_tool_design_json": display_path(
                p7_safe_write_tool_design_json
            ),
            "p7_operator_brief": display_path(p7_operator_brief),
            "p7_operator_brief_json": display_path(p7_operator_brief_json),
        },
        "doc_sync_status": doc_sync_payload["status"],
        "secret_guardrail_status": secret_payload["status"],
        "p6_readiness_status": p6_payload["status"],
        "p7_operator_workflow_status": p7_workflow_payload["status"],
        "p7_action_readiness_status": p7_action_payload["status"],
        "p7_safe_write_tool_design_status": p7_safe_write_tool_design_payload["status"],
        "p7_operator_brief_status": p7_payload["status"],
        "excluded_dirs": sorted(EXCLUDED_DIRS),
        "excluded_file_patterns": sorted(SECRET_NAME_PATTERNS),
    }
    manifest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Engine Brain indexes")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    payload = build_indexes(args.out_dir.resolve())
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
