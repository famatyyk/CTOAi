# B2 Phase-1 Extraction Execution

Tracker: #135
Date: 2026-05-31
Branch: feat/b2-studio-extraction-phase1
Status: IN_PROGRESS

## Extracted Studio Paths

1. archived/
2. labs/
3. backups/

## Companion Updates Included

1. Removed Studio-bound scripts:
- scripts/ops/lab003_validate_bundle.ps1
- scripts/ops/lab003_watcher_timer.ps1

2. Removed Studio-bound tests:
- tests/test_intel_news_api.py
- tests/test_intel_news_scraper.py
- tests/test_intel_news_watcher.py

3. Updated Core compatibility checks:
- scripts/ops/bridge_replacement_readiness.py no longer allowlists archived/runtime/agents_legacy.py
- .github/workflows/ctoa-pipeline.yml backup-archive deny guard now checks backups/** for tar.gz/sql.gz

## Validation Plan

1. Run targeted policy/helper checks.
2. Run smoke regression for response guardrail tests.
3. Run repo hygiene audit.

## Notes

Extraction-to-new-repo copy step for ctoa-studio is tracked operationally in issue #135; this PR removes Studio phase-1 surfaces from Core and keeps Core CI/policy checks coherent.
