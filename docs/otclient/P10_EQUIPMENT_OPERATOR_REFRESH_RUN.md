# P10 Equipment operator refresh run envelope

`otp10refresh` is one fixed, repo-only orchestration run. Its durable receipt is:

`runtime/solteria_helper_dev/equipment_operator_refresh_run.json`

The receipt uses schema `ctoa.equipment-operator-refresh-run.v1` and is valid
only after all seven stages complete in this exact order:

1. `capture_profile_doctor`
2. `observation_preview`
3. `dependency_preflight`
4. `candidate_catalog`
5. `capture_profile_change_plan`
6. `operator_readiness`
7. `consumer_parity`

The first six receipts bind the canonical JSON SHA-256 of their P10 artifacts.
The seventh binds `equipment_consumer_parity.json`, which must be `passed` and
must bind those same six canonical hashes, statuses, and blocker lists.

## Finalizer handshake

The orchestrator uses the fixed finalizer
`scripts/ops/otclient_equipment_operator_refresh_run.py`:

```powershell
$begin = & .\.venv\Scripts\python.exe scripts\ops\otclient_equipment_operator_refresh_run.py --begin | ConvertFrom-Json
$runId = $begin.run_id

# Run each fixed producer, then bind its fixed artifact immediately.
& .\.venv\Scripts\python.exe scripts\ops\otclient_equipment_operator_refresh_run.py --record-stage capture_profile_doctor --run-id $runId
# ...the remaining stages in the order above...
& .\.venv\Scripts\python.exe scripts\ops\otclient_equipment_operator_refresh_run.py --record-stage consumer_parity --run-id $runId

& .\.venv\Scripts\python.exe scripts\ops\otclient_equipment_operator_refresh_run.py --finalize --run-id $runId
```

`otp10refresh` performs this handshake internally. The finalizer accepts no
path override, artifact override, item identifier, confirmation, acceptance,
replay, or client-control argument.

`--begin` preserves the prior completed envelope and writes the private fixed
pending journal `.equipment_operator_refresh_run.pending.json`. Each
`--record-stage` requires the same UUIDv4 and the next exact stage. `--finalize`
re-reads all seven files before writing the completed envelope and then removes
the pending journal.

If a producer, stage receipt, or finalization fails, `otp10refresh` aborts only
its own matching pending UUID. It never removes or rewrites the last completed
good envelope during failure cleanup. The equivalent explicit recovery command
is:

```powershell
& .\.venv\Scripts\python.exe scripts\ops\otclient_equipment_operator_refresh_run.py --abort --run-id $runId
```

## Anti-mix and anti-replay checks

The completed envelope is emitted only when all of these hold:

- each artifact is strict JSON, a regular non-reparse file, and valid against
  its fixed Draft 2020-12 schema;
- artifact and embedded producer timestamps do not predate `--begin` and are
  no more than 30 seconds old;
- all seven file mtimes are ordered and their maximum skew is 30 seconds;
- every recorded SHA-256, mtime, schema, status, and blocker list still matches
  when the run is finalized;
- consumer parity is fully passed and independently binds the exact six source
  hashes, statuses, blocker lists, and empty divergence lists;
- all source and envelope no-action fields remain false, eligibility remains
  unchanged, operational readiness is not claimed, and the intrusive-action
  ledger is empty.

The aggregate hash is:

```text
SHA256(canonical_json({
  run_id,
  started_at_unix_ms,
  completed_at_unix_ms,
  stage_receipts
}))
```

Canonical JSON uses sorted keys, compact separators, ASCII escaping, and rejects
non-finite numbers.

## Failure semantics

The finalizer exits `0` only for a successful begin, stage receipt, or complete
finalization. A safety or consistency failure emits a sanitized
`status=blocked` JSON object and exits `1`; CLI shape errors exit `2`.

No completed run envelope is written for an incomplete, mixed, stale, reordered,
or hash-divergent run. The orchestrator cleans its matching pending journal and
returns `status=blocked`, allowing a fresh UUID on retry while preserving the
last good completed envelope. A foreign, corrupt, or mismatched pending journal
is never reclaimed automatically; it remains fail-closed for explicit operator
inspection.

Completion proves only that the repo-only refresh artifacts belong to one
coherent run. It does not grant acceptance, change eligibility, claim runtime
readiness, execute Equipment logic, launch or control OTClient, or write a live
client file.
