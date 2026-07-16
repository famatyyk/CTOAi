#!/usr/bin/env python3
"""Passive, secret-free OTClient fork and capability detector."""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import NamedTuple


MAX_MARKER_BYTES = 512_000


class Signature(NamedTuple):
    adapter: str
    markers: tuple[str, ...]


SIGNATURES = (
    Signature("redemption-mehah", ("otclient - redemption", "github.com/mehah/otclient")),
    Signature("otcv8", ("otcv8", "otclientv8")),
    Signature("otcbr", ("otclient brasil", "otc brasil", "github.com/otclientbr")),
    Signature("otclient-edubart", ("github.com/edubart/otclient",)),
)

MARKER_FILES = (
    "init.lua",
    "README.md",
    "README.txt",
    "CMakeLists.txt",
    "src/framework/config.h",
    "src/framework/core/application.h",
)


def _safe_marker_text(root: Path) -> tuple[str, list[str]]:
    parts: list[str] = []
    inspected: list[str] = []
    total = 0
    for relative in MARKER_FILES:
        path = root / relative
        if not path.is_file() or path.is_symlink():
            continue
        size = path.stat().st_size
        if size < 0 or size > MAX_MARKER_BYTES or total + size > MAX_MARKER_BYTES:
            continue
        parts.append(path.read_text(encoding="utf-8", errors="replace").lower())
        inspected.append(relative)
        total += size
    return "\n".join(parts), inspected


def _exists(root: Path, relative: str) -> bool:
    candidate = root / relative
    return candidate.exists() and not candidate.is_symlink()


def detect(root: Path) -> dict[str, object]:
    resolved = root.resolve(strict=True)
    if not resolved.is_dir():
        raise ValueError(f"Client root is not a directory: {resolved}")
    marker_text, inspected = _safe_marker_text(resolved)
    candidates: list[dict[str, object]] = []
    for signature in SIGNATURES:
        matches = [marker for marker in signature.markers if marker in marker_text]
        score = len(matches)
        if signature.adapter == "otcv8" and _exists(resolved, "modules/game_bot"):
            matches.append("modules/game_bot")
            score += 2
        if score:
            candidates.append(
                {"adapter": signature.adapter, "score": score, "evidence": matches}
            )
    candidates.sort(key=lambda item: (-int(item["score"]), str(item["adapter"])))
    best = candidates[0] if candidates else None
    tied = bool(best and len(candidates) > 1 and candidates[1]["score"] == best["score"])
    status = "unknown" if best is None else ("ambiguous" if tied else "detected")

    capabilities = {
        "programmatic_widget_creation": _exists(resolved, "modules/corelib/ui/uiwidget.lua"),
        "controller_api": _exists(resolved, "modules/corelib/controller.lua"),
        "keybind_api": _exists(resolved, "modules/corelib/keybind.lua"),
        "ui_item": _exists(resolved, "modules/game_interface/widgets/uiitem.lua"),
        "action_bar": _exists(resolved, "modules/game_actionbar"),
        "shader_ui": _exists(resolved, "modules/game_shaders/shaders.lua"),
        "html_ui": _exists(resolved, "modules/game_shaders/shaders.html"),
        "cef_assets": _exists(resolved, "cef") or _exists(resolved, "modules/client_webbrowser"),
    }
    return {
        "schema_version": "ctoa.otclient-fork-capability-report.v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "status": status,
        "adapter": None if best is None or tied else best["adapter"],
        "confidence": 0 if best is None else min(100, 35 + int(best["score"]) * 20),
        "candidates": candidates,
        "capabilities": capabilities,
        "inspected_marker_files": inspected,
        "read_only": True,
        "credentials_read": False,
        "connection_attempted": False,
        "runtime_actions": False,
    }


def _write_atomic(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--client-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = detect(args.client_root)
    if args.output:
        _write_atomic(args.output.resolve(), payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] == "detected" else 2


if __name__ == "__main__":
    raise SystemExit(main())
