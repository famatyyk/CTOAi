"""Build a secret-safe portable Engine Brain markdown pack."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ops.engine_brain_index import (
    DEFAULT_OUT_DIR,
    SECRET_NAME_PATTERNS,
    display_path,
)


DEFAULT_PACK_PATH = DEFAULT_OUT_DIR / "ENGINE_BRAIN_PACK.md"
DEFAULT_MANIFEST_PATH = DEFAULT_OUT_DIR / "ENGINE_BRAIN_PACK.json"

CURATED_FILES = [
    "AI/README.md",
    "AI/SYSTEM_PROMPT.md",
    "AI/PROJECT_CONTEXT.md",
    "AI/ENGINE_MEMORY.md",
    "AI/RULEBOOK.md",
    "AI/OPERATIONS_AUDIT.md",
    "AI/CODEX_CAPABILITY_MAP.md",
    "AI/ENGINE_BRAIN_STATUS.md",
    "AI/ARCHITECTURE_INDEX.md",
    "AI/API_INDEX.md",
    "AI/LUA_INDEX.md",
    "AI/OTCLIENT_INDEX.md",
    "AI/PACKET_INDEX.md",
    "AI/CLASS_INDEX.md",
    "AI/FEATURE_ROADMAP.md",
    "docs/P7_ROADMAP_STATE_REFRESH_DESIGN.md",
    "AI/KNOWN_BUGS.md",
    "AI/TECH_DEBT.md",
    "AI/SPECIALIZED_PROMPTS.md",
    "AI/TASK_TEMPLATE.md",
    "AI/AGENTS.md",
    "scripts/lua/AGENTS.md",
    "AI/generated/manifest.json",
    "AI/generated/ENV_DOCTOR.md",
    "AI/generated/OWNERSHIP_MAP.md",
    "AI/generated/DOC_SYNC.md",
    "AI/generated/SECRET_GUARDRAIL.md",
    "AI/generated/P6_CODEX_INTEGRATION_READINESS.md",
    "AI/generated/P7_OPERATOR_WORKFLOW.md",
    "AI/generated/P7_ACTION_READINESS.md",
    "AI/generated/P7_SAFE_WRITE_TOOL_DESIGN.md",
    "AI/generated/P7_OPERATOR_BRIEF.md",
]

OPTIONAL_SUMMARY_FILES = [
    "AI/generated/FILE_TREE.md",
    "AI/generated/SYMBOL_MAP.md",
]

GENERATED_PLAN3_FILES = [
    "AI/generated/manifest.json",
    "AI/generated/ENV_DOCTOR.md",
    "AI/generated/OWNERSHIP_MAP.md",
    "AI/generated/DOC_SYNC.md",
    "AI/generated/SECRET_GUARDRAIL.md",
    "AI/generated/P6_CODEX_INTEGRATION_READINESS.md",
    "AI/generated/P7_OPERATOR_WORKFLOW.md",
    "AI/generated/P7_ACTION_READINESS.md",
    "AI/generated/P7_SAFE_WRITE_TOOL_DESIGN.md",
    "AI/generated/P7_OPERATOR_BRIEF.md",
]

PROFILE_FILES = {
    "all": CURATED_FILES,
    "helper": [
        "AI/README.md",
        "AI/ENGINE_BRAIN_STATUS.md",
        "AI/FEATURE_ROADMAP.md",
        "AI/LUA_INDEX.md",
        "AI/OTCLIENT_INDEX.md",
        "docs/roadmaps/CTOAI_THREE_DEVELOPMENT_PLANS_2026-07-06.md",
        "docs/otclient/solteria_helper_development_plan.md",
        "docs/otclient/HELPER_RUNTIME_BRIDGE_V1.md",
        "docs/otclient/solteria_helper_test_env.md",
        "docs/otclient/solteria_helper_module_workplan.md",
        "docs/otclient/solteria_helper_module_contract.md",
        "docs/otclient/solteria_helper_next_modules_plan.md",
        "docs/otclient/ctoai_runtime_2_execution_plan.md",
        "docs/otclient/solteria_helper_supplemental_refactor_plan.md",
        "docs/otclient/solteria_helper_sandbox_smoke_queue.md",
        "docs/otclient/zerobot_reference.md",
        "docs/otclient/vbot_import_review.md",
        "scripts/ops/otclient_external_bot_intake.py",
        "scripts/ops/otclient_helper_module_contract.py",
        "scripts/ops/solteria_helper_sandbox_smoke_queue.py",
        "scripts/lua/AGENTS.md",
        *GENERATED_PLAN3_FILES,
    ],
    "control-center": [
        "AI/README.md",
        "AI/ENGINE_BRAIN_STATUS.md",
        "AI/FEATURE_ROADMAP.md",
        "AI/API_INDEX.md",
        "AI/ARCHITECTURE_INDEX.md",
        "docs/CTOA_CLI.md",
        "docs/P7_ROADMAP_STATE_REFRESH_DESIGN.md",
        "docs/roadmaps/CTOAI_THREE_DEVELOPMENT_PLANS_2026-07-06.md",
        *GENERATED_PLAN3_FILES,
    ],
    "infra": [
        "AI/README.md",
        "AI/ENGINE_BRAIN_STATUS.md",
        "AI/OPERATIONS_AUDIT.md",
        "docs/INFRASTRUCTURE_CANONICAL.md",
        "docs/DEPLOYMENT.md",
        "docs/roadmaps/CTOAI_THREE_DEVELOPMENT_PLANS_2026-07-06.md",
        *GENERATED_PLAN3_FILES,
    ],
    "security": [
        "AI/README.md",
        "AI/RULEBOOK.md",
        "AI/ENGINE_BRAIN_STATUS.md",
        "docs/REPO_HYGIENE_POLICY.md",
        "docs/roadmaps/CTOAI_THREE_DEVELOPMENT_PLANS_2026-07-06.md",
        ".pre-commit-config.yaml",
        *GENERATED_PLAN3_FILES,
    ],
}


def is_secretish_path(path: Path) -> bool:
    try:
        rel = path.relative_to(ROOT).as_posix()
    except ValueError:
        rel = path.as_posix()
    if rel == "AI/generated/SECRET_GUARDRAIL.md":
        return False
    name = path.name.lower()
    if name.startswith(".env") or name == "auth.json":
        return True
    return any(pattern in name for pattern in SECRET_NAME_PATTERNS)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def fence_for(path: Path) -> str:
    suffix = path.suffix.lower().lstrip(".")
    if suffix in {"md", "markdown"}:
        return "markdown"
    if suffix == "json":
        return "json"
    if suffix in {"yml", "yaml"}:
        return "yaml"
    if suffix == "py":
        return "python"
    if suffix == "ps1":
        return "powershell"
    if suffix == "lua":
        return "lua"
    return "text"


def append_file_section(lines: list[str], rel_path: str, *, max_chars: int) -> dict[str, Any]:
    path = ROOT / rel_path
    section: dict[str, Any] = {
        "path": rel_path,
        "included": False,
        "bytes": 0,
        "truncated": False,
        "reason": "",
    }
    if not path.exists():
        section["reason"] = "missing"
        return section
    if is_secretish_path(path):
        section["reason"] = "secretish path excluded"
        return section

    text = read_text(path)
    section["bytes"] = len(text.encode("utf-8"))
    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "\n\n[truncated]\n"
        section["truncated"] = True

    lines.extend(
        [
            "",
            f"## `{rel_path}`",
            "",
            f"```{fence_for(path)}",
            text.rstrip(),
            "```",
            "",
        ]
    )
    section["included"] = True
    return section


def build_pack(
    pack_path: Path = DEFAULT_PACK_PATH,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    *,
    include_generated: bool = True,
    max_chars_per_file: int = 45000,
    profile: str = "all",
) -> dict[str, Any]:
    if profile not in PROFILE_FILES:
        raise ValueError(f"Unknown Engine Brain pack profile: {profile}")
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    pack_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# CTOAi Engine Brain Pack",
        "",
        f"Generated at: `{generated_at}`",
        f"Repo root: `{ROOT}`",
        f"Profile: `{profile}`",
        "",
        "This pack is curated and secret-safe. It excludes `.env*`, auth stores,",
        "runtime data, logs, local databases, tokens, credentials, and generated",
        "dependency folders. It is intended as a portable context artifact for",
        "Codex or another code assistant.",
        "",
        "## Included Sources",
        "",
    ]

    files = list(dict.fromkeys(PROFILE_FILES[profile]))
    if include_generated:
        files.extend(OPTIONAL_SUMMARY_FILES)

    sections: list[dict[str, Any]] = []
    for rel_path in files:
        sections.append(append_file_section(lines, rel_path, max_chars=max_chars_per_file))

    pack_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "generated_at": generated_at,
        "root": str(ROOT),
        "pack_path": display_path(pack_path),
        "profile": profile,
        "include_generated": include_generated,
        "max_chars_per_file": max_chars_per_file,
        "sections": sections,
        "included_count": sum(1 for section in sections if section["included"]),
        "truncated_count": sum(1 for section in sections if section["truncated"]),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Build CTOAi Engine Brain markdown pack")
    parser.add_argument("--pack-path", type=Path, default=DEFAULT_PACK_PATH)
    parser.add_argument("--manifest-path", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--profile", choices=sorted(PROFILE_FILES), default="all")
    parser.add_argument("--no-generated", action="store_true", help="Skip generated FILE_TREE/SYMBOL_MAP sections")
    parser.add_argument("--max-chars-per-file", type=int, default=45000)
    args = parser.parse_args()

    manifest = build_pack(
        args.pack_path.resolve(),
        args.manifest_path.resolve(),
        include_generated=not args.no_generated,
        max_chars_per_file=max(1000, args.max_chars_per_file),
        profile=args.profile,
    )
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
