# Azure Activity Log Prompt Runbook

## Purpose
Use this runbook to manually verify prompt behavior for Azure Activity Log interpretation and to execute the first automation path.

## Test Input
Use sample entries from docs/examples/azure-activity-log-samples.json.

## Expected Response Shape
For each log entry, the response should include:
1. Timeline summary (eventTimestamp and submissionTimestamp if present).
2. Operation summary (operationName, status, subStatus).
3. Scope summary (resourceId, caller, correlationId).
4. Security and impact highlight when operation is high risk (RBAC, networking, delete, Key Vault, policy).
5. Plain-language impact statement.
6. Separation of confirmed facts vs inference.
7. Next best investigation step grounded in fields present in the log.

## Example Mapping
Input:
- operationName: Microsoft.Authorization/roleAssignments/write
- status: Succeeded
- resourceId: Key Vault resource

Expected type of answer:
- Calls out RBAC change as security-sensitive.
- States that access posture may have changed.
- Recommends validating assigned principal/role scope and correlating with the same correlationId.

## Failure Criteria
Mark test as failed if response:
- skips one of required fields,
- provides high-confidence conclusions from incomplete screenshot text,
- mixes speculation with facts without labeling,
- omits next investigation step.

## Automation Execution
Run the automation script against sample payload:

```bash
python scripts/ops/azure_activity_alerts.py \
  --source-file docs/examples/azure-activity-log-samples.json \
  --source-format json \
  --routes console,jsonl \
  --output-jsonl runtime/alerts/azure-activity-alerts.jsonl \
  --min-severity warning
```

Webhook ingestion mode (stdin JSON payload):

```bash
cat azure-webhook-payload.json | python scripts/ops/azure_activity_alerts.py \
  --ingest-mode stdin \
  --routes console,webhook \
  --webhook-url "$CTOA_AZURE_ALERT_WEBHOOK_URL" \
  --min-severity warning
```

## Automation Next Steps

1. Ingest Activity Logs from Azure Monitor or Log Analytics into Event Hub or webhook endpoint.
2. Normalize payload fields to guarantee operationName, status, subStatus, resourceId, caller, correlationId.
3. Classify high-impact operations (RBAC, policy, networking, delete, Key Vault).
4. Trigger alert routing only after enrichment (context, severity, owner).
5. Route to notification channels (Teams, Discord, email) with correlationId-linked investigation links.
## Discord-Only Production Note
If your notification strategy is Discord-only:
- keep CTOA_AZURE_ALERT_WEBHOOK_URL empty,
- keep CTOA_AZURE_DISCORD_WEBHOOK_URL configured,
- run routes that include discord_webhook and skip webhook.

Quick verification:
- powershell -NoProfile -ExecutionPolicy Bypass -File scripts/ops/azure-alerts-runner.ps1 -Action sample-dry-run
