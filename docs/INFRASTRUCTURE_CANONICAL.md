# CTOA Infrastructure - Canonical Configuration

Last Updated: 2026-05-18
Status: Active
Authority: This file is the single source of truth for infra and deployment.

## Final Decisions

- Production VPS host: 116.202.96.250
- SSH user: ctoa
- SSH key path: ~/.ssh/ctoa_vps_ed25519
- Runtime: Docker-first
- Docker registry namespace: docker.io/famatyyk/ctoa-toolkit

## Standard Local Flow

1. Build and run locally:
   docker compose up --build
2. Health check:
   curl -H "X-CTOA-Token: dev-token-change-me" http://127.0.0.1:8787/api/health

## Standard VPS Flow

Preferred deploy command with registry image:

./deploy-to-vps.sh 116.202.96.250 ctoa $HOME/.ssh/ctoa_vps_ed25519 v1.14.0 docker.io/famatyyk/ctoa-toolkit

Fallback deploy command without registry (image streamed over SSH):

./deploy-to-vps.sh 116.202.96.250 ctoa $HOME/.ssh/ctoa_vps_ed25519

## CI/CD Flow

Workflow: .github/workflows/docker-build.yml

On tag v*:
1. Build image
2. Run test suite in container
3. Publish image to docker.io/famatyyk/ctoa-toolkit
4. Deploy to VPS using deploy-to-vps.sh

Required GitHub secrets:
- DOCKER_HUB_TOKEN
- VPS_SSH_KEY
- VPS_HOST
- VPS_USER

Notes:
- Docker Hub username is fixed to famatyyk in workflow.
- VPS_HOST should be 116.202.96.250
- VPS_USER should be ctoa

## Operational Guardrails

- No password auth for SSH, key only.
- No secret values in committed files.
- Keep /opt/ctoa/.env on VPS for production env variables.
- If /opt/ctoa/.env is missing, deploy script uses safe fallback token and logs a warning.

## Current Blocker

- Public key from ~/.ssh/ctoa_vps_ed25519.pub must be added to ctoa@116.202.96.250 authorized_keys.
- Until then, automated deploy cannot complete.
