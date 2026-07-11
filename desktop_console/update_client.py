"""Release update checks and download helpers for the desktop client."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlsplit

import requests

from desktop_console.version import APP_REPO

MAX_UPDATE_DOWNLOAD_BYTES = 250 * 1024 * 1024


class UpdateError(RuntimeError):
    """Raised when update checks or update download fails."""


@dataclass(slots=True)
class UpdateInfo:
    current_version: str
    latest_version: str
    release_name: str
    release_notes_url: str
    published_at: str
    api_url: str
    download_url: str | None
    asset_name: str | None

    @property
    def update_available(self) -> bool:
        return _version_key(self.latest_version) > _version_key(self.current_version)


class GitHubReleaseUpdater:
    def __init__(self, repo: str = APP_REPO, timeout: int = 12) -> None:
        self.repo = _normalize_repo(repo)
        self.timeout = timeout

    def check_for_update(self, current_version: str) -> UpdateInfo:
        if not self.repo:
            raise UpdateError("Update repository is not configured")

        api_url = f"https://api.github.com/repos/{self.repo}/releases/latest"
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "CTOA-Desktop-Updater",
        }
        try:
            response = requests.get(api_url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise UpdateError(f"Unable to check updates: {exc}") from exc
        except ValueError as exc:
            raise UpdateError("Unable to parse update response") from exc

        latest_version = _extract_version(
            str(payload.get("tag_name") or payload.get("name") or "")
        )
        if not latest_version:
            raise UpdateError("Latest release does not contain a semantic version tag")

        asset_name, download_url = _select_windows_asset(payload.get("assets"))
        return UpdateInfo(
            current_version=current_version,
            latest_version=latest_version,
            release_name=str(payload.get("name") or payload.get("tag_name") or latest_version),
            release_notes_url=_safe_release_notes_url(payload.get("html_url")),
            published_at=str(payload.get("published_at") or ""),
            api_url=api_url,
            download_url=download_url,
            asset_name=asset_name,
        )

    def download_update(self, update: UpdateInfo, target_dir: Path | str) -> Path:
        if not update.download_url:
            raise UpdateError("No downloadable Windows asset found for latest release")

        target_root = Path(target_dir).expanduser().resolve()
        target_root.mkdir(parents=True, exist_ok=True)
        target_name = _safe_asset_name(update.asset_name or f"CTOA-Desktop-{update.latest_version}.exe")
        if not target_name:
            raise UpdateError("Update asset name is unsafe")
        target_path = (target_root / target_name).resolve()
        try:
            target_path.relative_to(target_root)
        except ValueError as exc:
            raise UpdateError("Update asset path escapes the update directory") from exc

        download_url = _require_github_https_url(update.download_url, "Update download")

        headers = {
            "Accept": "application/octet-stream",
            "User-Agent": "CTOA-Desktop-Updater",
        }

        try:
            temp_path = target_path.with_name(f"{target_path.name}.download")
            temp_path.unlink(missing_ok=True)
            with requests.get(download_url, headers=headers, timeout=90, stream=True) as response:
                response.raise_for_status()
                _require_github_https_url(
                    getattr(response, "url", download_url),
                    "Final update download",
                    allow_signed_asset_query=True,
                )
                content_length = _response_content_length(response)
                if content_length is not None and content_length > MAX_UPDATE_DOWNLOAD_BYTES:
                    raise UpdateError("Update download exceeds maximum allowed size")

                bytes_written = 0
                with temp_path.open("wb") as output:
                    for chunk in response.iter_content(chunk_size=1024 * 256):
                        if chunk:
                            bytes_written += len(chunk)
                            if bytes_written > MAX_UPDATE_DOWNLOAD_BYTES:
                                raise UpdateError("Update download exceeds maximum allowed size")
                            output.write(chunk)
                temp_path.replace(target_path)
        except UpdateError:
            temp_path.unlink(missing_ok=True)
            raise
        except requests.RequestException as exc:
            temp_path.unlink(missing_ok=True)
            raise UpdateError(f"Unable to download update: {exc}") from exc
        except OSError as exc:
            temp_path.unlink(missing_ok=True)
            raise UpdateError(f"Unable to save update file: {exc}") from exc

        return target_path


def _select_windows_asset(raw_assets: Any) -> tuple[str | None, str | None]:
    if not isinstance(raw_assets, list):
        return None, None

    candidates: list[tuple[str, str]] = []
    for asset in raw_assets:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name") or "").strip()
        name = _safe_asset_name(name)
        if not name:
            continue
        url = str(asset.get("browser_download_url") or "").strip()
        try:
            url = _require_github_https_url(url, "Update asset")
        except UpdateError:
            continue
        candidates.append((name, url))

    if not candidates:
        return None, None

    preferred = sorted(
        candidates,
        key=lambda item: (
            0 if "ctoa" in item[0].lower() and "desktop" in item[0].lower() else 1,
            item[0].lower(),
        ),
    )[0]
    return preferred


def _normalize_repo(raw_repo: str) -> str:
    repo = str(raw_repo or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise UpdateError("Update repository must be in owner/repo form")
    return repo


def _safe_asset_name(raw_name: Any) -> str:
    name = str(raw_name or "").strip()
    if "/" in name or "\\" in name:
        return ""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._ -]{0,127}\.exe", name, flags=re.IGNORECASE):
        return ""
    return name


def _require_github_https_url(raw_url: Any, label: str, *, allow_signed_asset_query: bool = False) -> str:
    url = str(raw_url or "").strip()
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    asset_hosts = {"objects.githubusercontent.com", "release-assets.githubusercontent.com"}
    allowed_hosts = {"github.com", "api.github.com", *asset_hosts}
    if parsed.scheme.lower() != "https" or host not in allowed_hosts:
        raise UpdateError(f"{label} URL must use a trusted GitHub HTTPS host")
    if parsed.username or parsed.password or parsed.fragment:
        raise UpdateError(f"{label} URL must not include credentials or fragments")
    if parsed.query and not (allow_signed_asset_query and host in asset_hosts):
        raise UpdateError(f"{label} URL must not include query strings")
    return url


def _response_content_length(response: requests.Response) -> int | None:
    headers = getattr(response, "headers", {})
    raw = headers.get("Content-Length", "")
    if not raw:
        return None
    try:
        parsed = int(raw)
    except ValueError as exc:
        raise UpdateError("Update download has invalid content length") from exc
    if parsed < 0:
        raise UpdateError("Update download has invalid content length")
    return parsed


def _safe_release_notes_url(raw_url: Any) -> str:
    try:
        url = _require_github_https_url(raw_url, "Release notes")
    except UpdateError:
        return ""
    return url if (urlsplit(url).hostname or "").lower() == "github.com" else ""


def _extract_version(raw: str) -> str:
    text = str(raw or "").strip()
    match = re.search(r"(\d+\.\d+\.\d+)", text)
    return match.group(1) if match else ""


def _version_key(version: str) -> tuple[int, ...]:
    numbers = re.findall(r"\d+", str(version or ""))
    if not numbers:
        return (0,)
    return tuple(int(item) for item in numbers)
