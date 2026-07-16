from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config" / "otclient" / "p8-p9-review-bundles.json"


def _manifest() -> dict[str, object]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_review_bundle_manifest_is_closed_and_paths_exist() -> None:
    manifest = _manifest()
    assert manifest["schema_version"] == "ctoa.otclient-review-bundles.v1"
    assert manifest["hunk_selection_required_for_integration_paths"] is True
    assert manifest["policy"] == {
        "runtime_artifacts_are_local_only": True,
        "dispatch_allowed": False,
        "promotion_allowed": False,
        "live_client_actions_allowed": False,
    }

    bundles = manifest["bundles"]
    assert isinstance(bundles, list)
    assert [bundle["id"] for bundle in bundles] == [
        "p8-background-noscreen",
        "p9-conditions-shadow",
    ]
    assert bundles[0]["depends_on"] == []
    assert bundles[1]["depends_on"] == ["p8-background-noscreen"]

    core_sets: list[set[str]] = []
    excluded = tuple(manifest["excluded_path_markers"])
    for bundle in bundles:
        core_paths = set(bundle["core_paths"])
        core_sets.append(core_paths)
        assert core_paths
        assert len(core_paths) == len(bundle["core_paths"])
        assert "npm --prefix web test" in bundle["required_commands"]
        for relative in core_paths:
            normalized = relative.lower().replace("\\", "/")
            assert not normalized.startswith("runtime/")
            assert not any(marker in normalized for marker in excluded)
            assert (ROOT / relative).is_file(), relative

    assert core_sets[0].isdisjoint(core_sets[1])


def test_shared_paths_require_hunk_selection_and_never_become_core() -> None:
    bundles = _manifest()["bundles"]
    for bundle in bundles:
        core = set(bundle["core_paths"])
        integration = set(bundle["integration_paths"])
        assert integration
        assert core.isdisjoint(integration)
        for relative in integration:
            assert (ROOT / relative).is_file(), relative


def test_pr_templates_preserve_blocked_no_action_boundaries() -> None:
    p8 = (
        ROOT / ".github" / "PULL_REQUEST_TEMPLATE" / "p8-background-noscreen.md"
    ).read_text(encoding="utf-8")
    p9 = (
        ROOT / ".github" / "PULL_REQUEST_TEMPLATE" / "p9-conditions-shadow.md"
    ).read_text(encoding="utf-8")

    assert "blocked_pending_promotion_bound_proof" in p8
    assert "does not create, repair, or rebind" in p8
    assert "blocked_by_p8_operational_acceptance" in p9
    assert "accept P9 conditions shadow" in p9
    for template in (p8, p9):
        assert "runtime artifacts" in template
        assert "Full non-e2e Python suite" in template
        assert "Web lint/tests" in template
