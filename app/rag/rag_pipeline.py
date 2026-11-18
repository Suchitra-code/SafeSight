"""
RAG Pipeline for SafeSight AI - Milestone 3.
Implements the complete question-answering workflow:
1. Input validation & sanitization
2. Context-aware follow-up question rewriting
3. Multi-modal unified retrieval
4. Context window assembly
5. Answer generation (LLM if available, else high-precision extractive)
6. Guardrail verification & citation checking
7. Message history logging & timing
"""
import time
import logging
from typing import Dict, Any, List, Optional
from app.db import execute_query, execute_insert
from app.rag.retriever import retrieve, Source
from app.rag.context_builder import build_rag_context
from app.rag.guardrails import sanitize_input, sanitize_output, verify_and_ground_answer, REFUSAL_MESSAGE
from app.llm.provider import get_llm_client, LLMError
from app.llm.prompts import STRICT_RAG_SYSTEM_PROMPT, STRICT_RAG_USER_PROMPT

logger = logging.getLogger(__name__)


def answer_rag_question(
    question: str,
    session_id: str = "default_session",
    filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Executes end-to-end RAG question answering.
    Returns:
    {
        "answer": str,
        "citations": list,
        "sources": list,
        "confidence": "High" | "Medium" | "Low",
        "took_ms": float,
        "mode_used": "llm" | "extractive",
        "question": str
    }
    """
    start_time = time.time()
    q_clean = sanitize_input(question)
    if not q_clean:
        return {
            "question": "",
            "answer": "Please ask a question about your safety policies, manuals, or camera events.",
            "citations": [],
            "sources": [],
            "confidence": "Low",
            "took_ms": 0.0,
            "mode_used": "extractive"
        }

    # 1. Stand-alone question rewriting using recent session history
    standalone_q = _rewrite_followup(q_clean, session_id)

    # 2. Retrieve top sources across documents & camera visual events
    sources = retrieve(standalone_q, top_k=6, filters=filters)

    # 3. Assemble bounded context block
    context_str = build_rag_context(sources)

    # 4. Generate Answer: LLM mode with fallback to Extractive mode
    raw_answer = ""
    mode_used = "extractive"
    llm = get_llm_client()

    if llm.is_available():
        try:
            user_prompt = STRICT_RAG_USER_PROMPT.format(context=context_str, question=standalone_q)
            raw_answer = llm.generate(STRICT_RAG_SYSTEM_PROMPT, user_prompt, max_tokens=600)
            mode_used = "llm"
        except LLMError as e:
            logger.info(f"LLM generation unavailable ({e}), using extractive synthesis.")
            raw_answer = ""

    if not raw_answer:
        # Fallback to high-precision extractive answer
        raw_answer = _synthesize_extractive_answer(standalone_q, sources)
        mode_used = "extractive"

    # 5. Guardrails & Citation Verification
    verified_answer, valid_citations, confidence = verify_and_ground_answer(raw_answer, sources)
    safe_answer = sanitize_output(verified_answer)
    took_ms = round((time.time() - start_time) * 1000.0, 2)

    # 6. Save exchange to chat_messages table
    try:
        import json
        execute_insert(
            """INSERT INTO chat_messages (session_id, role, content, mode_used, confidence, latency_ms, sources_json)
               VALUES (%s, 'user', %s, %s, %s, %s, %s)""",
            (session_id, q_clean, mode_used, confidence, took_ms, json.dumps([]))
        )
        execute_insert(
            """INSERT INTO chat_messages (session_id, role, content, mode_used, confidence, latency_ms, sources_json)
               VALUES (%s, 'assistant', %s, %s, %s, %s, %s)""",
            (session_id, safe_answer, mode_used, confidence, took_ms, json.dumps([s.to_dict() for s in sources]))
        )
    except Exception as e:
        logger.warning(f"Could not persist chat message: {e}")

    return {
        "question": q_clean,
        "answer": safe_answer,
        "citations": valid_citations,
        "sources": [s.to_dict() for s in sources],
        "confidence": confidence,
        "took_ms": took_ms,
        "mode_used": mode_used
    }


def _rewrite_followup(query: str, session_id: str) -> str:
    """Carries over topic keywords from recent chat messages if current query is a short follow-up."""
    tokens = query.split()
    if len(tokens) > 4:
        return query

    # Check last user query
    try:
        recent = execute_query(
            "SELECT content FROM chat_messages WHERE session_id = %s AND role = 'user' ORDER BY id DESC LIMIT 1",
            (session_id,),
            fetch=True
        )
        if recent and recent[0].get("content"):
            last_q = recent[0]["content"]
            # Carry over subject keywords
            for key in ["welding", "goggles", "helmet", "crane", "vest", "grinder", "harness"]:
                if key in last_q.lower() and key not in query.lower():
                    return f"{query} {key}"
    except Exception:
        pass
    return query


def _synthesize_extractive_answer(query: str, sources: List[Source]) -> str:
    """Deterministic extractive synthesis from top sources with [Sx] citations."""
    if not sources:
        return REFUSAL_MESSAGE

    q_words = set(w.lower() for w in query.split() if len(w) > 2)
    sentences_picked = []

    for s in sources:
        # Split snippet into sentences
        for sentence in s.snippet.split(". "):
            sent_clean = sentence.strip()
            if len(sent_clean) < 25:
                continue
            s_words = set(w.lower() for w in sent_clean.split())
            if len(q_words.intersection(s_words)) >= 1:
                sentences_picked.append(f"{sent_clean} [{s.source_id}]")
                break
        if len(sentences_picked) >= 3:
            break

    if not sentences_picked and sources:
        # Fallback to first source snippet with citation
        sentences_picked.append(f"{sources[0].snippet[:200]}... [{sources[0].source_id}]")

    return " ".join(sentences_picked)
