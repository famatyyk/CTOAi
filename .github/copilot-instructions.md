# CTOAi Workspace Instructions

## Scope
These instructions apply to all work in this repository.
When constraints overlap, apply sections in this priority order:
1. Architecture Defaults
2. Canonical Commands
3. Coding Conventions
4. CI And Core Integrity
5. Operational Pitfalls
6. Link, Do Not Embed
7. Agent Response Rules
If instructions conflict within the same section, follow the most specific instruction.
If ambiguity remains, choose the safest reversible action and state at most one explicit assumption before proceeding.

## Architecture Defaults
- Treat the project as four coordinated layers: agent definitions, prompt/scoring engine, runner orchestration, and governance policy.
- Keep boundaries clear:
  - agent model and capabilities: `agents/`
  - prompt templates and tool scoring: `prompts/`, `scoring/`
  - orchestration runtime: `runner/`
  - release and approval policy: `policies/`, `workflows/`
- Preserve BRAVE(R)-driven structure when editing agent execution logic: keep phases explicit—Background (context setup), Role (agent persona and constraints), Action (tool execution steps), Values (decision criteria and guardrails), Examples (few-shot evidence), Result (structured output schema). See `docs/AGENT_PROMPT_DEFINITIVE.md` for canonical terminology.

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
- When the user sends `/analyze-prompt`, analyze the prompt content first, then return: objective, constraints, ambiguities, likely failure modes, and a tightened prompt rewrite.
- When a user asks for help interpreting an Azure Activity Log, first summarize: timeline, `operationName`, `status` and `subStatus`, affected `resourceId`, `caller`, and `correlationId`.
- Highlight security-sensitive or high-impact changes explicitly (for example role assignments, policy changes, deletes, networking changes, Key Vault access, or resource creation failures).
- Explain likely impact in plain language, separate confirmed facts from inference, and suggest the next best investigation step using the fields already present in the log.
- If the user shares only a partial screenshot or excerpt, ask for the raw Azure Activity Log entry (JSON or text) before making high-confidence conclusions.
