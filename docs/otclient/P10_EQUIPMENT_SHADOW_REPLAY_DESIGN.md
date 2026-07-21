# P10 Equipment Shadow Replay

## Scope

P10 validates one exact ring replacement and rollback plan without moving or
using an item. The snapshot producer consumes only the sanitized passive
`BackgroundNoScreen` equipment observation and a fixed operator profile path.
Replay, acceptance, Release Evidence, and Control Center remain data-only.

## Operational time and paths

- Operational replay always evaluates with the current wall clock. The CLI
  rejects `--evaluated-at-unix-ms` in operational mode so stale observations
  cannot be made fresh by backdating the report.
- Profile, snapshot, P9 report/receipt, scenario pack, and output use fixed
  canonical confined paths. Fixture mode is `--no-write` only.
- The tracked profile template contains zero IDs. Real IDs may exist only in the
  fixed ignored `.ctoa-local` override and are never copied into docs or evidence.

## Passive equipment observation preview

Before an operator configures the ignored capture profile, the bounded preview
command can render the ring and candidate container/slot identities already
sanitized by the canonical `background_status.json` producer:

```powershell
.\.venv\Scripts\python.exe scripts\ops\otclient_equipment_observation_preview.py --no-write --allow-blocked
```

The command reads only the fixed
`runtime/solteria_helper_dev/background_status.json` path. Its optional
repo-local output is
`runtime/solteria_helper_dev/equipment_observation_preview.json`, validated by
`schemas/equipment-observation-preview.schema.json`. The projection contains
only bounded ring, item, container, slot, count, cooldown, freshness, and
provenance fields; it never copies identifiers into the local profile.

`preview_ready` means the background contract, adapter provenance, freshness,
online/life/PZ state, inventory completeness, and cooldown checks all passed.
Otherwise the report is `blocked`, but a structurally valid stale or
untrusted observation may remain visible for manual configuration with an
explicit blocker. All dispatch, runtime, execute-once, promotion, and
intrusive-action fields remain false/empty. The preview command has no client
launch, focus, input, screenshot, or live-client write path.

## Deterministic candidate catalog

After preview generation, the catalog command groups exact
`item_id/container_id/slot_index/count` tuples without selecting a candidate:

```powershell
.\\ctoa.ps1 otp10catalog
```

It reads only the fixed preview artifact and writes
`runtime/solteria_helper_dev/equipment_candidate_catalog.json`. Exact duplicate
tuples, conflicting occupants of one position, repeated item IDs at different
positions, and zero identifiers are explicit blockers. Groups are sorted and
carry occurrence counts and classification flags; `selection_policy` is
`none` and `recommendation` is always `null`. The catalog binds the complete
preview document SHA-256 and keeps every action, execution, promotion, and
intrusive-action field false/empty.

## Data-only capture-profile change plan

`otp10plan` reads only the fixed current capture doctor and observation preview.
With no identifiers it writes an explanatory `blocked` report. A plan is
generated only when all four explicit values match the current preview exactly
and the exact planning confirmation is supplied:

```powershell
.\ctoa.ps1 otp10plan
.\ctoa.ps1 otp10plan 3051 3048 2 1 "plan P10 capture profile change"
```

The generator validates positive bounded IDs, distinct equipped/candidate item
IDs, the equipped ring ID, and one exact candidate item/container/slot tuple.
It binds the complete doctor and preview hashes plus the doctor's current
profile hash and the preview's observation hash. Its only output is
`runtime/solteria_helper_dev/equipment_capture_profile_change_plan.json`, under
`schemas/equipment-capture-profile-change-plan.schema.json`.

The diff carries an expected-current-profile hash and a proposed safe profile,
but is not an apply command. The generator never reads or writes `.ctoa-local`,
never controls OTClient, and always keeps acceptance, readiness, eligibility,
dispatch, execution, and promotion false. The confirmation authorizes only
generation of this review artifact; a separate future workflow would still be
required to apply or accept anything.

## Canonical P9 to P10 dependency preflight

`otp10preflight` reads only five fixed repo-local artifacts: the current P8
`background_status.json`, full P9 replay report, accepted P9 receipt, capture
profile doctor, and `equipment_observation_preview.json`. It strictly rejects
missing, malformed, duplicate-key, oversized, non-regular, reparse, stale,
fixture, unsafe, unbound, or blocked evidence. The P9 receipt must bind the full
current report and trace, the trace must bind the normalized current P8 proof,
and the preview must bind the same current BackgroundNoScreen report.

The output is fixed at
`runtime/solteria_helper_dev/equipment_dependency_preflight.json` and conforms
to `schemas/equipment-dependency-preflight.schema.json`. A `passed` result only
means the dependency chain was consistent at evaluation time. The report always
sets `eligibility_changed=false`, `eligibility_state=unchanged`, every action
and promotion flag to false, and the intrusive-action ledger to an empty list.
It neither runs `otp10` nor writes an acceptance receipt.

## Consolidated operator readiness and explanation

`otp10ready` reads the fixed capture doctor, observation preview, dependency
preflight, candidate catalog, and capture-profile change plan. It does not run
any producer. Missing artifacts therefore remain explicit fail-closed blockers.
The report separates `missing`, `invalid`, `stale`, and `upstream` states,
preserves each producer's blocker list, and maps them to ordered passive or
repo-only commands such as `otp9`, `otp10doctor`, `otp10preview`,
`otp10preflight`, `otp10catalog`, and `otp10plan`.

Its only output is
`runtime/solteria_helper_dev/equipment_operator_readiness.json`, validated by
`schemas/equipment-operator-readiness.schema.json`. Even
`operator_inputs_ready` is explanatory only: `eligibility_changed=false`, no
operational readiness is claimed, and all dispatch, execution, promotion, and
intrusive-action fields remain false or empty. The report never invokes
`otp10`, acceptance, execute-once, or live promotion.

## Fixed repo-only operator refresh

`otp10refresh` is the single no-action refresh entry point for the explanatory
P10 evidence lane. It invokes only these fixed scripts and outputs, in order:

1. capture-profile doctor,
2. passive observation preview,
3. P8/P9 dependency preflight,
4. candidate catalog,
5. capture-profile change plan without IDs or confirmation,
6. operator readiness,
7. Python/Web consumer parity.

The first six stages use `--allow-blocked`; this changes only their process exit
code and does not weaken their schemas or no-action fields. The parity stage
never receives that flag and must write a `passed`
`equipment_consumer_parity.json` with all schema, status/blocker, hash-binding,
no-action, eligibility, and consumer-contract checks true.

An orchestrator result of `passed` certifies refresh completion and consumer
parity only. It does not turn a blocked no-ID plan into
`operator_inputs_ready`, grant acceptance, or claim operational readiness; the
summary exposes that state separately.

The orchestrator accepts no path overrides, identifiers, confirmation, replay,
acceptance, execute-once, or promotion arguments. It never invokes the client,
the local-profile initializer, `otp10`, or either acceptance command. Its
sanitized stdout summary is not a durable run receipt. During the same command,
the fixed finalizer writes the hash-bound anti-mix receipt
`runtime/solteria_helper_dev/equipment_operator_refresh_run.json`; see
`P10_EQUIPMENT_OPERATOR_REFRESH_RUN.md` for begin/record/finalize and failure
cleanup rules.

## Scenario corpus

The fixed pack contains exactly 30 unique mutations. It covers ring/item/
container/slot/rollback identity, inventory revision, stale/future evidence,
online/life/PZ/cooldown tri-state and provenance, P9 blocking/tamper, retry,
unsafe flags, and nested structural tamper. Every case is evaluated twice and
must produce the same decision hash, false action flags, and an empty intrusive
action ledger.

The replay result binds `scenario_pack_sha256`. Acceptance requires 30/30,
zero failures, exact mutation coverage, a fresh non-fixture operational trace,
the full P9 report-bound receipt, and exact operator confirmation. Fixture
success never makes P11 eligible.

## Schema and consumer parity

`equipment-shadow-trace.schema.json` closes input hashes, blockers, and the
ring-only plan. `equipment-shadow-scenario-pack.schema.json` enumerates the
30 mutations. `equipment-shadow-replay-report.schema.json` references the trace
and closes every nested scenario result/case. Python acceptance, Release
Evidence, and Control Center independently enforce count, hash, mutation set,
trace-ID binding, rollback identity, and the no-action contract.

## Commands

```powershell
.\.venv\Scripts\python.exe scripts\ops\otclient_equipment_shadow_replay.py --no-write --source fixture
.\ctoa.ps1 otp10doctor
.\ctoa.ps1 otp10preview
.\ctoa.ps1 otp10catalog
.\ctoa.ps1 otp10plan
.\ctoa.ps1 otp10preflight
.\ctoa.ps1 otp10ready
.\ctoa.ps1 otp10refresh
.\ctoa.ps1 otp10
.\ctoa.ps1 otp10accept
```

`otp10doctor` is a no-action preflight for the fixed ignored capture profile.
It writes only `runtime/solteria_helper_dev/equipment_capture_profile_doctor.json`
and reports missing operator confirmation, exact IDs, invalid schema, or an
equipped/candidate identity collision without reading or controlling OTClient.
The last two commands remain blocked until P8 and P9 have current accepted
operational evidence and the operator has configured exact ring/container/slot
IDs. No P10 command grants execute-once or live item dispatch.
