"""Local Docker Model Runner provider — OpenAI-compatible API."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

from runner.llm_providers import LLMProvider

__all__ = ["LocalModelProvider"]


class LocalModelProvider(LLMProvider):
    """Connects to local Docker Model Runner via OpenAI-compatible endpoint."""

    def __init__(self) -> None:
        self.base_url = os.getenv("CTOA_LOCAL_MODEL_URL", "http://localhost:11434/v1").rstrip("/")
        self.model_name = os.getenv("CTOA_LOCAL_MODEL_NAME", "hf.co/bartowski/Qwen2.5-Coder-1.5B-Instruct-GGUF")
        self.timeout = float(os.getenv("CTOA_LOCAL_MODEL_TIMEOUT_SECS", "120"))

    def health(self) -> bool:
        """Check if local model endpoint is reachable."""
        try:
            with httpx.Client(timeout=5) as client:
                resp = client.get(f"{self.base_url.replace('/v1', '')}/health")
                return resp.status_code == 200
        except Exception as e:
            print(f"[LocalModel] Health check failed: {e}")
            return False

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        """Send prompt to local model via OpenAI-compatible API."""
        try:
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[LocalModel] Completion failed: {e}")
            raise


def test_local_model() -> None:
    """CLI test for local model integration."""
    provider = LocalModelProvider()
    print(f"[test] Connecting to {provider.base_url}")
    print(f"[test] Model: {provider.model_name}")

    if not provider.health():
        print("[test] Health check failed — is Docker Model Runner running?")
        return

    print("[test] Health check passed ✓")

    response = provider.complete(
        system_prompt="You are a helpful assistant. Respond concisely.",
        user_prompt="Write a 1-line Python hello world function.",
        temperature=0.1,
        max_tokens=256,
    )
    print(f"[test] Model response: {response}")


if __name__ == "__main__":
    test_local_model()
