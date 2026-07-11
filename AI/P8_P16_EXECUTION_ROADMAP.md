# CTOAi P8-P16 Execution Roadmap

Status: P8 is `implementation_complete` and
`operational_acceptance_blocked` after P6/P7 readiness and Helper `v2.2.1` live
promotion. Its implementation is the `v2.3.0` staged-source lane and does not
auto-promote that version. P9 is queued and cannot start until P8 operational
acceptance is explicitly accepted.

## Operating Contract

The one-screen constraint is a product requirement, not an operator preference.
Routine Codex work must use `BackgroundNoScreen`: no mouse or keyboard input,
window focus, screenshots, client launch/stop, sandbox UI, or writes inside the
live client. Passive reads may consume bounded, sanitized heartbeat, log, process,
manifest, and hash evidence. Writes are confined to repo-local `runtime/` evidence.

Visual acceptance is not silently removed. UI-layout work waits for a separate
runner/VM or an explicit user-provided visual review. Live promotion remains a
separate, explicit wrapper action and never follows from background evidence.

## Phase Sequence

### P8 — BackgroundNoScreen Foundation

Objective: make routine Helper validation non-intrusive while the user plays.

State: `implementation_complete`; `operational_acceptance_blocked`. Acceptance
requires an official promotion-bound trusted pin, a fresh capability heartbeat,
and full producer/consumer parity for the no-action contract to pass together.

Deliverables:

- bounded shared parsers for the current helper session, API probe, runtime state,
  and capability heartbeat;
- deterministic passive reporter path under the client work directory;
- `BackgroundStatus` wrapper action and `ctoa.ps1 otbg` shortcut;
- inherited, non-downgradable `BackgroundNoScreen` operator mode with a positive
  action allowlist and guards around GUI/input/screenshot/start-stop/live-write
  primitives;
- sanitized `background_status.json`, release-evidence summary, and read-only
  Control Center tile;
- mutable profile drift separated from immutable package-code parity.

Done gates:

- no client process or screenshot-count change during collection;
- immutable live files match a manifest pinned by an official promotion record
  and remain unchanged during the observation; the observer never creates or
  repairs that trust anchor itself;
- readiness requires exactly one canonical live process plus an online,
  5-second heartbeat newer than that process; missing safety fields, an
  untrusted promotion pin, or cross-client evidence fail closed;
- any drift in a Lua vocation profile is reported separately but still blocks
  parity because the current profile format is executable; it cannot become a
  non-blocking data change until persistence moves to a non-executable format;
- missing, stale, malformed, oversized, symlinked, or unsafe capability evidence
  never claims readiness;
- the report is advisory-only with `promotion_allowed=false`,
  `dispatch_allowed=false`, and an empty intrusive-action ledger;
- Python, Lua, PowerShell, web, release-evidence, doc-sync, and secret-guardrail
  tests pass.

### P9 — Conditions Shadow Observation And Replay

Objective: validate only `plan_paralyze_recovery` from passive observations before
any execute-once design.

Dependencies: explicitly accepted P8 operational acceptance, including its trusted
promotion pin, fresh heartbeat, and full consumer-parity proofs; accepted Recovery
trace. P9 must not start while P8 remains `operational_acceptance_blocked`.

Deliverables: sanitized Conditions observation schema, freshness/PZ tri-state,
action-bound trace replay, deterministic positive and negative scenario pack, and
read-only Control Center evidence. Before profile drift can be accepted as data,
profile persistence must gain a non-executable, schema-validated representation.

Done gates: stale/offline/dead/PZ/wrong-condition/wrong-spell/cooldown/retry cases
fail closed; replay parity is deterministic; runtime and dispatch remain false.

### P10 — Equipment Ring-Only Shadow And Rollback Replay

Objective: validate one ring-swap plan and its rollback without touching inventory.

Dependencies: accepted action-bound P9 trace.

Deliverables: exact item/slot/container/revision snapshot, zero-retry plan, rollback
simulation, tamper detection, and negative scenario pack.

Done gates: ambiguous inventory, revision drift, missing slot, wrong IDs, missing
rollback, stale evidence, or PZ block readiness; no amulet or rotation scope.

### P11 — Heal Friend Exact-Whitelist Shadow And Replay

Objective: validate one `exura sio` decision without casting.

Dependencies: accepted P9 and P10 traces.

Deliverables: persisted whitelist revision, stable creature ID/name, real party-ID
membership, fresh HP/range/floor/visibility evidence, and deterministic replay.

Done gates: self/spoofed/changed/stale/non-party/out-of-range/PZ/cooldown cases fail
closed; whitelist mutation, ranking, multi-target healing, and dispatch remain out.

### P12 — Execute-Once Sandbox Acceptance

Objective: introduce separate, manually approved sandbox bridges in the order
Conditions, Equipment, Heal Friend.

Dependencies: complete P9-P11 shadow packs and a separate per-lane review.

Done gates for each lane: exactly one bounded action, current domain evidence,
operator confirmation, result trace, immediate KILL/disarm, zero automatic retry,
and no implication of live promotion. A lane cannot inherit another lane's approval.

### P13 — Runtime Evidence And Machine-Readable Roadmap State

Objective: make P8-P12 state replayable and drift-resistant.

Deliverables: bounded decision/result ledger, schema registry, artifact freshness and
tamper status, read-only Control Center cards, and generated `ROADMAP_STATE.json/md`.

Done gates: atomic writes, path confinement, symlink rejection, redaction, stable
schema tests, pack parity, and an audited dry-run contract. Enabling another MCP
safe-write tool requires a separate review; the P7 tool count does not grow here.

### P14 — Independent Runner And Release Automation

Objective: move visual and in-world regression work away from the user's only screen.

Deliverables: second-machine/VM runner contract, artifact-only handoff, CI schema and
replay checks, signed manifest/evidence bundle, canary/rollback evidence, and explicit
promotion approval outside plugin MCP actions.

Done gates: no operator workstation focus/input dependency, reproducible clean-runner
evidence, immutable artifact provenance, and tested rollback.

### P15 — Combat Design-Only Digital Twin

Objective: model monster-only combat risks without an attack executor.

Dependencies: P8-P14 complete and a new formal risk review.

Scope: target identity, player/NPC/PZ guards, spell/rune budgets, cooldowns, kill
switch, deterministic replay, and adversarial scenarios. `g_game.attack`, rune use,
and live dispatch remain forbidden in this phase.

### P16 — CaveBot Design-Only Digital Twin

Objective: model movement/path/retry/stuck behavior independently of Combat.

Dependencies: P15 review complete; a separate movement risk review.

Scope: route provenance, floor/PZ transitions, reachability, retry budgets, stuck
detection, and kill switch. `autoWalk` and live movement remain forbidden.

## Beyond P16

Only accepted low-risk lanes may enter an explicit live-canary program. Combat and
CaveBot require separate canaries and must never be opened by a generic static gate.
TFS/protocol indexing remains read-only until real source is supplied. Multi-client
or hosted operation starts only after provenance, tenancy, secrets, rollback, and
operator-authorization models have their own evidence-backed phase.

## Commit And Release Boundaries

1. P8 implementation ships as one reviewable background-observability bundle;
   operational acceptance remains separate and fail-closed until its three
   required proofs pass together.
2. P9, P10, and P11 remain separate commits/PRs and cannot share acceptance evidence.
3. P12 uses one bridge commit and one acceptance record per lane.
4. P13/P14 are platform work and do not smuggle runtime executors into evidence code.
5. P15/P16 remain design/replay only until new user approval and new gates exist.
