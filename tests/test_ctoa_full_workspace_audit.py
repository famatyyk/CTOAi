import json

import pytest

from scripts.ops import ctoa_full_workspace_audit as audit


def test_full_workspace_audit_categories_keep_git_vendor_and_secrets_visible():
    assert (
        audit._category(".git/objects/pack/pack-example.pack", tracked=False)[0]
        == "git_internal"
    )
    assert (
        audit._category("web/node_modules/pkg/token.js", tracked=False)[0]
        == "vendor_or_cache"
    )
    assert audit._category(".env", tracked=False)[0] == "local_secret_or_sensitive"
    assert audit._category("runner/main.py", tracked=True)[0] == "tracked_source"
    assert (
        audit._category("scripts/new_helper.py", tracked=False)[0]
        == "untracked_source_candidate"
    )


def test_three_development_plans_render_expected_plan_names():
    markdown = audit.render_plans_markdown(
        {
            "coverage": {"file_count": 10, "tracked_file_count": 4},
        }
    )

    assert "Plan 1: Helper-First Productization" in markdown
    assert "Plan 2: Control Center And Evidence Platform" in markdown
    assert "Plan 3: Engine Brain And CTOAi Platform" in markdown
    assert "P6_CODEX_INTEGRATION_READINESS.md" in markdown
    assert "P7_OPERATOR_BRIEF.md" in markdown
    assert "BackgroundNoScreen" in markdown
    assert "AI/P8_P16_EXECUTION_ROADMAP.md" in markdown
    assert "ctoai-engine-brain" in markdown
    assert "ctoai_engine_brain_self_check" in markdown
    assert "ctoai_engine_brain_brief" in markdown
    assert "runtime smoke base URLs" in markdown
    assert "LAB003 base URLs stay on loopback HTTP(S)" in markdown
    assert "GS reset API URLs/timing values are validated" in markdown
    assert "Conditions paralyze-only gate" in markdown
    assert "RuntimeModuleGatesSandboxSmoke" in markdown
    assert "Combat and CaveBot remain `deferred_high_risk`" in markdown


def test_full_workspace_audit_markdown_reports_integrity_gate_without_stale_pass_claims():
    markdown = audit.render_audit_markdown(
        {
            "generated_at_utc": "2026-07-07T00:00:00+00:00",
            "root": "C:/repo",
            "coverage": {
                "scope": "All files under workspace root, including .git internals.",
                "file_count": 2,
                "regular_file_count": 2,
                "skipped_non_regular_count": 1,
                "skipped_entries_by_kind": {"symlink": 1},
                "tracked_file_count": 1,
                "dirty_entry_count": 0,
                "hashed_max_bytes": 1000,
                "hashed_file_count": 1,
                "sensitive_hash_count": 0,
            },
            "counts_by_category": {
                "local_secret_or_sensitive": 1,
                "tracked_source": 1,
            },
            "bytes_by_category": {
                "local_secret_or_sensitive": 10,
                "tracked_source": 20,
            },
            "top_directories": {
                "scripts": {"files": 1, "bytes": 20},
                "web": {"files": 0, "bytes": 0},
            },
            "dirty_entries": [],
            "audit_gate": {
                "status": "evidence_ready",
                "checks": [
                    {
                        "name": "regular_file_inventory",
                        "status": "passed",
                        "evidence": "2 regular files inventoried.",
                    }
                ],
                "completion_note": "Inventory mechanics only.",
            },
        }
    )

    assert "## Audit Integrity Gate" in markdown
    assert "`evidence_ready`" in markdown
    assert "## Required Completion Evidence" in markdown
    assert "passed in the current worktree before this audit wave" not in markdown


def test_full_workspace_audit_markdown_reports_validation_evidence_gate():
    inventory = {
        "generated_at_utc": "2026-07-07T00:00:00+00:00",
        "root": "C:/repo",
        "coverage": {
            "scope": "All files under workspace root, including .git internals.",
            "file_count": 2,
            "regular_file_count": 2,
            "skipped_non_regular_count": 0,
            "skipped_entries_by_kind": {},
            "tracked_file_count": 1,
            "dirty_entry_count": 0,
            "hashed_max_bytes": 1000,
            "hashed_file_count": 1,
            "sensitive_hash_count": 0,
        },
        "counts_by_category": {"tracked_source": 2},
        "bytes_by_category": {"tracked_source": 20},
        "top_directories": {"scripts": {"files": 2, "bytes": 20}},
        "dirty_entries": [],
        "audit_gate": {
            "status": "evidence_ready",
            "checks": [
                {
                    "name": "regular_file_inventory",
                    "status": "passed",
                    "evidence": "2 regular files inventoried.",
                }
            ],
            "completion_note": "Inventory mechanics only.",
        },
    }
    validation = {
        "generated_at_utc": "2026-07-07T01:00:00+00:00",
        "commands": [
            {
                "id": "python_non_e2e",
                "status": "passed",
                "duration": "133.75s",
                "summary": "1039 passed, 32 skipped",
            },
            {
                "id": "web_lint",
                "status": "passed",
                "duration": "9.5s",
                "summary": "eslint .",
            },
            {
                "id": "web_tests",
                "status": "passed",
                "duration": "2.25s",
                "summary": "117 passed",
            },
            {
                "id": "diff_check",
                "status": "warn",
                "duration": "0.9s",
                "summary": "CRLF/LF warnings only",
            },
            {
                "id": "brain_refresh",
                "status": "passed",
                "duration": "1.8s",
                "summary": "doc sync and secret guardrail passed",
            },
            {
                "id": "brain_doctor",
                "status": "warn",
                "duration": "14.5s",
                "summary": "overall warn, fail=0",
            },
            {
                "id": "brain_pack_all",
                "status": "passed",
                "duration": "0.6s",
                "summary": "28 sections",
            },
        ],
    }

    markdown = audit.render_audit_markdown(inventory, validation)

    assert "## Validation Evidence Gate" in markdown
    assert "- Status: `evidence_ready`" in markdown
    assert "- Missing command evidence: `<none>`" in markdown
    assert (
        "| `python_non_e2e` | `passed` | `133.75s` | 1039 passed, 32 skipped |"
        in markdown
    )


def test_full_workspace_audit_does_not_follow_symlinked_files(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    source_dir = workspace / "scripts"
    source_dir.mkdir(parents=True)
    real_file = source_dir / "real.py"
    real_file.write_text("print('ok')\n", encoding="utf-8")
    outside_secret = tmp_path / "outside-secret.txt"
    outside_secret.write_text("outside-secret-token-value", encoding="utf-8")
    linked_secret = source_dir / "linked-secret.txt"

    try:
        linked_secret.symlink_to(outside_secret)
    except OSError as exc:
        pytest.skip(f"symlinks are not available: {exc}")

    monkeypatch.setattr(audit, "ROOT", workspace)
    monkeypatch.setattr(audit, "_run_git", lambda _args: [])

    inventory = audit.build_inventory(max_hash_bytes=1000)
    serialized = json.dumps(inventory)
    paths = {record["path"] for record in inventory["files"]}

    assert "scripts/real.py" in paths
    assert "scripts/linked-secret.txt" not in paths
    assert inventory["coverage"]["skipped_entries_by_kind"]["symlink"] == 1
    assert inventory["audit_gate"]["status"] == "evidence_ready"
    assert "outside-secret-token-value" not in serialized
    assert "outside-secret.txt" not in serialized
