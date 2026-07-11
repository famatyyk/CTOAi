# P9 Conditions Shadow Observation And Replay

Implementation status: `offline_implementation_complete`. Operational acceptance:
`operational_acceptance_blocked`; blocker reason:
`blocked_by_p8_operational_acceptance`.

## Purpose

P9 validates only `plan_paralyze_recovery` from passive, sanitized evidence. It
does not cast, dispatch, arm runtime, execute once, promote a package, or touch a
client window. The product is a deterministic offline replay lane fed by the
existing P8 heartbeat.

P9 operational acceptance requires one jointly accepted P8 proof set:

1. an official promotion-bound trusted manifest pin;
2. one canonical process with a fresh online capability heartbeat newer than
   that process;
3. full producer/consumer parity for the BackgroundNoScreen no-action contract.

Offline/staging implementation is allowed while that proof is blocked because
the complete lane is data-only, deterministic, and no-action. It must not be
represented as P9 runtime readiness or operational acceptance.

## Data Flow

```text
guarded OTClient adapter
  -> optional Conditions observation in the P8 heartbeat
  -> bounded headless validation and sanitization
  -> deterministic replay with a data-only JSON profile
  -> conditions_shadow_replay.json
  -> read-only Release Evidence and Control Center summaries
```

The existing 5-second heartbeat remains the only client-side producer loop. A
missing Conditions observation blocks P9 only and remains compatible with the
currently protected `v2.2.1` live client.

## Data-Only Profile

Canonical path: `config/otclient/conditions-shadow-profile.json`.

Canonical schema: `ctoa.conditions-shadow-profile.v1`, JSON Schema draft
2020-12, with `additionalProperties=false` at every object boundary.

Required fixed safety values:

```json
{
  "schema_version": "ctoa.conditions-shadow-profile.v1",
  "mode": "shadow_only",
  "action": "plan_paralyze_recovery",
  "condition": "paralyze",
  "spell": "exura",
  "max_observation_age_ms": 6000,
  "cooldown_required": "ready",
  "retry_budget": 0,
  "requires_p8_ready": true,
  "requires_recovery_trace": true,
  "dispatch_allowed": false,
  "runtime_actions": false,
  "executes_plan": false,
  "execute_once_allowed": false,
  "promotion_allowed": false
}
```

This profile is consumed only by the offline P9 replay tool. Lua, `dofile`, the
client UI, autosave, and runtime dispatch must never load it. It does not migrate
the existing vocation profiles; their executable-Lua drift remains blocking.

## Sanitized Observation

Schema `ctoa.conditions-observation.v1` contains only:

- observation timestamp and bounded observation ID;
- `online|offline|unknown`;
- `alive|dead|unknown`;
- protection-zone tri-state `outside|inside|unknown` plus an allowlisted source;
- fixed condition ID `paralyze` and state `present|absent|unknown`;
- cooldown `ready|active|unknown` plus an allowlisted source;
- producer source `otclient_guarded_adapter|fixture`;
- explicit false action, dispatch, execute-once, and promotion flags.

Names, creature IDs, coordinates, raw state bitmasks, log lines, local paths, and
arbitrary strings are forbidden.

## Deterministic Replay Trace

Schema `ctoa.conditions-shadow-trace.v1` binds:

- the exact action, condition, and spell;
- SHA-256 of the profile, observation, accepted P8 status, and Recovery trace;
- evaluation timestamp and derived observation age;
- stable, allowlisted blockers in canonical order;
- canonical input and decision SHA-256 values;
- `operator_review_required=true`;
- `dispatch_allowed=false`, `runtime_actions=false`,
  `execute_once_allowed=false`, and `promotion_allowed=false`;
- an empty intrusive-action ledger.

Two replays of identical canonical inputs must produce the same decision hash.
A normal observation without paralyze is a valid blocked decision, not a tool
failure.

## Scenario Pack

The deterministic pack must include one positive shadow decision and negative
cases for:

- missing, blocked, or stale P8 evidence;
- missing, malformed, or hash-mismatched Recovery evidence;
- stale or future observation;
- offline, dead, or unknown player state;
- protection zone `inside` and `unknown`;
- condition absent, unknown, or wrong;
- action or spell mismatch;
- cooldown active or unknown;
- non-zero retry budget;
- malformed, future-version, oversized, symlinked, or extra-field profile.

Every case runs twice and asserts trace parity. Runtime and dispatch flags must
remain false in every result.

## Implemented Offline Slices

1. Strict profile, observation, trace, and report schemas plus fixtures.
2. Passive Conditions observation added to the existing heartbeat through a
   guarded adapter; no new loop and no action API.
3. Bounded P8 sanitizer support for the optional observation.
4. Recovery predecessor trace with version and hash binding.
5. Offline replay tool with path confinement, size limits, symlink rejection,
   atomic repo-local evidence writes, and deterministic hashes.
6. Read-only Release Evidence and Control Center consumers with full mutation
   tests.
7. Documentation, Engine Brain refresh, and separate P9 review commit.

The first six slices are implemented in staging. `ctoa.ps1 otp9` first refreshes
the bounded P8 artifact through the existing `BackgroundStatus` allowlist and
then runs the repo-local replay tool. The fixture pack can pass independently,
but a real trace remains `operational_acceptance_blocked` when P8, the optional
Conditions observation, or the hash-bound Recovery predecessor is missing,
stale, or unaccepted. No live promotion is implied.

## P9 Done Gate

P9 may be marked accepted only when a real, current observation produces an
action-bound trace under an accepted P8 proof set and accepted Recovery trace;
the entire positive/negative pack is deterministic; consumers fail closed; and
all execution, dispatch, promotion, and intrusive-action fields remain false.

P10 remains blocked until that trace is reviewed and explicitly accepted.
