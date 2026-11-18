"""
Document Retrieval Node for SafeSight Copilot (Mentor Requirement 5).
Leverages hybrid keyword and semantic retrieval across safety handbooks, SOPs,
and past inspection reports.
"""
from typing import Dict, Any, List
from app.copilot.events import traced
from app.services.search_service import search_knowledge
from app.db import execute_query


@traced("document_retrieval")
def document_retrieval(state: Dict[str, Any]) -> Dict[str, Any]:
    """Retrieves safety manual excerpts and inspection report findings."""
    plan = state.get("plan", {})
    entities = plan.get("entities", {})
    question = state.get("question", "")

    # Construct targeted search query
    query_parts = [question]
    if entities.get("violation_type"):
        query_parts.append(entities["violation_type"])
    if entities.get("ppe_type"):
        query_parts.append(f"{entities['ppe_type']} mandatory rule policy")

    search_query = " ".join(query_parts)

    # 1. Hybrid Search over Document Chunks
    search_res = search_knowledge(search_query, mode="hybrid", limit=4)
    chunks = search_res.get("results", [])

    document_evidence = []
    for idx, c in enumerate(chunks):
        did = f"D{idx + 1}"
        doc_title = c.get("doc_title") or c.get("original_name") or "Safety Manual"
        page = c.get("page_no", 1)
        section = c.get("repo_name", "General Policy")
        text = c.get("text", "")
        score = float(c.get("score", 0.85))

        document_evidence.append({
            "id": did,
            "ref_id": f"doc:{c.get('document_id', 1)}",
            "title": doc_title,
            "page": page,
            "section": section,
            "snippet": text[:350],
            "score": score
        })

    # 2. Check structured manual_rules or report_findings tables if chunks are sparse
    if len(document_evidence) < 2 and entities.get("ppe_type"):
        try:
            sql = "SELECT id, document_id, rule_text, page_no FROM manual_rules WHERE ppe_type LIKE %s LIMIT 2"
            rows = execute_query(sql, (f"%{entities['ppe_type']}%",), fetch=True) or []
            for r in rows:
                did = f"D{len(document_evidence) + 1}"
                document_evidence.append({
                    "id": did,
                    "ref_id": f"rule:{r['id']}",
                    "title": "Corporate Safety Standards",
                    "page": r.get("page_no", 1),
                    "section": "PPE Policy",
                    "snippet": r.get("rule_text", ""),
                    "score": 0.90
                })
        except Exception:
            pass

    summary = f"Retrieved {len(document_evidence)} document excerpt(s) from safety repository"
    return {
        "document_evidence": document_evidence,
        "summary": summary
    }
