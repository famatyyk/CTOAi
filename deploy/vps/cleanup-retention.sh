#!/usr/bin/env bash
set -euo pipefail

LOG_DIR="/opt/ctoa/logs"
RUNTIME_DIR="/opt/ctoa/runtime"

mkdir -p "$LOG_DIR" "$RUNTIME_DIR"

# Remove compressed logs older than 14 days and stale plain logs older than 21 days.
find "$LOG_DIR" -type f -name "*.log.*" -mtime +14 -delete || true
find "$LOG_DIR" -type f -name "*.log" -mtime +21 -delete || true

# Keep only newest health history entries (append-only stream cap).
if [[ -f "$RUNTIME_DIR/health-history.jsonl" ]]; then
    tmp_file="$(mktemp)"
    tail -n 20000 "$RUNTIME_DIR/health-history.jsonl" > "$tmp_file" || true
    mv "$tmp_file" "$RUNTIME_DIR/health-history.jsonl"
fi

# Prune stale temp artifacts.
find /tmp -maxdepth 1 -type d -name "pip-*" -mtime +2 -exec rm -rf {} + || true

exit 0
