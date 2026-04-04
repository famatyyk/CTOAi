---
description: "Use when editing PowerShell ops scripts, VPS automation, SSH remoting, here-strings, environment variable resolution, or service control under scripts/ops. Covers quoting safety, helper reuse, strict-mode compatible functions, and secret-safe remote execution."
name: "Ops PowerShell Safety"
applyTo:
  - "scripts/ops/**/*.ps1"
---
# Ops PowerShell Safety

- Prefer extending existing helpers in `scripts/ops/ctoa-vps.ps1` such as `Get-RequiredEnv`, `Get-OptionalEnv`, `Invoke-SshCommand`, and `Invoke-SshScript` instead of adding ad hoc SSH command construction.
- Do not embed secrets directly into remote shell commands. Prefer environment-variable lookup and VPS-side execution patterns such as the existing `RegisterServer` flow.
- In PowerShell-to-SSH flows, avoid unescaped `$()` or `$var` in strings that will be evaluated remotely. If a double-quoted here-string must emit bash code, escape bash variables as `` `$var ``, `` `${name} ``, and `` `$(cmd) ``.
- Keep here-string closing markers at column 1. Indented `'@` or `"@` footers break parsing.
- Under strict-mode-compatible function style, put `param()` at the top of each function before variable access and avoid assigning to automatic variables such as `$Host`.
- Preserve the existing environment resolution order where established: `Process -> User -> Machine`.
- Reuse retry, timeout, and validation patterns already present in `ctoa-vps.ps1` instead of introducing parallel implementations.
- When editing VPS automation, prefer repo-supported actions and service wrappers over one-off remote inline commands.
- Keep changes minimal and operationally safe; avoid rewriting large remote script blocks unless the task requires it.
- Link to `docs/CORE_GUARDRAILS.md`, `docs/DEPLOYMENT.md`, and `docs/LOCAL_SETUP.md` for process detail instead of duplicating runbooks in code comments or instructions.