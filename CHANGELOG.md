# Changelog

All notable changes to this project will be documented in this file.

## [1.2.0] - 2026-03-25 (Sprint-029: Training Hardening + Quality Gate + VPS Autonomy)

### Added
- **Training curriculum v1.2.0**: `training/curriculum.md` rozbudowany do pełnego dokumentu — 5 modułów z teorią, szablonami BRAVE(R), ćwiczeniami praktycznymi i macierzą PASS/FAIL
- **Quality gate expansion** (CTOA-143): rozszerzenie polityki CI gate o dodatkowe weryfikacje; focused tests 2/2 PASS
- **Nightly trend automation** (CTOA-144): `nightly_stability.py` extended with `--sprint` CLI flag; sprint-029 nightly run produces drift visibility fields (`trend_24h`, `trend_7d`, `drift`, `anomaly`) and writes evidence to `runtime/evidence/sprint-029/`; focused tests 2/2 PASS
- **Dashboard ergonomics pass** (CTOA-145): `/api/dashboard` now returns `status_message` field with human-readable operator message for all operating modes (healthy/degraded/error); focused tests 2/2 PASS
- **CI evidence hardening** (CTOA-146): evidence entries now carry `sprint_id`, `kind`, `path`, `sha256`, `recorded_at` — all fields required for CI artifact discovery; canonical path `runtime/evidence/sprint-{id}/evidence-index.json`; focused tests 2/2 PASS
- **VPS DB ownership hardening**: ownership wszystkich tabel i sekwencji przeniesiony na użytkownika `ctoa`; rola NOSUPERUSER
- **Tiered reseed self-heal**: Tier A/B/C z nowymi serwerami `rising-continents.com` i `altheaworld.org` (6 serwerów READY)

### Validation
- Sprint-029 release pack wave_1: PASS (automated, sprint029_validate 10/10)
- Sprint-029 release pack wave_2: PASS (CTOA-143..146 DONE, focused tests 7/7)

## [1.1.1] - 2026-03-24 (Sprint-028: Release Stabilization + Operator UX + Evidence Continuity)

### Added
- **Dashboard timeline stabilization**: mobile console trend view now caps visible rows, keeps overflow visible, and prioritizes critical signal groups
- **Evidence retention policy**: `evidence_retention.py` applies bounded TTL and max-entry pruning for SHA256-indexed evidence artifacts
- **Nightly anomaly tuning**: `nightly_stability.py` now emits an `anomaly` section with configurable thresholds and low-sample guard
- **Sprint-028 CI gate**: `sprint028_validate.py` validates dashboard/nightly regressions and evidence interactions with actionable diagnostics

### Validation
- Sprint-028 release pack wave_1: PASS (automated)
- Sprint-028 release pack wave_2: PASS (STRATEGOS sign-off)

## [1.1.0] - 2026-03-24 (Sprint-027: Quality + Delivery Continuity + Automation Hardening)

### Added
- **Sprint-027 API regression coverage**: focused contract tests for execution, metrics, and dashboard reliability surfaces
- **Nightly trend report v2**: `nightly_stability.py` now emits `trend_24h`, `trend_7d`, and `drift` sections
- **Dashboard ergonomics pass**: grouped reason-code signals, collapsible sections, dominant signal summary, and 24h SLO timeline
- **Sprint-027 evidence hardening**: validator and nightly runs now write SHA256-backed entries to `runtime/evidence/sprint-027/`
- **CI evidence bundle**: pipeline runs nightly batch and uploads Sprint-027 evidence artifacts

### Validation
- Sprint-027 release pack wave_1: PASS (automated)
- Sprint-027 release pack wave_2: PASS (STRATEGOS sign-off)

## [1.0.9] - 2026-03-24 (Sprint-026: Reliability + Observability + Nightly Automation)

### Added
- **Execution metrics API**: `GET /api/agents/execution/metrics` with per-reason_code counts, `success_rate_24h`, `error_budget_remaining`, `alert_active`, and `alert_reason`
- **Alert rule function**: `runner.alert_rules.check_generation_failed_spike()` integrated into metrics computation flow
- **Nightly artifact schema test**: automated validation for `nightly_stability.py` output contract
- **Dashboard SLO extensions**: `/api/dashboard` now exposes `top_reason_codes` and `slo_summary`
- **Dashboard trend widget**: frontend mini trend summary for dominant reason_code + SLO status

### Validation
- Sprint-026 release pack wave_1: PASS (automated)
- Sprint-026 release pack wave_2: PASS (STRATEGOS sign-off)

## [1.0.8] - 2026-03-24 (Sprint-025: Control Plane UX + Execution Telemetry + Governance)

### Added
- **reason_code taxonomy**: `/api/agents/execution/run` now returns `reason_code` (`ARTIFACTS_READY` | `MANIFEST_PENDING` | `ARTIFACTS_PENDING` | `GENERATION_FAILED`) and full `reason_code_taxonomy` dict for operator-side display
- **execution_trend per run**: execution endpoint returns last-N run summary (ready/failed/empty counts) via internal `_execution_trend_from_manifests()`
- **Operator trend endpoint**: `GET /api/agents/execution/trend?limit_runs=N` — role-protected, returns per-run status breakdown and aggregate summary
- **health_timeline + timeline_summary**: `/api/dashboard` now includes per-day quality timeline list and rolling summary (days, avg_quality, latest_day)
- **Frontend timeline display**: `static/app.js` updated — one-click shows trend, dashboard always shows `timeline_summary` + last-5 `health_timeline_preview`
- **Sprint-025 CI gate**: `sprint025_validate.py` gate inserted in `.github/workflows/ctoa-pipeline.yml`
- **VS Code task chain**: Sprint-025 Validate + Wave-1 Run tasks added to `.vscode/tasks.json`

### Docs
- `docs/MOBILE_CONSOLE.md`: reason_code taxonomy table and operator trend endpoint documented

## [Unreleased]

### Added
- **Public/private product architecture**: added productization boundary document for public toolkit vs private studio assets
- **Mandatory bootstrap flow**: `ctoa_product_bootstrap.py` creates ignored local JSON config and SQLite state for customer-specific setup
- **Mandatory update gate**: `ctoa_update_gate.py` blocks launch until bootstrap exists and local version/schema match the tracked product manifest
- **Product manifest + config template**: added tracked public manifest and local config template for customer bootstrap flows

### Security
- **SSH Key Rotation (2026-03-12)**: Rotated ed25519 SSH key for VPS access
  - Old key removed from `/root/.ssh/authorized_keys` on VPS
  - New key generated locally at `~/.ssh/ctoa_vps_ed25519`
  - Verified connectivity via new key before removing old key
  - Commit: 27333c2

- **PAT Token Rotation (2026-03-12)**: Rotated GitHub Personal Access Token
  - Old compromised PAT (now revoked) was safely removed from repo and local env
  - New PAT installed locally and on VPS at `/opt/ctoa/.env`
  - Verified GitHub API connectivity with new token (Issue #1 update successful)
  - Commits: d436661, deb7bda

- **Repository Cleanup (2026-03-12)**: Removed embedded secrets from tracked files
  - Sanitized `.vscode/tasks.json` - removed inline PAT/SSH key references
  - Created `scripts/ops/ctoa-vps.ps1` wrapper using environment variables
  - Hardened pipeline secret scanning with broader regex pattern
  - Commit: 86a8315

- **Pipeline Hardening (2026-03-12)**: Enhanced secret detection in CI/CD
  - Updated `.github/workflows/ctoa-pipeline.yml` secret scan pattern
  - Pattern now detects: GitHub PAT formats (`ghp_*`, `github_pat_*`), AWS keys (`AKIA*`), SSH keys
  - Scans `git ls-files` (tracked files only) to avoid false positives in temp/node_modules
  - Commit: d436661

- **Audit Trail Setup (2026-03-12)**: Documented PAT usage monitoring approach
  - VPS audit log location: `/opt/ctoa/logs/pat-audit.log`
  - Each PAT usage logged via wrapper with timestamp and action
  - See `deploy/vps/SETUP.md` for monitoring instructions

## [0.1.0] - 2026-03-12

### Initial Release
- CTOA AI Toolkit scaffold with 10-agent organization
- BRAVE(R) prompt engine framework
- Tool advisor scoring system
- CI approval gate integration
- Training module structure

