# CTOAi Full Workspace Audit

- Generated at UTC: `2026-07-21T08:06:22+00:00`
- Root: `C:\Users\zycie\CTOAi`
- Coverage: `All files under workspace root, including .git internals.`
- Files inventoried: `48305`
- Non-regular entries skipped: `4216`
- Git tracked files: `1329`
- Dirty status entries: `28`
- Runtime JSON inventory: `runtime/audits/ctoai-full-workspace-audit.json`

## Coverage Note

The JSON inventory lists every file found under the workspace root, including `.git` internals. Sensitive-name files are listed by path, size, timestamp, and category only; secret contents are not copied. Symlinks and other non-regular entries are counted separately and are not opened or hashed.

## Counts By Category

| Category | Files | Size |
| --- | ---: | ---: |
| `git_internal` | 417 | 1022.42 MB |
| `local_secret_or_sensitive` | 8 | 0.08 MB |
| `runtime_or_local_state` | 7732 | 1748.00 MB |
| `tracked_source` | 1323 | 11.39 MB |
| `untracked_local` | 55 | 0.39 MB |
| `untracked_source_candidate` | 7432 | 754.42 MB |
| `vendor_or_cache` | 31338 | 594.75 MB |

## Largest Top-Level Areas

| Path | Files | Size |
| --- | ---: | ---: |
| `web` | 33422 | 1217.21 MB |
| `runtime` | 7414 | 1735.52 MB |
| `.venv` | 4543 | 116.28 MB |
| `tests` | 612 | 10.87 MB |
| `scripts` | 489 | 6.53 MB |
| `.git` | 417 | 1022.42 MB |
| `docs` | 312 | 4.22 MB |
| `runner` | 154 | 1.55 MB |
| `bot` | 144 | 0.73 MB |
| `_local_archive` | 111 | 1.52 MB |
| `.tmp` | 105 | 1.59 MB |
| `workflows` | 89 | 0.18 MB |
| `metrics` | 82 | 0.06 MB |
| `AI` | 45 | 0.86 MB |
| `deploy` | 43 | 0.04 MB |
| `.github` | 41 | 0.14 MB |
| `.ruff_cache` | 39 | 0.05 MB |
| `releases` | 36 | 0.02 MB |
| `agents` | 32 | 0.08 MB |
| `mobile_console` | 20 | 0.64 MB |
| `desktop_console` | 16 | 0.42 MB |
| `.ctoa-local` | 12 | 0.05 MB |
| `.codex-tmp` | 10 | 0.14 MB |
| `api` | 9 | 0.26 MB |
| `training` | 8 | 0.07 MB |

## Audit Integrity Gate

- Status: `evidence_ready`
- Note: This gate proves the inventory mechanics for the current run. It does not by itself prove the whole repository objective complete; targeted and broad validation commands still need current run evidence.

| Check | Status | Evidence |
| --- | --- | --- |
| `regular_file_inventory` | `passed` | 48305 regular files inventoried. |
| `non_regular_accounting` | `passed` | 4216 non-regular entries skipped ({'directory': 4216}). |
| `bounded_hashing` | `passed` | 16389 files hashed with max size 2000000 bytes. |
| `sensitive_content_omitted` | `passed` | 8 sensitive-name files inventoried; 0 hashed. |
| `git_status_captured` | `passed` | 28 git status entries captured. |

## Validation Evidence Gate

- Status: `evidence_ready`
- Missing command evidence: `<none>`
- Failed command evidence: `<none>`
- Evidence generated at UTC: `2026-07-18T12:34:49Z`

| Command ID | Status | Duration | Summary |
| --- | --- | ---: | --- |
| `python_non_e2e` | `passed` | `233.56s` | passed=2028; skipped=50 |
| `web_lint` | `passed` | `14.69s` | eslint completed |
| `web_tests` | `passed` | `8.47s` | files=38; tests=204 |
| `diff_check` | `warn` | `0.22s` | no whitespace errors; working-copy warnings reported |
| `brain_refresh` | `passed` | `3.11s` | doc_sync=passed; secret_guardrail=passed; p6=ready_for_plugin_design |
| `brain_doctor` | `warn` | `12.89s` | overall=warn; fail=0; warn=0 |
| `brain_pack_all` | `passed` | `0.30s` | profile=all; included=49; truncated=6 |
| `p6_plugin_self_check` | `passed` | `0.33s` | status=ready; hard_blockers=0 |
| `p6_plugin_mcp` | `passed` | `0.25s` | initialize=ready; tools=12; brief=ready |
| `p7_operator_brief` | `passed` | `0.27s` | status=ready; decision=needs_attention; hard_blockers=0 |
| `p7_generated_brief` | `passed` | `0.00s` | status=ready; decision=ready_for_p7_operator_workflow; hard_blockers=0 |

## Findings

### HIGH: workspace-state

- Finding: Worktree is dirty with 28 status entries.
- Evidence: git status --short; see runtime audit JSON dirty_entries.
- Action: Package current Helper/Control Center changes into one reviewable change set before opening another lane.

### HIGH: local-sensitive-state

- Finding: 8 sensitive-name files are present in the workspace inventory.
- Evidence: .env-style files are inventoried but content was not copied into docs.
- Action: Keep these ignored/local; never copy values into AI packs, docs, issues, or release evidence.

### MEDIUM: dependency-cache

- Finding: Vendor/cache files dominate the workspace (31338 files).
- Evidence: Full inventory includes node_modules/.venv/cache paths so they are not hidden.
- Action: Keep audits category-aware; do not treat dependency cache churn as product source changes.

### MEDIUM: runtime-state

- Finding: Runtime/local state is large and active (7732 files).
- Evidence: runtime/log/data/local dirs are visible in the file inventory.
- Action: Continue writing release and Helper evidence to runtime, but keep canonical docs in docs/AI/release paths.

### MEDIUM: web-surface

- Finding: Control Center/web is the largest source tree (33422 files including local deps).
- Evidence: web/package.json exposes dev, build, lint, and vitest gates.
- Action: Keep Control Center panels read-only by default and extend tests whenever evidence payloads change.

### MEDIUM: helper-release

- Finding: OTClient Helper has a real release-gate pipeline, but live approval must remain explicit.
- Evidence: solteria_helper_test_env.ps1, release_gate/goal_audit scripts, Control Center Helper status.
- Action: Do not add shortcuts around PromoteLiveCtoa -ApproveLiveDeploy.

## Required Completion Evidence

The audit inventory and validation evidence gates must both be current before claiming the full repo-wide objective complete. Keep fresh command evidence for:

- `python -m pytest tests\ --ignore=tests\e2e -q`
- `cd web; npm run lint`
- `cd web; npm test` or the scoped Control Center evidence/action suites changed by the wave
- `git diff --check`
- `.\ctoa.ps1 brain refresh`
- `.\ctoa.ps1 brain doctor`
- `.\ctoa.ps1 brain pack all` or the scoped pack for the active lane

## File Inventory

The complete per-file inventory is intentionally stored in JSON instead of this Markdown file:

- `runtime/audits/ctoai-full-workspace-audit.json`
