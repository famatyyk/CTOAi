# P8/P9 Review Boundaries

Status: implementation boundaries ready; operational acceptance remains blocked.

The canonical path lists for the two review bundles are stored in
`config/otclient/p8-p9-review-bundles.json`. They are deliberately narrower
than the current working tree.

## P8 — BackgroundNoScreen

P8 owns passive collection, trusted-pin classification, the no-action contract,
`background_status.json`, `ctoa.ps1 otbg`, and its read-only evidence consumers.
It must be reviewed first. Passing tests does not create or repair a trusted pin
and does not change `operational_acceptance` from blocked.

## P9 — Conditions Shadow

P9 depends on P8 and owns the non-executable Conditions profile, sanitized
observation, Recovery proof pair, deterministic replay, `ctoa.ps1 otp9`, and the
exact-confirmation `otp9accept` receipt boundary. The receipt remains data-only
and cannot authorize P10 or any runtime action.

## Shared integration files

The CLI, command dictionary, Release Evidence, and Control Center files contain
multiple roadmap lanes. They must be selected hunk-by-hunk. A whole-file commit
from the current mixed working tree is not an acceptable P8 or P9 boundary.

P10 Equipment, P11 Heal Friend, CTOA Safe, live promotion, sandbox UI, client
launch/stop, screenshots, focus, input, and writes inside the live client are
excluded. Repo-local `runtime/` artifacts are evidence only and are never part
of either GitHub bundle.

## Review order

1. Review P8 core paths and only P8 hunks from shared integration files.
2. Run the P8 commands listed in the bundle manifest.
3. Review P9 core paths and only P9 hunks from shared integration files.
4. Run the P9 commands listed in the bundle manifest.
5. Run the full non-e2e Python suite, web lint/tests, and Engine Brain checks.

The repository pull-request templates mirror this order and require the author
to record the actual commands and evidence status without claiming operational
acceptance.
