## P8 BackgroundNoScreen

### Outcome

- Implementation status: `implementation_complete`
- Operational acceptance: `blocked_pending_promotion_bound_proof`
- This PR does not create, repair, or rebind a trusted promotion pin.

### Boundary

- [ ] Contains only P8 core paths and P8-specific hunks from shared integration files.
- [ ] Excludes P9/P10/P11, CTOA Safe, live promotion, and runtime artifacts.
- [ ] Keeps dispatch, promotion, and live-client actions disabled.

### Evidence

- [ ] P8 targeted Python tests passed.
- [ ] Control Center tests passed and expose read-only evidence only.
- [ ] Full non-e2e Python suite passed.
- [ ] Web lint/tests passed.
- [ ] Engine Brain doc-sync and secret guardrail passed.

Commands and results:

```text
Record exact commands, pass/skip counts, and any expected blocked status here.
```

### Review notes

Describe trusted-pin classification, current blockers, and why no operational
acceptance is claimed.
