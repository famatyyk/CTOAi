# P9 Conditions Shadow Operator Acceptance

Status: data-only acceptance boundary implemented; current operational acceptance
remains dependent on a fresh trusted P8 proof, a real guarded Conditions
observation, and current hash-bound Recovery evidence.

## Boundary

`scripts/ops/otclient_conditions_shadow_acceptance.py` closes the evidence-type
gap between the P9 shadow report and any later predecessor review. It does not
start P10, create an Equipment plan, dispatch an action, write to OTClient, or
claim runtime readiness.

The tool rereads the P9 report and all source documents, rebuilds the report at
its recorded timestamp, verifies canonical hash parity, enforces a 30-second
freshness window, rejects fixture operational inputs, and validates the full
no-action scenario pack. Its default invocation is a read-only preflight:

```powershell
python scripts/ops/otclient_conditions_shadow_acceptance.py
```

A preflight prints either `blocked` or `ready_for_operator_review` and never
writes an accepted receipt. Even with the confirmation present, `--no-write`
cannot produce `accepted`:

```powershell
python scripts/ops/otclient_conditions_shadow_acceptance.py `
  --confirm "accept P9 conditions shadow" `
  --no-write
```

Only a fully operational, fresh, exactly recomputed report plus this exact
case-sensitive confirmation may atomically write
`runtime/solteria_helper_dev/conditions_shadow_acceptance.json`:

```powershell
python scripts/ops/otclient_conditions_shadow_acceptance.py `
  --confirm "accept P9 conditions shadow"
```

Immediately before writing, the tool rereads every physical input and rejects
any fingerprint change. The writer boundary performs this current-evidence
revalidation itself; it cannot persist a caller-supplied receipt dictionary.
Persistence also requires the canonical repo profile,
scenario pack, runtime P9 report, raw `background_status.json`, and runtime
Recovery paths; alternate fixture or explicit-observation paths cannot be used
to create an accepted receipt. The persisted receipt remains data-only:
`runtime_readiness_claimed=false`; dispatch, runtime, execution, execute-once,
and promotion flags are false; the intrusive-action ledger is empty. Its
`downstream_use_requires_separate_review=true` field prevents the receipt from
being treated as automatic permission for P10 or any runtime bridge.

## Fail-Closed Cases

- missing, malformed, duplicate-key, oversized, symlinked, or non-object report;
- report/source recomputation mismatch or input change before write;
- future or older-than-30-seconds report;
- blocked operational trace, failed scenario pack, or unsafe action field;
- fixture observation, P8 proof, Recovery trace, or Recovery proof;
- absent confirmation for persistence or any non-exact confirmation value.

The schema is `schemas/conditions-shadow-acceptance.schema.json`. P10 stays
blocked until the real P9 evidence is independently reviewed; this receipt does
not alter Lua, Helper runtime policy, Equipment, Control Center, or live files.
