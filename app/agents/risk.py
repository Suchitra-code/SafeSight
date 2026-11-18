'''Risk scoring utilities for SafeSight AI Milestone 3.

Pure deterministic functions – no LLM involved.  The logic mirrors the
specification from the mentor: base scores per severity, plus optional
increments for recent similar events, open findings, and mandatory rules.
''' 

from typing import Tuple

def compute_risk(
    violation_type: str,
    severity: str,
    similar_count_7d: int = 0,
    has_open_finding: bool = False,
    mandatory_rule: bool = False,
) -> Tuple[int, str]:
    """Return a numeric risk ``score`` and a textual ``level``.

    Scoring rules (from the mentor):
    * Base: HIGH=3, MEDIUM=2, LOW=1 (derived from ``severity`` string).
    * +1 if ≥3 similar events in the last 7 days.
    * +1 if an open inspector finding of the same category exists.
    * +1 if a manual rule is marked "mandatory".
    * Map the total to a level:
        - 1‑2 → "LOW"
        - 3‑4 → "MEDIUM"
        - 5   → "HIGH"
        - 6+  → "CRITICAL"
    """

    base_map = {"low": 1, "medium": 2, "high": 3}
    score = base_map.get(severity.lower(), 1)

    if similar_count_7d >= 3:
        score += 1
    if has_open_finding:
        score += 1
    if mandatory_rule:
        score += 1

    if score >= 6:
        level = "CRITICAL"
    elif score == 5:
        level = "HIGH"
    elif 3 <= score <= 4:
        level = "MEDIUM"
    else:
        level = "LOW"

    return score, level
