# Azure Activity Log Prompt Runbook

## Purpose
Use this runbook to manually verify that prompt behavior for Azure Activity Log interpretation is consistent.

## Test Input
Use sample entries from docs/examples/azure-activity-log-samples.json.

## Expected Response Shape
For each log entry, the response should include:
1. Timeline summary (eventTimestamp and submissionTimestamp if present).
2. Operation summary (operationName, status, subStatus).
3. Scope summary (esourceId, caller, correlationId).
4. Security/impact highlight when operation is high risk (RBAC, networking, delete, Key Vault, policy).
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
## Automation Next Steps
1. Ingest Activity Logs from Azure Monitor / Log Analytics into a stable source (Event Hub or webhook endpoint).
2. Normalize payload fields to guarantee operationName, status, subStatus, resourceId, caller, correlationId.
3. Add a classifier for high-impact operations (RBAC, policy, networking, delete, Key Vault).
4. Trigger alert pipeline only after enrichment (context, severity, owner).
5. Route to notification channels (Teams/Discord/email) with correlationId-linked investigation links.