#!/usr/bin/env python3
"""
Collect OTClient / Tibia bot source code from GitHub for fine-tuning dataset.
Usage: python collect_github.py --token <GITHUB_TOKEN> --output ../data/raw/
"""
import os, json, time, argparse, urllib.request, urllib.parse
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


def gh_get(url: str, token: str) -> dict:
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "CTOAi-DataCollector/1.0",
    })
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def collect_tree(owner: str, repo: str, token: str, out_dir: Path):
    print(f"[+] {owner}/{repo}")
    try:
        repo_info = gh_get(f"https://api.github.com/repos/{owner}/{repo}", token)
        branch = repo_info.get("default_branch", "main")
        tree = gh_get(
            f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1",
            token,
        )
    except Exception as e:
        print(f"    ERROR: {e}")
        return

    files = [f for f in tree.get("tree", [])
             if f["type"] == "blob"
             and Path(f["path"]).suffix in EXTENSIONS
             and f.get("size", 0) < MAX_BYTES
             and f.get("size", 0) > 50]

    print(f"    {len(files)} qualifying files")
    repo_dir = out_dir / f"{owner}__{repo}"
    repo_dir.mkdir(parents=True, exist_ok=True)

    for i, file in enumerate(files):
        dest = repo_dir / file["path"].replace("/", "__")
        if dest.exists():
            continue
        try:
            raw_url = (
                f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file['path']}"
            )
            req = urllib.request.Request(raw_url, headers={"User-Agent": "CTOAi/1.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                content = r.read().decode("utf-8", errors="replace")
            dest.write_text(content, encoding="utf-8")
            if i % 50 == 0:
                print(f"    {i}/{len(files)} files saved")
            time.sleep(0.05)  # rate limit courtesy
        except Exception as e:
            pass  # skip broken files silently


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--token", default=os.environ.get("GITHUB_TOKEN", ""))
    ap.add_argument("--output", default=str(Path(__file__).parent.parent / "data" / "raw"))
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
