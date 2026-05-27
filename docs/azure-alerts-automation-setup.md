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

## Must-Pass Smoke Suite
Use a single smoke entrypoint to validate core Azure alert flow before merge:
- Local command: python scripts/ops/smoke_must_pass.py
- CI workflow: CTOA Smoke Must Pass (.github/workflows/ctoa-smoke-must-pass.yml)

Smoke scope:
- tests/test_azure_activity_alerts.py
- sample dry-run via scripts/ops/azure_activity_alerts.py

Report artifact:
- runtime/ci-artifacts/smoke-must-pass-summary.json

## Discord-Only Production Safe Profile
Use this profile when Discord is your only notification channel.

Required local env:
- CTOA_AZURE_DISCORD_WEBHOOK_URL=<your discord webhook>

Keep empty in Discord-only mode:
- CTOA_AZURE_ALERT_WEBHOOK_URL=

Recommended routes:
- console,jsonl,discord_webhook

Validation command:
- powershell -NoProfile -ExecutionPolicy Bypass -File scripts/ops/azure-alerts-runner.ps1 -Action sample-dry-run

Expected signal:
- routed_alerts > 0
- discord_webhook delivery status = sent

## Discord-Only CI Safety Checklist
1. Run the smoke suite locally:
- python scripts/ops/smoke_must_pass.py
2. Confirm smoke artifact exists:
- runtime/ci-artifacts/smoke-must-pass-summary.json
3. Ensure CTOA_AZURE_ALERT_WEBHOOK_URL is blank in local env when generic webhook is not used.
4. Ensure CTOA_AZURE_DISCORD_WEBHOOK_URL is set in local env.
5. Keep routes in automation path aligned with Discord-only mode (no webhook route required).

## Azure AI Foundry Path For Agent Improvement
Use Azure AI Foundry when you want to improve prompts/agent workflows with evaluation loops.

Minimal execution path:
1. Define target scenarios and success criteria (quality + safety + latency).
2. Build a small evaluation dataset from real CTOA cases (including failures).
3. Run prompt variants against the same dataset.
4. Compare outcomes with quantitative metrics and qualitative review.
5. Promote only variants that improve metrics without regressions.

Practical note:
- The VS Code extension ms-toolsai.vscode-ai-remote is useful for Azure ML compute workflows, but prompt/agent quality iteration is better driven by Foundry-style eval loops and dataset-based comparison.
