"""Response guardrails for CTOA agent outputs.

These checks are intentionally lightweight so they can be reused in tests,
CI helpers, or future runtime validation without pulling in the whole runner.
"""

from __future__ import annotations

import re


FORBIDDEN_MARKERS = ("<think>", "</think>")

FORBIDDEN_META_PATTERNS = (
    re.compile(r"they\s+don't\s+see\s+my\s+thoughts", re.IGNORECASE),
    re.compile(r"i\s+must\s+apologize", re.IGNORECASE),
    re.compile(r"i\s+shouldn't\s+have\s+done\s+that", re.IGNORECASE),
    re.compile(r"wait,\s*no", re.IGNORECASE),
    re.compile(r"i\s+shouldn't\s+have\s+done\s+it", re.IGNORECASE),
)

GENERIC_FOLLOW_UP_PATTERNS = (
    re.compile(r"anything\s+else\s+you're\s+curious\s+about\?$", re.IGNORECASE),
    re.compile(r"anything\s+else\?$", re.IGNORECASE),
    re.compile(r"let\s+me\s+know\s+if\s+you\s+need\s+anything\s+else\.?$", re.IGNORECASE),
)


def validate_response(text: str) -> list[str]:
    """Return a list of guardrail violations for an agent response."""
    violations: list[str] = []
    lowered = text.lower()

    for marker in FORBIDDEN_MARKERS:
        if marker in text:
            violations.append(f"forbidden marker present: {marker}")

    for pattern in FORBIDDEN_META_PATTERNS:
        if pattern.search(lowered):
            violations.append(f"forbidden meta commentary: {pattern.pattern}")

    stripped_lines = [line.strip() for line in text.splitlines() if line.strip()]
    final_line = stripped_lines[-1] if stripped_lines else ""
    for pattern in GENERIC_FOLLOW_UP_PATTERNS:
        if pattern.search(final_line):
            violations.append(f"generic follow-up ending: {final_line}")

    return violations


def is_response_compliant(text: str) -> bool:
    """Check whether a response passes all guardrails."""
    return not validate_response(text)