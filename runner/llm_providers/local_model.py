"""Local Ollama provider — OpenAI-compatible API."""

from __future__ import annotations

import os

import httpx

from runner.llm_providers import LLMProvider

__all__ = ["LocalModelProvider"]


class LocalModelProvider(LLMProvider):
    """Connects to local Ollama via OpenAI-compatible endpoint."""

    def __init__(self) -> None:
        self.base_url = os.getenv("CTOA_LOCAL_MODEL_URL", "http://localhost:11434/v1").rstrip("/")
        self.model_name = os.getenv("CTOA_LOCAL_MODEL_NAME", "qwen2.5-coder:1.5b")
        self.timeout = float(os.getenv("CTOA_LOCAL_MODEL_TIMEOUT_SECS", "120"))

    def _api_root(self) -> str:
        if self.base_url.endswith("/v1"):
            return self.base_url[:-3]
        return self.base_url

    def health(self) -> bool:
        try:
            with httpx.Client(timeout=5) as client:
                resp = client.get(self._api_root() + "/api/tags")
                return resp.status_code == 200
        except Exception as e:
            print(f"[LocalModel] Health check failed: {e}")
            return False

    def complete(self, system_prompt, user_prompt, temperature=0.1, max_tokens=2048):
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        openai_payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        with httpx.Client(timeout=self.timeout) as client:
            openai_url = self.base_url + "/chat/completions"
            resp = client.post(openai_url, json=openai_payload)
            if resp.status_code != 404:
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]

            # Fallback for Ollama deployments exposing only native API.
            native_payload = {
                "model": self.model_name,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            }
            native_url = self._api_root() + "/api/chat"
            native_resp = client.post(native_url, json=native_payload)
            native_resp.raise_for_status()
            return native_resp.json()["message"]["content"]
