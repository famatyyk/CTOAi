import importlib.util
from pathlib import Path


def _load_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "ops" / "phase5_nightly_sync.py"
    spec = importlib.util.spec_from_file_location("phase5_nightly_sync", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_remote_timestamps_filters_invalid_rows():
    module = _load_module()

    raw = "\n".join(
        [
            "20260515T185948Z",
            "phase5-drycheck-20260515T185948Z",
            "not-a-timestamp",
            "20260516T022021Z",
            "20260516T022021Z",
        ]
    )
    rows = module.parse_remote_timestamps(raw)

    assert rows == ["20260515T185948Z", "20260516T022021Z"]


def test_should_sync_snapshot_detects_missing_required_files(tmp_path: Path):
    module = _load_module()

    snapshot = tmp_path / "phase5-drycheck-20260516T022021Z"
    snapshot.mkdir()
    (snapshot / "summary.md").write_text("ok\n", encoding="utf-8")

    assert module.should_sync_snapshot(snapshot, sync_all=False) is True

    (snapshot / "report.txt").write_text("ok\n", encoding="utf-8")
    (snapshot / "status-porcelain.txt").write_text("", encoding="utf-8")

    assert module.should_sync_snapshot(snapshot, sync_all=False) is False
    assert module.should_sync_snapshot(snapshot, sync_all=True) is True


def test_render_short_status_includes_key_kpis():
    module = _load_module()

    payload = {
        "overall_status": "IN_PROGRESS",
        "selected_nightly_runs": 1,
        "target_runs": 3,
        "pending_runs": 2,
        "alerts_count": 0,
    }
    line = module.render_short_status(payload, pulled_new=2, skipped_existing=4)

    assert "status=IN_PROGRESS" in line
    assert "nightly_runs=1/3" in line
    assert "pending=2" in line
    assert "alerts=0" in line
    assert "pulled_new=2" in line
    assert "skipped_existing=4" in line

def test_build_morning_brief_returns_attention_when_pending_runs_exist():
    module = _load_module()

    payload = {
        "overall_status": "IN_PROGRESS",
        "selected_nightly_runs": 1,
        "target_runs": 3,
        "pending_runs": 2,
        "alerts_count": 0,
    }
    brief = module.build_morning_brief(payload, pulled_new=1, skipped_existing=0)

    assert brief["verdict"] == "ATTENTION"
    assert brief["reason"] == "nightly_runs_pending"
    assert brief["nightly_runs"] == "1/3"


def test_render_morning_brief_markdown_includes_sprint_log_paste_line():
    module = _load_module()

    brief = {
        "generated_utc": "20260516T070000Z",
        "verdict": "PASS",
        "reason": "three_nightly_runs_verified",
        "checklist_status": "COMPLETE",
        "nightly_runs": "3/3",
        "pending": 0,
        "alerts": 0,
        "pulled_new": 1,
        "skipped_existing": 3,
    }
    md = module.render_morning_brief_markdown(brief)

    assert "# Phase-5 Morning Brief" in md
    assert "verdict: PASS" in md
    assert "## Sprint Log Paste" in md
    assert "Phase-5 morning check: PASS" in md


def test_send_attention_notifications_sends_only_configured_channels():
    module = _load_module()

    calls = []

    def fake_post(url: str, payload: dict):
        calls.append((url, payload))
        return True, "http_204"

    brief = {
        "verdict": "ATTENTION",
        "reason": "nightly_runs_pending",
        "checklist_status": "IN_PROGRESS",
        "nightly_runs": "0/3",
        "pending": 3,
        "alerts": 0,
    }

    result = module.send_attention_notifications(
        brief,
        discord_webhook_url="https://discord.example/webhook",
        slack_webhook_url="",
        post_json=fake_post,
    )

    assert result["reason"] == "sent"
    assert result["results"]["discord"]["state"] == "sent"
    assert result["results"]["slack"]["state"] == "skipped"
    assert len(calls) == 1
    assert "ATTENTION" in calls[0][1]["content"]


def test_send_attention_notifications_skips_when_verdict_is_pass():
    module = _load_module()

    calls = []

    def fake_post(url: str, payload: dict):
        calls.append((url, payload))
        return True, "http_204"

    brief = {
        "verdict": "PASS",
        "reason": "three_nightly_runs_verified",
        "checklist_status": "COMPLETE",
        "nightly_runs": "3/3",
        "pending": 0,
        "alerts": 0,
    }

    result = module.send_attention_notifications(
        brief,
        discord_webhook_url="https://discord.example/webhook",
        slack_webhook_url="https://slack.example/webhook",
        post_json=fake_post,
    )

    assert result["reason"] == "verdict_not_attention"
    assert len(calls) == 0


def test_mark_step9_done_in_plan_updates_active_line(tmp_path: Path):
    module = _load_module()

    plan_path = tmp_path / "VPS_WORKTREE_HYGIENE_PLAN.md"
    plan_path.write_text(
        "8. [x] foo\n"
        "9. [ ] Monitor first 3 nightly dry-check runs and alert on any non-empty porcelain status. (ACTIVE NEXT STEP)\n",
        encoding="utf-8",
    )

    result = module.mark_step9_done_in_plan(
        plan_path,
        done_utc="20260516T070000Z",
        evidence_rel_path="docs/evidence/vps-worktree-hygiene/phase5-step9-closure.md",
    )

    content = plan_path.read_text(encoding="utf-8")
    assert result["updated"] is True
    assert "9. [x] Monitor first 3 nightly dry-check runs" in content
    assert "DONE: 20260516T070000Z" in content


def test_auto_close_step9_if_ready_writes_evidence_and_updates_docs(tmp_path: Path):
    module = _load_module()

    plan_path = tmp_path / "VPS_WORKTREE_HYGIENE_PLAN.md"
    plan_path.write_text(
        "9. [ ] Monitor first 3 nightly dry-check runs and alert on any non-empty porcelain status. (ACTIVE NEXT STEP)\n",
        encoding="utf-8",
    )

    readme_path = tmp_path / "README.md"
    readme_path.write_text("# Evidence\n", encoding="utf-8")

    closure_path = tmp_path / "phase5-step9-closure.md"

    payload = {
        "overall_status": "COMPLETE",
        "selected_nightly_runs": 3,
        "target_runs": 3,
        "pending_runs": 0,
        "alerts_count": 0,
    }
    brief = {
        "generated_utc": "20260516T070000Z",
        "verdict": "PASS",
        "reason": "three_nightly_runs_verified",
        "checklist_status": "COMPLETE",
        "nightly_runs": "3/3",
        "pending": 0,
        "alerts": 0,
    }

    result = module.auto_close_step9_if_ready(
        payload,
        brief,
        plan_path=plan_path,
        closure_evidence_path=closure_path,
        evidence_readme_path=readme_path,
    )

    assert result["ok"] is True
    assert result["ready"] is True
    assert closure_path.exists()
    assert "Phase 5 Step-9 Closure" in readme_path.read_text(encoding="utf-8")

