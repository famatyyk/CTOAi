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
