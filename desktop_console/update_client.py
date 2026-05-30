"""Release update checks and download helpers for the desktop client."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import requests

from desktop_console.version import APP_REPO


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
        self.repo = repo.strip()
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
            release_notes_url=str(payload.get("html_url") or ""),
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
        target_name = update.asset_name or f"CTOA-Desktop-{update.latest_version}.exe"
        target_path = target_root / target_name

        headers = {
            "Accept": "application/octet-stream",
            "User-Agent": "CTOA-Desktop-Updater",
        }

        try:
            with requests.get(update.download_url, headers=headers, timeout=90, stream=True) as response:
                response.raise_for_status()
                with target_path.open("wb") as output:
                    for chunk in response.iter_content(chunk_size=1024 * 256):
                        if chunk:
                            output.write(chunk)
        except requests.RequestException as exc:
            raise UpdateError(f"Unable to download update: {exc}") from exc
        except OSError as exc:
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
        if not name.lower().endswith(".exe"):
            continue
        url = str(asset.get("browser_download_url") or "").strip()
        if not url:
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


def _extract_version(raw: str) -> str:
    text = str(raw or "").strip()
    match = re.search(r"(\d+\.\d+\.\d+)", text)
    return match.group(1) if match else ""


def _version_key(version: str) -> tuple[int, ...]:
    numbers = re.findall(r"\d+", str(version or ""))
    if not numbers:
        return (0,)
    return tuple(int(item) for item in numbers)
