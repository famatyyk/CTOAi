"""CTOA desktop API client utilities."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

import requests


class ApiError(RuntimeError):
    """Raised when API communication or API-level validation fails."""


@dataclass(slots=True)
class AuthContext:
    username: str
    role: str
    auth_mode: str


class CtoaApiClient:
    def __init__(self, base_url: str) -> None:
        self._token: str = ""
        self.session = requests.Session()
        self.base_url = ""
        self.set_base_url(base_url)

    def set_base_url(self, base_url: str) -> None:
        self.base_url = _normalize_base_url(base_url)

    def login(self, username: str, password: str) -> AuthContext:
        payload = self._request("POST", "/api/auth/login", json_body={
            "username": username,
            "password": password,
        })
        token = str(payload.get("token", ""))
        if token:
            self._token = token
        return self.me()

    def register(self, username: str, password: str, registration_code: str = "") -> dict[str, Any]:
        return self._request("POST", "/api/auth/register", json_body={
            "username": username,
            "password": password,
            "registration_code": registration_code,
        })

    def me(self) -> AuthContext:
        payload = self._request("GET", "/api/auth/me")
        return AuthContext(
            username=str(payload.get("username", "")),
            role=str(payload.get("role", "operator")),
            auth_mode=str(payload.get("auth_mode", "unknown")),
        )

    def status(self) -> dict[str, Any]:
        return self._request("GET", "/api/status")

    def presets(self) -> list[str]:
        payload = self._request("GET", "/api/presets")
        commands = payload.get("commands", [])
        if isinstance(commands, list):
            return [str(cmd) for cmd in commands]
        return []

    def run_command(self, command: str, timeout: int = 25, cwd: str = "") -> dict[str, Any]:
        return self._request("POST", "/api/command", json_body={
            "command": command,
            "timeout": timeout,
            "cwd": cwd,
        })

    def logout(self) -> None:
        try:
            self._request("POST", "/api/auth/logout")
        finally:
            self._token = ""
            self.session.cookies.clear()

    def _request(self, method: str, path: str, json_body: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        headers: dict[str, str] = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                json=json_body,
                timeout=25,
            )
        except requests.RequestException as exc:
            raise ApiError(f"Network error while calling {path}: {exc}") from exc

        payload: dict[str, Any]
        if response.content:
            try:
                raw_payload = response.json()
                payload = raw_payload if isinstance(raw_payload, dict) else {"payload": raw_payload}
            except ValueError:
                payload = {"detail": response.text.strip()}
        else:
            payload = {}

        if response.status_code >= 400:
            detail = payload.get("detail") or payload.get("error") or response.reason
            raise ApiError(f"{response.status_code} {detail}")

        return payload


def _normalize_base_url(raw_url: str) -> str:
    value = str(raw_url or "").strip().rstrip("/")
    if not value:
        raise ApiError("API base URL is required")
    if not re.match(r"^https?://", value, re.IGNORECASE):
        value = f"http://{value}"
    return value
