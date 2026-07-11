"""Azure Foundry provider — compatibility wrapper for existing setup."""

from __future__ import annotations

import os

from runner import http_safety
from runner.llm_providers import LLMProvider

try:
    from openai import AzureOpenAI
except ImportError:
    AzureOpenAI = None


__all__ = ["AzureFoundryProvider"]


class AzureFoundryProvider(LLMProvider):
    """Azure OpenAI Foundry provider — maintains existing integration."""

    def __init__(self) -> None:
        raw_endpoint = os.getenv("FOUNDRY_ENDPOINT", "").strip()
        self.endpoint = (
            http_safety.require_azure_service_url(raw_endpoint) if raw_endpoint else ""
        )
        self.api_key = os.getenv("FOUNDRY_API_KEY", "")
        self.api_version = os.getenv("FOUNDRY_API_VERSION", "2024-10-21")
        self.model_name = os.getenv("MODEL_MAIN_DEPLOYMENT", "gpt-4o")
        self.client = None

        if AzureOpenAI and self.endpoint and self.api_key:
            self.client = AzureOpenAI(
                azure_endpoint=self.endpoint,
                api_key=self.api_key,
                api_version=self.api_version,
            )

    def health(self) -> bool:
        """Check if Azure client is configured."""
        return self.client is not None

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        """Send prompt to Azure OpenAI."""
        if not self.client:
            raise RuntimeError("Azure OpenAI client not configured")

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""
