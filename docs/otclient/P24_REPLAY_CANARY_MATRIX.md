# P24.1 Helper Replay And Canary Matrix

P24.1 binds the completed P18-P23 refactor to explicit evidence levels. Static
and deterministic Lua replay remain useful, but neither can satisfy sandbox,
independent-runner, or live acceptance.

The machine-readable source is `AI/P24_REPLAY_CANARY_MATRIX.json`.

## Replay coverage

- P18: condition operators, combinators, cooldown, hysteresis, randomization,
  and safe-disabled migration.
- P19: editable ordered target, spell, rune, and stance rule models.
- P20: spell-state transitions, recast blocking, and bounded unknown fallback.
- P21: canonical profile migration and data-only vocation packs.
- P22: contained UI previews and distinct operator feedback states.
- P23: numeric Helper/Safe parity plus strict product ownership boundaries.

Every lane names both what it proves and what it does not prove. In particular,
UI previews do not prove native rendered pixels, and fixture parity does not
prove equal Safe/Helper randomization lifecycle.

## Current independent-runner state

The local P14 preflight snapshot reports an online matching Windows runner and
a previously successful signed run, but the result does not match the current
source revision. Acceptance for visual regression, in-world regression, canary
rehearsal, and rollback rehearsal is missing. The protected environment also
lacks a required reviewer and still permits admin bypass. Its correct status is
therefore `externally_verified_stale`, not ready.

The local official stage manifest is also stale against tracked Helper source.
The first proven mismatch is `mods/ctoa_otclient/ctoa_helper_hud.lua` (4071
bytes in source versus 3845 bytes in the stage manifest). The strict P14 test
correctly fails on that mismatch; it is not weakened or treated as acceptance.

## Sandbox canaries

Four canaries are specified but not executed:

1. Profile migration with zero dispatch and safe boot preserved.
2. Passive negative targeting guards for NPCs, players, and Exercise Dummies.
3. PZ/anti-spam spell-state canary with at most one allowlisted haste cast and
   a separate explicit session approval.
4. Sandbox-only package rollback with manifest hash replay.

Each canary defines preconditions, operator actions, observations, abort
conditions, and rollback. None authorizes launching, focusing, controlling, or
writing to a client in this slice. Live promotion remains a separate explicit
approval after current independent-runner and sandbox evidence exists.
