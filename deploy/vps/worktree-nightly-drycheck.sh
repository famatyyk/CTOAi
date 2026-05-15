#!/usr/bin/env bash
set -euo pipefail

repo="/opt/ctoa"
evidence_root="$repo/runtime/evidence/worktree-hygiene"
phase5_root="$evidence_root/phase5-drycheck"
ts="$(date -u +%Y%m%dT%H%M%SZ)"
run_dir="$phase5_root/$ts"
status_file="$run_dir/status-porcelain.txt"
summary_file="$run_dir/summary.md"
report_file="$run_dir/report.txt"
latest_file="$phase5_root/latest.txt"

mkdir -p "$run_dir" /opt/ctoa/logs

if [[ ! -d "$repo/.git" ]]; then
  echo "[phase5-drycheck] missing git repository at $repo" | tee "$report_file"
  exit 64
fi

branch="$(git -C "$repo" branch --show-current 2>/dev/null || echo unknown)"
head="$(git -C "$repo" rev-parse --short HEAD 2>/dev/null || echo unknown)"

git -C "$repo" status --porcelain=v1 > "$status_file"
echo "$run_dir" > "$latest_file"

if [[ -s "$status_file" ]]; then
  cat > "$summary_file" <<EOF
# Phase 5 Nightly Worktree Dry-Check Summary

timestamp_utc: $ts
branch: $branch
head: $head
status: DIRTY
mirror_policy: REQUIRED_WITHIN_ONE_SPRINT
result: FAIL
EOF

  cat > "$report_file" <<EOF
[phase5-drycheck] FAIL: dirty worktree detected
repo: $repo
branch: $branch
head: $head
status_file: $status_file
summary_file: $summary_file

Required action:
1) Preserve or classify emergency edits.
2) Mirror emergency VPS edits to main within one sprint cycle.
3) Re-run the dry-check after cleanup.
EOF

  cat "$report_file"
  exit 2
fi

cat > "$summary_file" <<EOF
# Phase 5 Nightly Worktree Dry-Check Summary

timestamp_utc: $ts
branch: $branch
head: $head
status: CLEAN
mirror_policy: SATISFIED
result: PASS
EOF

cat > "$report_file" <<EOF
[phase5-drycheck] PASS: worktree clean
repo: $repo
branch: $branch
head: $head
status_file: $status_file
summary_file: $summary_file
EOF

cat "$report_file"
exit 0