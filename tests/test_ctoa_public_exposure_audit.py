import json
from pathlib import Path

from scripts.ops.ctoa_public_exposure_audit import evaluate_snapshot


PROJECT_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = PROJECT_ROOT / "config" / "security" / "public-exposure-policy.json"


def _policy():
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def _snapshot():
    return {
        "github": {
            "repositories": [
                {
                    "full_name": "famatyyk/CTOAi",
                    "private": True,
                    "fork": False,
                    "has_pages": False,
                },
                {
                    "full_name": "famatyyk/otclient",
                    "private": False,
                    "fork": True,
                    "has_pages": False,
                },
                {
                    "full_name": "famatyyk/zerobot-docs",
                    "private": False,
                    "fork": True,
                    "has_pages": False,
                },
            ],
            "public_fork_branches": {
                "famatyyk/otclient": {
                    "reported_parent": "edubart/otclient",
                    "fork_branches": {"master": "abc"},
                    "upstream_branches": {"master": "abc"},
                },
                "famatyyk/zerobot-docs": {
                    "reported_parent": "Cjaker/zerobot-docs",
                    "fork_branches": {"main": "def"},
                    "upstream_branches": {"main": "def"},
                },
            },
        },
        "vercel": {
            "aliases": {"aliases": []},
            "project": {"autoAssignCustomDomains": False},
            "protection": {
                "ssoProtection": {"deploymentType": "all_except_custom_domains"}
            },
        },
    }


def test_private_first_snapshot_passes():
    report = evaluate_snapshot(_policy(), _snapshot())

    assert report["mode"] == "private_first"
    assert report["status"] == "passed"


def test_public_owned_source_fails():
    snapshot = _snapshot()
    snapshot["github"]["repositories"][0]["private"] = False

    report = evaluate_snapshot(_policy(), snapshot)

    assert report["status"] == "failed"
    assert (
        next(
            check
            for check in report["checks"]
            if check["name"] == "github_owned_sources_private"
        )["status"]
        == "failed"
    )


def test_divergent_public_fork_fails():
    snapshot = _snapshot()
    snapshot["github"]["public_fork_branches"]["famatyyk/otclient"]["fork_branches"][
        "master"
    ] = "private-change"

    report = evaluate_snapshot(_policy(), snapshot)

    assert report["status"] == "failed"
    assert (
        next(
            check
            for check in report["checks"]
            if check["name"] == "github_public_forks_match_upstream"
        )["status"]
        == "failed"
    )


def test_public_vercel_alias_or_auto_assignment_fails():
    snapshot = _snapshot()
    snapshot["vercel"]["aliases"]["aliases"] = [{"alias": "ctoa-web.vercel.app"}]
    snapshot["vercel"]["project"]["autoAssignCustomDomains"] = True

    report = evaluate_snapshot(_policy(), snapshot)

    assert report["status"] == "failed"
    failed = {
        check["name"] for check in report["checks"] if check["status"] == "failed"
    }
    assert "vercel_public_aliases_absent" in failed
    assert "vercel_auto_alias_assignment_disabled" in failed


def test_pages_publication_workflow_is_disabled():
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "site-pages.yml").read_text(
        encoding="utf-8"
    )

    assert "actions/deploy-pages" not in workflow
    assert "upload-pages-artifact" not in workflow


def test_private_repo_has_local_secret_scanner():
    pre_commit = (PROJECT_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")

    assert "https://github.com/gitleaks/gitleaks" in pre_commit
    assert "id: gitleaks-docker" in pre_commit
