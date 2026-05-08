from __future__ import annotations

from typing import Iterable


def select_track(domain: Iterable[str]) -> str | None:
    domain_set = set(domain or [])
    if "documentation" in domain_set:
        return "track_a"
    if "kpi" in domain_set or ("automation" in domain_set and "metrics" in domain_set):
        return "track_b"
    if "reliability" in domain_set and "guardrails" in domain_set:
        return "track_c"
    if "governance" in domain_set:
        return "track_d"
    return None
