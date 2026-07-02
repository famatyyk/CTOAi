# README Inventory

This file prevents documentation cleanup from deleting useful data. A README can
stay outside the root only when it has a clear local purpose. Otherwise it should
be consolidated through `docs/INDEX.md` or archived with a traceable move.

## Policy

1. Do not delete README files during cleanup.
2. Classify first: `keep-local`, `canonical-root`, `evidence`, `historical`, or `merge-candidate`.
3. If a README is moved later, preserve the original content in git history and leave a short replacement pointer for one cleanup cycle.
4. Root `README.md` remains the only project entry point.

## Inventory

| Path | Classification | Reason | Next action |
| --- | --- | --- | --- |
| `README.md` | canonical-root | Main project entry point. | Keep short; route to `docs/INDEX.md`. |
| `alembic/README` | keep-local | Local migration baseline note. | Keep unless Alembic docs are consolidated. |
| `agents/toolkit/README.md` | keep-local | Local editable-agent toolkit note. | Keep. |
| `agents/toolkit/ctoai_foundry_agent/README.md` | keep-local | Scaffold-specific instructions. | Keep. |
| `desktop_console/README.md` | keep-local | Desktop launcher instructions and shortcuts. | Keep while desktop remains wrapper. |
| `docs/evidence/vps-worktree-hygiene/README.md` | evidence | Evidence-folder index. | Keep as evidence context. |
| `docs/README_BOT.md` | merge-candidate | Long bot technical doc outside bot folder. | Later move or split into bot-local README plus docs history. |
| `evals/README-azure-agent-eval-dataset.md` | keep-local | Eval dataset contract. | Keep near eval assets. |
| `evals/runs/README.md` | keep-local | Eval run artifact guidance. | Keep. |
| `runner/hybrid_bot/README.md` | merge-candidate | Large subsystem doc for hybrid bot. | Keep for now; later align with current product scope. |
| `scripts/lua/otclient/README.md` | merge-candidate | OTClient module doc for a specialized track. | Keep for now; later classify active vs historical. |

## Cleanup Rule

When reducing docs, update this inventory first. A README can be removed from an
active surface only after its classification and replacement path are explicit.
