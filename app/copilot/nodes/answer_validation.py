"""
Answer Validation Node for SafeSight Copilot (Mentor Requirement 7).
Runs automated verification checks and computes Trust Meter score.
"""
from typing import Dict, Any
from app.copilot.events import traced
from app.copilot.validators import validate_answer


@traced("answer_validation")
def answer_validation(state: Dict[str, Any]) -> Dict[str, Any]:
    """Validates the generated AnswerCard against evidence and facts."""
    answer_card = state.get("answer_card", {})
    visual_evidence = state.get("visual_evidence", [])
    document_evidence = state.get("document_evidence", [])
    facts = state.get("facts", {})
    plan = state.get("plan", {})
    retries = state.get("retries", 0)

    val_report = validate_answer(
        answer_card=answer_card,
        visual_evidence=visual_evidence,
        document_evidence=document_evidence,
        facts=facts,
        plan=plan
    )

    summary = f"Validation score: {val_report.score}% (Verdict: {val_report.verdict}, Feedback: {len(val_report.feedback)} item(s))"
    return {
        "validation": val_report.model_dump(),
        "validator_feedback": val_report.feedback,
        "summary": summary
    }
