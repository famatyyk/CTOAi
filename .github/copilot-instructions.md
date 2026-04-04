# CTOAi Workspace Instructions

## Scope
These instructions apply to all work in this repository.

## Architecture Defaults
- Treat the project as four coordinated layers: agent definitions, prompt/scoring engine, runner orchestration, and governance policy.
- Keep boundaries clear:
  - agent model and capabilities: `agents/`
  - prompt templates and tool scoring: `prompts/`, `scoring/`
  - orchestration runtime: `runner/`
  - release and approval policy: `policies/`, `workflows/`
- Preserve BRAVE(R)-driven structure when editing agent execution logic.

## Canonical Commands
- Use the workspace tasks in `.vscode/tasks.json` as first choice.
- Core local loop:
  - `CTOA: Bootstrap Product Config`
  - `CTOA: Check Update Gate`
  - `CTOA: Run All Tests`
  - sprint-specific `CTOA: Sprint-XXX Validate ...`
  - `CTOA: Launch Pack`
- Default test command is `.venv/Scripts/python.exe -m pytest tests/ --ignore=tests/e2e -v`.

## Coding Conventions
- Keep changes minimal and scoped; do not refactor unrelated modules.
- Prefer deterministic, auditable outputs for runner and governance changes.
- Preserve status/gate semantics in orchestration flows (`NEW -> IN_PROGRESS -> IN_QA -> IN_CI_GATE -> WAITING_APPROVAL -> RELEASED|BLOCKED`).
- Use atomic write patterns for runtime state files where already established.

## CI And Core Integrity
- `core/` guardrails are mandatory for protected assets.
- If protected files change intentionally, update manifest with `python scripts/ops/core_guard.py --update` in the same change set.
- For verification or pre-PR checks, run `python scripts/ops/core_guard.py --check`.

## Operational Pitfalls
- In PowerShell+SSH flows, avoid unescaped `$` interpolation in remote commands; use existing scripts in `scripts/ops/ctoa-vps.ps1` when possible.
- Keep secrets in environment variables or local `.env` files, never in committed source.
- Treat `runtime/` as transient evidence/state unless specific artifacts are intentionally versioned.

## Link, Do Not Embed
- For detailed procedures, link to canonical docs instead of duplicating content:
  - `README.md`
  - `docs/ARCHITECTURE.md`
  - `docs/LOCAL_SETUP.md`
  - `docs/DEPLOYMENT.md`
  - `docs/SPRINT_GOVERNANCE.md`
  - `docs/CORE_GUARDRAILS.md`
  - `docs/REPO_HYGIENE_POLICY.md`
  - `docs/MOBILE_CONSOLE.md`

## Agent Response Rules
- Keep responses concise, direct, and implementation-oriented.
- Do not expose internal reasoning.
- When correcting output, correct once and proceed.
