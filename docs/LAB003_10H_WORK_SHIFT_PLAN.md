# LAB-003 10h Work Shift Plan

## Objective
Keep Intel LAB pipeline healthy for the next 10 hours with repeated end-to-end checks through main mobile_console endpoint.

## Start Time
2026-05-21 20:56:04 +02:00

## Scope
- Watcher tick health and diff generation
- Mobile proxy endpoint health for status/state/diff
- Shift logs for audit and post-shift review

## Timeline (10h)
1. H+0 (now): Run bundled validation once and confirm green.
2. H+0 to H+10: Run automated guard every 30 minutes.
3. H+1, H+3, H+5, H+7, H+9: Quick log spot-check for failures.
4. H+10: Review summary, check failures count, and decide follow-up.

## Execution Commands
1. Immediate bundle check:
   powershell -NoProfile -ExecutionPolicy Bypass -File scripts/ops/lab003_validate_bundle.ps1 -BaseUrl http://127.0.0.1:8787
2. 10h shift guard:
   powershell -NoProfile -ExecutionPolicy Bypass -File scripts/ops/lab003_shift_guard.ps1 -DurationHours 10 -IntervalMinutes 30 -BaseUrl http://127.0.0.1:8787
3. Log tail:
   Get-Content "C:\Users\zycie\AppData\Local\CTOA\logs\lab003-shift-guard.log" -Tail 80

## Success Criteria
- No failed iterations in shift guard summary
- Endpoint checks keep returning ok=true and status=200
- Watcher digest checks continue without runtime errors

## Escalation Criteria
- Any iteration with non-zero exit code
- Endpoint error contains connection refused or timeout
- Missing state/diff file flags in proxy responses

## Artifacts
- scripts/ops/lab003_validate_bundle.ps1
- scripts/ops/lab003_shift_guard.ps1
- .vscode/tasks.json tasks for bundle and 10h guard
- %LOCALAPPDATA%\CTOA\logs\lab003-shift-guard.log

## Webhook Alert Setup
- Optional webhook URL can be provided by environment variable CTOA_LAB003_ALERT_WEBHOOK_URL or by script parameter AlertWebhookUrl.
- Default behavior sends alert only on the first failed iteration.
- Use AlertOnEveryFailure switch to send webhook on each failed iteration.

Example:
$env:CTOA_LAB003_ALERT_WEBHOOK_URL = "https://example-webhook-url"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/ops/lab003_shift_guard.ps1 -DurationHours 10 -IntervalMinutes 30 -BaseUrl http://127.0.0.1:8787
