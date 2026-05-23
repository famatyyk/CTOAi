# Azure Activity Log Manual Validation - 2026-05-23

## Scope
Validated prompt response shape against 3 sample logs from docs/examples/azure-activity-log-samples.json.

## Result
- Sample 1 (roleAssignments/write): PASS
- Sample 2 (securityRules/delete, Failed/Forbidden): PASS
- Sample 3 (virtualMachines/delete): PASS

## Pass Criteria Checked
- timeline summary present
- operationName + status/subStatus present
- resourceId + caller + correlationId present
- high-impact/security risk called out when applicable
- facts separated from inference
- next investigation step included