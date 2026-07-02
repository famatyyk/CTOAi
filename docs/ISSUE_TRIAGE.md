# CTOAi Issue Triage

## Done
- Monitoring alerts `#147`, `#148`, `#150`, `#151`, and `#171` are closed.
- Git is now available in PATH on this machine.

## PR 1: Control Center, evidence, and VPS parity
Focus on the active coupled lane first.

- `#12` CTOA
- `#39` CTOA-138: Dashboard SLO timeline stabilization pass
- `#65` CTOA-205: Sprint-041 Link-check i governance gate w CI

Goal:
- Keep Control Center as the canonical operator cockpit.
- Keep evidence/reporting and VPS config aligned with the shared `CTOA_*` surface.
- Close the remaining governance and timeline rough edges around the cockpit.

## PR 2: Observability and failure recovery
Make the system easier to trust before adding more feature depth.

- `#21` Error recovery and crash detection
- `#22` Telemetry and performance reporting
- `#15` Auto-heal decision module

Goal:
- Add the missing runtime signals.
- Make failures visible and actionable.
- Stabilize recovery loops before expanding more automation.

## PR 3: Tibia/Lua feature pack
Treat this as a separate product lane.

- `#13` Lua logger for Tibia events
- `#14` Lua pathing helper for OpenTibia
- `#16` Potion and supply manager
- `#17` Target prioritization engine
- `#18` Combat action sequencer
- `#19` Loot and farming optimizer
- `#20` Player detection and avoidance
- `#26` [CTOA-001] Lua logger for Tibia events
- `#27` [CTOA-002] Lua pathing helper for OpenTibia
- `#28` [CTOA-003] Auto-heal decision module

Goal:
- Batch the old gameplay work into one coherent package.
- Avoid mixing it with Control Center / evidence / VPS work.

## Ordering
1. PR 1
2. PR 2
3. PR 3

## Notes
- `#12` looks like an umbrella status issue rather than a code task.
- The old alert issues are operationally closed and should not block the feature backlog.
