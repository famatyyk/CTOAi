#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p runtime logs

ITER=0
while true; do
  python3 runner/runner.py tick >> logs/runner.log 2>&1
  ITER=$((ITER + 1))

  if (( ITER % 4 == 0 )); then
    python3 runner/runner.py report --publish >> logs/runner.log 2>&1
  fi

  sleep 900
done
