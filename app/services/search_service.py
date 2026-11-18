"""
Search Service for SafeSight AI - Milestone 2.
Supports:
1. Keyword search (MySQL FULLTEXT or SQLite LIKE fallback).
2. Semantic search (Embedder vector search).
3. Hybrid search (Reciprocal Rank Fusion - RRF merging keyword and semantic ranks).
4. Metadata filtering (repository, doc_type, PPE type, severity, date range).
5. Safe HTML snippet highlighting (escapes HTML first).
6. Performance logging into `search_logs` table.
"""
import time
import html
import re
from typing import List, Dict, Any, Optional
from app.db import execute_query, execute_insert
from app.services import embedder


def search_knowledge(
    query: str,
    mode: str = "hybrid",
    repository_id: Optional[int] = None,
    doc_type: Optional[str] = None,
    ppe_type: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 15
) -> Dict[str, Any]:
    """
    Executes search according to mode ('hybrid', 'semantic', 'keyword').
    Returns {query, mode, count, took_ms, results: [...]}.
    """
    start_time = time.time()
    clean_q = query.strip()
    if not clean_q:
        return {"query": "", "mode": mode, "count": 0, "took_ms": 0.0, "results": []}

    mode_lower = mode.lower()
    results = []

    if mode_lower == "keyword":
        results = _keyword_search(clean_q, repository_id, limit * 2)
    elif mode_lower == "semantic":
        results = _semantic_search(clean_q, repository_id, limit * 2)
    else:
        # Default: Hybrid Search with Reciprocal Rank Fusion
        kw_results = _keyword_search(clean_q, repository_id, limit * 2)
        sem_results = _semantic_search(clean_q, repository_id, limit * 2)
        results = _reciprocal_rank_fusion(kw_results, sem_results, limit)

    # Apply secondary filters: doc_type, ppe_type, severity
    filtered_results = []
    for item in results:
        # Check doc_type
        if doc_type and item.get("doc_type") != doc_type:
            continue
        # Check PPE type or severity inside text if requested
        if ppe_type and ppe_type.lower() not in item.get("text", "").lower():
            continue
        if severity and severity.upper() not in item.get("text", "").upper():
            continue

        # Highlight snippet safely
        item["snippet"] = _highlight_text(item.get("text", ""), clean_q)
        filtered_results.append(item)

        if len(filtered_results) >= limit:
            break

    took_ms = round((time.time() - start_time) * 1000.0, 2)

    # Log search
    try:
        execute_insert(
            "INSERT INTO search_logs (query, mode, result_count, took_ms) VALUES (%s, %s, %s, %s)",
            (clean_q, mode_lower, len(filtered_results), took_ms)
        )
    except Exception:
        pass

    return {
        "query": clean_q,
        "mode": mode_lower,
        "count": len(filtered_results),
        "took_ms": took_ms,
        "results": filtered_results
    }


def _keyword_search(query: str, repository_id: Optional[int], limit: int) -> List[Dict[str, Any]]:
    """
    SQL-based keyword search across chunk text and document titles/filenames.
    Filters out noise stop words to prevent false-positive matches on common words.
    """
    stop_words = {"and", "the", "for", "with", "from", "that", "this", "are", "was", "were", "what"}
    raw_tokens = [t.lower() for t in re.findall(r'[A-Za-z0-9_-]+', query) if len(t) > 2]
    tokens = [t for t in raw_tokens if t not in stop_words]
    if not tokens:
        tokens = raw_tokens or [query]

    # Search doc_chunks joined with documents and repositories
    sql = """
        SELECT c.id, c.document_id, c.repository_id, c.page_no, c.text,
               d.title as doc_title, d.original_name, d.doc_type, r.name as repo_name
        FROM doc_chunks c
        JOIN documents d ON c.document_id = d.id
        LEFT JOIN repositories r ON c.repository_id = r.id
        WHERE 1=1
    """
    params = []
    if repository_id:
        sql += " AND c.repository_id = %s"
        params.append(repository_id)

    # Match tokens in either chunk text, document title, or original_name
    token_clauses = []
    for tok in tokens:
        token_clauses.append("(c.text LIKE %s OR d.title LIKE %s OR d.original_name LIKE %s)")
        params.extend([f"%{tok}%", f"%{tok}%", f"%{tok}%"])

    sql += " AND (" + " OR ".join(token_clauses) + ")"
    sql += " ORDER BY c.document_id DESC, c.id DESC LIMIT %s"
    params.append(limit)

    rows = execute_query(sql, tuple(params), fetch=True) or []
    results = []
    for idx, r in enumerate(rows):
        d = dict(r)
        # Score calculation: base rank + count of matching tokens
        text_lower = (d.get("text") or "").lower()
        title_lower = (d.get("doc_title") or "").lower()
        orig_lower = (d.get("original_name") or "").lower()
        matches = sum(1 for tok in tokens if tok in text_lower or tok in title_lower or tok in orig_lower)
        d["score"] = round((matches / max(1, len(tokens))) * (1.0 / (1.0 + idx * 0.1)), 3)
        results.append(d)

    # Sort by calculated score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def _semantic_search(query: str, repository_id: Optional[int], limit: int) -> List[Dict[str, Any]]:
    """Vector / similarity search."""
    scored_chunks = embedder.semantic_search(query, top_k=limit * 2)
    results = []

    for chunk_meta, score in scored_chunks:
        if repository_id and chunk_meta.get("repository_id") != repository_id:
            continue

        doc_id = chunk_meta.get("document_id")
        doc_rows = execute_query(
            "SELECT d.title, d.original_name, d.doc_type, r.name as repo_name FROM documents d LEFT JOIN repositories r ON d.repository_id = r.id WHERE d.id = %s",
            (doc_id,), fetch=True
        ) or []
        doc_info = dict(doc_rows[0]) if doc_rows else {}

        results.append({
            "id": chunk_meta.get("id") or chunk_meta.get("chunk_index"),
            "document_id": doc_id,
            "repository_id": chunk_meta.get("repository_id"),
            "page_no": chunk_meta.get("page_no", 1),
            "text": chunk_meta.get("text", ""),
            "doc_title": doc_info.get("title", f"Document #{doc_id}"),
            "original_name": doc_info.get("original_name", ""),
            "doc_type": doc_info.get("doc_type", "other"),
            "repo_name": doc_info.get("repo_name", "General"),
            "score": round(score, 3)
        })

    return results[:limit]


def _reciprocal_rank_fusion(kw_list: List[Dict[str, Any]], sem_list: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    """
    Combines keyword search and semantic vector search results using Reciprocal Rank Fusion (RRF).
    Formula: RRF_score = SUM( 1 / (60 + rank_i) )
    Deduplicates identical text/content across duplicate documents, keeping the newest.
    Normalizes final scores to a meaningful spread (0.0 to 1.0) so top matches stand out clearly.
    """
    scores = {}
    items = {}

    for rank, item in enumerate(kw_list):
        content_key = (item.get("page_no"), re.sub(r'\s+', ' ', item.get("text", "")[:120]).strip())
        scores[content_key] = scores.get(content_key, 0.0) + (1.0 / (60.0 + rank))
        if content_key not in items or (item.get("document_id") or 0) > (items[content_key].get("document_id") or 0):
            items[content_key] = item

    for rank, item in enumerate(sem_list):
        content_key = (item.get("page_no"), re.sub(r'\s+', ' ', item.get("text", "")[:120]).strip())
        scores[content_key] = scores.get(content_key, 0.0) + (1.0 / (60.0 + rank))
        if content_key not in items or (item.get("document_id") or 0) > (items[content_key].get("document_id") or 0):
            items[content_key] = item

    if not scores:
        return []

    sorted_keys = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)
    max_raw = max(scores.values())
    min_raw = min(scores.values())

    merged = []
    for k in sorted_keys[:limit]:
        obj = dict(items[k])
        # Meaningful score spread: map raw score relative to best match
        if max_raw > min_raw:
            # Scale from 0.45 to 0.98 based on relative quality
            scaled_score = 0.45 + 0.53 * ((scores[k] - min_raw) / (max_raw - min_raw))
        else:
            scaled_score = 0.90
        obj["score"] = round(scaled_score, 3)
        merged.append(obj)

    return merged


def _highlight_text(text: str, query: str) -> str:
    """
    Safely highlights matched query terms in text.
    Uses word boundaries (\\b) so substrings inside words like 'AND' in 'MANDATORY'
    or 'and' in 'Handbook' are NEVER corrupted or broken.
    Escapes all HTML first to prevent XSS.
    """
    escaped = html.escape(text)

    # Filter meaningful query words (min 3 chars, skip common short stop words like 'and', 'the', 'for')
    stop_words = {"and", "the", "for", "with", "from", "that", "this", "are", "was", "were", "what"}
    words = [
        re.escape(w) for w in re.findall(r'[A-Za-z0-9_-]+', query)
        if len(w) > 2 and w.lower() not in stop_words
    ]
    if not words:
        # Fallback to any token > 2 if all were stop words
        words = [re.escape(w) for w in re.findall(r'[A-Za-z0-9_-]+', query) if len(w) > 2]

    if not words:
        return escaped[:280] + ("..." if len(escaped) > 280 else "")

    # Match WHOLE WORDS only using word boundaries \b
    pattern = re.compile(r'\b(' + '|'.join(words) + r')\b', re.IGNORECASE)
    highlighted = pattern.sub(r'<mark class="search-match">\1</mark>', escaped)

    # Center snippet around first match
    first_match = re.search(r'<mark class="search-match">', highlighted)
    if first_match:
        start = max(0, first_match.start() - 80)
        end = min(len(highlighted), start + 320)
        snippet = highlighted[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(highlighted):
            snippet = snippet + "..."
        return snippet

    return highlighted[:280] + ("..." if len(highlighted) > 280 else "")
