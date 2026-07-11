from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_root_compose_api_binds_to_loopback_by_default():
    text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert '"0.0.0.0:8001:8000"' not in text
    assert '"${CTOA_BIND_HOST:-127.0.0.1}:8001:8000"' in text


def test_bot_infra_compose_binds_dashboard_and_monitoring_to_loopback_by_default():
    text = (ROOT / "bot" / "infra" / "docker-compose.yml").read_text(encoding="utf-8")

    assert 'version: "3.9"' not in text
    assert '"8000:8000"' not in text
    assert '"9090:9090"' not in text
    assert '"${CTOA_BOT_DASHBOARD_BIND_HOST:-127.0.0.1}:8000:8000"' in text
    assert '"${CTOA_MONITOR_BIND_HOST:-127.0.0.1}:9090:9090"' in text


def test_env_example_documents_local_bind_controls():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")

    assert "CTOA_BIND_HOST=127.0.0.1" in text
    assert "CTOA_BOT_DASHBOARD_BIND_HOST=127.0.0.1" in text
    assert "CTOA_MONITOR_BIND_HOST=127.0.0.1" in text
    assert "intentionally need access from another device" in text
