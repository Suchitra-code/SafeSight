"""
Knowledge Base Search and Q&A Routes for SafeSight AI - Milestone 2.
Implements:
- GET /knowledge (Search & Ask UI)
- GET /api/knowledge/search
- POST /api/knowledge/ask
- POST /api/knowledge/rebuild
- GET /api/knowledge/stats
"""
import logging
from flask import Blueprint, request, jsonify, render_template

from app.db import execute_query
from app.services import search_service, qa_service, embedder

logger = logging.getLogger(__name__)

knowledge_bp = Blueprint("knowledge", __name__)


@knowledge_bp.route("/knowledge")
def knowledge_page():
    """Knowledge Base UI (Search & Ask Q&A)."""
    repos = execute_query("SELECT * FROM repositories ORDER BY name ASC") or []
    status = embedder.get_embedder_status()
    return render_template(
        "knowledge.html",
        active_page="knowledge",
        repositories=[dict(r) for r in repos],
        embedder_status=status
    )


@knowledge_bp.route("/api/knowledge/search", methods=["GET"])
def api_knowledge_search():
    """Multi-mode document search (hybrid, semantic, keyword) with filtering."""
    q = request.args.get("q", "")
    mode = request.args.get("mode", "hybrid")
    repo_id_val = request.args.get("repository")
    repo_id = int(repo_id_val) if repo_id_val and repo_id_val.isdigit() else None
    doc_type = request.args.get("type")
    ppe_type = request.args.get("ppe")
    severity = request.args.get("severity")

    res = search_service.search_knowledge(
        query=q,
        mode=mode,
        repository_id=repo_id,
        doc_type=doc_type,
        ppe_type=ppe_type,
        severity=severity,
        limit=20
    )
    return jsonify(res)


@knowledge_bp.route("/api/knowledge/ask", methods=["POST"])
def api_knowledge_ask():
    """Q&A endpoint: answers safety inquiries backed by citations."""
    data = request.json or {}
    question = data.get("question", "")
    repo_id = data.get("repository_id")

    res = qa_service.answer_question(question, repository_id=repo_id)
    return jsonify(res)


@knowledge_bp.route("/api/knowledge/rebuild", methods=["POST"])
def api_rebuild_index():
    """Rebuilds the vector and similarity index across all chunks."""
    all_chunks = execute_query(
        "SELECT document_id, repository_id, page_no, chunk_index, text FROM doc_chunks",
        fetch=True
    ) or []
    success = embedder.build_index([dict(c) for c in all_chunks])
    return jsonify({"success": success, "chunk_count": len(all_chunks)})


@knowledge_bp.route("/api/knowledge/stats", methods=["GET"])
def api_knowledge_stats():
    """Returns analytics for document intelligence dashboard section."""
    doc_count_res = execute_query("SELECT COUNT(*) as cnt FROM documents") or [{"cnt": 0}]
    processed_count_res = execute_query("SELECT COUNT(*) as cnt FROM documents WHERE status IN ('processed', 'verified')") or [{"cnt": 0}]
    review_count_res = execute_query("SELECT COUNT(*) as cnt FROM documents WHERE status = 'needs review'") or [{"cnt": 0}]
    failed_count_res = execute_query("SELECT COUNT(*) as cnt FROM documents WHERE status = 'failed'") or [{"cnt": 0}]
    findings_count_res = execute_query("SELECT COUNT(*) as cnt FROM report_findings") or [{"cnt": 0}]
    open_findings_res = execute_query("SELECT COUNT(*) as cnt FROM report_findings WHERE status != 'closed'") or [{"cnt": 0}]

    # Category breakdown
    cat_rows = execute_query("""
        SELECT category, COUNT(*) as count
        FROM report_findings
        GROUP BY category
        ORDER BY count DESC
    """) or []

    # Severity breakdown
    sev_rows = execute_query("""
        SELECT severity, COUNT(*) as count
        FROM report_findings
        GROUP BY severity
    """) or []

    # Top search terms
    terms_rows = execute_query("""
        SELECT query, COUNT(*) as count
        FROM search_logs
        GROUP BY query
        ORDER BY count DESC
        LIMIT 6
    """) or []

    # Recent processed docs
    recent_docs = execute_query("""
        SELECT id, title, doc_type, status, uploaded_at, page_count
        FROM documents
        ORDER BY uploaded_at DESC
        LIMIT 5
    """) or []

    return jsonify({
        "total_documents": doc_count_res[0]["cnt"],
        "processed_documents": processed_count_res[0]["cnt"],
        "needs_review": review_count_res[0]["cnt"],
        "failed_documents": failed_count_res[0]["cnt"],
        "total_findings": findings_count_res[0]["cnt"],
        "open_findings": open_findings_res[0]["cnt"],
        "findings_by_category": [dict(r) for r in cat_rows],
        "findings_by_severity": [dict(r) for r in sev_rows],
        "top_search_terms": [dict(r) for r in terms_rows],
        "recent_documents": [dict(r) for r in recent_docs]
    })
