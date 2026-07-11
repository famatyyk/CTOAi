# CTOAi Dirty Worktree Execution Plan - 2026-07-11

Purpose: turn the current dirty worktree into reviewable, validated bundles
without reverting, deleting, staging, or mixing unrelated user changes.

## Verified Baseline

- Branch: `codex/control-center-guarded-actions`.
- Git status entries: `421` total, including `236` tracked changes and `185`
  untracked entries.
- Tracked diff: `236 files changed, 17035 insertions(+), 2909 deletions(-)`.
- Full workspace inventory: `69245` regular files.
- Inventory composition: `31338` vendor/cache files, `29111` Git internals,
  `1266` runtime/local-state files, and `1118` tracked source files.
- Engine Brain manifest generated at `2026-07-10T23:08:56+00:00` for `1233`
  indexed files.
- Engine Brain gates: `doc_sync_status=passed` and
  `secret_guardrail_status=passed`.
- Environment doctor: `warn` with `5` checks OK, `2` warnings, and `0`
  failures. The warnings cover repository/PR hygiene and VS Code extension
  state; they are not hard runtime blockers.
- Engine Brain pack: profile `all`, `33` included sections, `4` sections
  truncated by the configured per-file context limit.

## Safety Boundary

- Preserve every existing tracked and untracked user change.
- Do not stage or commit mixed bundles.
- Do not delete legacy UI before Control Center parity is proven.
- Do not promote the Solteria Helper to a live client without explicit user
  approval and fresh release-gate evidence.
- Keep plugin writes dry-run-first, explicitly confirmed, audited, and visible
  through read-only Control Center evidence.
- Never add runtime dumps, logs, databases, auth stores, or secret-bearing
  local files to a review bundle.

## Ordered Execution

### P0. Establish current evidence baseline

Status: implemented on 2026-07-11.

Actions:

1. Run the full workspace audit.
2. Refresh Engine Brain generated artifacts.
3. Run the environment doctor.
4. Build the `all` context pack.
5. Verify doc-sync and secret guardrails.

Gate:

- Engine Brain audit/index/doctor/pack tests pass.
- `git diff --check` reports no whitespace errors.

### P1. Review `control-center-evidence-security`

Status: implemented and validated on 2026-07-11.

Scope:

- `web/`, `api/main.py`, `mobile_console/`, and the Control Center/evidence
  documentation and tests that prove the same contracts.

Actions:

1. Classify changed files into auth, guarded actions, evidence access,
   redaction/display paths, operational state, and UI-only changes.
2. Review risky API boundaries before formatting or refactoring.
3. Run targeted web tests, lint, and relevant Python security/contract tests.
4. Record failures as bundle-local follow-ups; do not absorb unrelated fixes.

Exit gate:

- No unresolved high-severity auth, origin, path, redaction, or command-action
  finding in the bundle.
- Targeted tests and lint pass.

Evidence:

- Closed unauthenticated reads of the Control Center snapshot, client
  inventory/capabilities, telemetry events, source inventory, update feed, and
  diff ledger by reusing the operator evidence-access gate.
- Added route-level regressions proving local operational state is not read
  before authorization succeeds.
- Web validation passed: `138` tests, ESLint, TypeScript, and the production
  Next.js build.
- Python API/mobile security validation passed: `100` tests with `3` skipped.
- The production build retains a non-failing Turbopack NFT warning for
  intentionally dynamic runtime evidence paths. The warning does not bypass
  authorization or fail compilation; keep it visible for packaging follow-up.

### P2. Review `engine-brain-p6-p7`

Status: implemented and validated on 2026-07-11.

Scope:

- `AI/`, Engine Brain scripts, P6/P7 smoke tools, and their targeted tests.

Exit gate:

- Refresh, doctor, pack, self-check, operator brief, cockpit, and MCP smoke are
  consistent with the generated manifest.

Evidence:

- Targeted Engine Brain and P6/P7 tests passed: `32` passed, `3` skipped;
  Ruff passed.
- Plugin status and install self-check report `ready` with no hard blockers.
- Fresh P6 handoff smoke passed `17/17`; P7 cockpit smoke passed `14/14`.
- MCP smoke exposes the expected `4` read-only and `5` bounded safe-write
  tools, with no deploy or live-client action.
- Engine Brain was refreshed after the smoke runs and the final pack profile is
  `all` with `33` included sections.
- Fresh-thread UI discovery remains a documented handoff check, not a failed
  repository or plugin contract.

### P3. Review `helper-solteria`

Status: implemented and sandbox-validated on 2026-07-11.

Scope:

- `scripts/lua/otclient/`, Helper operator scripts, profile/release tooling,
  and Helper tests.

Exit gate:

- Static contracts, profile audit, release gate, sandbox ready check, module
  attach smoke, and full attach smoke are fresh for the same manifest.

Evidence:

- Helper/Solteria suite passed `164/164`; module contract passed `30/30` and
  profile audit passed.
- Updated stale test expectations after the helper shell dropped below its
  4500-line budget; remaining extraction pressure is function-count based.
- `SmokePreflight` and `ReadyCheck` passed after the test character entered the
  sandbox client.
- `SmokeAttachModules` passed `4/4`; `SmokeAttachAll` passed with `16/16`
  coverage while runtime remained disarmed.
- The refreshed release gate has exactly one expected blocker: the live
  promotion report predates the current manifest. Live promotion was
  intentionally not attempted or approved as part of this cleanup plan.

### P4. Review `runner-bot-security`

Status: implemented and validated on 2026-07-11.

Scope:

- `runner/`, `bot/`, shared process/file/HTTP safety helpers, and related tests.

Exit gate:

- Targeted runner/bot/security tests pass, followed by the non-e2e Python
  suite or a documented list of pre-existing failures.

Evidence:

- Targeted P4 suite passed: `443` tests with `11` skipped.
- Ruff passes for all `37` changed Python files in `runner/` and `bot/`.
- Removed three unused imports in changed agent files; focused regressions
  passed `23/23`.
- A full-directory Ruff scan still reports pre-existing findings in untouched
  bot/hybrid files; these remain separate debt rather than being mixed into the
  reviewed diff.

### P5. Review `ops-infra-vps`

Status: implemented and validated on 2026-07-11.

Scope:

- Docker, VPS/deploy wrappers, scheduled-task helpers, environment defaults,
  and their security tests.

Exit gate:

- Docker configuration has no broad default binds; wrapper and secret-handling
  tests pass; environment doctor has no failures.

Evidence:

- `docker compose config --format json` shows API and Ollama published only on
  `127.0.0.1`; no broad bind is configured.
- Infra/VPS/Windows security suite passed `93` tests with `3` skipped.
- Changed PowerShell scripts pass parser validation and changed Bash wrappers
  pass `bash -n`.
- No deploy, token rotation, remote command, or live-client promotion was run.

### P6. Reconcile docs, packaging, training, and lab/R&D surfaces

Status: automated validation completed; final Helper interaction pending.

Actions:

1. Reconcile canonical docs and package manifests with the reviewed bundles.
2. Keep training/evals behind supply-chain gates.
3. Classify R&D scripts as Keep, Wrap, Review, or Drop; deletion requires an
   explicit ownership decision.
4. Re-run full Engine Brain refresh/doctor/pack and broad validation.

Exit gate:

- Every status entry belongs to one reviewed bundle or a documented local-only
  exclusion, and canonical docs match the resulting product boundaries.

Evidence:

- Full non-e2e Python suite passed: `1162` tests with `35` skipped.
- Final Engine Brain refresh reports doc sync and secret guardrails `passed`,
  P6 ready for plugin design, and P7 bounded safe-write tools enabled.
- Final doctor has `0` failures; its two warnings remain repository/PR and VS
  Code extension-state hygiene signals.
- Final context pack is profile `all`, with `33` sections.
- `git diff --check` passes. The worktree remains intentionally uncommitted and
  unstaged; this plan does not claim that 431 mixed status entries should be
  committed as one unit.

## Immediate Next Action

Keep the reviewed bundles separate when staging or committing. Start with the
Control Center/evidence/security bundle and its tests, then Engine Brain P6/P7,
Helper/Solteria, runner/bot, and infra. Do not turn the remaining mixed status
entries into one commit, and do not include runtime evidence or live-client
state.
