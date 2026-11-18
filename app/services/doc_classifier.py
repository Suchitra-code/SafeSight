"""
Document Classifier for SafeSight AI - Milestone 2.
Classifies text into:
- inspection_report
- safety_manual
- sop
- other
Uses rule-based keyword scoring with category weightings.
"""
from typing import Tuple, Dict


def classify_document(full_text: str, file_name: str = "") -> Tuple[str, float]:
    """
    Returns (predicted_doc_type, confidence_score)
    where predicted_doc_type is one of:
    ['inspection_report', 'safety_manual', 'sop', 'other']
    """
    if not full_text:
        return ("other", 0.3)

    text_lower = (full_text + " " + file_name).lower()

    # Keyword dictionaries
    report_keywords = [
        "inspection", "audit", "inspector", "supervisor", "findings",
        "deficiency", "corrective action", "non-compliance", "severity",
        "infraction", "violation", "site inspection", "due date", "observation"
    ]

    manual_keywords = [
        "manual", "handbook", "policy", "guidelines", "general requirements",
        "shall be", "must be worn", "mandatory", "ppe policy", "respirator",
        "fall protection", "hearing conservation", "code of practice"
    ]

    sop_keywords = [
        "standard operating procedure", "sop", "procedure", "step 1",
        "step 2", "purpose", "scope", "responsibilities", "prerequisites",
        "step-by-step", "workflow", "work instruction"
    ]

    def score_keywords(keywords):
        score = 0
        for kw in keywords:
            if kw in text_lower:
                # Give higher weight to multi-word or exact title matches
                count = text_lower.count(kw)
                score += (2 if " " in kw else 1) * min(count, 5)
        return score

    report_score = score_keywords(report_keywords)
    manual_score = score_keywords(manual_keywords)
    sop_score = score_keywords(sop_keywords)

    scores = {
        "inspection_report": report_score,
        "safety_manual": manual_score,
        "sop": sop_score
    }

    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]

    if best_score < 3:
        return ("other", 0.5)

    total = sum(scores.values()) + 1
    confidence = min(0.98, max(0.65, round(best_score / total + 0.3, 2)))

    return (best_type, confidence)
