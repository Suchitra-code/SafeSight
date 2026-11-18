"""
Unified Retriever for SafeSight AI - Milestone 3.
Searches BOTH Document Repositories (manuals, inspection reports, SOPs)
AND Visual Events (camera detections, live violations).
Merges rankings via Reciprocal Rank Fusion (RRF), dedupes near-identical results,
and attaches standard Source metadata objects with IDs S1..Sn.
"""
import re
import logging
from typing import List, Dict, Any, Optional
from app.db import execute_query
from app.services.search_service import search_knowledge
from app.rag.visual_indexer import search_visual_events

logger = logging.getLogger(__name__)


class Source:
    """Standardized retrieved source reference."""
    def __init__(
        self,
        source_id: str,
        source_type: str,
        title: str,
        snippet: str,
        score: float,
        ref_id: str,
        page: Optional[int] = None,
        section: Optional[str] = None,
        snapshot_url: Optional[str] = None,
        camera: Optional[str] = None,
        event_time: Optional[str] = None
    ):
        self.source_id = source_id
        self.source_type = source_type  # 'document' or 'visual_event'
        self.title = title
        self.snippet = snippet
        self.score = score
        self.ref_id = ref_id  # 'doc:123' or 'vis:45'
        self.page = page
        self.section = section
        self.snapshot_url = snapshot_url
        self.camera = camera
        self.event_time = event_time

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type,
            "title": self.title,
            "snippet": self.snippet,
            "score": self.score,
            "ref_id": self.ref_id,
            "page": self.page,
            "section": self.section,
            "snapshot_url": self.snapshot_url,
            "camera": self.camera,
            "event_time": self.event_time
        }


def retrieve(
    query: str,
    top_k: int = 6,
    filters: Optional[Dict[str, Any]] = None
) -> List[Source]:
    """
    Unified retrieval across documents and visual events.
    Returns ranked list of Source objects numbered S1..Sk.
    """
    clean_q = query.strip()
    if not clean_q:
        return []

    filters = filters or {}
    source_types = filters.get("source_types") or ["document", "visual_event"]

    doc_results = []
    if "document" in source_types:
        try:
            m2_res = search_knowledge(
                clean_q,
                mode="hybrid",
                repository_id=filters.get("repository_id"),
                doc_type=filters.get("doc_type"),
                limit=top_k * 2
            )
            doc_results = m2_res.get("results", [])
        except Exception as e:
            logger.warning(f"Document search error in retriever: {e}")

    vis_results = []
    if "visual_event" in source_types:
        try:
            vis_results = search_visual_events(
                clean_q,
                top_k=top_k * 2,
                filters=filters
            )
        except Exception as e:
            logger.warning(f"Visual event search error in retriever: {e}")

    # Merge with Reciprocal Rank Fusion
    scored_items = []
    seen_texts = set()

    for rank, doc in enumerate(doc_results):
        txt_norm = re.sub(r'\s+', ' ', (doc.get("text") or "")[:120]).strip().lower()
        if txt_norm in seen_texts:
            continue
        seen_texts.add(txt_norm)
        rrf = 1.0 / (60.0 + rank)
        scored_items.append({
            "type": "document",
            "score": rrf,
            "raw_score": doc.get("score", 0.8),
            "data": doc
        })

    for rank, vis in enumerate(vis_results):
        txt_norm = re.sub(r'\s+', ' ', (vis.get("text") or "")[:120]).strip().lower()
        if txt_norm in seen_texts:
            continue
        seen_texts.add(txt_norm)
        rrf = 1.0 / (60.0 + rank)
        scored_items.append({
            "type": "visual_event",
            "score": rrf,
            "raw_score": vis.get("score", 0.8),
            "data": vis
        })

    # Sort descending by fused rank score
    scored_items.sort(key=lambda x: (x["score"], x["raw_score"]), reverse=True)

    sources = []
    for idx, item in enumerate(scored_items[:top_k]):
        sid = f"S{idx + 1}"
        d = item["data"]
        if item["type"] == "document":
            snippet = d.get("text", "")[:350]
            sources.append(Source(
                source_id=sid,
                source_type="document",
                title=d.get("doc_title") or d.get("original_name") or "Document",
                snippet=snippet,
                score=round(float(item["raw_score"]), 3),
                ref_id=f"doc:{d.get('document_id')}",
                page=d.get("page_no", 1),
                section=d.get("repo_name")
            ))
        else:
            snippet = d.get("text", "")[:350]
            sources.append(Source(
                source_id=sid,
                source_type="visual_event",
                title=f"Camera Event: {d.get('violation_type', 'Violation')} ({d.get('camera', 'Cam')})",
                snippet=snippet,
                score=round(float(item["raw_score"]), 3),
                ref_id=f"vis:{d.get('violation_id')}",
                camera=d.get("camera"),
                event_time=str(d.get("event_time")),
                snapshot_url=f"/api/violations/{d.get('violation_id')}/snapshot" if d.get("violation_id") else None
            ))

    return sources
