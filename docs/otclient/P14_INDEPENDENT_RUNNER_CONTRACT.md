# P14 Independent Runner And Release Automation

Status: `protected_replay_ready_acceptance_pending`.

## Integration annotation — 2026-07-21

This annotation starts P14 as the next CTOAi integration candidate. It records
the review and evidence handoff only; it does not mark P14 merged, accepted, or
authorised to perform a runtime, release, or promotion action.

### Current merge boundary

A local dry run of `codex/p14-independent-runner` into the current `main`
found conflicts in generated Engine Brain evidence and a small number of CI and
test files. Therefore P14 must be ported through a dedicated integration branch
based on current `main`; it must not be merged directly from its historical
branch tip. Resolve source, workflow, and test conflicts first, then regenerate
the `AI/generated` evidence from the merged source. Generated artifacts are
evidence, not hand-merged source of truth.

- P14 must be reviewed as the complete `codex/p14-independent-runner` lineage.
  P8 is already an ancestor of that lineage, so it must not be integrated as a
  competing or separately promoted implementation.
- Before source integration, validate the P14 contract, runner preflight,
  acceptance-attestation, and VM-capture test surfaces, then require the
  GitHub-hosted contract workflow for the reviewed revision.
- After source integration, regenerate the bounded Engine Brain and Control
  Center evidence, then run `otclient_p14_runner_preflight.py` against the
  current protected environment. The preflight result—not this annotation—is
  the authority for any external configuration or evidence-collection step.
- The next operational evidence remains ordered and explicit: protected
  foundation replay, visual and in-world attestations, canary rehearsal, then
  rollback rehearsal. A missing, expired, partial, or revision-mismatched
  result remains fail-closed.

Environment approval, signing-material configuration, runner operation, visual
capture, in-world checks, canary execution, rollback, and any release promotion
remain external actions. They require their own approved workflow and cannot be
triggered by this documentation change, an MCP call, or a Control Center read.

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
It checks only the fixed workflow, protected GitHub-hosted capacity,
environment protection metadata, secret-name and key-ID presence, branch policy,
the latest protected job, artifact expiry, and structural request/result binding.
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

## Protected GitHub-hosted Windows replay

The second workflow job is intentionally limited to a trusted manual dispatch with
`run_protected_replay=true`. It never runs for `pull_request` and does not use
`pull_request_target`. It uses the standard ephemeral `windows-latest` pool, which
is free for this public repository and does not depend on an operator-managed VM.

The job is also bound to the protected GitHub environment
`p14-independent-runner`. That environment supplies the secret
`CTOA_P14_RUNNER_SIGNING_KEY` and the non-secret variable
`CTOA_P14_RUNNER_KEY_ID`. Environment approval should be required before the job
can read the signing material. The job validates both values without printing the
key, binds a provider-scoped schema-safe ID, performs a clean checkout without
persisted GitHub credentials, and uploads a separately named seven-day artifact.
The GitHub-hosted VM is disposable, is never the operator workstation, and removes
the persistent host-capacity blocker while retaining the required environment
review and no-admin-bypass gate.

The `ctoa.p14-runner-preflight.v2` preflight emits
`ctoa.p14-remediation-plan.v1`: a bounded capability plan
whose steps contain only allowlisted action IDs, capability IDs, status, risk,
interaction, reason codes, and dependency IDs. The evidence reader verifies the
exact action-to-capability/risk/interaction contract and fails closed on malformed
counts, duplicate actions, unknown dependencies, metadata substitution, or a next
action that is not ready. Control Central exposes only the minimized ordered steps;
it never exposes reviewer identity, runner identity, secret values, URLs, commands,
signatures, or artifact payloads.

The plan retains every known P14 capability action required by the observed
state, up to the contract maximum of 11 actions: 10 recovery capabilities plus
the fail-closed review fallback. Consumers reject oversized or substituted
actions; they do not silently truncate a valid dependency chain such as canary
followed by rollback.

`ROADMAP_STATE` consumes the same fixed preflight artifact as an advisory source.
When P13 remains operational but P14 requires external work, its `next_action`
inherits the validated remediation action ID. Invalid or substituted plans fail
to `review_p14_external_state`; they never change runtime or live authority.

## Current gate and next slice

The foundation and independent-runner execution path are complete. The current
operational preflight remains fail-closed on these bounded blocker codes:

- `p14_self_hosted_result_revision_mismatch`
- `p14_visual_regression_not_proven`
- `p14_in_world_regression_not_proven`
- `p14_canary_rehearsal_not_proven`
- `p14_rollback_rehearsal_not_proven`

The environment is hardened and standard GitHub-hosted capacity requires no
operator-managed machine. A new protected manual replay for the current clean
revision must now provide visual, in-world, canary, and rollback evidence in
dependency order. Legacy `p14_self_hosted_*` blocker identifiers remain stable for
existing Control Central consumers; they now describe the protected replay result,
not a dependency on a persistent self-hosted machine.
P14 remains open until those controls pass, the signed acceptance request is
completed by an isolated visual/in-world suite without operator-workstation
focus/input, and the canary plus actual rollback transitions are independently
evidenced. Promotion approval remains outside plugin MCP actions.

## Deterministic Windows VM capture

The only supported workstation-independent client capture is
`scripts/windows/otclient_p14_vm_capture.ps1`. It runs inside the logged-in guest
desktop, launches the preinstalled client, waits for the passive Helper reporter to
publish `online=true`, captures the guest display, and writes hashed evidence. It
fails closed when the guest session, client root, or isolation context is missing;
it never accepts a workstation screenshot or a manually supplied “ready” marker.

The golden runner image must contain the complete Redemption client under
`C:\P14Runner\client`, including `mods\ctoa_otclient`, its DAT/SPR pair, and a
known-good graphics configuration. The image is restored from a clean snapshot
before every run. The protected launcher sets these process-scoped values before
calling the script:

```powershell
$env:CTOA_P14_ISOLATED_ENVIRONMENT = 'true'
$env:CTOA_P14_CAPTURE_CONTEXT = 'guest'
$env:CTOA_P14_OPERATOR_WORKSTATION_FOCUS_USED = 'false'
$env:CTOA_P14_OPERATOR_WORKSTATION_INPUT_USED = 'false'
$env:CTOA_P14_NETWORK_DISPATCH_USED = 'false'
$env:CTOA_P14_LIVE_CLIENT_ACCESSED = 'false'
$env:CTOA_P14_PROMOTION_ATTEMPTED = 'false'
& C:\P14Runner\repo\scripts\windows\otclient_p14_vm_capture.ps1 `
  -SourceRevision $env:GITHUB_SHA
```

The capture output is raw protected evidence. The acceptance report must be
derived from its hashes and the independent canary/rollback manifests; no caller
may edit the isolation flags or promote a capture whose marker timed out.
