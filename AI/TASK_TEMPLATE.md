# CTOAi Task Template

## Intake

- User request:
- Target subsystem:
- Source files:
- Runtime risk:
- Evidence required:
- Unknowns:

## Context To Load

- Always: `SYSTEM_PROMPT.md`, `PROJECT_CONTEXT.md`, `ENGINE_MEMORY.md`,
  `RULEBOOK.md`.
- API task: `API_INDEX.md`.
- Lua/OTClient task: `LUA_INDEX.md`, `OTCLIENT_INDEX.md`.
- Packet/TFS task: `PACKET_INDEX.md`, `CLASS_INDEX.md`.
- Review/debug task: `KNOWN_BUGS.md`, `TECH_DEBT.md`.

## Work Plan

1. Inspect current source and git state.
2. Identify existing pattern.
3. Make scoped changes.
4. Run targeted validation.
5. Run broader validation if shared behavior changed.
6. Report exact files changed and validation result.

## Delivery Checklist

- [ ] No secrets or runtime state committed.
- [ ] Existing config key order preserved.
- [ ] Safe boot/runtime gates preserved.
- [ ] Native OTClient APIs guarded.
- [ ] Tests or smoke path run.
- [ ] Evidence/log/screenshot included when relevant.
- [ ] Packet/TFS claims backed by source or marked pending.

## Final Response Shape

- What changed.
- Where it changed.
- Validation run.
- Remaining limitations or follow-up, only if material.
