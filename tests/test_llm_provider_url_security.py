import asyncio

import pytest

import api.main as api_main
from runner.llm_providers.azure_foundry import AzureFoundryProvider
from runner.llm_providers.local_model import LocalModelProvider


def test_local_model_provider_rejects_remote_backend_without_opt_in(monkeypatch):
    monkeypatch.setenv("CTOA_LOCAL_MODEL_URL", "https://models.example.test/v1")
    monkeypatch.delenv("CTOA_ALLOW_REMOTE_LOCAL_MODEL", raising=False)
    monkeypatch.delenv("CTOA_ALLOW_REMOTE_MODEL_BACKENDS", raising=False)

    with pytest.raises(ValueError):
        LocalModelProvider()


def test_local_model_provider_allows_local_backend(monkeypatch):
    monkeypatch.setenv("CTOA_LOCAL_MODEL_URL", "http://host.docker.internal:11434/v1/")

    provider = LocalModelProvider()

    assert provider.base_url == "http://host.docker.internal:11434/v1"


def test_local_model_provider_requires_https_for_remote_opt_in(monkeypatch):
    monkeypatch.setenv("CTOA_ALLOW_REMOTE_LOCAL_MODEL", "true")
    monkeypatch.setenv("CTOA_LOCAL_MODEL_URL", "http://models.example.test/v1")

    with pytest.raises(ValueError):
        LocalModelProvider()

    monkeypatch.setenv("CTOA_LOCAL_MODEL_URL", "https://models.example.test/v1")
    provider = LocalModelProvider()
    assert provider.base_url == "https://models.example.test/v1"


def test_azure_provider_rejects_unsafe_endpoint_before_client(monkeypatch):
    calls: list[dict[str, str]] = []

    class FakeAzureOpenAI:
        def __init__(self, **kwargs):
            calls.append(kwargs)

    monkeypatch.setattr(
        "runner.llm_providers.azure_foundry.AzureOpenAI",
        FakeAzureOpenAI,
    )
    monkeypatch.setenv("FOUNDRY_API_KEY", "secret-key")
    monkeypatch.setenv("FOUNDRY_ENDPOINT", "https://evil.example.test")

    with pytest.raises(ValueError):
        AzureFoundryProvider()

    assert calls == []


def test_azure_provider_accepts_allowlisted_https_endpoint(monkeypatch):
    calls: list[dict[str, str]] = []

    class FakeAzureOpenAI:
        def __init__(self, **kwargs):
            calls.append(kwargs)

    monkeypatch.setattr(
        "runner.llm_providers.azure_foundry.AzureOpenAI",
        FakeAzureOpenAI,
    )
    monkeypatch.setenv("FOUNDRY_API_KEY", "secret-key")
    monkeypatch.setenv("FOUNDRY_ENDPOINT", "https://resource.openai.azure.com/")

    provider = AzureFoundryProvider()

    assert provider.client is not None
    assert calls[0]["azure_endpoint"] == "https://resource.openai.azure.com"


def test_api_call_model_rejects_remote_backend_before_http_client(monkeypatch):
    class FailClient:
        def __init__(self, *_args, **_kwargs):
            raise AssertionError("http client must not be constructed")

    monkeypatch.delenv("CTOA_ALLOW_REMOTE_MODEL_BACKENDS", raising=False)
    monkeypatch.setattr(api_main.httpx, "AsyncClient", FailClient)

    with pytest.raises(ValueError):
        asyncio.run(
            api_main._call_model(
                "model",
                "https://models.example.test/v1?token=secret",
                "secret-key",
                [{"role": "user", "content": "hello"}],
                0.1,
                128,
            )
        )
