"""
Answer Generation Node for SafeSight Copilot (Mentor Requirement 6).
Generates an AnswerCard with strict grounding, precise citations, and risk rating.
Falls back to deterministic offline templates when LLM is unavailable or offline.
"""
from typing import Dict, Any
from app.copilot.events import traced
from app.copilot.offline_templates import generate_offline_answer
from app.copilot.schemas import AnswerCard
import config


@traced("answer_generation")
def answer_generation(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generates the grounded AnswerCard."""
    question = state.get("question", "")
    plan = state.get("plan", {})
    facts = state.get("facts", {})
    visual_evidence = state.get("visual_evidence", [])
    document_evidence = state.get("document_evidence", [])
    validator_feedback = state.get("validator_feedback", [])
    retries = state.get("retries", 0)

    # 1. Determine Risk Level from Code Rules (risk.py logic)
    total_v = facts.get("total_violations", 0)
    compliance = facts.get("compliance_percent", 94.5)

    if compliance < 80.0 or total_v >= 10:
        risk_level = "CRITICAL"
    elif compliance < 90.0 or total_v >= 5:
        risk_level = "HIGH"
    elif total_v > 0:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    # 2. Check if online LLM is configured
    mode = "offline"
    answer_card = None

    if config.LLM_PROVIDER and config.LLM_API_KEY:
        try:
            from app.llm.provider import get_llm_client
            llm = get_llm_client()
            if llm.is_available():
                # Formulate strict grounding prompt
                context_v = "\n".join([f"[{v['id']}] {v['text']}" for v in visual_evidence])
                context_d = "\n".join([f"[{d['id']}] {d['title']} (p.{d['page']}): {d['snippet']}" for d in document_evidence])
                facts_str = ", ".join(f"{k}: {v}" for k, v in facts.items())

                feedback_prompt = ""
                if validator_feedback:
                    feedback_prompt = f"\nPREVIOUS VALIDATION ERRORS (FIX THEM STRICTLY):\n" + "\n".join(f"- {f}" for f in validator_feedback)

                sys_prompt = (
                    "You are SafeSight Copilot, an AI safety officer. Synthesize a concise answer grounded ONLY in the evidence below.\n"
                    "CRITICAL RULES:\n"
                    "1. Every factual sentence MUST end with its source tag like [V1] or [D1].\n"
                    "2. Only cite numbers explicitly present in FACTS or EVIDENCE.\n"
                    "3. Return a clean AnswerCard with headline and answer."
                )
                user_prompt = (
                    f"Question: {question}\n\n"
                    f"FACTS: {facts_str}\n\n"
                    f"VISUAL EVIDENCE:\n{context_v}\n\n"
                    f"DOCUMENT EVIDENCE:\n{context_d}\n"
                    f"{feedback_prompt}"
                )
                raw_ans = llm.generate(sys_prompt, user_prompt, max_tokens=350)
                if raw_ans and len(raw_ans.strip()) > 30:
                    answer_card = AnswerCard(
                        headline=f"AI Safety Assessment ({risk_level} Risk)",
                        answer=raw_ans.strip(),
                        risk_level=risk_level
                    )
                    mode = "llm"
        except Exception:
            answer_card = None

    # 3. Default: Deterministic Offline Answer Template
    if not answer_card:
        answer_card = generate_offline_answer(
            question=question,
            plan=plan,
            facts=facts,
            visual_evidence=visual_evidence,
            document_evidence=document_evidence,
            risk_level=risk_level
        )
        mode = "offline"

    summary = f"Generated {mode} answer card (Risk: {risk_level}, Headline: '{answer_card.headline[:40]}...')"
    return {
        "answer_card": answer_card.model_dump(),
        "mode": mode,
        "summary": summary
    }
