from scripts.ops.repo_hygiene_audit import classify_distribution
from scripts.ops.repo_hygiene_migration_plan import build_plan


def test_classify_distribution_marks_raw_artifacts_private_studio():
    result = classify_distribution("decrypted_xxtea")
    assert result["visibility"] == "private"
    assert result["package_tier"] == "Studio"


def test_classify_distribution_marks_mobile_console_as_pro_public():
    result = classify_distribution("mobile_console")
    assert result["visibility"] == "public"
    assert result["package_tier"] == "Pro"


def test_build_plan_carries_visibility_and_package_tier():
    plan = build_plan(
        [
            {
                "path": "decrypted_xxtea",
                "reason": "top-level artifact/data tree outside product surface",
                "visibility": "private",
                "package_tier": "Studio",
                "surface_action": "remove-from-public-surface",
            }
        ]
    )
    item = plan["batches"]["3"]["items"][0]
    assert item["visibility"] == "private"
    assert item["package_tier"] == "Studio"
    assert item["surface_action"] == "remove-from-public-surface"