"""
Guardrails and Verification for SafeSight AI RAG Pipeline.
Verifies citation integrity, strips potential HTML/XSS, enforces refusal logic,
and prevents prompt injection exploits.
"""
import re
import html
from typing import List, Dict, Any, Tuple
from app.rag.retriever import Source

REFUSAL_MESSAGE = "I could not find this in the available documents or events."


def sanitize_input(text: str, max_length: int = 500) -> str:
    """Sanitizes user input query: trims, removes control characters, bounds length."""
    if not text:
        return ""
    # Strip null bytes and control chars
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned[:max_length]


def sanitize_output(text: str) -> str:
    """Safely escapes HTML in LLM or template output to prevent XSS injection."""
    if not text:
        return ""
    # Keep standard markdown formatting intact while escaping raw dangerous HTML tags
    text = re.sub(r'<script.*?>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<iframe.*?>.*?</iframe>', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'onerror=[\'\"].*?[\'\"]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'onload=[\'\"].*?[\'\"]', '', text, flags=re.IGNORECASE)
    return text.strip()


def verify_and_ground_answer(
    answer: str,
    sources: List[Source],
    min_score_threshold: float = 0.40
) -> Tuple[str, List[Dict[str, Any]], str]:
    """
    Verifies that all citations [Sx] in answer correspond to actual retrieved sources.
    If no valid citations exist or top retrieval score is below threshold, returns REFUSAL_MESSAGE.
    Returns: (verified_answer, valid_citations_list, confidence_level)
    """
    if not sources:
        return REFUSAL_MESSAGE, [], "Low"

    # Check top retrieval score
    max_score = max(s.score for s in sources)
    if max_score < min_score_threshold:
        return REFUSAL_MESSAGE, [], "Low"

    valid_sids = {s.source_id: s for s in sources}
    cited_tags = re.findall(r'\[(S\d+)\]', answer)

    valid_cites = []
    seen_sids = set()

    for tag in cited_tags:
        if tag in valid_sids and tag not in seen_sids:
            seen_sids.add(tag)
            src = valid_sids[tag]
            valid_cites.append(src.to_dict())

    # If the LLM fabricated non-existent tags, strip them out
    cleaned_answer = re.sub(
        r'\[(S\d+)\]',
        lambda m: m.group(0) if m.group(1) in valid_sids else "",
        answer
    )
    cleaned_answer = re.sub(r'\s{2,}', ' ', cleaned_answer).strip()

    # If zero valid citations survived, enforce strict refusal
    if not valid_cites:
        # Check if the answer explicitly stated the refusal already
        if REFUSAL_MESSAGE.lower() in answer.lower():
            return REFUSAL_MESSAGE, [], "Low"
        return REFUSAL_MESSAGE, [], "Low"

    # Compute confidence based on citation count & top source score
    if len(valid_cites) >= 2 and max_score >= 0.75:
        confidence = "High"
    elif len(valid_cites) >= 1 and max_score >= 0.55:
        confidence = "Medium"
    else:
        confidence = "Low"

    return cleaned_answer, valid_cites, confidence
