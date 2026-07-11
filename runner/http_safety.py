"""HTTP guardrails shared by runner scripts and agents."""

from __future__ import annotations

import os
import ssl
import ipaddress
import re
import urllib.parse


_TRUE_VALUES = {"1", "true", "yes", "on"}
_GITHUB_OWNER_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38}[A-Za-z0-9])?$")
_GITHUB_REPO_RE = re.compile(r"^[A-Za-z0-9._-]+$")
_GITHUB_API_ALLOWED_QUERY_KEYS = {
    "direction",
    "labels",
    "page",
    "per_page",
    "recursive",
    "since",
    "sort",
    "state",
}
_TOKEN_QUERY_KEYS = {
    "access_token",
    "api_key",
    "auth_token",
    "client_secret",
    "private_token",
    "refresh_token",
    "token",
}
_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}
_LOCAL_MODEL_HOSTS = _LOOPBACK_HOSTS | {"host.docker.internal"}
_INTERNAL_HOST_SUFFIXES = (".local", ".internal", ".lan", ".home", ".corp")
_AZURE_SERVICE_HOST_SUFFIXES = (
    ".openai.azure.com",
    ".cognitiveservices.azure.com",
    ".services.ai.azure.com",
)
_DISCORD_WEBHOOK_HOSTS = {"discord.com", "discordapp.com"}
_SLACK_WEBHOOK_HOSTS = {"hooks.slack.com", "hooks.slack-gov.com"}


def env_enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in _TRUE_VALUES


def require_http_url(url: str) -> str:
    value = str(url or "").strip()
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL must use http:// or https:// and include a host")
    return value


def require_github_repository(repo: str) -> str:
    value = str(repo or "").strip()
    parts = value.split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError("GitHub repository must use owner/repo format")

    owner, name = parts
    decoded_parts = [urllib.parse.unquote(part) for part in parts]
    if any(part in {".", ".."} for part in decoded_parts):
        raise ValueError("GitHub repository must not contain traversal segments")
    if any("/" in part or "\\" in part for part in decoded_parts):
        raise ValueError("GitHub repository must not contain encoded separators")
    if not _GITHUB_OWNER_RE.fullmatch(owner) or not _GITHUB_REPO_RE.fullmatch(name):
        raise ValueError("GitHub repository contains unsupported characters")
    return f"{owner}/{name}"


def require_github_api_url(url: str) -> str:
    value = require_http_url(url)
    parsed = urllib.parse.urlparse(value)
    host = (parsed.hostname or "").lower()
    if parsed.scheme.lower() != "https" or host != "api.github.com":
        raise ValueError("GitHub API URL must use https://api.github.com")
    if parsed.username or parsed.password or parsed.fragment:
        raise ValueError("GitHub API URL must not include credentials or fragments")
    if "\\" in parsed.path or not parsed.path.startswith("/repos/"):
        raise ValueError("GitHub API URL path must stay under /repos/")
    path_parts = [urllib.parse.unquote(part) for part in parsed.path.split("/")]
    if (
        len(path_parts) < 4
        or path_parts[0] != ""
        or path_parts[1] != "repos"
        or not path_parts[2]
        or not path_parts[3]
    ):
        raise ValueError("GitHub API URL path must include owner and repo")
    if any(part in {".", ".."} for part in path_parts):
        raise ValueError("GitHub API URL path must not contain traversal")
    if any("/" in part or "\\" in part for part in path_parts[2:]):
        raise ValueError("GitHub API URL path must not contain encoded separators")
    for key, _value in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True):
        normalized = key.strip().lower()
        if normalized in _TOKEN_QUERY_KEYS:
            raise ValueError("GitHub API URL must not include token query parameters")
        if normalized not in _GITHUB_API_ALLOWED_QUERY_KEYS:
            raise ValueError("GitHub API URL query parameter is not allowed")
    return value


def require_loopback_http_url(url: str) -> str:
    value = require_http_url(url)
    parsed = urllib.parse.urlparse(value)
    host = (parsed.hostname or "").lower()
    if host not in _LOOPBACK_HOSTS:
        raise ValueError("URL must use localhost, 127.0.0.1, or [::1]")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError(
            "Loopback URL must not include credentials, query, or fragment"
        )
    if "\\" in parsed.path:
        raise ValueError("Loopback URL path must not include backslashes")
    path_parts = [urllib.parse.unquote(part) for part in parsed.path.split("/")]
    if any(part in {".", ".."} for part in path_parts):
        raise ValueError("Loopback URL path must not contain traversal")
    return value


def _reject_token_query(parsed: urllib.parse.ParseResult, label: str) -> None:
    for key, _value in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True):
        if key.strip().lower() in _TOKEN_QUERY_KEYS:
            raise ValueError(f"{label} URL must not include token query parameters")


def _is_ip_literal(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True


def _reject_private_discovery_host(host: str, label: str) -> None:
    if not host:
        raise ValueError(f"{label} URL must include a host")

    normalized = host.rstrip(".").lower()
    if normalized in _LOCAL_MODEL_HOSTS:
        raise ValueError(f"{label} URL must not target loopback or local hosts")

    try:
        ip = ipaddress.ip_address(normalized)
    except ValueError:
        # Avoid ambiguous IPv4 forms such as decimal or octal-like host strings.
        if all(ch.isdigit() or ch == "." for ch in normalized):
            raise ValueError(f"{label} URL host must not use ambiguous IP notation")
        if "." not in normalized:
            raise ValueError(f"{label} URL host must be a public domain name")
        if normalized.endswith(_INTERNAL_HOST_SUFFIXES):
            raise ValueError(f"{label} URL host must not be an internal hostname")
        return

    if not ip.is_global:
        raise ValueError(f"{label} URL must not target private or reserved IPs")


def require_public_discovery_url(url: str, *, label: str = "Discovery") -> str:
    value = require_http_url(url)
    parsed = urllib.parse.urlparse(value)
    if parsed.username or parsed.password or parsed.fragment:
        raise ValueError(f"{label} URL must not include credentials or fragments")
    if "\\" in parsed.path:
        raise ValueError(f"{label} URL path must not include backslashes")
    path_parts = [urllib.parse.unquote(part) for part in parsed.path.split("/")]
    if any(part in {".", ".."} for part in path_parts):
        raise ValueError(f"{label} URL path must not contain traversal")
    _reject_token_query(parsed, label)
    host = (parsed.hostname or "").lower()
    _reject_private_discovery_host(host, label)
    return value


def _reject_url_secret_parts(parsed: urllib.parse.ParseResult, label: str) -> None:
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError(
            f"{label} URL must not include credentials, query, or fragment"
        )
    if "\\" in parsed.path:
        raise ValueError(f"{label} URL path must not include backslashes")
    path_parts = [urllib.parse.unquote(part) for part in parsed.path.split("/")]
    if any(part in {".", ".."} for part in path_parts):
        raise ValueError(f"{label} URL path must not contain traversal")


def require_model_backend_url(url: str, *, allow_remote: bool = False) -> str:
    value = require_http_url(url)
    parsed = urllib.parse.urlparse(value)
    _reject_url_secret_parts(parsed, "Model backend")
    host = (parsed.hostname or "").lower()
    if host in _LOCAL_MODEL_HOSTS:
        return value.rstrip("/")
    if not allow_remote:
        raise ValueError("Remote model backend URLs require explicit opt-in")
    if parsed.scheme.lower() != "https":
        raise ValueError("Remote model backend URLs must use https://")
    return value.rstrip("/")


def require_azure_service_url(url: str) -> str:
    value = require_http_url(url)
    parsed = urllib.parse.urlparse(value)
    _reject_url_secret_parts(parsed, "Azure service")
    host = (parsed.hostname or "").lower()
    if parsed.scheme.lower() != "https":
        raise ValueError("Azure service URL must use https://")
    if not any(host.endswith(suffix) for suffix in _AZURE_SERVICE_HOST_SUFFIXES):
        raise ValueError("Azure service URL host is not allowlisted")
    return value.rstrip("/")


def _require_strict_path_parts(
    parsed: urllib.parse.ParseResult,
    label: str,
) -> list[str]:
    _reject_url_secret_parts(parsed, label)
    if not parsed.path.startswith("/") or parsed.path.endswith("/") or "//" in parsed.path:
        raise ValueError(f"{label} URL path is incomplete")
    parts = [urllib.parse.unquote(part) for part in parsed.path.lstrip("/").split("/")]
    if any(not part or part in {".", ".."} for part in parts):
        raise ValueError(f"{label} URL path must not contain empty or traversal segments")
    if any("/" in part or "\\" in part for part in parts):
        raise ValueError(f"{label} URL path must not contain encoded path separators")
    return parts


def require_notify_webhook_url(url: str) -> str:
    value = require_http_url(url)
    parsed = urllib.parse.urlparse(value)
    host = (parsed.hostname or "").lower()
    if parsed.scheme.lower() != "https":
        raise ValueError("Notify webhook URL must use https://")
    parts = _require_strict_path_parts(parsed, "Notify webhook")
    if host in _SLACK_WEBHOOK_HOSTS:
        if len(parts) >= 4 and parts[0] == "services":
            return value
        raise ValueError("Slack webhook URL path is not allowlisted")
    if host in _DISCORD_WEBHOOK_HOSTS:
        if len(parts) >= 4 and parts[:2] == ["api", "webhooks"]:
            return value
        raise ValueError("Discord webhook URL path is not allowlisted")
    raise ValueError("Notify webhook URL host is not allowlisted")


def require_discord_webhook_url(url: str) -> str:
    value = require_http_url(url)
    parsed = urllib.parse.urlparse(value)
    host = (parsed.hostname or "").lower()
    if parsed.scheme.lower() != "https":
        raise ValueError("Discord webhook URL must use https://")
    if host not in _DISCORD_WEBHOOK_HOSTS:
        raise ValueError("Discord webhook URL host is not allowlisted")
    parts = _require_strict_path_parts(parsed, "Discord webhook")
    if len(parts) >= 4 and parts[:2] == ["api", "webhooks"]:
        return value
    raise ValueError("Discord webhook URL path is not allowlisted")


def discovery_ssl_context(insecure_env_name: str) -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    if env_enabled(insecure_env_name):
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx
