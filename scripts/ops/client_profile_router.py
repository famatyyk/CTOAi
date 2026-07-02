"""Resolve a bot client profile name from a client path or executable name."""
from __future__ import annotations

import argparse
from pathlib import Path


def resolve_client_profile(client_path: str) -> str:
    path = Path(client_path)
    haystack = f"{path.as_posix()} {path.name.lower()} {path.parent.name.lower()}".lower()

    if "kamil-client" in haystack or path.name.lower() == "klient.exe":
        return "kamil_client"
    if "kingsvale" in haystack:
        return "kingsvale_official"
    if "otclient" in haystack or "forgotten server" in haystack or path.name.lower() == "client.exe":
        return "otclient_generic"
    return "default"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True)
    args = parser.parse_args()
    print(resolve_client_profile(args.path))


if __name__ == "__main__":
    main()
