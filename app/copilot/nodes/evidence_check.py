"""
Evidence Check Node for SafeSight Copilot.
Validates whether retrieved visual and document evidence is sufficient to answer.
"""
from typing import Dict, Any
from app.copilot.events import traced
import config


@traced("evidence_check")
def evidence_check(state: Dict[str, Any]) -> Dict[str, Any]:
    """Determines whether usable evidence exists based on confidence and facts."""
    v_evidence = state.get("visual_evidence", [])
    d_evidence = state.get("document_evidence", [])
    facts = state.get("facts", {})

    has_visual = len(v_evidence) > 0
    has_docs = len(d_evidence) > 0
    has_facts = bool(facts and facts.get("total_violations") is not None)

    # Check minimum score threshold
    usable_docs = any(d.get("score", 0.0) >= config.COPILOT_MIN_EVIDENCE_SCORE for d in d_evidence)

    usable = has_visual or usable_docs or has_facts

    summary = f"Evidence usable: {usable} (Visual: {len(v_evidence)}, Docs: {len(d_evidence)}, Facts: {has_facts})"
    return {
        "has_usable_evidence": usable,
        "summary": summary
    }
