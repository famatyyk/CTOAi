# P11 Heal Friend Shadow Replay

## Scope

P11 validates one `exura sio` shadow decision for exactly one allowlisted party
member. Its regression pack remains fixture-only and data-only; the completed
operational lane adds a guarded passive sandbox producer, ignored local
exact-target profile, deterministic operational replay, and a separately
confirmed receipt. Neither lane casts, talks, dispatches, or claims runtime
readiness.

## Fixed inputs and binding

- `positive-profile.json` permits one stable creature ID and canonical name.
- `positive-observation.json` supplies bounded party, HP, distance, floor,
  visibility, PZ, freshness, and cooldown facts.
- The replay constructs complete contract-valid synthetic P9 and P10 reports and
  accepted receipts in memory, then verifies every canonical SHA-256 relationship.
- Inputs are fixed tracked regular files; reparse ancestors, duplicate JSON keys,
  NaN, excessive depth, unexpected fields, and path overrides fail closed.

## Exact-target policy

The Helper exposes `HealFriend.scanExactTarget(config, ctx)` as a passive future
producer boundary. It accepts one whitelist entry only, requires the configured
stable ID and normalized name to match the same visible party creature, checks
same-floor, range, HP and line-of-sight, and rejects ambiguous duplicates. It
performs no ranking, fallback, multi-target selection, casting, talking, or
state mutation. These read-only predicates adapt the reviewed Vithrax/vBot
spectator/Sio pattern, while deliberately excluding its macro and action paths.

## Evidence and status

Run:

```powershell
.\.venv\Scripts\python.exe scripts\ops\otclient_heal_friend_shadow_replay.py --no-write
```

The 55-case scenario pack covers identity, party membership, freshness, range,
floor, visibility, PZ, cooldown, HP, whitelist, action, predecessor, receipt,
hash, provenance, and deterministic blocker-order failures. A passing fixture
report sets `fixture_only=true`, `operational_acceptance_status=not_evaluated`,
and keeps all action/readiness/promotion flags false.

## Operational acceptance evidence

Operational P11 completed on 2026-07-15 against accepted, hash-bound P9 and P10
evidence. The sandbox adapter observed exact target `268435471 / amir to moja
dziwka` and excluded local player `268435472 / el cvvel` as self. A positive
sample at `53%` HP and distance `0` produced `would_plan_sio` with zero blockers.
The canonical report SHA-256 is
`b6d5f8e53c7e7354445ab9b134b4b04a7bda984df93c477ed2cbb2a57d575ed8`.

The exact `accept P11 heal friend shadow` confirmation persisted receipt
`heal-friend-shadow-acceptance-82535ea97fd19483`; its acceptance-basis SHA-256
is `82535ea97fd19483f704451972f21cc56405c82cc0749f26724bce51cd774358`.
The receipt explicitly requires a separate downstream review and keeps runtime,
dispatch, execute-once, promotion, cast, talk, and intrusive-action fields
false/empty. It grants no P12 action authority.
