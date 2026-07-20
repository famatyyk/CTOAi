# Infrastructure Decision Log - 2026-05-25

Date: 2026-05-25
Decision Authority: God Mode + STRATEGOS
Status: Execution authorized

## Confirmed Inputs

- VPS Host: 116.202.96.250
- SSH User: ctoa
- SSH Key File: ~/.ssh/ctoa_vps_ed25519
- Docker Registry: ghcr.io/famatyyk/ctoa-toolkit
- Go ahead: YES
- CI policy: PR-only build/test, tag-based publish/deploy on `v*`

## Effective Baseline

- Host: 116.202.96.250
- User: ctoa
- Auth: SSH key only
- Runtime: Docker-first
- Registry namespace: ghcr.io/famatyyk/ctoa-toolkit

## Execution Sequence

Phase 1 - Local validation

- docker compose up --build
- health check on /api/health with X-CTOA-Token header

Phase 2 - Access validation

- verify key exists: ~/.ssh/ctoa_vps_ed25519
- verify SSH to ctoa@116.202.96.250

Phase 3 - PR merge and tag release

- merge PR to main after checks pass
- create tag v1.14.0 or newer release tag

Phase 4 - VPS deployment

- registry mode:
  ./deploy-to-vps.sh 116.202.96.250 ctoa $HOME/.ssh/ctoa_vps_ed25519 v1.14.0 ghcr.io/famatyyk/ctoa-toolkit
- direct mode (no registry):
  ./deploy-to-vps.sh 116.202.96.250 ctoa $HOME/.ssh/ctoa_vps_ed25519

Phase 5 - Post-deploy checks

- container running on VPS
- /api/health returns OK
- phase-5 artifacts continue to update

## Current Blocker

SSH key is generated locally but not yet authorized on VPS.
Until public key is added to ctoa authorized_keys, deploy cannot finish.

The older ACR publish path is deprecated and should not be reintroduced in this flow.

Public key file:

- ~/.ssh/ctoa_vps_ed25519.pub

## Rosetta Preset Notes

- Governance preset: docs, governance, validation, and release-process review across the README, sprint governance/checklist docs, sprint flow manifests, policies, selected governance ops scripts, and `.github/workflows/ctoa-pipeline.yml`, with runtime, eval, lab, and tooling noise excluded.
- Infra preset: Docker, deployment, CI, VPS, and workflow-hardening review across `Dockerfile`, `docker-compose.yml`, `deploy/`, selected infra ops scripts, and infra docs.
- Infra narrowed from broad workflow matching to this explicit workflow list: `ctoa-daily-ci-health.yml`, `ctoa-monitoring-alerts.yml`, `ctoa-pipeline.yml`, `docker-build.yml`, `vps-authorize-ctoa-key.yml`, `vps-gs-cycle.yml`.
- Verified bundle reduction: `runtime/rosetta-bundles/infra-bundle_3.txt` = 233244 bytes, `runtime/rosetta-bundles/infra-bundle_4.txt` = 206255 bytes, down 26989 bytes (11.57%).
