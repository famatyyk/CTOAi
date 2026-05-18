# Infrastructure Decision Log - 2026-05-18

**Date**: 2026-05-18T01:10Z  
**Decision Authority**: God Mode + STRATEGOS  
**Status**: ✅ EXECUTION AUTHORIZED (slow, step-by-step rollout)

---

## Confirmed Inputs From God Mode

- VPS Host: `116.202.96.250`
- SSH User: `ctoa`
- SSH Key File: `~/.ssh/ctoa_vps_ed25519`
- Deployment Approval: `YES`

## Open Input (Non-Blocking)

- Docker Registry URL: not provided yet.
- Decision: deployment script supports two modes:
  - registry mode (push/pull)
  - direct SSH image streaming mode (no registry required)

---

## Governance Decision

`docs/INFRASTRUCTURE_CANONICAL.md` remains the single source of truth for infrastructure.

Effective baseline for deployments:
- host = `116.202.96.250`
- user = `ctoa`
- auth = SSH key only
- runtime = Docker-first

---

## Execution Plan (Slow Rollout)

### Phase 1: Local validation
1. Build and run locally:
   - `docker compose up --build`
2. Verify:
   - `GET /api/health`
   - mobile console responds on `:8787`

### Phase 2: Deployment prep
1. Verify key path exists:
   - `~/.ssh/ctoa_vps_ed25519`
2. Verify SSH access:
   - `ssh -i ~/.ssh/ctoa_vps_ed25519 ctoa@116.202.96.250`

### Phase 3: VPS deployment
1. Deploy with direct SSH image transfer (no registry needed):
   - `./deploy-to-vps.sh 116.202.96.250 ctoa $HOME/.ssh/ctoa_vps_ed25519`
2. If registry is later defined, deploy with tag + repo:
   - `./deploy-to-vps.sh 116.202.96.250 ctoa $HOME/.ssh/ctoa_vps_ed25519 v1.14.0 <registry/ctoa-toolkit>`

### Phase 4: Post-deploy verification
1. Confirm container is running on VPS
2. Confirm `/api/health` returns OK
3. Confirm Phase-5 monitoring artifacts continue updating

---

## Current Sprint Alignment

- Sprint-041: released (v1.14.0)
- Sprint-042: active
- Infrastructure track: moved from ambiguity to canonical, Docker-based path

---

## Confirmation Snapshot

```text
VPS Host:      116.202.96.250 ✓
SSH User:      ctoa [x] or root [ ]
SSH Key File:  ~/.ssh/ctoa_vps_ed25519
Docker Registry: TBD (optional, non-blocking)
Go ahead?      YES [x] NO [ ]
```

