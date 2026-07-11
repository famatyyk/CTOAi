# AI Folder Instructions

This folder is the curated Engine Brain for CTOAi. Keep it secret-safe and
evidence-first.

## Rules

- Do not copy `.env`, Vercel env values, GitHub tokens, auth stores, local logs,
  runtime data, database dumps, or private keys into this folder.
- Keep stable project rules separate from time-sensitive status.
- Put current operational findings in `OPERATIONS_AUDIT.md`.
- Put generated indexes under `AI/generated/`; do not hand-edit generated files
  unless the generator is also updated.
- Mark unknown TFS/protocol facts as pending source instead of inferring them.

## Refresh

From the repo root:

```powershell
.\ctoa.ps1 brain refresh
.\ctoa.ps1 brain doctor
.\ctoa.ps1 brain pack
```

This regenerates `AI/generated/FILE_TREE.md`, `AI/generated/SYMBOL_MAP.md`, and
`AI/generated/manifest.json`, then audits local operations into
`AI/generated/ENV_DOCTOR.md` and `AI/generated/ENV_DOCTOR.json`, and builds a
portable pack at `AI/generated/ENGINE_BRAIN_PACK.md`.
