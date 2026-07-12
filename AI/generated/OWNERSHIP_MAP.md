# Engine Brain Ownership Map

Generated at: `2026-07-12T00:19:26+00:00`
Source audit: `runtime\audits\ctoai-full-workspace-audit.json`
Status: `ready`

| Path | Owner | Validation gate | Files | Categories |
|---|---|---|---:|---|
| `.ctoa-local` | Local/uncategorized | `manual review` | 9 | runtime_or_local_state:9 |
| `.devcontainer` | Local/uncategorized | `manual review` | 2 | tracked_source:2 |
| `.dockerignore` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `.env.example` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `.foundry` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `.git` | Local/uncategorized | `manual review` | 371 | git_internal:371 |
| `.gitattributes` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `.github` | Local/uncategorized | `manual review` | 41 | tracked_source:41 |
| `.gitignore` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `.gitmodules` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `.luarc.json` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `.pre-commit-config.yaml` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `.pytest_cache` | Local/uncategorized | `manual review` | 5 | vendor_or_cache:5 |
| `.ruff_cache` | Local/uncategorized | `manual review` | 39 | untracked_local:39 |
| `.tmp` | Local/uncategorized | `manual review` | 105 | runtime_or_local_state:105 |
| `.venv` | Local/uncategorized | `manual review` | 4543 | vendor_or_cache:4543 |
| `.vscode` | Local/uncategorized | `manual review` | 4 | tracked_source:4 |
| `AGENTS.md` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `AI` | Engine Brain | `brain refresh; brain pack` | 46 | tracked_source:46 |
| `CHANGELOG.md` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `Dockerfile` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `Dockerfile.api` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `Dockerfile.bot` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `README.md` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `__pycache__` | Local/uncategorized | `manual review` | 4 | vendor_or_cache:4 |
| `_local_archive` | Local/uncategorized | `manual review` | 111 | runtime_or_local_state:111 |
| `agent.yaml` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `agents` | Agent governance | `pytest tests/ --ignore=tests/e2e` | 32 | tracked_source:30, untracked_source_candidate:2 |
| `alembic` | Local/uncategorized | `manual review` | 6 | tracked_source:4, untracked_local:2 |
| `alembic.ini` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `api` | API runtime | `pytest tests/ --ignore=tests/e2e` | 9 | tracked_source:3, untracked_source_candidate:6 |
| `bot` | Bot runtime | `pytest tests/ --ignore=tests/e2e` | 144 | tracked_source:43, untracked_source_candidate:101 |
| `config` | Local/uncategorized | `manual review` | 7 | local_secret_or_sensitive:1, tracked_source:6 |
| `conftest.py` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `core` | Local/uncategorized | `manual review` | 3 | tracked_source:3 |
| `ctoa-vps.ps1` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `ctoa.ps1` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `ctoa_local.log` | Local/uncategorized | `manual review` | 1 | untracked_local:1 |
| `ctoa_ui_prefs.lua` | Local/uncategorized | `manual review` | 1 | untracked_local:1 |
| `data` | Local/uncategorized | `manual review` | 5 | runtime_or_local_state:5 |
| `deploy` | VPS/deploy | `engine_brain_doctor; deployment smoke` | 43 | tracked_source:43 |
| `desktop_console` | Local/uncategorized | `manual review` | 16 | tracked_source:6, untracked_source_candidate:10 |
| `docker` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `docker-compose.yml` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `docs` | Documentation | `doc sync guard` | 317 | tracked_source:311, untracked_source_candidate:6 |
| `evals` | Local/uncategorized | `manual review` | 6 | tracked_source:6 |
| `logs` | Local/uncategorized | `manual review` | 3 | runtime_or_local_state:3 |
| `metrics` | Local/uncategorized | `manual review` | 24 | runtime_or_local_state:24 |
| `mobile_console` | Mobile console | `pytest tests/ --ignore=tests/e2e` | 20 | tracked_source:9, untracked_source_candidate:11 |
| `node_modules` | Local/uncategorized | `manual review` | 1 | vendor_or_cache:1 |
| `policies` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `product` | Local/uncategorized | `manual review` | 4 | tracked_source:4 |
| `prompts` | Local/uncategorized | `manual review` | 6 | tracked_source:4, untracked_source_candidate:2 |
| `releases` | Release evidence | `release_evidence_pack.py` | 36 | tracked_source:36 |
| `requirements-bot.txt` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `requirements-dev.txt` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `requirements.txt` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `runner` | Runner runtime | `pytest tests/ --ignore=tests/e2e` | 154 | tracked_source:57, untracked_source_candidate:97 |
| `runtime` | Local/uncategorized | `manual review` | 2482 | runtime_or_local_state:2482 |
| `runtime_context.py` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `schemas` | Contracts | `schema consumers and pytest` | 15 | tracked_source:15 |
| `scoring` | Local/uncategorized | `manual review` | 5 | tracked_source:3, untracked_source_candidate:2 |
| `scripts` | Operator automation | `pytest targeted script tests` | 451 | tracked_source:270, untracked_source_candidate:181 |
| `src` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `tests` | Regression suite | `pytest tests/ --ignore=tests/e2e` | 532 | local_secret_or_sensitive:2, tracked_source:197, untracked_source_candidate:333 |
| `training` | Local/uncategorized | `manual review` | 8 | tracked_source:5, untracked_source_candidate:3 |
| `up` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `web` | Control Center | `cd web; npm run lint; npm test` | 32304 | local_secret_or_sensitive:2, tracked_source:98, untracked_source_candidate:5419, vendor_or_cache:26785 |
| `workflows` | Sprint workflows | `sprint validators` | 89 | tracked_source:89 |
