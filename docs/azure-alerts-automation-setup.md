# Azure Alerts Automation Setup

## Goal
Enable end-to-end automation for Azure Activity Log alerts:
1. source ingestion,
2. normalization,
3. high-impact classification,
4. routing.

## Local Environment
Create .ctoa-local/azure-alerts.env (copy from .ctoa-local/azure-alerts.env.example) and set:
- CTOA_AZURE_ALERT_WEBHOOK_URL (generic webhook route)
- CTOA_AZURE_DISCORD_WEBHOOK_URL (Discord-native route)
- CTOA_AZURE_INGEST_SECRET (optional)

## Task Entry Points
Use VS Code tasks:
- CTOA: Azure Alerts Pipeline (sample dry-run)
- CTOA: Azure Alerts Pipeline (file source)
- CTOA: Azure Alerts Webhook Listener
- CTOA: Azure Alerts Pipeline (poll 60s)

## Source Integration Options
1. Event Hub route:
- Deliver Event Hub capture/output to runtime/ingest/azure-activity-log.json
- Run task CTOA: Azure Alerts Pipeline (file source)

2. Webhook route:
- Start CTOA: Azure Alerts Webhook Listener
- Configure Azure Monitor Action Group webhook URL to:
  http://<host>:8791/azure/activity
- If secret is set, include X-Webhook-Secret header in sender path/proxy.

## Routing Modes
- webhook: sends full alert JSON payload to CTOA_AZURE_ALERT_WEBHOOK_URL
- discord_webhook: sends Discord-compatible payload (content + embeds) to CTOA_AZURE_DISCORD_WEBHOOK_URL

## Output Artifacts
- runtime/alerts/azure-activity-alerts.jsonl

## Safety Notes
- Keep secrets outside git-tracked files.
- Use min-severity warning or critical in production to reduce noise.

## Automatic Env Loading
Azure alert tasks now run through scripts/ops/azure-alerts-runner.ps1, which auto-loads .ctoa-local/azure-alerts.env for each run.
