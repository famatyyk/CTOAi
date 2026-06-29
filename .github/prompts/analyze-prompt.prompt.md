---
description: "Analyze a CTOAi prompt or copilot instruction file for structural completeness, BRAVE(R) alignment, canonical reference coverage, and agent-role fit. Use when authoring, reviewing, or auditing prompt files in .github/prompts/, .github/instructions/, or .github/skills/."
name: "CTOA Analyze Prompt"
argument-hint: "Path to the prompt, instruction, or skill file to analyze (e.g. .github/prompts/my-prompt.prompt.md)"
agent: "agent"
---
Analyze the provided prompt, instruction, or copilot-instruction file against the CTOAi prompt quality standard.

Use the workspace conventions in [.github/copilot-instructions.md](../copilot-instructions.md) and the canonical agent/prompt definitions in [docs/AGENT_PROMPT_DEFINITIVE.md](../../docs/AGENT_PROMPT_DEFINITIVE.md) as the evaluation baseline.

Workflow:
- Read the target file. If no path is given, analyze [.github/copilot-instructions.md](../copilot-instructions.md).
- Check structural completeness:
  - For `.prompt.md` files: YAML front matter includes `description`, `name`, `argument-hint`, and `agent`; body contains a workflow section and a return-format section; links to at least one canonical reference.
  - For `.instructions.md` files: YAML front matter includes `description`, `name`, and a valid `applyTo` glob; body states its rules concisely without duplicating content from linked docs.
  - For skill `SKILL.md` files: front matter includes `name`, `description`, `argument-hint`, and `user-invocable`; body contains When To Use, Workflow, CTOAi-Specific Rules, Output Format, and References sections.
- Check BRAVE(R) alignment: verify the file keeps phases explicit — context setup, constraint checks, action/tool execution, verification with evidence, exception handling, and end-of-step status.
- Check agent-role fit: confirm the prompt addresses an agent role defined in `docs/AGENT_PROMPT_DEFINITIVE.md` (Scout, Ingest, Brain, Generator, Validator, Publisher, Prompt Forge, Tool Advisor, Orchestrator, or Governance/Queen) or explicitly scopes to a cross-cutting concern.
- Check canonical reference coverage: confirm links to relevant docs from the "Link, Do Not Embed" list (`README.md`, `docs/ARCHITECTURE.md`, `docs/LOCAL_SETUP.md`, `docs/DEPLOYMENT.md`, `docs/SPRINT_GOVERNANCE.md`, `docs/CORE_GUARDRAILS.md`, `docs/REPO_HYGIENE_POLICY.md`, `docs/MOBILE_CONSOLE.md`) are present where the prompt touches those concerns; flag embedded duplicate content that should be a link instead.
- Check governance semantics: if the prompt touches runner, CI, or release flows, verify it references the canonical status flow (`NEW -> IN_PROGRESS -> IN_QA -> IN_CI_GATE -> WAITING_APPROVAL -> RELEASED|BLOCKED`) and defers to [runner governance instructions](../instructions/runner-governance.instructions.md).
- Do not modify any file during analysis unless the user explicitly requests fixes.

Return format:
- `Target:` file analyzed
- `Structure:` PASS or list of missing required elements
- `BRAVE(R) alignment:` PASS or specific missing phases
- `Agent-role fit:` matched role or gap description
- `Reference coverage:` PASS or missing/duplicated links
- `Governance semantics:` PASS, N/A, or specific gap
- `Recommendations:` ordered list of concrete improvements, smallest first

References:
- [.github/copilot-instructions.md](../copilot-instructions.md)
- [docs/AGENT_PROMPT_DEFINITIVE.md](../../docs/AGENT_PROMPT_DEFINITIVE.md)
- [runner governance instructions](../instructions/runner-governance.instructions.md)
- [ops PowerShell safety](../instructions/ops-powershell-safety.instructions.md)
