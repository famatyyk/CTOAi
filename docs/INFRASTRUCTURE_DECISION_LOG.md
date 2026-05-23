# Infrastructure Decision Log - 2026-05-18

Date: 2026-05-18
Decision Authority: God Mode + STRATEGOS
Status: Execution authorized

## Confirmed Inputs

- VPS Host: 116.202.96.250
- SSH User: ctoa
- SSH Key File: ~/.ssh/ctoa_vps_ed25519
- Docker Registry: docker.io/famatyyk/ctoa-toolkit
- Go ahead: YES

## Effective Baseline

- Host: 116.202.96.250
- User: ctoa
- Auth: SSH key only
- Runtime: Docker-first
- Registry namespace: docker.io/famatyyk/ctoa-toolkit

## Execution Sequence

Phase 1 - Local validation
- docker compose up --build
- health check on /api/health with X-CTOA-Token header

Phase 2 - Access validation
- verify key exists: ~/.ssh/ctoa_vps_ed25519
- verify SSH to ctoa@116.202.96.250

Phase 3 - VPS deployment
- registry mode:
  ./deploy-to-vps.sh 116.202.96.250 ctoa $HOME/.ssh/ctoa_vps_ed25519 v1.14.0 docker.io/famatyyk/ctoa-toolkit
- direct mode (no registry):
  ./deploy-to-vps.sh 116.202.96.250 ctoa $HOME/.ssh/ctoa_vps_ed25519

Phase 4 - Post-deploy checks
- container running on VPS
- /api/health returns OK
- phase-5 artifacts continue to update

## Current Blocker

SSH key is generated locally but not yet authorized on VPS.
Until public key is added to ctoa authorized_keys, deploy cannot finish.

Public key file:
- ~/.ssh/ctoa_vps_ed25519.pub

