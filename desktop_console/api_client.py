"""CTOA desktop API client utilities."""

from __future__ import annotations

from dataclasses import dataclass
import ipaddress
from typing import Any, Iterable
from urllib.parse import urlsplit, urlunsplit

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
        self.base_url = normalize_base_url(base_url)

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

    def auth_auto_check(self) -> dict[str, Any]:
        return self._request("GET", "/api/auth/auto-check")
    def status(self) -> dict[str, Any]:
        return self._request("GET", "/api/status")

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/api/health")

    def dashboard(self) -> dict[str, Any]:
        return self._request("GET", "/api/dashboard")

    def agents_status(self) -> dict[str, Any]:
        return self._request("GET", "/api/agents/status")

    def intel_report(self) -> dict[str, Any]:
        return self._request("GET", "/api/agents/intel/report")

    def launch_intel_mission(
        self,
        urls: Iterable[str] | None = None,
        force_rescout: bool = False,
        trigger_now: bool = True,
        reason: str = "",
        confirm: bool = True,
    ) -> dict[str, Any]:
        payload = {
            "urls": [str(url).strip() for url in (urls or []) if str(url).strip()],
            "force_rescout": bool(force_rescout),
            "trigger_now": bool(trigger_now),
            "confirm": bool(confirm),
            "reason": str(reason).strip(),
        }
        return self._request("POST", "/api/agents/intel/launch", json_body=payload)

    def run_agents_one_click(self, reason: str = "", confirm: bool = True) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/agents/execution/run",
            json_body={"confirm": bool(confirm), "reason": str(reason).strip()},
        )

    def live_profile(self) -> dict[str, Any]:
        return self._request("GET", "/api/live-dashboard/profile")

    def save_live_profile(self, api_base: str, refresh_seconds: int) -> dict[str, Any]:
        return self._request(
            "PUT",
            "/api/live-dashboard/profile",
            json_body={
                "api_base": str(api_base).strip(),
                "refresh_seconds": int(refresh_seconds),
            },
        )

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
            self._token = str()
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


def _is_local_http_host(hostname: str) -> bool:
    host = hostname.strip().lower()
    if host == "localhost" or host.endswith(".localhost"):
        return True

    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def normalize_base_url(raw_url: str) -> str:
    value = str(raw_url or "").strip().rstrip("/")
    if not value:
        raise ApiError("API base URL is required")

    if "://" not in value:
        value = f"http://{value}"

    parsed = urlsplit(value)
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"} or not parsed.netloc or not parsed.hostname:
        raise ApiError("API base URL must be an absolute HTTP(S) URL")

    if parsed.username or parsed.password:
        raise ApiError("API base URL must not include credentials")

    if parsed.query or parsed.fragment:
        raise ApiError("API base URL must not include query strings or fragments")

    if scheme == "http" and not _is_local_http_host(parsed.hostname):
        raise ApiError("API base URL must use https:// for non-local hosts")

    normalized_path = parsed.path.rstrip("/")
    return urlunsplit((scheme, parsed.netloc, normalized_path, "", ""))


def _normalize_base_url(raw_url: str) -> str:
    return normalize_base_url(raw_url)
