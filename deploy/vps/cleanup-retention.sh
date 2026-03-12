#!/usr/bin/env bash
set -euo pipefail

LOG_DIR="/opt/ctoa/logs"
RUNTIME_DIR="/opt/ctoa/runtime"

mkdir -p "$LOG_DIR" "$RUNTIME_DIR"

# Remove compressed logs older than 14 days and stale plain logs older than 21 days.
find "$LOG_DIR" -type f -name "*.log.*" -mtime +14 -delete || true
find "$LOG_DIR" -type f -name "*.log" -mtime +21 -delete || true

# Keep runtime health history for 30 days.
if [[ -f "$RUNTIME_DIR/health-history.jsonl" ]]; then
    tmp_file="$(mktemp)"
    cutoff_epoch="$(date -u -d '30 days ago' +%s)"
    awk -v cutoff="$cutoff_epoch" '
    function to_epoch(ts,  cmd, out) {
        gsub(/\"/, "", ts)
        gsub(/T/, " ", ts)
        gsub(/Z/, " UTC", ts)
        cmd = "date -u -d \"" ts "\" +%s 2>/dev/null"
        cmd | getline out
        close(cmd)
        return out + 0
    }
    {
        if (match($0, /"timestamp"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
            ts = substr($0, RSTART, RLENGTH)
            sub(/^.*:[[:space:]]*"/, "", ts)
            sub(/"$/, "", ts)
            if (to_epoch(ts) >= cutoff) {
                print $0
            }
        } else {
            print $0
        }
    }
    ' "$RUNTIME_DIR/health-history.jsonl" > "$tmp_file" || true
    mv "$tmp_file" "$RUNTIME_DIR/health-history.jsonl"
fi

# Prune stale temp artifacts.
find /tmp -maxdepth 1 -type d -name "pip-*" -mtime +2 -exec rm -rf {} + || true

exit 0
