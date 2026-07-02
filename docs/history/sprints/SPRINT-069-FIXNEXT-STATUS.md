# Sprint-069 Final Status

## Completed
- `scripts/ops/launch_kamil_client_macro_studio.ps1` now uses repo-local `.venv\Scripts\python.exe` for profile resolution and Macro Studio startup.
- Added `-SmokeTest` to the Macro Studio launcher so repo-local Python, profile resolution, module imports, and config parsing can be checked without starting the GUI.
- Added `scripts/ops/status_overlay_smoke.ps1` for a short GUI smoke of `bot/overlay/status_overlay.py`.
- `deploy/vps/systemd/ctoa-runner.service`, `ctoa-report.service`, and `ctoa-lab-runner.service` are pinned to `/opt/ctoa/.venv/bin/python3`.
- `scripts/ops/ctoa-vps.ps1` now uses the VPS venv interpreter for publish and gs-api validation paths.
- `deploy/vps/SETUP.md` now documents that the main runtime services are venv-pinned.
- Added contract tests for the launcher and VPS Python parity: `tests/test_vps_python_parity.py`.
- `web/src/components/ControlCenterShell.tsx` now shows the live backend probe in the overview instead of leaning only on static status tiles.
- `web/src/lib/controlCenterSnapshot.ts` was neutralized so the fallback surface no longer advertises stale numeric metrics.
- Added `web/src/lib/__tests__/controlCenterSnapshot.test.ts` to keep the fallback surface live-oriented.
- `runner/hybrid_bot/command_executor.py` now treats bare batch `wait`/`pause` steps as timed waits instead of unknown commands.
- Added a unit test for batch `wait`/`pause` handling in `tests/unit/bot/test_command_executor.py`.

## Validation
- `scripts/ops/status_overlay_smoke.ps1` -> `status-overlay-smoke-ok`
- `pytest tests/test_vps_python_parity.py tests/test_release_evidence_pack.py tests/unit/test_client_profile_router.py tests/unit/bot/test_command_executor.py -q`
- `npm test -- --run src/lib/__tests__/controlCenterActions.test.ts src/lib/__tests__/controlCenterEvidence.test.ts src/lib/__tests__/controlCenterOps.test.ts src/lib/__tests__/controlCenterAuth.test.ts`
- `npm test -- --run src/lib/__tests__/controlCenterSnapshot.test.ts src/lib/__tests__/controlCenterActions.test.ts src/lib/__tests__/controlCenterEvidence.test.ts src/lib/__tests__/controlCenterOps.test.ts src/lib/__tests__/controlCenterAuth.test.ts`
- `npm run build`
- `pytest tests/unit/bot/test_command_executor.py -q`

## Notes
- `docs/history/sprints/SPRINT-069-FIXNEXT-CHANGELOG.md` was folded into the canonical sprint closure and removed as a duplicate artifact.
