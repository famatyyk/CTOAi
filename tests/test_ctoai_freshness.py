from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


PLUGIN_SCRIPTS = Path.home() / "plugins" / "ctoai-engine-brain" / "scripts"
pytestmark = pytest.mark.skipif(
    not PLUGIN_SCRIPTS.is_dir(),
    reason="Engine Brain operator plugin is not installed",
)


def load_freshness_module():
    if str(PLUGIN_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(PLUGIN_SCRIPTS))
    path = PLUGIN_SCRIPTS / "ctoai_freshness.py"
    spec = importlib.util.spec_from_file_location("ctoai_freshness_for_tests", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def valid_policy() -> dict[str, object]:
    return {
        "schema_version": 1,
        "revision": "test-v1",
        "artifacts": {
            "manifest": 300,
            "pack": 300,
            "workspace_audit": 300,
            "validation": 300,
            "p6_handoff": 300,
            "evidence": 300,
            "action_audit": 300,
            "p7_cockpit_smoke": 300,
            "p7_dry_run_smoke": 300,
        },
    }


def test_policy_is_workspace_configurable_but_strict_and_bounded(tmp_path: Path):
    freshness = load_freshness_module()
    path = tmp_path / "AI" / "control-central-freshness-policy.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(valid_policy()), encoding="utf-8")

    configured = freshness.load_freshness_policy(tmp_path)
    assert configured["status"] == "configured"
    assert configured["revision"] == "test-v1"

    invalid = valid_policy()
    invalid["artifacts"] = {"manifest": 1}
    path.write_text(json.dumps(invalid), encoding="utf-8")
    assert freshness.load_freshness_policy(tmp_path)["status"] == "fallback_invalid"


def test_freshness_classification_fails_closed_for_stale_invalid_and_future():
    freshness = load_freshness_module()
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rule = {"max_age_seconds": 300, "severity": "hard"}

    assert freshness.classify_freshness("not-a-timestamp", rule, now=now)["status"] == "invalid"
    assert (
        freshness.classify_freshness(
            (now - timedelta(seconds=301)).isoformat(), rule, now=now
        )["status"]
        == "stale"
    )
    assert (
        freshness.classify_freshness(
            (now + timedelta(seconds=301)).isoformat(), rule, now=now
        )["status"]
        == "future"
    )


def test_gate_blocks_hard_staleness_and_warns_for_soft_staleness():
    freshness = load_freshness_module()
    policy = {
        "status": "configured",
        "artifacts": {
            "evidence": {"max_age_seconds": 300, "severity": "hard"},
            "action_audit": {"max_age_seconds": 300, "severity": "warn"},
        },
    }
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    results = freshness.evaluate_freshness(
        policy,
        {
            "evidence": (now - timedelta(seconds=301)).isoformat(),
            "action_audit": (now - timedelta(seconds=301)).isoformat(),
        },
        now=now,
    )

    blockers, warnings = freshness.freshness_gate(policy, results)
    assert blockers == ["freshness:evidence:stale"]
    assert warnings == ["freshness:action_audit:stale"]


def test_engine_brain_status_cannot_report_ready_with_stale_manifest():
    freshness = load_freshness_module()
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    result = freshness.classify_freshness(
        (now - timedelta(days=2)).isoformat(),
        {"max_age_seconds": 300, "severity": "hard"},
        now=now,
    )

    blockers, _warnings = freshness.freshness_gate(
        {"status": "configured"}, {"manifest": result}
    )
    assert "freshness:manifest:stale" in blockers
