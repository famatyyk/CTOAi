"""LLM provider abstraction — Azure Foundry / Local Docker Model Runner / fallback."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod

__all__ = ["LLMProvider", "get_provider"]


class LLMProvider(ABC):
    """Base class for LLM providers."""

    @abstractmethod
    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        """Send prompt to model and return completion."""
        pass

    @abstractmethod
    def health(self) -> bool:
        """Check provider health."""
        pass


def get_provider() -> LLMProvider:
    """Factory: return configured provider based on environment."""
    mode = os.getenv("CTOA_LLM_PROVIDER", "auto").lower()

    # Explicit local model override
    if mode == "local":
        from runner.llm_providers.local_model import LocalModelProvider

        return LocalModelProvider()

    # Explicit Azure Foundry
    if mode == "azure":
        from runner.llm_providers.azure_foundry import AzureFoundryProvider

        return AzureFoundryProvider()

    # Auto-detect: local model if available, fallback to Azure
    if mode == "auto":
        try:
            from runner.llm_providers.local_model import LocalModelProvider

            provider = LocalModelProvider()
            if provider.health():
                return provider
        except Exception as exc:
            print(
                f"[llm] Local provider auto-detect failed; falling back to Azure: {exc}"
            )

        from runner.llm_providers.azure_foundry import AzureFoundryProvider

        return AzureFoundryProvider()

    raise ValueError(f"Unknown LLM provider mode: {mode}")
