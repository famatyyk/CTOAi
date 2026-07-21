# CTOA Infrastructure - Canonical Configuration

Last Updated: 2026-05-25
Status: Active
Authority: This file is the single source of truth for infra and deployment.

## Final Decisions

- Production VPS host: 116.202.96.250
- SSH user: ctoa
- SSH key path: ~/.ssh/ctoa_vps_ed25519
- Runtime: Docker-first
- Docker registry namespace: ghcr.io/famatyyk/ctoa-toolkit
- CI promotion path: PR-only build/test, then tag-based GHCR publish on `v*`; VPS deploy is opt-in

## Standard Local Flow

1. Build and run locally:
   docker compose up --build
2. Health check:
   curl -H "X-CTOA-Token: dev-token-change-me" <http://127.0.0.1:8787/api/health>

## Standard VPS Flow

Preferred deploy command with registry image:

./deploy-to-vps.sh 116.202.96.250 ctoa $HOME/.ssh/ctoa_vps_ed25519 v1.14.0 ghcr.io/famatyyk/ctoa-toolkit

Fallback deploy command without registry (image streamed over SSH):

./deploy-to-vps.sh 116.202.96.250 ctoa $HOME/.ssh/ctoa_vps_ed25519

## CI/CD Flow

Workflow: .github/workflows/docker-build.yml

On pull request to `main`:

1. Build image
2. Run test suite in container
3. Do not publish or deploy

On tag `v*`:

1. Build image
2. Run test suite in container
3. Publish image to ghcr.io/famatyyk/ctoa-toolkit using the built-in `GITHUB_TOKEN`
4. Deploy to VPS only when repository variable `CTOA_ENABLE_VPS_DEPLOY=true`

Required GitHub secrets:

- VPS_SSH_KEY
- VPS_HOST
- VPS_USER

Notes:

- GHCR package owner follows the GitHub repository owner.
- VPS_HOST should be 116.202.96.250
- VPS_USER should be ctoa
- Docker Hub publishing was removed; GHCR is the canonical registry.
- VPS deployment remains opt-in until registry pull authentication and the deploy wrapper are configured.
- Direct push to `main` is not part of this flow; PR merge and tag release are the standard path.

## Operational Guardrails

- No password auth for SSH, key only.
- No secret values in committed files.
- Keep /opt/ctoa/.env on VPS for production env variables.
- If /opt/ctoa/.env is missing, deploy script uses safe fallback token and logs a warning.

## Current Blocker

- Public key from ~/.ssh/ctoa_vps_ed25519.pub must be added to ctoa@116.202.96.250 authorized_keys.
- Until then, automated deploy cannot complete.
