# CTOAi Surface Consolidation

The project has too many parallel surfaces. The fix is not to keep adding more wrappers. The fix is to define one canonical surface per job and slowly retire or wrap the rest.

## Canonical surfaces

| Job | Keep as canonical | What happens to duplicates |
| --- | --- | --- |
| Main cockpit | `web/src/app/control-center` | Other dashboards become panels or links inside Control Center. |
| Chat | `web/src/components/ChatWindow.tsx` | Other chats reuse this component or are retired. |
| Login/auth | Web auth flow backed by API | Desktop/mobile login screens become clients of the same auth contract. |
| Windows entry point | `desktop_console` EXE | It becomes a launcher, not a separate product brain. |
| Operations commands | `ctoa.ps1` and fixed API probes | UI buttons call guarded wrappers, not ad-hoc shell snippets. |
| Backend status | `/api/control-center` and `/api/control-center/ops` | Old status widgets should read these endpoints or be deleted. |

## Current duplicates to collapse

| Duplicate family | Current problem | Target |
| --- | --- | --- |
| Consoles | Desktop console, mobile console, web dashboard, scripts and VPS runbooks overlap. | Control Center is the operator console. Desktop is only the Windows launcher. |
| Login screens | Web, desktop and mobile have separate UX. | One auth contract, one visual language, separate shells only where needed. |
| Chats | Main web chat plus future cockpit chat risk becoming separate products. | One `ChatWindow` engine reused everywhere. |
| Dashboards | Metrics/status are scattered across docs, desktop, web and VPS scripts. | One ops endpoint and one dashboard surface. |
| Docs maps | `REPO_SCHEMA.md` is the refreshed repo map; cleanup decisions live beside it. | Keep schema and cleanup map aligned as boundaries change. |

## Rule going forward

No new surface unless it replaces or wraps an old one.

If a feature needs UI, it goes into Control Center first. If Windows needs access, desktop opens Control Center. If mobile needs access, mobile should consume the same API contracts.

## Deletion policy

Do not delete old consoles immediately. First:

1. Mark the canonical replacement.
2. Move or link the missing capability into Control Center.
3. Confirm the old surface has no unique capability left.
4. Archive or delete it in a separate cleanup commit.

This avoids losing working features while still moving toward one clean product.

## Foundation cleanup map

The active foundation cleanup inventory lives in:

```text
docs/CTOAI_FOUNDATION_CLEANUP.md
```

Use that document as the decision table for `KEEP / WRAP / MERGE / ARCHIVE LATER / DELETE LATER`.

Current canonical decisions:

| Job | Canonical |
| --- | --- |
| Main operator cockpit | `web/src/app/control-center` |
| Chat engine | `web/src/components/ChatWindow.tsx` |
| Windows entry point | `desktop_console` as launcher |
| Backend/API compatibility | `mobile_console/app.py` |
| Ops status data | `web/src/app/api/control-center/*` |
| Operator command engine | `ctoa.ps1` and guarded wrappers |

`docs/REPO_SCHEMA.md` has been refreshed and is no longer treated as stale. Use it as the current repository map, with `docs/CTOAI_FOUNDATION_CLEANUP.md` as the cleanup decision table.
