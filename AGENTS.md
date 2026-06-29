# Repository Guidelines

## Project Structure & Module Organization
Core Python code lives in `runner/`, `agents/`, `api/`, `bot/`, `scoring/`, and `prompts/`. Operational scripts and one-off utilities are in `scripts/` and `scripts/ops/`; platform-specific helpers live in `scripts/windows/` and `scripts/lua/`. Documentation, sprint records, and runbooks belong in `docs/`, `workflows/`, `policies/`, `releases/`, `evals/`, and `training/`. Tests live under `tests/`, with focused unit tests in `tests/unit/` and higher-level contract or integration checks alongside them.

## Build, Test, and Development Commands
- `python scripts/ops/ctoa_product_bootstrap.py`: create or refresh local product state.
- `python scripts/ops/ctoa_update_gate.py`: verify the local toolkit is allowed to launch.
- `python -m pytest tests/ --ignore=tests/e2e -q`: run the main Python test suite.
- `python scripts/ops/sprintNN_validate.py`: run a sprint-specific validator, using the relevant sprint number.
- `pre-commit run --all-files`: run Ruff, Ruff format, mypy, Bandit, and dependency checks.
- `.\ctoa.ps1 help`: inspect the Windows operator entry points.

## Coding Style & Naming Conventions
Use 4-space indentation for Python, `snake_case` for functions and modules, `PascalCase` for classes, and `UPPER_SNAKE_CASE` for constants. Keep imports ordered, prefer type hints where the surrounding file already uses them, and let `ruff format` handle formatting. PowerShell scripts should keep `Set-StrictMode -Version Latest`, fail fast, and use descriptive `PascalCase` function names. Preserve existing YAML/JSON key order when files are treated as configuration or evidence artifacts.

## Testing Guidelines
Pytest is the primary test runner, and it also collects `unittest`-style tests. Name new test files `test_*.py` and keep assertions narrow and reproducible. When changing runtime, release, or sprint logic, run the targeted validator first and then the broader pytest suite. Prefer tests that verify file contracts, generated artifacts, and guardrail behavior over pure implementation details.

## Commit & Pull Request Guidelines
Recent history uses Conventional Commit subjects such as `chore: ...`, `fix: ...`, and `docs: ...`. Keep the subject line imperative and specific, and include sprint, issue, or PR references when useful. Pull requests should explain the change, list validation commands run, and include screenshots or evidence for UI, workflow, or report updates.

## Security & Configuration Tips
Do not commit secrets from `.env` or runtime state from `runtime/`, `logs/`, or local databases in `data/`. Update `.env.example` or the relevant template file instead. If a change affects published evidence, update the matching artifact in `releases/evidence/` or the corresponding sprint documentation.
