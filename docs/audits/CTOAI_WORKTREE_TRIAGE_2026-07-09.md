# CTOAi Worktree Triage - 2026-07-09

Purpose: start the CTOAi cleanup sequence by classifying the current dirty
worktree before any deletion, staging, or product promotion.

## Current Snapshot

- Branch: `codex/control-center-guarded-actions`.
- Scope: `402` changed status entries from `git status --porcelain=v1`.
- Tracked changes: `236`.
- Untracked entries: `166`.
- Tracked diff size: `236 files changed, 16992 insertions(+), 2909 deletions(-)`.
- Engine Brain manifest: `AI/generated/manifest.json` generated at
  `2026-07-09T00:22:52+00:00`.
- Engine Brain guardrails: `doc_sync_status=passed`,
  `secret_guardrail_status=passed`.
- Control Center cockpit: `ready`, with warning `helper_not_ready`.
- Helper lane: blocked until fresh sandbox/in-world smoke is rerun against the
  current dev manifest.

Largest changed top-level groups:

| Top-level path | Status entries | Triage lane |
| --- | ---: | --- |
| `scripts` | 165 | Mixed: operator automation, Engine Brain, Helper, R&D helpers |
| `tests` | 97 | Validation suite; keep with the feature/security lane it proves |
| `web` | 56 | Control Center and evidence platform |
| `runner` | 30 | Agent Execution Engine and security hardening |
| `docs` | 15 | Canonical docs, roadmap, audits, migration plans |
| `bot` | 13 | Bot runtime; decide product vs lab before promotion |
| `training` | 4 | Training/evals supply-chain lane |
| `desktop_console` | 4 | Legacy launcher/desktop compatibility |
| `mobile_console` | 3 | Legacy Control Plane compatibility |
| `deploy` | 2 | VPS/deploy hardening |
| `api` | 2 | API runtime/auth guardrails |

## Product Classification

| Lane | Paths | Classification | Decision |
| --- | --- | --- | --- |
| Control Center / Evidence Platform | `web/`, `docs/CTOAI_CONTROL_CENTER_PHASE1.md`, `docs/CTOAI_COMMAND_RISK_MODEL.md` | Product | Keep as the main operator cockpit. Continue read-only/evidence surfaces first; write actions require risk model, audit records, and tests. |
| Control Plane legacy | `mobile_console/`, `desktop_console/`, `docs/site/live-dashboard.html` | Legacy compatibility | Do not delete. Migrate parity into Control Center in the documented order, then slim only after explicit parity evidence. |
| Agent Execution Engine | `runner/`, `agents/`, `prompts/`, `scoring/`, `schemas/` | Core product | Keep as Core. Split future changes into execution contracts, queue/reporting, provider safety, and validation bundles. |
| Release Governance | `workflows/`, `policies/`, `releases/evidence/`, `scripts/ops/sprint*_validate.py` | Product governance | Keep as release gate. Evidence pack generation should become a prerequisite, not an optional report. |
| Engine Brain / CTOAi platform | `AI/`, `scripts/ops/engine_brain_*`, `scripts/ops/ctoa_full_workspace_audit.py`, P6/P7 smoke scripts | Platform capability | Keep. Generated context is secret-safe now; future plugin actions must stay bounded and audited. |
| OTClient/Solteria Helper | `scripts/lua/otclient/`, `scripts/windows/solteria_helper_test_env.ps1`, Helper audit/release scripts | Product lane, currently blocked | Keep as Helper-first product lane. Do not promote live until sandbox smoke and release gate are fresh for the current manifest. |
| Bot Runtime | `bot/` | Review | Decide whether this is product, Control Center module, or lab before more UI work. Preserve tests and safety hardening either way. |
| Infra/VPS/Docker | `deploy/`, `docker-compose.yml`, `ctoa-vps.ps1`, VPS wrappers | Product operations | Keep. Maintain loopback/private defaults and explicit opt-in for broad exposure. |
| Security hardening | security tests, URL/path/process guards, auth/cookie/redaction helpers | Cross-cutting product guardrail | Keep with the lane it protects. Do not mix unrelated guardrails into one review bundle unless the tests prove the same contract. |
| Training/Evals | `training/`, `evals/` | Review / future product support | Keep separate from Core release until supply-chain gates and immutable model revisions are verified. |
| R&D / lab helpers | depack/capture/reverse helpers under `scripts/ops/`, local archives, experiment outputs | Studio/private or lab | Do not present as public product. Classify as Keep, Wrap, Review, or Drop later only after owner decision. |
| Local/runtime state | `.ctoa-local/`, `runtime/`, `logs/`, `data/`, caches | Local evidence/state | Do not commit secrets or runtime dumps. Summarize evidence only through bounded, redacted artifacts. |

## First Cleanup Bundles

Use these bundles to avoid one oversized review:

1. `control-center-evidence-security`
   - Paths: `web/`, `docs/CTOAI_COMMAND_RISK_MODEL.md`,
     `docs/CTOAI_CONTROL_CENTER_PHASE1.md`, relevant web/API tests.
   - Gate: `cd web; npm run lint; npm test`, plus targeted Python tests for
     release evidence and Control Center evidence contracts.

2. `engine-brain-p6-p7`
   - Paths: `AI/`, `scripts/ops/engine_brain_*`,
     `scripts/ops/control_center_p*_*.py`,
     `tests/test_engine_brain_*`,
     `tests/test_control_center_p*_*.py`.
   - Gate: Engine Brain status/self-check/brief/cockpit plus targeted pytest.

3. `helper-solteria`
   - Paths: `scripts/lua/otclient/`, `scripts/windows/solteria_helper_test_env.ps1`,
     Helper audit/release scripts, Helper tests.
   - Gate: module contract, profile audit, release gate, then sandbox
     `ReadyCheck`, `SmokeAttachModules`, `SmokeAttachAll`.

4. `runner-bot-security`
   - Paths: `runner/`, `bot/`, related security helpers and tests.
   - Gate: targeted pytest for runner/bot safety, then broader non-e2e pytest.

5. `ops-infra-vps`
   - Paths: `deploy/`, `docker-compose.yml`, `ctoa-vps.ps1`,
     `scripts/ops/*vps*`, task wrappers.
   - Gate: Docker compose config, VPS wrapper tests, environment doctor.

6. `docs-product-packaging`
   - Paths: `README.md`, `docs/INDEX.md`, `docs/PRODUCT_PORTFOLIO.md`,
     `product/packages/*.manifest.json`.
   - Gate: doc sync guard and package boundary review.

7. `training-evals`
   - Paths: `training/`, `evals/`.
   - Gate: supply-chain security tests before inclusion in any public package.

## Immediate Rules

- Do not delete legacy UI until Control Center parity is proven.
- Do not live-promote Helper until current smoke evidence is fresh.
- Do not add new P7 plugin write actions until the next action has risk model
  coverage, audit logging, Control Center evidence gates, and targeted MCP tests.
- Do not stage generated runtime, logs, local databases, auth stores, or secret
  bearing files.
- Do not combine unrelated product, R&D, and local-state changes in one review
  bundle.

## Next Concrete Step

Start with bundle `control-center-evidence-security`, because README identifies
Control Center plus evidence/reporting plus VPS parity as the current lane. The
next action should be a scoped diff review for that bundle, followed by its
targeted lint/test gates. After that, move to `helper-solteria` to clear the
current `helper_not_ready` blocker.
