"""Local Ollama provider — OpenAI-compatible API."""

from __future__ import annotations

import os

import httpx

from runner import http_safety
from runner.llm_providers import LLMProvider

__all__ = ["LocalModelProvider"]


class LocalModelProvider(LLMProvider):
    """Connects to local Ollama via OpenAI-compatible endpoint."""

    def __init__(self) -> None:
        raw_base_url = os.getenv("CTOA_LOCAL_MODEL_URL", "http://localhost:11434/v1")
        allow_remote = http_safety.env_enabled(
            "CTOA_ALLOW_REMOTE_LOCAL_MODEL"
        ) or http_safety.env_enabled("CTOA_ALLOW_REMOTE_MODEL_BACKENDS")
        self.base_url = http_safety.require_model_backend_url(
            raw_base_url,
            allow_remote=allow_remote,
        )
        self.model_name = os.getenv("CTOA_LOCAL_MODEL_NAME", "qwen2.5-coder:1.5b")
        self.timeout = float(os.getenv("CTOA_LOCAL_MODEL_TIMEOUT_SECS", "120"))

    def health(self) -> bool:
        try:
            with httpx.Client(timeout=5) as client:
                base = self.base_url.replace("/v1", "")
                resp = client.get(base + "/api/tags")
                return resp.status_code == 200
        except Exception as e:
            print(f"[LocalModel] Health check failed: {e}")
            return False

    def complete(self, system_prompt, user_prompt, temperature=0.1, max_tokens=2048):
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
            resp = client.post(self.base_url + "/chat/completions", json=payload)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
