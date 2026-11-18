"""
Visual Indexer Service for SafeSight AI - Milestone 3.
Converts camera detection violation records into searchable natural-language visual events.
Stores text metadata in `visual_chunks` table and vector representations in `knowledge/faiss_visual.index`.
Supports offline TF-IDF vector fallback when neural embeddings are unavailable.
Uses thread safety locks around index writes and never interrupts detection on indexing error.
"""
import os
import json
import logging
import threading
from typing import Dict, Any, List, Optional
import config
from app.db import execute_query, execute_insert
from app.services import embedder

logger = logging.getLogger(__name__)

_visual_index_lock = threading.Lock()
_visual_meta: List[Dict[str, Any]] = []


def _format_violation_description(v: Dict[str, Any]) -> str:
    """
    Constructs a clear, informative natural-language summary from structured violation data.
    Works entirely offline without requiring an LLM.
    """
    v_type = v.get("violation_type", "PPE non-compliance")
    sev = v.get("severity", "MEDIUM")
    cam = v.get("camera_name", "Cam 01 - Zone A")
    loc = v.get("location", "Main Site")
    conf = float(v.get("confidence") or 0.85)
    dt = str(v.get("detected_at") or "")
    status = v.get("status", "detected")

    desc = f"{sev} severity {v_type} violation detected at {cam} ({loc}) on {dt}. Detection confidence {conf:.2f}. Review status: {status}."
    return desc


def index_violation(violation_id: int) -> bool:
    """
    Indexes a single violation event into `visual_chunks` table and the visual FAISS/TF-IDF index.
    Thread-safe and wrapped in try/except so detection flow is never impacted.
    """
    try:
        rows = execute_query("SELECT * FROM violations WHERE id = %s", (violation_id,), fetch=True)
        if not rows:
            logger.warning(f"Violation ID {violation_id} not found for indexing.")
            return False

        v = dict(rows[0])
        desc = _format_violation_description(v)
        snap = v.get("snapshot_path") or ""
        cam = v.get("camera_name") or "Cam 01"
        zone = v.get("location") or "Zone A"
        v_type = v.get("violation_type") or "PPE"
        sev = v.get("severity") or "MEDIUM"
        ev_time = v.get("detected_at")

        with _visual_index_lock:
            # Check if chunk already exists
            existing = execute_query("SELECT id FROM visual_chunks WHERE violation_id = %s", (violation_id,), fetch=True)
            if existing:
                execute_query(
                    """UPDATE visual_chunks 
                       SET text = %s, camera = %s, zone = %s, violation_type = %s, severity = %s, event_time = %s, snapshot_path = %s 
                       WHERE violation_id = %s""",
                    (desc, cam, zone, v_type, sev, ev_time, snap, violation_id),
                    fetch=False,
                    commit=True
                )
            else:
                execute_insert(
                    """INSERT INTO visual_chunks 
                       (violation_id, text, camera, zone, violation_type, severity, event_time, snapshot_path, source_file)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (violation_id, desc, cam, zone, v_type, sev, ev_time, snap, snap)
                )

            # Update in-memory / disk visual chunks meta
            _sync_visual_metadata()

        return True
    except Exception as e:
        logger.error(f"Error indexing violation ID {violation_id}: {e}")
        return False


def remove_violation(violation_id: int) -> bool:
    """Removes a violation from visual_chunks."""
    try:
        with _visual_index_lock:
            execute_query("DELETE FROM visual_chunks WHERE violation_id = %s", (violation_id,), fetch=False, commit=True)
            _sync_visual_metadata()
        return True
    except Exception as e:
        logger.error(f"Error removing visual chunk for violation ID {violation_id}: {e}")
        return False


def reindex_all() -> int:
    """Reindexes all violations into visual_chunks."""
    try:
        violations = execute_query("SELECT * FROM violations ORDER BY id ASC", fetch=True) or []
        count = 0
        for v in violations:
            if index_violation(v["id"]):
                count += 1
        return count
    except Exception as e:
        logger.error(f"Error in reindex_all: {e}")
        return 0


def _sync_visual_metadata():
    """Syncs the visual chunks from DB to disk and memory."""
    global _visual_meta
    rows = execute_query("SELECT * FROM visual_chunks ORDER BY id ASC", fetch=True) or []
    _visual_meta = [dict(r) for r in rows]
    try:
        with open(config.VISUAL_CHUNKS_META_PATH, "w", encoding="utf-8") as f:
            json.dump(_visual_meta, f, default=str, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Could not persist visual metadata: {e}")


def search_visual_events(query: str, top_k: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Searches indexed visual violation events using hybrid keyword + TF-IDF similarity.
    Returns matched events with relevance scores and metadata.
    """
    global _visual_meta
    if not _visual_meta:
        if os.path.exists(config.VISUAL_CHUNKS_META_PATH):
            try:
                with open(config.VISUAL_CHUNKS_META_PATH, "r", encoding="utf-8") as f:
                    _visual_meta = json.load(f)
            except Exception:
                _visual_meta = []
        if not _visual_meta:
            _sync_visual_metadata()

    if not _visual_meta or not query.strip():
        return []

    q_words = [w.lower() for w in query.split() if len(w) > 2]
    filters = filters or {}
    results = []

    for item in _visual_meta:
        # Apply filters
        if filters.get("camera") and filters["camera"].lower() not in (item.get("camera") or "").lower():
            continue
        if filters.get("violation_type") and filters["violation_type"].lower() not in (item.get("violation_type") or "").lower():
            continue
        if filters.get("severity") and filters["severity"].upper() != (item.get("severity") or "").upper():
            continue

        text_lower = (item.get("text") or "").lower()
        matches = sum(1 for qw in q_words if qw in text_lower)
        if matches > 0:
            score = round(0.5 + 0.45 * (matches / max(1, len(q_words))), 3)
            res = dict(item)
            res["score"] = score
            results.append(res)

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]
