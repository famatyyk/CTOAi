from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any, Callable


class IdeasService:
    """Stage-1 service wrapper for idea parking operations."""

    def __init__(
        self,
        read_items: Callable[[], list[dict[str, Any]]],
        write_items: Callable[[list[dict[str, Any]]], list[dict[str, Any]]],
        normalize_item: Callable[[dict[str, Any], str], dict[str, Any] | None],
    ) -> None:
        self._read_items = read_items
        self._write_items = write_items
        self._normalize_item = normalize_item

    def list_items(self) -> list[dict[str, Any]]:
        return self._read_items()

    def add(self, text: str, author: str) -> tuple[dict[str, Any] | None, int]:
        ideas = self._read_items()
        idea = self._normalize_item(
            {
                "id": secrets.token_hex(8),
                "text": text,
                "createdAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "author": author,
            },
            author,
        )
        if not idea:
            return None, len(ideas)
        ideas.insert(0, idea)
        saved = self._write_items(ideas)
        return idea, len(saved)

    def delete(self, idea_id: str) -> tuple[int, int]:
        ideas = self._read_items()
        remaining = [item for item in ideas if str(item.get("id", "")) != idea_id]
        deleted = len(ideas) - len(remaining)
        if deleted <= 0:
            return 0, len(ideas)
        saved = self._write_items(remaining)
        return deleted, len(saved)

    def clear(self) -> int:
        self._write_items([])
        return 0
