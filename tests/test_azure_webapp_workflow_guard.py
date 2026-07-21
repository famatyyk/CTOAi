from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "main_ctoai.yml"


def test_azure_deploy_requires_explicit_repository_variable() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")

    assert "if: vars.AZURE_DEPLOY_ENABLED == 'true'" in source
    assert "uses: azure/webapps-deploy@v3" in source
    assert "uses: azure/login@v2" in source
