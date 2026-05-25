# CTOAI Foundry Agent Scaffold

Two-stage operator agent scaffold for CTOAI:

1. Mini model triages and classifies incident risk.
2. Main model is used only when triage marks incident as complex.

This keeps cost/latency lower while preserving high-quality final responses.

## Files

- `app.py` - HTTP + CLI agent scaffold with evidence hooks
- `.env.example` - Foundry configuration template
- `requirements.txt` - local dependencies for this scaffold

## Quick Start

1. Create and activate a Python virtual environment.

1. Install dependencies:

```bash
pip install -r agents/toolkit/ctoai_foundry_agent/requirements.txt
```

1. Copy env template and fill secrets:

```bash
copy agents\toolkit\ctoai_foundry_agent\.env.example agents\toolkit\ctoai_foundry_agent\.env
```

1. Run in CLI mode:

```bash
python agents/toolkit/ctoai_foundry_agent/app.py --cli
```

1. Run as HTTP server:

```bash
python agents/toolkit/ctoai_foundry_agent/app.py --server --port 8088
```

## API Contract

POST `/invoke`

Request:

```json
{
  "title": "AKS node pool provisioning failed",
  "details": "Deployment blocked with quota error in westeurope",
  "context": {
    "subscription": "...",
    "resource_group": "..."
  }
}
```

Response:

```json
{
  "facts": ["..."],
  "inference": ["..."],
  "next_step": "...",
  "triage": {
    "severity": "high",
    "category": "quota",
    "needs_main": true,
    "reason": "..."
  },
  "used_model": "gpt-4.1"
}
```

## Evidence Hooks

Every triage/final event is appended to:

- `runtime/evidence/aitk-agent/ctoai_foundry_agent.jsonl`

Format:

- `recorded_at`
- `kind` (`triage` or `final`)
- `payload`
