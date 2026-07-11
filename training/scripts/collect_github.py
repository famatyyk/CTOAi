#!/usr/bin/env python3
"""
Collect OTClient / Tibia bot source code from GitHub for fine-tuning dataset.
Usage: python collect_github.py --token <GITHUB_TOKEN> --output ../data/raw/
"""

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# Repos with high-quality OTClient / Tibia Lua/C++ code
TARGET_REPOS = [
    ("edubart", "otclient"),
    ("opentibia", "otclientv8"),
    ("mehah", "otclient"),
    ("otland", "forgottenserver"),
    ("otland", "canary"),
    ("nicklvsa", "otclient-redemption"),
]

# File extensions to collect
EXTENSIONS = {".lua", ".cpp", ".h", ".py", ".md"}

# Max file size (skip huge generated files)
MAX_BYTES = 80_000
SAFE_REPO_COMPONENT = re.compile(r"^[A-Za-z0-9_.-]+$")


def _validate_repo_component(value: str, label: str) -> str:
    cleaned = value.strip()
    if not cleaned or not SAFE_REPO_COMPONENT.fullmatch(cleaned):
        raise ValueError(
            f"Unsafe GitHub {label}: {label} must use letters, numbers, dots, underscores, or dashes"
        )
    return cleaned


def _validate_branch(value: str) -> str:
    cleaned = value.strip()
    if not cleaned or any(ord(char) < 32 for char in cleaned):
        raise ValueError("Unsafe GitHub branch name")
    return cleaned


def _safe_url_path_parts(path: str) -> list[str]:
    if "\\" in path:
        raise ValueError("GitHub URL path must not contain backslashes")
    decoded_path = urllib.parse.unquote(path)
    if "\\" in decoded_path or any(ord(char) < 32 for char in decoded_path):
        raise ValueError("GitHub URL path must not contain unsafe characters")
    path_parts = [part for part in decoded_path.split("/") if part]
    if any(part in {".", ".."} for part in path_parts):
        raise ValueError("GitHub URL path must not contain traversal")
    return path_parts


def _validate_github_api_url(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or parts.netloc.lower() != "api.github.com":
        raise ValueError("GitHub API URL must use https://api.github.com")
    if parts.username or parts.password or parts.fragment:
        raise ValueError("GitHub API URL must not contain credentials or fragments")
    path_parts = _safe_url_path_parts(parts.path)
    if len(path_parts) < 3 or path_parts[0] != "repos":
        raise ValueError("GitHub API URL must stay under /repos/")
    query_items = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    if query_items and not (
        len(query_items) == 1
        and query_items[0][0] == "recursive"
        and query_items[0][1] == "1"
        and path_parts[3:5] == ["git", "trees"]
    ):
        raise ValueError("GitHub API URL query string is not allowed")
    return urllib.parse.urlunsplit(parts)


def _validate_github_raw_url(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or parts.netloc.lower() != "raw.githubusercontent.com":
        raise ValueError("GitHub raw URL must use https://raw.githubusercontent.com")
    if parts.username or parts.password or parts.query or parts.fragment:
        raise ValueError(
            "GitHub raw URL must not contain credentials, query strings, or fragments"
        )
    path_parts = _safe_url_path_parts(parts.path)
    if len(path_parts) < 4:
        raise ValueError("GitHub raw URL path is not a repository file path")
    return urllib.parse.urlunsplit(parts)


def _safe_dataset_filename(repo_path: str) -> str:
    normalized = urllib.parse.unquote(repo_path.replace("\\", "/"))
    parts = normalized.split("/")
    if not parts or any(
        part in {"", ".", ".."} or any(ord(char) < 32 for char in part)
        for part in parts
    ):
        raise ValueError("Unsafe repository file path")
    return "__".join(parts)


def _build_raw_url(owner: str, repo: str, branch: str, repo_path: str) -> str:
    safe_owner = _validate_repo_component(owner, "owner")
    safe_repo = _validate_repo_component(repo, "repo")
    safe_branch = urllib.parse.quote(_validate_branch(branch), safe="")
    normalized_path = repo_path.replace("\\", "/")
    _safe_dataset_filename(normalized_path)
    safe_path = urllib.parse.quote(normalized_path, safe="/")
    return _validate_github_raw_url(
        f"https://raw.githubusercontent.com/{safe_owner}/{safe_repo}/{safe_branch}/{safe_path}"
    )


def gh_get(url: str, token: str) -> dict:
    safe_url = _validate_github_api_url(url)
    req = urllib.request.Request(
        safe_url,
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "CTOAi-DataCollector/1.0",
        },
    )
    # _validate_github_api_url restricts API fetches to trusted GitHub HTTPS URLs.
    with urllib.request.urlopen(req, timeout=15) as r:  # nosec B310
        return json.loads(r.read())


def collect_tree(owner: str, repo: str, token: str, out_dir: Path):
    safe_owner = _validate_repo_component(owner, "owner")
    safe_repo = _validate_repo_component(repo, "repo")
    print(f"[+] {safe_owner}/{safe_repo}")
    try:
        repo_info = gh_get(
            f"https://api.github.com/repos/{safe_owner}/{safe_repo}", token
        )
        branch = _validate_branch(str(repo_info.get("default_branch", "main")))
        branch_ref = urllib.parse.quote(branch, safe="")
        tree = gh_get(
            f"https://api.github.com/repos/{safe_owner}/{safe_repo}/git/trees/{branch_ref}?recursive=1",
            token,
        )
    except (
        KeyError,
        OSError,
        urllib.error.URLError,
        ValueError,
        json.JSONDecodeError,
    ) as e:
        print(f"    ERROR: {e}")
        return

    files = []
    for item in tree.get("tree", []):
        if not isinstance(item, dict) or item.get("type") != "blob":
            continue
        repo_path = str(item.get("path", ""))
        size = int(item.get("size", 0) or 0)
        if Path(repo_path).suffix in EXTENSIONS and 50 < size < MAX_BYTES:
            files.append({"path": repo_path, "size": size})

    print(f"    {len(files)} qualifying files")
    repo_dir = out_dir / f"{safe_owner}__{safe_repo}"
    repo_dir.mkdir(parents=True, exist_ok=True)

    for i, file in enumerate(files):
        repo_path = str(file["path"])
        dest = repo_dir / _safe_dataset_filename(repo_path)
        if dest.exists():
            continue
        try:
            raw_url = _build_raw_url(safe_owner, safe_repo, branch, repo_path)
            req = urllib.request.Request(raw_url, headers={"User-Agent": "CTOAi/1.0"})
            # _build_raw_url restricts file fetches to trusted GitHub raw HTTPS URLs.
            with urllib.request.urlopen(req, timeout=10) as r:  # nosec B310
                content = r.read().decode("utf-8", errors="replace")
            dest.write_text(content, encoding="utf-8")
            if i % 50 == 0:
                print(f"    {i}/{len(files)} files saved")
            time.sleep(0.05)  # rate limit courtesy
        except (
            OSError,
            urllib.error.URLError,
            UnicodeError,
            ValueError,
            KeyError,
        ) as e:
            print(f"    skip {repo_path}: {e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--token", default=os.environ.get("GITHUB_TOKEN", ""))
    ap.add_argument(
        "--output", default=str(Path(__file__).parent.parent / "data" / "raw")
    )
    args = ap.parse_args()

    if not args.token:
        print("ERROR: provide --token or set GITHUB_TOKEN env var")
        return

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    for owner, repo in TARGET_REPOS:
        collect_tree(owner, repo, args.token, out)
        time.sleep(1)

    print(f"\nDone. Raw data in: {out}")


if __name__ == "__main__":
    main()
