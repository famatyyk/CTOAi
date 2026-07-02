# Repo Cleanup Waves

This document records the cleanup wave contract for the repo surface.
It exists so local cleanup tasks have a canonical place to write execution notes
instead of pointing at ad hoc scratch files.

## Wave 2 and Wave 3 Executed

- Archive root: `_local_archive/sprint-070`
- Executed moves:
  - `training/ctoa-merged`
  - `training/ctoa-1.5b-q4km.gguf`
  - `training/kaggle-output`
  - `training/kaggle-output-final`
  - `training/kaggle-output-v24`
  - `training/kaggle-output-v25`
  - `training/kaggle-output-v26`
  - `training/kaggle-output-v3`
  - `training/kaggle-upload`
  - `training/logs-v4`
  - `training/logs-v5`
  - `training/logs-v6`
  - `training/logs-v7`
  - `artifacts/enc3`
  - `labs/projects`
  - `labs/__pycache__`
- Kept in place:
  - `bot`
  - `tools/rosetta-assembler` (`.gitmodules` submodule)
- Result:
  - `training/` keeps source-side assets only
  - `labs/` top-level payload removed
  - forensic payload removed from main repo paths

## Contract

- Cleanup tasks should write execution notes here and in the matching sprint progress doc.
- Local archive contents stay under `_local_archive/` and out of git history.
- Canonical public repo state should not depend on raw archive payloads.
