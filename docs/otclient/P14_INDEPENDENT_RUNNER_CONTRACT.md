# P14 Independent Runner And Release Automation

Status: `isolated_appliance_runner_implemented_acceptance_pending`.

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

- This integration is an intentionally bounded, dependency-complete P14
  contract port from the historical `codex/p14-independent-runner` lineage.
  It contains only the runner, acceptance, schema, workflow, Helper-module,
  roadmap-boundary, and regression-test sources required to make that contract
  reviewable on current `main`.
- Historical P8, P13, and P17–P24 work remains outside this pull request. It
  is neither represented nor implicitly accepted by merging this P14 contract;
  any later port must have its own bounded review and evidence handoff.
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

Signing-material configuration, appliance provisioning, visual capture, in-world
checks, canary execution, rollback, and any release promotion remain external
actions. P14 intentionally has no human approval/review gate: the bounded
protected workflow, signature verification, isolated hardware contract, and
evidence bindings are the gate. Documentation and Control Central reads cannot
create a passing result.

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
  `scripts/lua/otclient` and `scripts/lua/ctoa_chooser` sources, rejecting any
  untracked package input before signing. The chooser is the only normal P14
  autoload module; Helper remains disabled until the chooser explicitly activates
  it in ordinary sessions, and the unimplemented Safe option is not exposed. The
  isolated P14 capture process may instead supply its complete, exact guest-context
  flag set to select the same Helper UI-only loader path without operator-workstation
  focus or synthetic input; it is not a generic or live-client autoload. The command
  embeds the terminal P13
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
- `attest` accepts only a P-256 signed guest evidence envelope. The protected
  workflow pins its public certificate, key ID, logical snapshot ID, one-time
  16-hex run ID, source revision, Helper manifest, and rollback baseline before
  it projects the payload to an `acceptance-report.json`. It requires the exact
  proof set for each reported capability, non-empty digest-bound evidence for
  every passed proof, a real changed manifest for canary, and exact baseline
  restoration for rollback. It derives blocker codes and signs
  `acceptance-result.json`; receipt identifiers, run IDs, signatures, payloads,
  and free-form details are not copied.
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
`CTOA_P14_RUNNER_SIGNING_KEY` and the non-secret variables
`CTOA_P14_RUNNER_KEY_ID`, `CTOA_P14_GUEST_EVIDENCE_PUBLIC_CERT_B64`,
`CTOA_P14_GUEST_EVIDENCE_KEY_ID`, and `CTOA_P14_GUEST_SNAPSHOT_ID`.
There is deliberately no required reviewer: `can_admins_bypass=false` and the
cryptographically bound evidence contract provide the control boundary. When an
external envelope is supplied, the dispatch must also provide the matching
one-time `guest_run_id`. The job validates values without printing keys or the
envelope payload, performs a clean checkout without persisted GitHub credentials,
and uploads a separately named seven-day artifact containing only the fixed
preflight allowlist: `request.json`, `result.json`, `acceptance-request.json`,
`acceptance-result.json`, and `acceptance-report.json`. The injected
`guest-evidence-envelope.json` and replay-ledger `guest-run-claim.json` remain
inside the protected job and are never uploaded. The GitHub-hosted VM is
disposable and never the operator workstation.

### Durable one-time guest-run ledger

Before a protected job signs an acceptance result, it verifies the external
envelope cryptographically and reserves its guest run in a durable GitHub Issue
ledger. The protected job is serialized repository-wide with
`p14-guest-evidence-ledger-${github.repository_id}` and has only the additional
`issues: write` permission required to create that ledger record. The record is
created and immediately closed, with a deterministic SHA-256 commitment derived
from the repository and `guest_run_id`; neither the raw run ID, snapshot ID, nor
envelope payload is written to GitHub.

If an identical guest run ID is dispatched again, the existing commitment is
found and the job fails before it writes an acceptance report/result. The ledger
is deliberately consumed before attestation: a job failure after reservation is
fail-closed, and the operator must run a fresh isolated appliance ID instead of
retrying the envelope. This blocks both a duplicate envelope and a substituted
envelope that claims the same guest run ID.

The repository must keep Issues enabled and permit the protected workflow token
to create issues. Ledger issues are durable audit records: do not delete, reopen,
or repurpose them. If the GitHub API, permissions, lookup, or close postcondition
fails, no acceptance result is produced and P14 remains blocked;
this ledger never grants client, network, runtime-action, or promotion authority.

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

## Isolated appliance runner and evidence transport

The P14 appliance consists of four fixed components:

- `otclient_p14_guest_provision.ps1` stages only the tracked Helper package,
  creates a non-exportable ECDSA P-256 signing key in the current dedicated guest
  account, emits its public certificate for the GitHub variable, records an
  immutable snapshot manifest, and installs only an HKCU broker entry.
- `otclient_p14_guest_broker.ps1` consumes one opaque run ID through VBox guest
  properties, validates the snapshot manifest and all fixed code hashes, runs the
  guest capture/review plus real file-only sandbox canary and rollback, signs the
  compact receipt with the guest CNG key, and returns only a base64 envelope and
  hash through guest properties.
- `otclient_p14_vm_runner.ps1` is host-side and pins the P14 VM and snapshot. It
  rejects every enabled NIC (including NAT), shared folders, clipboard,
  drag-and-drop, VRDE, USB, wrong endpoint profile, and non-powered-off state. It
  waits only for the signed compact envelope, powers the ephemeral VM off, restores
  the snapshot, and clears transport properties.
- `otclient_p14_sandbox_executor.py` makes a complete verified package copy,
  creates exactly one sandbox-only canary marker, checks it, removes it, and proves
  the original baseline was restored. It never launches a client or accepts a
  source path, command, promotion flag, or output path.

Before a real run, a human owner must prepare a new appliance snapshot while the
guest is offline: copy the reviewed revision into `C:\P14Runner\repo`, install
the known client and Python runtime, establish the approved interactive guest
session, and run provisioning with a logical snapshot ID plus the SHA-256 of an
approved client-window visual baseline. The runner never supplies credentials,
unlocks Windows, or sends keyboard/mouse input. The snapshot must resume that
approved interactive session; a lock screen is deliberately a blocker.

After provisioning, pin the emitted public certificate, key ID, and logical
snapshot ID as the three GitHub environment variables above. Disable every VM NIC
and guest integration channel, set `CTOA/P14/EndpointProfile` to
`p14-offline-replay-v1`, create the new snapshot, and replace the source-controlled
snapshot UUID only after recording the new UUID. The previous NAT-capable snapshot
is not an acceptable fallback and is rejected by the host runner.

For each run, generate a new lowercase 16-hex run ID, execute the host runner with that ID,
then dispatch the protected workflow with `run_protected_replay=true`, the returned
`acceptance_envelope_b64`, and the same `guest_run_id`. This binds a result to a
single appliance run. The protected workflow records the opaque one-time ledger
commitment before attestation, so a second dispatch of that ID is rejected even
if its envelope differs. No path in this flow grants live-network, runtime-action,
or promotion authority.
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

For that child process only, the capture script adds the exact
`CTOA_P14_CAPTURE_HELPER_ACTIVATION=helper-ui-only` flag and an allowlisted,
nonce-bound `CTOA_P14_CAPTURE_REPORT_PATH` beneath `C:\P14Runner\evidence`. The
passive reporter accepts that destination only when every guest-context flag is
present, and the capture report records the resulting marker filename. Ordinary
sessions retain the chooser and never inherit this activation path.

The capture output is raw protected evidence. The acceptance report must be
derived from its hashes and the independent canary/rollback manifests; no caller
may edit the isolation flags or promote a capture whose marker timed out.
