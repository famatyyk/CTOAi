## P9 Conditions Shadow

### Outcome

- Implementation status: `offline_implementation_complete`
- Operational acceptance: `blocked_by_p8_operational_acceptance`
- This PR does not authorize P10, execute-once, dispatch, or promotion.

### Boundary

- [ ] Depends on the reviewed P8 BackgroundNoScreen boundary.
- [ ] Contains only P9 core paths and P9-specific hunks from shared integration files.
- [ ] Excludes Equipment, Heal Friend, CTOA Safe, and runtime artifacts.
- [ ] Preserves the exact confirmation `accept P9 conditions shadow`.

### Evidence

- [ ] Recovery proof, replay, acceptance, consumer, and Release Evidence tests passed.
- [ ] Scenario replay is deterministic and all no-action invariants remain false.
- [ ] Full non-e2e Python suite passed.
- [ ] Web lint/tests passed.
- [ ] Engine Brain doc-sync and secret guardrail passed.

Commands and results:

```text
Record exact commands, pass/skip counts, and the expected acceptance blocker here.
```

### Review notes

Describe the canonical P8/Recovery inputs, freshness result, and why fixture or
schema success is not operational acceptance.
