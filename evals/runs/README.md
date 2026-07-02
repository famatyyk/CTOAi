# evals/runs

This directory is the canonical drop zone for evaluation run artifacts used by
`scripts/ops/api_cost_report.py`.

Supported files:
- `*.jsonl` with one JSON object per line
- `*.json` containing either one object or an object with `records`, `results`,
  `rows`, `runs`, `evals`, or `items`

Recommended record fields:
- `case_id` or `id`
- `created_at` or `timestamp`
- `component`
- `variant` or `prompt_variant`
- `model`
- `usage.input_tokens` or `usage.prompt_tokens`
- `usage.output_tokens` or `usage.completion_tokens`
- `usage.total_tokens`
- `cost_usd`

If `cost_usd` is missing, the report will still count tokens. Dollar estimates
are produced only when an explicit pricing file is passed with `--pricing-json`.

Example:

```json
{
  "case_id": "eval-001",
  "component": "prompt-forge",
  "variant": "strict-evidence",
  "model": "example-model",
  "usage": {
    "input_tokens": 1200,
    "output_tokens": 420
  },
  "cost_usd": 0.0123,
  "created_at": "2026-06-29T08:00:00Z"
}
```

Run:

```bash
python scripts/ops/api_cost_report.py \
  --runs-dir evals/runs \
  --json-out runtime/api-cost/latest.json \
  --md-out runtime/api-cost/latest.md
```
