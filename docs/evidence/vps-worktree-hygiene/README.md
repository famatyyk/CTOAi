# VPS Worktree Hygiene Evidence

This directory stores non-destructive inventory evidence collected from the VPS repository at /opt/ctoa.

## Phase 1 Snapshot: 20260515T130807Z

- branch: main
- head: c69e25336c3c1e9cb1559718ff91806c3b6a775d
- changed_entries: 24
- keep-and-commit: 9
- keep-but-stash: 15
- archive-and-remove: 0

## Artifacts

- phase1-20260515T130807Z/summary.md
- phase1-20260515T130807Z/classification.md
- phase1-20260515T130807Z/classification.csv
- phase1-20260515T130807Z/status-short.txt
- phase1-20260515T130807Z/status-porcelain.txt
- phase1-20260515T130807Z/status-full.txt
- phase1-20260515T130807Z/diff-stat.txt
- phase1-20260515T130807Z/diff.patch
- phase1-20260515T130807Z/untracked.txt
- phase1-20260515T130807Z.tar.gz

The snapshot was generated on VPS and copied to this repository for traceability and Sprint governance evidence.
## CTOA-237 Verification Snapshot: 20260515T135557Z

- branch: main
- head: c69e253
- gate_expected_block: YES
- purpose: verify operational pre-update dirty-worktree gate blocks update flow on VPS

### Artifacts

- ctoa-237-20260515T135557Z/preupdate-gate-20260515T135557Z.txt
- ctoa-237-20260515T135557Z/preupdate-status-20260515T135557Z.txt

## Phase 2 Snapshot: 20260515T140911Z

- branch: main
- head: c69e253
- changed_entries_before: 24
- untracked_entries_before: 18
- stash_message: hygiene:phase2:20260515T140911Z
- stash_exit_code: 0
- post_status_clean: YES
- stash_top: stash@{0}: On main: hygiene:phase2:20260515T140911Z

### Artifacts

- phase2-20260515T140911Z/summary.md
- phase2-20260515T140911Z/status-short.txt
- phase2-20260515T140911Z/status-porcelain.txt
- phase2-20260515T140911Z/changed-paths.txt
- phase2-20260515T140911Z/untracked.txt
- phase2-20260515T140911Z/tracked-diff.patch
- phase2-20260515T140911Z/post-status-porcelain.txt
- pre-clean-20260515T140911Z.tar.gz
- manual-edits-20260515T140911Z.tar.gz

## Phase 3 Snapshot: 20260515T141636Z

- branch: main
- head_before: c69e253
- head_after: 0981aa9
- fetch_exit_code: 0
- pull_exit_code: 0
- status_before_clean: YES
- status_after_clean: YES
- reconcile_result: RECONCILE_OK

### Artifacts

- phase3-20260515T141636Z/summary.md
- phase3-20260515T141636Z/fetch-output.txt
- phase3-20260515T141636Z/pull-output.txt
- phase3-20260515T141636Z/status-before.txt
- phase3-20260515T141636Z/status-after.txt

## Phase 4 Readiness Snapshot: 20260515T141731Z

- stash_entries_detected: 1
- stash_top: stash@{0}: On main: hygiene:phase2:20260515T140911Z
- tracked_paths_in_top_stash: 6
- grouped_ready_for_controlled_reapply: YES

### Artifacts

- phase4-readiness-20260515T141731Z/summary.md
- phase4-readiness-20260515T141731Z/grouped-paths.json
- phase4-readiness-20260515T141731Z/stash-list.txt
- phase4-readiness-20260515T141731Z/stash-top-name-status.txt
- phase4-readiness-20260515T141731Z/stash-top-stat.txt
