from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "cd_bot.yml"
COMPOSE = ROOT / "bot" / "infra" / "docker-compose.yml"


def test_bot_cd_recovers_disk_without_deleting_named_volumes() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")

    assert "Recover VPS disk before sync" in source
    assert 'if [ "$FREE_MB" -lt 512 ]' in source
    assert 'if [ "$FREE_MB" -lt 256 ]' in source
    assert 'if [ "$FREE_MB" -lt 4096 ]' in source
    assert "docker compose down --remove-orphans" not in source
    assert "docker compose stop bot dashboard" in source
    assert "docker compose rm -f bot dashboard" in source
    assert "docker system prune -af" in source
    assert "docker system prune -af --volumes" not in source
    assert 'if [ "$FREE_MB" -lt 2048 ]' in source
    assert "docker compose build bot" in source
    assert "docker compose build bot dashboard" not in source
    assert "docker compose pull prometheus grafana" not in source
    assert "docker compose up -d bot dashboard" in source
    assert 'if [ "$FREE_MB" -ge 1536 ]' in source
    assert "docker compose up -d prometheus grafana" in source


def test_bot_and_dashboard_share_one_built_image() -> None:
    payload = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    services = payload["services"]

    assert services["bot"]["image"] == "ctoa-bot:latest"
    assert services["dashboard"]["image"] == "ctoa-bot:latest"
    assert "build" in services["bot"]
    assert "build" not in services["dashboard"]
