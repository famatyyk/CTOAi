from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_repo_cleanup_wave_contract_has_canonical_docs_and_tasks():
    cleanup_doc = PROJECT_ROOT / "docs" / "REPO_CLEANUP_WAVES.md"
    progress_doc = PROJECT_ROOT / "docs" / "history" / "sprints" / "SPRINT-070-PROGRESS.md"
    tasks_json = (PROJECT_ROOT / ".vscode" / "tasks.json").read_text(encoding="utf-8")
    index_doc = (PROJECT_ROOT / "docs" / "INDEX.md").read_text(encoding="utf-8")

    assert cleanup_doc.exists()
    assert progress_doc.exists()
    assert "Repo Cleanup Waves" in index_doc
    assert "Sprint-070 Cleanup Documentation Sync" in tasks_json
    assert "Sprint-070 Validate Cleanup Contract" in tasks_json
    assert "Sprint-070 cleanup contract check" in (PROJECT_ROOT / ".github" / "workflows" / "ctoa-pipeline.yml").read_text(encoding="utf-8")
    assert "Sprint-070 cleanup contract check" in (PROJECT_ROOT / ".github" / "workflows" / "pr_quality.yml").read_text(encoding="utf-8")
    assert "REPO_CLEANUP_WAVES.md" in tasks_json
    assert "SPRINT-070-PROGRESS.md" in tasks_json
