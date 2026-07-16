# CTOAi Public Exposure Lockdown

Date: 2026-07-15 (Europe/Warsaw)

## Decision

CTOAi now uses a private-first source model. Canonical repositories, Git
history, operator evidence, Helper logic, and production interfaces are not a
public distribution channel. Any future external release must be a separately
reviewed, sanitized export without repository history and requires owner
approval.

## Before

- `famatyyk/CTOAi`, `famatyyk/CTOmodule`, and `famatyyk/medivia` were public.
- GitHub Pages for CTOAi was enabled and anonymously reachable.
- Three Vercel production aliases were anonymously reachable.
- Two upstream forks contained local divergent commits.
- CTOAi GitHub traffic reported 1,590 clones from 305 unique cloners in the
  available 14-day traffic window before lockdown.

## Actions Applied

- Changed the three owned, non-fork repositories above to private.
- Unpublished CTOAi GitHub Pages and disabled its remote Pages workflow.
- Removed all Vercel aliases for `ctoa-web`.
- Disabled automatic Vercel custom-domain assignment.
- Preserved Vercel deployment history and settings; remaining generated
  deployment URLs require Vercel authentication.
- Mirrored divergent fork history into private archive repositories before
  resetting every public fork branch to the matching upstream commit.
- Changed Core, Pro, and Studio source manifests to private visibility.
- Replaced the source-publication model with controlled, sanitized exports.
- Added a live GitHub/Vercel exposure audit and a Gitleaks pre-commit/CI hook.

## Verified State

The live exposure audit reports `passed` for all checks:

- every owned non-fork repository is private;
- no owned repository publishes GitHub Pages;
- the only public repositories are explicitly allowlisted upstream forks;
- every public fork branch is identical to its upstream branch;
- Vercel has zero aliases;
- automatic Vercel alias assignment is disabled;
- retained Vercel deployments require authentication.

Unauthenticated probes return `404` for the three former public repositories,
the former GitHub Pages site, and the former Vercel production alias.

## Validation Evidence

- Public exposure live audit: `passed`.
- Targeted private-first and security tests: `39 passed`.
- Post-format contract rerun: `15 passed`.
- Gitleaks full pre-commit run: `passed`.
- Engine Brain `doc_sync_status`: `passed`.
- Engine Brain `secret_guardrail_status`: `passed`, zero generated-context leaks.
- Engine Brain pack profile: `security`.

## Residual Facts

- Previously downloaded clones and external caches cannot be recalled. GitHub
  reported no hosted forks of CTOAi at lockdown time, but local copies may
  continue to exist.
- Historical revisions remain subject to the terms that applied when they were
  public. The private/proprietary source policy applies prospectively.
- GitHub-hosted Secret Scanning became unavailable after the personal-account
  repository changed to private. Gitleaks and the Engine Brain secret guardrail
  are the compensating controls.
- The two remaining public repository entries are upstream-only forks, not CTOAi
  source distributions. Their divergent commits are preserved only in private
  archives.
- Four broader Engine Brain index tests still expect older P8/P9 roadmap markers.
  This is a pre-existing Helper-roadmap contract mismatch and is not part of the
  exposure lockdown.

## Canonical Controls

- `config/security/public-exposure-policy.json`
- `scripts/ops/ctoa_public_exposure_audit.py`
- `runtime/audits/public-exposure-latest.json` (local evidence)
- `docs/PRODUCT_PUBLIC_PRIVATE_ARCHITECTURE.md`
- `docs/REPO_HYGIENE_POLICY.md`
- `.pre-commit-config.yaml`
