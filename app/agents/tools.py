'''Utility tools that LangGraph agents may call.
All functions catch exceptions and return JSON‑serialisable results suitable for
storing in the ``agent_steps`` table.
''' 

import logging
from typing import List, Optional, Tuple

from app.db import execute_query
from app.rag.retriever import retrieve
from app.rag.visual_indexer import search_visual_events

logger = logging.getLogger(__name__)


def get_violation(v_id: int) -> dict:
    """Return a violation record as a dict or an empty dict if not found."""
    try:
        rows = execute_query(
            "SELECT * FROM violations WHERE id = %s", (v_id,), fetch=True
        )
        return dict(rows[0]) if rows else {}
    except Exception as e:
        logger.exception("get_violation error")
        return {}


def search_knowledge(query: str, filters: Optional[dict] = None) -> List[dict]:
    """Wrapper around the unified retriever used by the assistant.
    Returns a list of source dicts.
    """
    try:
        sources = retrieve(query, top_k=6, filters=filters)
        # Convert Source objects to plain dicts
        return [s.to_dict() for s in sources]
    except Exception as e:
        logger.exception("search_knowledge error")
        return []


def find_similar_events(violation_id: int, days: int = 30) -> List[dict]:
    """SQL query for events with the same type within ``days``."""
    try:
        v = get_violation(violation_id)
        if not v:
            return []
        v_type = v.get("violation_type")
        rows = execute_query(
            """
            SELECT * FROM violations
            WHERE violation_type = %s
              AND id != %s
            ORDER BY id DESC
            LIMIT 10
            """,
            (v_type, violation_id),
            fetch=True,
        )
        return [dict(r) for r in rows]
    except Exception as e:
        logger.exception("find_similar_events error")
        return []


def find_related_findings(category: str, from_date: str = "", to_date: str = "") -> List[dict]:
    """Return open findings matching ``category`` from report_findings table."""
    try:
        rows = execute_query(
            """
            SELECT * FROM report_findings
            WHERE (category = %s OR description LIKE %s)
              AND status = 'open'
            LIMIT 10
            """,
            (category, f"%{category}%"),
            fetch=True,
        )
        return [dict(r) for r in rows]
    except Exception as e:
        logger.exception("find_related_findings error")
        return []


def violation_stats(date_from: str, date_to: str, v_type: Optional[str] = None, camera: Optional[str] = None) -> dict:
    """Aggregate statistics for violations.
    Returns total count, distinct cameras, and optional type filter.
    """
    try:
        sql = "SELECT COUNT(*) as total, COUNT(DISTINCT camera) as cameras FROM violations WHERE detected_at BETWEEN %s AND %s"
        params = [date_from, date_to]
        if v_type:
            sql += " AND violation_type = %s"
            params.append(v_type)
        if camera:
            sql += " AND camera = %s"
            params.append(camera)
        rows = execute_query(sql, tuple(params), fetch=True)
        return dict(rows[0]) if rows else {}
    except Exception as e:
        logger.exception("violation_stats error")
        return {}


def compliance_trend(days: int = 30) -> List[Tuple[str, int]]:
    """Return a list of (date, violation_count) for the past ``days``.
    Used for dashboard graphs.
    """
    try:
        rows = execute_query(
            """
            SELECT DATE(detected_at) as day, COUNT(*) as cnt
            FROM violations
            WHERE detected_at >= datetime('now', ?)
            GROUP BY day
            ORDER BY day ASC
            """,
            (f"-{days} days",),
            fetch=True,
        )
        return [(r["day"], r["cnt"]) for r in rows]
    except Exception as e:
        logger.exception("compliance_trend error")
        return []


def open_findings(severity: Optional[str] = None) -> List[dict]:
    """Return all open findings, optionally filtered by severity.
    """
    try:
        sql = "SELECT * FROM findings WHERE status = 'open'"
        params = []
        if severity:
            sql += " AND severity = %s"
            params.append(severity)
        rows = execute_query(sql, tuple(params) if params else None, fetch=True)
        return [dict(r) for r in rows]
    except Exception as e:
        logger.exception("open_findings error")
        return []


def update_violation_status(v_id: int, status: str, notes: str = "", reviewed_by: str = "system") -> bool:
    """Update a violation's status. Returns ``True`` on success.
    The function is safe – it uses a parameterised query.
    """
    try:
        execute_query(
            "UPDATE violations SET status = %s, notes = %s, reviewed_by = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
            (status, notes, reviewed_by, v_id),
            commit=True
        )
        return True
    except Exception as e:
        logger.exception("update_violation_status error")
        return False


def generate_incident_pdf(run_id: str) -> Optional[str]:
    """Call the PDF service and return the absolute path to the generated file.
    ``None`` indicates failure.
    """
    try:
        from app.services.incident_report_pdf import generate_report
        return generate_report(run_id)
    except Exception as e:
        logger.exception("generate_incident_pdf error")
        return None
