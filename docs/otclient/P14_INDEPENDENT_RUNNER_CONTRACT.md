# P14 Independent Runner And Release Automation

Status: `foundation_ready_operational_hardening_required`.

P14 moves regression evidence away from the operator workstation. The first
implementation slice is deliberately artifact-only: it does not launch a client,
capture the user's screen, send input, dispatch network or game actions, promote a
package, or add an MCP write tool.

## Capability basis

The current source checkout at `C:\otclient` was detected as
`mehah-redemption` with high confidence. Module discovery, `.otmod` metadata,
`g_ui.loadUI`, `g_ui.createWidget`, OTUI files, anchors, and state selectors are
supported by native-source evidence. The exact client version and all widget aliases
remain unproven and are not used as an authorization signal.

## Contract

`scripts/ops/otclient_p14_independent_runner.py` exposes only three foundation
commands:

- `prepare` derives the official Helper package manifest from the current tracked
  `scripts/lua/otclient` and `scripts/lua/ctoa_chooser` sources, embeds the terminal P13
  roadmap state, adds a rollback baseline, signs the canonical request, and writes
  only `request.json` under the selected artifact root.
- `verify` accepts only that fixed request file, verifies the versioned schema,
  trusted key ID, HMAC-SHA256 signature, embedded hashes, terminal P13 boundary,
  sanitized Helper manifest, Git revision, clean checkout, and deterministic
  rollback replay. It writes only `result.json`.
- `verify-result` performs the controller-side schema, signature, request-hash,
  check-order, authority, clean-checkout, and rollback binding verification without
writing another artifact.

`scripts/ops/otclient_p14_acceptance_attestation.py` adds a separate
capability-driven acceptance boundary:

- `prepare` verifies the signed foundation result and creates
  `acceptance-request.json`, bound to the exact source revision, Helper manifest,
  runner request, and runner result. By default it requests all four P14 acceptance
  capabilities; a runner may request a bounded subset while collecting evidence.
- `attest` accepts only a schema-valid `acceptance-report.json` produced in the
  isolated environment. It requires the exact proof set for each reported
  capability, non-empty digest-bound evidence for every passed proof, a real
  changed manifest for canary, and exact baseline restoration for rollback. It
  derives blocker codes and signs `acceptance-result.json`; free-form details are
  not copied.
- `verify-result` replays the request signature, result signature, source binding,
  capability/proof set, isolation flags, transition invariants, blocker derivation,
  and status derivation.

The acceptance capabilities are `visual_regression`, `in_world_regression`,
`canary_rehearsal`, and `rollback_rehearsal`. The report contains evidence hashes
and counts, not paths, screenshots, logs, commands, identities, or URLs. Raw
artifacts stay on the protected evidence transport and are never returned by
Control Central.

`scripts/ops/otclient_p14_runner_preflight.py` is the bounded operational reader.
It checks only the fixed workflow, matching runner labels and availability,
environment protection metadata, secret-name and key-ID presence, branch policy,
the latest self-hosted job, artifact expiry, and structural request/result binding.
Its compact snapshot contains status codes and booleans only: it does not persist
signatures, keys, runner identity, URLs, commands, logs, or artifact payloads.

The request never carries a command, executable path, local client path, runtime
log, credential, signing key, or arbitrary output path. Every authority field is
fixed to false. Canary status is `planned_not_executed`; promotion always requires a
separate external approval and cannot be granted by this runner.

The acceptance workflow prepares only the signed request. It never creates a
synthetic report, marks a proof passed from static checks, launches the client, or
captures the operator screen. A missing or partial result becomes four bounded
capability gaps. The remediation plan allows visual and in-world collection after a
current foundation attestation, then requires both before canary and canary before
rollback. No step auto-executes.

The signing key and its trusted ID are injected outside the repository:

```powershell
$env:CTOA_P14_RUNNER_SIGNING_KEY = '<at least 32 bytes from a secret store>'
$env:CTOA_P14_RUNNER_KEY_ID = 'independent-runner-prod'
```

The key must never be committed, printed, copied into Engine Brain, or included in
an uploaded artifact. HMAC is the v1 transport integrity mechanism; production
sender and runner must obtain the shared key from their independent secret stores.

## GitHub-hosted PR replay

`.github/workflows/p14-independent-runner-contract.yml` runs on a clean Windows
runner. It generates job-scoped test signing material, runs the schema/tamper/path
tests, prepares the signed request from tracked sources, verifies it on the same
clean job, and uploads the non-promotable request/result evidence for seven days.
The CI key is discarded, so that artifact proves the contract job only and is never
eligible for release promotion.

This job is the pull-request gate. It runs on `windows-latest`, has read-only
repository permissions, and checkout credentials are not persisted.

## Self-hosted Windows replay

The second workflow job is intentionally limited to a trusted manual dispatch with
`run_self_hosted=true`. It never runs for `pull_request` and does not use
`pull_request_target`. The runner must be registered on a separate machine or VM
with all four labels:

- `self-hosted`
- `Windows`
- `X64`
- `ctoa-p14`

The job is also bound to the protected GitHub environment
`p14-independent-runner`. That environment supplies the secret
`CTOA_P14_RUNNER_SIGNING_KEY` and the non-secret variable
`CTOA_P14_RUNNER_KEY_ID`. Environment approval should be required before the job
can read the signing material. The job validates both values without printing the
key, derives a schema-safe ID from `RUNNER_NAME`, performs a clean checkout without
persisted GitHub credentials, and uploads a separately named seven-day artifact.

The operator workstation must not be labeled `ctoa-p14` and cannot satisfy the
independence gate. A matching Windows runner is now registered and online, and a
manual self-hosted replay has completed successfully. The returned result is
structurally valid, authority-safe, clean-checkout bound, rollback-replay passed,
and was signature-verified inside the protected job. It is not current for the
present repository revision, so it remains evidence rather than authorization.

The `ctoa.p14-runner-preflight.v2` preflight emits
`ctoa.p14-remediation-plan.v1`: a bounded capability plan
whose steps contain only allowlisted action IDs, capability IDs, status, risk,
interaction, reason codes, and dependency IDs. The evidence reader verifies the
exact action-to-capability/risk/interaction contract and fails closed on malformed
counts, duplicate actions, unknown dependencies, metadata substitution, or a next
action that is not ready. Control Central exposes only the minimized ordered steps;
it never exposes reviewer identity, runner identity, secret values, URLs, commands,
signatures, or artifact payloads.

## Current gate and next slice

The foundation and independent-runner execution path are complete. The current
operational preflight remains fail-closed on three bounded blocker codes:

- `p14_environment_required_reviewer_missing`
- `p14_environment_admin_bypass_enabled`
- `p14_self_hosted_result_revision_mismatch`

The first two require an explicit repository-owner choice of reviewer and bypass
policy; Control Central marks `harden_p14_environment` ready but cannot make that
change automatically. It keeps `refresh_p14_independent_runner_evidence` blocked by
`environment_protection` until the environment is hardened. The third blocker is
then cleared only by a new manual self-hosted replay for the current clean revision.
P14 remains open until those controls pass, the signed acceptance request is
completed by an isolated visual/in-world suite without operator-workstation
focus/input, and the canary plus actual rollback transitions are independently
evidenced. Promotion approval remains outside plugin MCP actions.
