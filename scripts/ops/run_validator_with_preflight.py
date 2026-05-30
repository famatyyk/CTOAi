"""Run sprint validators with a preflight file-existence check."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preflight wrapper for sprint validators"
    )
    parser.add_argument(
        "validator",
        help="Path to validator script (for example scripts/ops/sprint042_validate.py)",
    )
    parser.add_argument(
        "validator_args",
        nargs=argparse.REMAINDER,
        help="Arguments forwarded to validator",
    )
    args = parser.parse_args()

    validator_path = Path(args.validator)

    if not validator_path.exists():
        print("[validator_preflight] BLOCKED")
        print(f"[validator_preflight] Missing validator script: {validator_path}")
        print("[validator_preflight] Legacy sprint tasks may point to validators not present in this repo snapshot.")
        print("[validator_preflight] Use active sprint validators (027+) or restore the missing validator script.")
        return 2

    cmd = [sys.executable, str(validator_path), *args.validator_args]
    result = subprocess.run(cmd)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
