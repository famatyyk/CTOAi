# P14 Independent Runner And Release Automation

Status: `foundation_in_progress`.

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

`scripts/ops/otclient_p14_independent_runner.py` exposes only three commands:

- `prepare` derives the official 63-file Helper package manifest from tracked
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

The request never carries a command, executable path, local client path, runtime
log, credential, signing key, or arbitrary output path. Every authority field is
fixed to false. Canary status is `planned_not_executed`; promotion always requires a
separate external approval and cannot be granted by this runner.

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
independence gate. Until a separate Windows runner is registered, GitHub will keep
the manually selected self-hosted job queued and P14 remains operationally open.

## Current gate and next slice

The local checkout is intentionally fail-closed for an operational request while it
contains tracked modifications or lacks externally supplied signing material. The
foundation is complete when local tests pass; P14 itself remains open until a real
second machine or VM returns a matching signed result, an isolated visual/in-world
suite is attached without operator-workstation focus/input, and a canary plus actual
rollback rehearsal are independently evidenced. Promotion approval remains outside
plugin MCP actions.
