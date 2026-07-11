from __future__ import annotations

import argparse
import json
import re
import string
import zipfile
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path


FUNCTION_RE = re.compile(r"^function\s+([A-Za-z_][\w\.]*)(?::([A-Za-z_]\w*))?\(([^)]*)\)\s+end\s*$")
CLASS_RE = re.compile(r"^---@class\s+([A-Za-z_]\w*)")
ALIAS_RE = re.compile(r"^---@alias\s+([A-Za-z_]\w*)")
PARAM_RE = re.compile(r"^---@param\s+(\w+)\??\s+(.+)$")
RETURN_RE = re.compile(r"^---@return\s+(.+)$")


@dataclass
class ApiFunction:
    owner: str
    name: str
    full_name: str
    params: list[dict[str, str]]
    returns: list[str]
    line: int
    raw_params: str


def parse_meta(meta_path: Path) -> dict[str, object]:
    lines = meta_path.read_text(encoding="utf-8", errors="replace").splitlines()
    classes: dict[str, dict[str, object]] = {}
    aliases: list[dict[str, object]] = []
    functions: list[ApiFunction] = []
    pending_params: list[dict[str, str]] = []
    pending_returns: list[str] = []

    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()

        class_match = CLASS_RE.match(stripped)
        if class_match:
            class_name = class_match.group(1)
            classes.setdefault(class_name, {"name": class_name, "line": lineno, "methods": []})

        alias_match = ALIAS_RE.match(stripped)
        if alias_match:
            aliases.append({"name": alias_match.group(1), "line": lineno, "text": stripped})

        param_match = PARAM_RE.match(stripped)
        if param_match:
            pending_params.append({"name": param_match.group(1), "type": param_match.group(2).strip()})
            continue

        return_match = RETURN_RE.match(stripped)
        if return_match:
            pending_returns.append(return_match.group(1).strip())
            continue

        function_match = FUNCTION_RE.match(stripped)
        if not function_match:
            if stripped and not stripped.startswith("---"):
                pending_params = []
                pending_returns = []
            continue

        prefix = function_match.group(1)
        method = function_match.group(2)
        raw_params = function_match.group(3).strip()
        if method:
            owner = prefix
            name = method
            full_name = f"{prefix}:{method}"
        elif "." in prefix:
            owner, name = prefix.rsplit(".", 1)
            full_name = prefix
        else:
            owner = "_G"
            name = prefix
            full_name = prefix

        api = ApiFunction(
            owner=owner,
            name=name,
            full_name=full_name,
            params=pending_params,
            returns=pending_returns,
            line=lineno,
            raw_params=raw_params,
        )
        functions.append(api)
        classes.setdefault(owner, {"name": owner, "line": None, "methods": []})
        classes[owner]["methods"].append(asdict(api))
        pending_params = []
        pending_returns = []

    namespaces: dict[str, list[dict[str, object]]] = defaultdict(list)
    for api in functions:
        namespaces[api.owner].append(asdict(api))

    return {
        "meta_path": str(meta_path),
        "class_count": len(classes),
        "function_count": len(functions),
        "alias_count": len(aliases),
        "classes": classes,
        "aliases": aliases,
        "functions": [asdict(api) for api in functions],
        "namespaces": dict(sorted(namespaces.items())),
    }


def printable_strings(path: Path, min_len: int = 5) -> list[str]:
    allowed = set(bytes(string.printable, "ascii"))
    result: list[str] = []
    current = bytearray()
    with path.open("rb") as file:
        while True:
            chunk = file.read(1024 * 1024)
            if not chunk:
                break
            for byte in chunk:
                if byte in allowed and byte not in (0x0B, 0x0C):
                    current.append(byte)
                else:
                    if len(current) >= min_len:
                        result.append(current.decode("ascii", errors="ignore"))
                    current = bytearray()
        if len(current) >= min_len:
            result.append(current.decode("ascii", errors="ignore"))
    return result


def scan_binary(path: Path, keywords: list[str]) -> dict[str, list[str]]:
    if not path.exists():
        return {}
    strings = printable_strings(path)
    found: dict[str, list[str]] = {}
    for keyword in keywords:
        matches = [value for value in strings if keyword.lower() in value.lower()]
        found[keyword] = sorted(set(matches))[:50]
    return found


def list_archive(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"path": str(path), "exists": False}
    with zipfile.ZipFile(path) as archive:
        entries = [
            {
                "name": item.filename,
                "size": item.file_size,
                "compressed_size": item.compress_size,
            }
            for item in archive.infolist()
        ]
    text_like = [
        entry
        for entry in entries
        if Path(entry["name"]).suffix.lower() in {".lua", ".otmod", ".otui", ".otml", ".json", ".txt"}
    ]
    return {
        "path": str(path),
        "exists": True,
        "entry_count": len(entries),
        "text_like_count": len(text_like),
        "text_like_entries": text_like,
    }


def render_markdown(report: dict[str, object]) -> str:
    meta = report["meta"]
    namespaces: dict[str, list[dict[str, object]]] = meta["namespaces"]  # type: ignore[assignment]
    lines = [
        "# Solteria API Audit",
        "",
        f"Client path: `{report['client_path']}`",
        "",
        "## Summary",
        "",
        f"- Classes/namespaces: {meta['class_count']}",
        f"- Functions/methods: {meta['function_count']}",
        f"- Aliases: {meta['alias_count']}",
        "",
        "## High-value Namespaces",
        "",
    ]

    high_value = [
        "g_game",
        "g_map",
        "LocalPlayer",
        "Creature",
        "Tile",
        "Thing",
        "Item",
        "Container",
        "ProtocolGame",
        "g_resources",
        "g_keyboard",
        "g_mouse",
        "g_ui",
        "UIWidget",
        "UIMap",
        "UIMinimap",
        "g_settings",
        "g_platform",
    ]
    for namespace in high_value:
        methods = namespaces.get(namespace, [])
        if not methods:
            continue
        lines.append(f"### {namespace}")
        for method in methods:
            params = method.get("raw_params") or ""
            returns = method.get("returns") or []
            return_text = f" -> {', '.join(returns)}" if returns else ""
            lines.append(f"- `{method['full_name']}({params})`{return_text} [line {method['line']}]")
        lines.append("")

    lines.extend(["## Archive Inventory", ""])
    for archive in report["archives"]:  # type: ignore[index]
        lines.append(
            f"- `{archive['path']}`: entries={archive.get('entry_count', 0)}, "
            f"text_like={archive.get('text_like_count', 0)}"
        )

    lines.extend(["", "## Binary Keyword Hits", ""])
    binary_hits: dict[str, list[str]] = report["binary_keyword_hits"]  # type: ignore[assignment]
    for keyword, values in binary_hits.items():
        if not values:
            continue
        lines.append(f"### {keyword}")
        for value in values[:15]:
            lines.append(f"- `{value}`")
        lines.append("")

    lines.extend(["## Full Catalog", ""])
    for namespace, methods in namespaces.items():
        lines.append(f"### {namespace}")
        for method in methods:
            params = method.get("raw_params") or ""
            returns = method.get("returns") or []
            return_text = f" -> {', '.join(returns)}" if returns else ""
            lines.append(f"- `{method['full_name']}({params})`{return_text} [line {method['line']}]")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Solteria OTClient Lua/API surface.")
    parser.add_argument(
        "--client-dir",
        type=Path,
        default=Path.home() / "AppData" / "Local" / "Solteria" / "client",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("runtime") / "solteria_api_audit",
    )
    args = parser.parse_args()

    client_dir = args.client_dir
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    meta_path = client_dir / "meta.lua"
    report = {
        "client_path": str(client_dir),
        "meta": parse_meta(meta_path),
        "archives": [
            list_archive(client_dir / "protected.otpkg"),
            list_archive(client_dir / "data-things-1525.otpkg"),
        ],
        "binary_keyword_hits": scan_binary(
            client_dir / "solteria-client.exe",
            [
                "walk",
                "autoWalk",
                "findPath",
                "LocalPlayer",
                "g_game",
                "g_map",
                "ProtocolGame",
                "actionbar",
                "hotkey",
                "health",
                "mana",
                "container",
                "creature",
                "tile",
            ],
        ),
    }

    (out_dir / "solteria_api_catalog.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (out_dir / "solteria_api_catalog.md").write_text(render_markdown(report), encoding="utf-8")
    print(f"Wrote {out_dir / 'solteria_api_catalog.json'}")
    print(f"Wrote {out_dir / 'solteria_api_catalog.md'}")
    print(f"Functions: {report['meta']['function_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
