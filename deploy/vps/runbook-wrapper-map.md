# CTOA Root Wrapper Map

This file maps approved root wrapper actions to CTOA VPS automation calls.

## Scope

- Phase: Sprint-042 / CTOA-210 least-privilege hardening
- Goal: remove generic `sudo bash -s` from default execution path

## Wrapper Command

- Installed path on VPS: `/opt/ctoa/scripts/ops/ctoa-root-action.sh`
- Allowed via sudoers: `ctoa-admin ALL=(root) NOPASSWD: /opt/ctoa/scripts/ops/ctoa-root-action.sh *`

## Action Map

| Wrapper action | Used by ctoa-vps action | Purpose |
|---|---|---|
| `validate-services` | `ValidateServices` | Start/check runner+report services and tail recent runner log |
| `inspect-report-env` | `InspectReportEnv` | Verify PAT presence mask and restart/check report service |
| `healthcheck-one-shot` | `HealthCheckOneShot` | Full one-shot service+dashboard+secret sanity validation |

## Operational Notes

- Default privileged path should use wrapper actions only.
- Legacy inline root shell mode is gated behind env var `CTOA_VPS_ALLOW_LEGACY_ROOT_BASH=1` for emergency fallback.
- Any new privileged operation must be added as an explicit wrapper action and documented here.
