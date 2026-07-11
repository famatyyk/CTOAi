import ssl
from pathlib import Path

import pytest

from runner.http_safety import (
    discovery_ssl_context,
    require_azure_service_url,
    require_discord_webhook_url,
    require_github_api_url,
    require_github_repository,
    require_http_url,
    require_loopback_http_url,
    require_model_backend_url,
    require_notify_webhook_url,
    require_public_discovery_url,
)


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/data",
        "https:///missing-host",
        "example.com/no-scheme",
    ],
)
def test_require_http_url_rejects_non_http_urls(url: str) -> None:
    with pytest.raises(ValueError):
        require_http_url(url)


@pytest.mark.parametrize("url", ["http://example.com", "https://example.com/path"])
def test_require_http_url_allows_http_urls(url: str) -> None:
    assert require_http_url(url) == url


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://localhost:8000/catalog",
        "http://127.0.0.1:8000/catalog",
        "http://10.0.0.4/catalog",
        "http://172.16.0.4/catalog",
        "http://192.168.1.5/catalog",
        "http://169.254.169.254/latest/meta-data",
        "http://[::1]:8000/catalog",
        "http://user:secret@example.com/catalog",
        "https://example.com/catalog#token",
        "https://example.com/catalog?access_token=secret",
        "https://example.com/catalog/../admin",
        "https://example.com/catalog\\admin",
        "http://internal-service/catalog",
        "http://dashboard.local/catalog",
        "http://2130706433/catalog",
    ],
)
def test_require_public_discovery_url_rejects_ssrf_and_secret_urls(
    url: str,
) -> None:
    with pytest.raises(ValueError):
        require_public_discovery_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://otservlist.org/list-server_players-desc.html",
        "https://open-tibia.com/api/status?name=Gamemaster",
        "https://93.184.216.34/api/status",
    ],
)
def test_require_public_discovery_url_allows_public_discovery_targets(
    url: str,
) -> None:
    assert require_public_discovery_url(url) == url


def test_discovery_agents_use_public_discovery_url_guard() -> None:
    root = Path(__file__).resolve().parents[1]
    for relative in [
        "runner/agents/catalog_agent.py",
        "runner/agents/scout_agent.py",
        "runner/agents/ingest_agent.py",
    ]:
        text = (root / relative).read_text(encoding="utf-8")
        assert "require_public_discovery_url" in text
        assert "safe_url = http_safety.require_http_url" not in text


@pytest.mark.parametrize(
    "url",
    [
        "http://api.github.com/repos/famatyyk/CTOAi",
        "https://api.github.com.evil.test/repos/famatyyk/CTOAi",
        "https://user:secret@api.github.com/repos/famatyyk/CTOAi",
        "https://api.github.com/repos/famatyyk/CTOAi#secret",
        "https://api.github.com/repos/famatyyk/CTOAi?access_token=secret",
        "https://api.github.com/repos/famatyyk/CTOAi?client_secret=secret",
        "https://api.github.com/repos/famatyyk/CTOAi/../other",
        "https://api.github.com/repos//CTOAi/issues",
        "https://api.github.com/repos/famatyyk//issues",
        "https://api.github.com/repos/famatyyk%2Fother/CTOAi/issues",
        "https://api.github.com/repos/famatyyk/CTOAi%5Cevil/issues",
        "https://api.github.com/search/issues?q=repo:famatyyk/CTOAi",
    ],
)
def test_require_github_api_url_rejects_unsafe_urls(url: str) -> None:
    with pytest.raises(ValueError):
        require_github_api_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://api.github.com/repos/famatyyk/CTOAi",
        "https://api.github.com/repos/famatyyk/CTOAi/issues?state=open&per_page=100&page=2",
        "https://api.github.com/repos/famatyyk/CTOAi/actions/runs?per_page=100&page=1",
        "https://api.github.com/repos/famatyyk/CTOAi/issues/1/comments",
    ],
)
def test_require_github_api_url_allows_repo_api_urls(url: str) -> None:
    assert require_github_api_url(url) == url


@pytest.mark.parametrize(
    "repo",
    [
        "",
        "famatyyk",
        "/CTOAi",
        "famatyyk/",
        "famatyyk/CTOAi/issues",
        "famatyyk%2Fother/CTOAi",
        "famatyyk/CTOAi%5Cevil",
        "../CTOAi",
        "famatyyk/..",
        "fam at/CTOAi",
        "famatyyk/CTOAi?token=secret",
    ],
)
def test_require_github_repository_rejects_unsafe_repo_ids(repo: str) -> None:
    with pytest.raises(ValueError):
        require_github_repository(repo)


@pytest.mark.parametrize(
    "repo",
    [
        "famatyyk/CTOAi",
        "openai/.github",
        "owner/repo.name_1-2",
    ],
)
def test_require_github_repository_allows_owner_repo_ids(repo: str) -> None:
    assert require_github_repository(repo) == repo


def test_token_bearing_github_callers_validate_repository_ids() -> None:
    root = Path(__file__).resolve().parents[1]
    for relative in [
        "runner/runner.py",
        "runner/daily_insights.py",
        "runner/weekly_report.py",
        "runner/issue_sync.py",
        "runner/status_sync.py",
        "runner/close_on_gate.py",
        "runner/health_metrics.py",
        "scripts/ops/ci_executive_report.py",
    ]:
        source = (root / relative).read_text(encoding="utf-8")
        assert "require_github_repository" in source


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com:8001/api/auth/login",
        "http://127.0.0.1:8001/api/auth/login?token=secret",
        "http://user:secret@127.0.0.1:8001/api/auth/login",
        "http://127.0.0.1:8001/api/auth/login#token",
        "http://127.0.0.1:8001/api/../auth/login",
        "http://127.0.0.1:8001/api\\auth\\login",
        "http://127.0.0.2:8001/api/auth/login",
    ],
)
def test_require_loopback_http_url_rejects_unsafe_urls(url: str) -> None:
    with pytest.raises(ValueError):
        require_loopback_http_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8001",
        "http://127.0.0.1:8001/api/auth/login",
        "http://localhost:8001/api/auth/login",
        "http://[::1]:8001/api/auth/login",
    ],
)
def test_require_loopback_http_url_allows_local_urls(url: str) -> None:
    assert require_loopback_http_url(url) == url


@pytest.mark.parametrize(
    "url",
    [
        "https://models.example.test/v1",
        "http://models.example.test/v1",
        "http://127.0.0.1:11434/v1?token=secret",
        "http://user:secret@127.0.0.1:11434/v1",
        "http://host.docker.internal:11434/v1#token",
        "http://127.0.0.1:11434/v1/../admin",
    ],
)
def test_require_model_backend_url_rejects_unsafe_defaults(url: str) -> None:
    with pytest.raises(ValueError):
        require_model_backend_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:11434/v1",
        "http://localhost:11434/v1",
        "http://host.docker.internal:11434/v1/",
    ],
)
def test_require_model_backend_url_allows_local_backends(url: str) -> None:
    assert require_model_backend_url(url) == url.rstrip("/")


def test_require_model_backend_url_allows_remote_only_with_https_opt_in() -> None:
    assert (
        require_model_backend_url(
            "https://models.example.test/v1",
            allow_remote=True,
        )
        == "https://models.example.test/v1"
    )
    with pytest.raises(ValueError):
        require_model_backend_url("http://models.example.test/v1", allow_remote=True)


@pytest.mark.parametrize(
    "url",
    [
        "http://resource.openai.azure.com",
        "https://resource.example.test",
        "https://user:secret@resource.openai.azure.com",
        "https://resource.openai.azure.com?api_key=secret",
        "https://resource.openai.azure.com/deployments/../other",
    ],
)
def test_require_azure_service_url_rejects_unsafe_urls(url: str) -> None:
    with pytest.raises(ValueError):
        require_azure_service_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://resource.openai.azure.com",
        "https://resource.cognitiveservices.azure.com",
        "https://project.services.ai.azure.com/api/projects/example",
    ],
)
def test_require_azure_service_url_allows_azure_hosts(url: str) -> None:
    assert require_azure_service_url(url) == url


@pytest.mark.parametrize(
    "url",
    [
        "http://hooks.slack.com/services/T/B/C",
        "https://hooks.slack.com/services/T/B/C?token=secret",
        "https://hooks.slack.com/services/T/B/C#secret",
        "https://user:secret@hooks.slack.com/services/T/B/C",
        "https://hooks.slack.com/services/T/B/../C",
        "https://hooks.slack.com/services/T/B/%2fsecret",
        "https://evil.example.test/services/T/B/C",
        "https://discord.com/api/webhooks/123/token#fragment",
        "https://discord.com/api\\webhooks\\123\\token",
        "https://discord.com/api/webhooks/123",
        "https://discord.com/channels/123/token",
    ],
)
def test_require_notify_webhook_url_rejects_unsafe_urls(url: str) -> None:
    with pytest.raises(ValueError):
        require_notify_webhook_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://hooks.slack.com/services/T000/B000/secret",
        "https://hooks.slack-gov.com/services/T000/B000/secret",
        "https://discord.com/api/webhooks/123/token",
        "https://discordapp.com/api/webhooks/123/token",
    ],
)
def test_require_notify_webhook_url_allows_slack_and_discord(url: str) -> None:
    assert require_notify_webhook_url(url) == url


@pytest.mark.parametrize(
    "url",
    [
        "http://discord.com/api/webhooks/123/token",
        "https://hooks.slack.com/services/T000/B000/secret",
        "https://evil.example.test/api/webhooks/123/token",
        "https://user:secret@discord.com/api/webhooks/123/token",
        "https://discord.com/api/webhooks/123/token?wait=true",
        "https://discord.com/api/webhooks/123/token#fragment",
        "https://discord.com/api/webhooks/123/../token",
        "https://discord.com/api/webhooks/123/%2ftoken",
        "https://discord.com/api\\webhooks\\123\\token",
        "https://discord.com/api/webhooks/123",
        "https://discord.com/channels/123/token",
    ],
)
def test_require_discord_webhook_url_rejects_unsafe_urls(url: str) -> None:
    with pytest.raises(ValueError):
        require_discord_webhook_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://discord.com/api/webhooks/123/token",
        "https://discordapp.com/api/webhooks/123/token",
    ],
)
def test_require_discord_webhook_url_allows_discord_hosts(url: str) -> None:
    assert require_discord_webhook_url(url) == url


def test_discovery_ssl_context_verifies_tls_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CTOA_TEST_ALLOW_INSECURE_SSL", raising=False)

    ctx = discovery_ssl_context("CTOA_TEST_ALLOW_INSECURE_SSL")

    assert ctx.check_hostname is True
    assert ctx.verify_mode == ssl.CERT_REQUIRED


def test_discovery_ssl_context_requires_explicit_insecure_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CTOA_TEST_ALLOW_INSECURE_SSL", "true")

    ctx = discovery_ssl_context("CTOA_TEST_ALLOW_INSECURE_SSL")

    assert ctx.check_hostname is False
    assert ctx.verify_mode == ssl.CERT_NONE
