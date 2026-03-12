# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

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

