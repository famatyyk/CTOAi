# Core Guardrails

This repository uses a hard core + branches model to avoid accidental file corruption.

## Core Concept

- Core files are listed in `core/protected-files.txt`.
- Their hashes are stored in `core/core-manifest.sha256`.
- CI runs `python scripts/ops/core_guard.py --check` and fails if any protected file changed without manifest update.

## Day-to-Day Flow

1. Create a branch from `main` for every change.
2. Work only in branch.
3. If you intentionally changed a core file:
   - run `python scripts/ops/core_guard.py --update`
   - commit the core file + manifest together
4. Open PR and wait for pipeline.

## Local Commands

```bash
python scripts/ops/core_guard.py --check
python scripts/ops/core_guard.py --update
```

## Safe Server Registration

To avoid PowerShell quoting problems for API calls over SSH, use:

```powershell
$env:CTOA_SERVER_URL = "https://example.org"
$env:CTOA_SERVER_NAME = "Example"
powershell -ExecutionPolicy Bypass -File scripts/ops/ctoa-vps.ps1 -Action RegisterServer
```

This action performs token lookup and API POST on the VPS side.
