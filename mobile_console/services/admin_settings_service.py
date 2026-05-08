from __future__ import annotations

from typing import Any, Callable


class AdminSettingsService:
    """Thin service facade for admin settings persistence."""

    def __init__(
        self,
        read_settings: Callable[[], dict[str, Any]],
        write_settings: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        self._read_settings = read_settings
        self._write_settings = write_settings

    def get(self) -> dict[str, Any]:
        return self._read_settings()

    def save(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._write_settings(payload)
